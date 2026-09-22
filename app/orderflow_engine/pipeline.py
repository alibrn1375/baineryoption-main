"""Order Flow Feature Pipeline orchestrating multi-sensor feature extraction from Footprint bars."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.core.exceptions import ConfigurationError
from app.models.footprint import FootprintBar
from app.models.orderflow_context import OrderFlowContext
from app.models.orderflow_features import (
    AbsorptionFeature,
    DeltaFeature,
    ExhaustionFeature,
    ImbalanceFeature,
    StackedImbalanceFeature,
)
from app.orderflow_engine.absorption_detector import AbsorptionDetector
from app.orderflow_engine.base import FeatureDirection
from app.orderflow_engine.delta_analyzer import DeltaAnalyzer
from app.orderflow_engine.exhaustion_detector import ExhaustionDetector
from app.orderflow_engine.imbalance_detector import ImbalanceDetector
from app.orderflow_engine.stacked_imbalance import StackedImbalanceDetector
from app.storage.orderflow_storage import OrderFlowStorage


class OrderFlowFeaturePipeline:
    """Multi-sensor pipeline transforming FootprintBar data into unified OrderFlowContext snapshots."""

    def __init__(
        self,
        config_path: str = "configs/orderflow_config.yaml",
        storage: Optional[OrderFlowStorage] = None
    ) -> None:
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.storage = storage or OrderFlowStorage()

        of_cfg = self.config.get("orderflow", {})
        inst_cfg = self.config.get("instruments", {})

        # 1. Delta Analyzer
        delta_cfg = of_cfg.get("delta", {})
        self.delta_analyzer = DeltaAnalyzer(
            lookback_period=int(delta_cfg.get("lookback_period", 20)),
            extreme_percentile_high=float(delta_cfg.get("extreme_percentile_high", 90.0)),
            extreme_percentile_low=float(delta_cfg.get("extreme_percentile_low", 10.0)),
            min_samples=int(delta_cfg.get("min_samples", 5))
        )

        # 2. Imbalance Detector
        imb_cfg = of_cfg.get("imbalance", {})
        self.imbalance_detector = ImbalanceDetector(
            ratio_threshold=float(imb_cfg.get("ratio_threshold", 3.0)),
            minimum_volume=float(imb_cfg.get("minimum_volume", 10.0)),
            minimum_delta=float(imb_cfg.get("minimum_delta", 5.0))
        )

        # 3. Stacked Imbalance Detector
        stk_cfg = of_cfg.get("stacked_imbalance", {})
        self.stacked_detector = StackedImbalanceDetector(
            min_consecutive_levels=int(stk_cfg.get("min_consecutive_levels", 3)),
            max_level_gap_ticks=int(stk_cfg.get("max_level_gap_ticks", 1)),
            imbalance_detector=self.imbalance_detector
        )

        # 4. Absorption Detector
        abs_cfg = of_cfg.get("absorption", {})
        self.absorption_detector = AbsorptionDetector(
            volume_percentile_threshold=float(abs_cfg.get("volume_percentile_threshold", 80.0)),
            price_efficiency_max=float(abs_cfg.get("price_efficiency_max", 0.35)),
            rejection_return_pct=float(abs_cfg.get("rejection_return_pct", 0.40)),
            min_absorption_volume=float(abs_cfg.get("min_absorption_volume", 50.0))
        )

        # 5. Exhaustion Detector
        exh_cfg = of_cfg.get("exhaustion", {})
        self.exhaustion_detector = ExhaustionDetector(
            delta_drop_ratio=float(exh_cfg.get("delta_drop_ratio", 0.50)),
            thin_volume_threshold=float(exh_cfg.get("thin_volume_threshold", 0.30)),
            lookback_period=int(exh_cfg.get("lookback_period", 10))
        )

        self.instruments_cfg = inst_cfg

    def _load_config(self) -> Dict[str, Any]:
        """Load orderflow configuration."""
        if not self.config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {self.config_path}")
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to read {self.config_path}: {e}") from e

    def process_bar(self, bar: FootprintBar) -> OrderFlowContext:
        """Process a single completed FootprintBar and generate comprehensive OrderFlowContext."""
        # 1. Delta Analysis
        delta_feat = self.delta_analyzer.analyze(bar)

        # 2. Imbalance Detection
        imbalances = self.imbalance_detector.detect_imbalances(bar)

        # 3. Stacked Imbalance Detection
        sym_cfg = self.instruments_cfg.get(bar.symbol.upper(), {})
        tick_size = float(sym_cfg.get("tick_size", 0.1))
        stacked_imbalances = self.stacked_detector.detect_stacked(
            bar=bar,
            tick_size=tick_size,
            existing_imbalances=imbalances
        )

        # 4. Absorption Detection
        absorption_feat = self.absorption_detector.detect(bar)

        # 5. Exhaustion Detection
        exhaustion_feat = self.exhaustion_detector.detect(bar)

        # 6. Synthesize Dominant Direction (Purely Descriptive Observation)
        dominant_direction = FeatureDirection.NEUTRAL
        if stacked_imbalances:
            dominant_direction = stacked_imbalances[0].direction
        elif delta_feat.direction != FeatureDirection.NEUTRAL:
            dominant_direction = delta_feat.direction

        context = OrderFlowContext(
            timestamp=bar.start_time,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            delta_feature=delta_feat,
            imbalances=imbalances,
            stacked_imbalances=stacked_imbalances,
            absorption_feature=absorption_feat,
            exhaustion_feature=exhaustion_feat,
            dominant_direction=dominant_direction,
            quality=bar.quality,
            telemetry={
                "levels_count": len(bar.levels),
                "total_volume": bar.total_volume,
                "bar_delta": bar.bar_delta
            }
        )

        # Persist context snapshot
        self.storage.save_context(context)

        return context
