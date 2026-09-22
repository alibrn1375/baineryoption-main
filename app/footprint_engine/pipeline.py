"""End-to-end Footprint Processing Pipeline orchestrating ticks, bars, CVD, and storage."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
import yaml

from app.core.exceptions import ConfigurationError
from app.core.logging import app_logger, log_event
from app.footprint_engine.bar_aggregator import BarAggregator
from app.footprint_engine.cvd_engine import CVDEngine
from app.footprint_engine.storage import FootprintStorage
from app.models.footprint import CVDPoint, FootprintBar
from app.models.tick import Tick


class FootprintPipeline:
    """Orchestrates stream-based or batch tick processing into completed FootprintBars and CVDPoints."""

    def __init__(
        self,
        config_path: str = "configs/orderflow_config.yaml",
        storage: Optional[FootprintStorage] = None
    ) -> None:
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.storage = storage or FootprintStorage()

        # Extract config params dynamically (no hardcoded defaults)
        self.instruments_cfg: Dict[str, Any] = self.config.get("instruments", {})
        self.footprint_cfg: Dict[str, Any] = self.config.get("footprint", {})
        self.sessions_cfg: Dict[str, Any] = self.config.get("sessions", {})

        self.cvd_engine = CVDEngine(sessions_config=self.sessions_cfg)
        self._aggregators: Dict[str, BarAggregator] = {}

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration."""
        if not self.config_path.exists():
            raise ConfigurationError(f"Config file not found at {self.config_path}")
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to read config {self.config_path}: {e}") from e

    def _get_or_create_aggregator(self, symbol: str) -> BarAggregator:
        """Instantiate aggregator with symbol-specific tick size and price precision from config."""
        sym_upper = symbol.upper()
        if sym_upper not in self._aggregators:
            inst_cfg = self.instruments_cfg.get(sym_upper, {})
            tick_size = float(inst_cfg.get("tick_size", 0.01))
            price_precision = int(inst_cfg.get("price_precision", 2))
            tf_sec = int(self.footprint_cfg.get("timeframe_seconds", 300))
            tf_str = str(self.footprint_cfg.get("timeframe", "5m"))

            self._aggregators[sym_upper] = BarAggregator(
                symbol=sym_upper,
                timeframe_seconds=tf_sec,
                tick_size=tick_size,
                price_precision=price_precision,
                timeframe_str=tf_str
            )
        return self._aggregators[sym_upper]

    def process_tick(self, tick: Tick) -> tuple[Optional[FootprintBar], Optional[CVDPoint]]:
        """Process a single tick in live or sequential replay mode.
        
        Returns:
            (FootprintBar, CVDPoint) if a bar was completed on this tick, otherwise (None, None).
        """
        aggregator = self._get_or_create_aggregator(tick.symbol)
        completed_bar = aggregator.add_tick(tick)

        cvd_point: Optional[CVDPoint] = None
        if completed_bar:
            cvd_point = self.cvd_engine.update(
                symbol=completed_bar.symbol,
                timestamp=completed_bar.start_time,
                bar_delta=completed_bar.bar_delta
            )
            # Auto-persist if storage is active
            self.storage.save_footprint_bars([completed_bar])
            self.storage.save_cvd_points([cvd_point])

        return completed_bar, cvd_point

    def process_ticks_batch(self, ticks: List[Tick]) -> List[FootprintBar]:
        """Process a sequence of ticks (e.g. historical replay or batch processing)."""
        completed_bars: List[FootprintBar] = []
        cvd_points: List[CVDPoint] = []

        for t in ticks:
            bar, cvd = self.process_tick(t)
            if bar:
                completed_bars.append(bar)
            if cvd:
                cvd_points.append(cvd)

        # Flush any remaining partial bar at the end of the batch
        for sym, agg in self._aggregators.items():
            final_bar = agg.finalize_bar()
            if final_bar:
                cvd = self.cvd_engine.update(
                    symbol=final_bar.symbol,
                    timestamp=final_bar.start_time,
                    bar_delta=final_bar.bar_delta
                )
                completed_bars.append(final_bar)
                cvd_points.append(cvd)

        if completed_bars:
            self.storage.save_footprint_bars(completed_bars)
        if cvd_points:
            self.storage.save_cvd_points(cvd_points)

        return completed_bars
