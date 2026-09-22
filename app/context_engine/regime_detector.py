"""Market Regime detection engine classifying Trending, Ranging, and Volatility states."""

from collections import deque
from typing import Deque, List, Optional
import numpy as np

from app.models.footprint import FootprintBar
from app.models.market_context import MarketRegime, MarketRegimeState
from app.models.market_structure import StructureState


class RegimeDetector:
    """Classifies current market environment into empirical structural and volatility regimes."""

    def __init__(self, volatility_window: int = 20, trend_threshold_ratio: float = 1.8) -> None:
        self.volatility_window = volatility_window
        self.trend_threshold_ratio = trend_threshold_ratio
        self._ranges: Deque[float] = deque(maxlen=self.volatility_window)

    def reset(self) -> None:
        """Reset internal rolling state."""
        self._ranges.clear()

    def detect_regime(
        self,
        bar: FootprintBar,
        structure_state: StructureState,
        atr_value: float = 2.0
    ) -> MarketRegime:
        """Classify current market regime combining structural state and range expansion metrics."""
        bar_range = bar.high - bar.low
        self._ranges.append(bar_range)

        hist_ranges = list(self._ranges)
        mean_range = float(np.mean(hist_ranges)) if hist_ranges else bar_range

        # Range expansion ratio
        range_ratio = bar_range / mean_range if mean_range > 0 else 1.0

        state = MarketRegimeState.TRANSITION
        strength = 1.0

        if structure_state == StructureState.TREND_UP:
            state = MarketRegimeState.TRENDING_BULLISH
            strength = round(range_ratio, 2)
        elif structure_state == StructureState.TREND_DOWN:
            state = MarketRegimeState.TRENDING_BEARISH
            strength = round(range_ratio, 2)
        elif structure_state == StructureState.RANGE:
            state = MarketRegimeState.RANGING
            strength = 1.0
        elif range_ratio >= self.trend_threshold_ratio:
            state = MarketRegimeState.HIGH_VOLATILITY
            strength = round(range_ratio, 2)
        elif range_ratio <= 0.5:
            state = MarketRegimeState.LOW_VOLATILITY
            strength = 0.5

        return MarketRegime(
            state=state,
            strength=strength,
            confidence=1.0 if bar.quality.value == "HIGH_PRECISION" else 0.5,
            metrics={
                "bar_range": round(bar_range, 3),
                "mean_range": round(mean_range, 3),
                "range_expansion_ratio": round(range_ratio, 2),
                "atr_value": round(atr_value, 3)
            }
        )
