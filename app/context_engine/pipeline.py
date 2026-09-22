"""Market Context Engine Pipeline synthesizing all environmental observations into a unified MarketContext."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from app.context_engine.liquidity_engine import LiquidityEngine
from app.context_engine.liquidity_sweep import LiquiditySweepDetector
from app.context_engine.news_guard import NewsGuard
from app.context_engine.regime_detector import RegimeDetector
from app.context_engine.session_detector import SessionDetector
from app.context_engine.structure_analyzer import StructureAnalyzer
from app.context_engine.swing_detector import SwingDetector
from app.context_engine.volatility_analyzer import VolatilityAnalyzer
from app.core.exceptions import ConfigurationError
from app.models.footprint import FootprintBar
from app.models.market_context import MarketContext
from app.storage.context_storage import ContextStorage


class MarketContextPipeline:
    """Orchestrates market structure, liquidity analysis, regime, session, volatility, and news filtering."""

    def __init__(
        self,
        config_path: str = "configs/base_config.yaml",
        storage: Optional[ContextStorage] = None
    ) -> None:
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.storage = storage or ContextStorage()

        ctx_cfg = self.config.get("context", {})
        struct_cfg = ctx_cfg.get("structure", {})
        liq_cfg = ctx_cfg.get("liquidity", {})
        regime_cfg = ctx_cfg.get("regime", {})
        session_cfg = ctx_cfg.get("session", {})
        news_cfg = ctx_cfg.get("news", {})

        # Subsystems
        self.swing_detector = SwingDetector(swing_length=int(struct_cfg.get("swing_length", 3)))
        self.structure_analyzer = StructureAnalyzer(
            swing_detector=self.swing_detector,
            bos_min_ticks=int(struct_cfg.get("bos_min_ticks", 2))
        )
        self.liquidity_engine = LiquidityEngine(
            tolerance_ticks=int(liq_cfg.get("tolerance_ticks", 3))
        )
        self.sweep_detector = LiquiditySweepDetector(
            sweep_rejection_pct=float(liq_cfg.get("sweep_rejection_pct", 0.40))
        )
        self.regime_detector = RegimeDetector(
            volatility_window=int(regime_cfg.get("volatility_window", 20))
        )
        self.session_detector = SessionDetector(
            timezone_str=session_cfg.get("timezone", "UTC"),
            session_config=session_cfg.get("sessions")
        )
        self.volatility_analyzer = VolatilityAnalyzer()
        self.news_guard = NewsGuard(
            quarantine_before_minutes=int(news_cfg.get("quarantine_before_minutes", 15)),
            quarantine_after_minutes=int(news_cfg.get("quarantine_after_minutes", 20))
        )

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration."""
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return {}

    def process_bar(self, bar: FootprintBar) -> MarketContext:
        """Process FootprintBar through all context layers and synthesize MarketContext."""
        # 1. Structure Analysis
        structure_state = self.structure_analyzer.analyze_bar(bar)

        # 2. Liquidity Updating
        recent_swings = self.swing_detector.get_recent_swings(count=15)
        active_zones = self.liquidity_engine.update_liquidity(recent_swings)

        # 3. Liquidity Sweep Detection
        liq_event, updated_zones = self.sweep_detector.evaluate_bar(bar, active_zones)

        # 4. Volatility Analysis
        vol_state = self.volatility_analyzer.analyze(bar)

        # 5. Regime Detection
        regime = self.regime_detector.detect_regime(bar, structure_state.current_state, vol_state.atr_value)

        # 6. Session Detection
        session = self.session_detector.detect_session(bar.start_time)

        # 7. News Quarantine Evaluation
        news_state = self.news_guard.evaluate_news_state(bar.start_time)

        # 8. Composite Context
        context = MarketContext(
            timestamp=bar.start_time,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            structure=structure_state,
            active_liquidity_zones=updated_zones,
            recent_liquidity_event=liq_event,
            regime=regime,
            session=session,
            volatility=vol_state,
            news=news_state,
            data_quality=bar.quality,
            overall_confidence=1.0 if not news_state.blocked else 0.2
        )

        # Persist context snapshot
        self.storage.save_context(context)

        return context
