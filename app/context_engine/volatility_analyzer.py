"""Volatility Analyzer measuring ATR, range expansion percentiles, and candle efficiency."""

from collections import deque
from typing import Deque, List, Optional
import numpy as np

from app.models.footprint import FootprintBar
from app.models.market_context import VolatilityLevel, VolatilityState


class VolatilityAnalyzer:
    """Measures rolling statistical volatility conditions and candle progression efficiency."""

    def __init__(self, period: int = 14, lookback_history: int = 50) -> None:
        self.period = period
        self.lookback_history = lookback_history
        self._true_ranges: Deque[float] = deque(maxlen=self.lookback_history)
        self._prev_close: Optional[float] = None

    def reset(self) -> None:
        """Reset internal volatility buffer."""
        self._true_ranges.clear()
        self._prev_close = None

    def analyze(self, bar: FootprintBar) -> VolatilityState:
        """Compute True Range, rolling ATR, historical percentile, and candle efficiency."""
        high = bar.high
        low = bar.low
        close = bar.close

        # Compute True Range
        if self._prev_close is not None:
            tr = max(high - low, abs(high - self._prev_close), abs(low - self._prev_close))
        else:
            tr = high - low

        self._prev_close = close
        self._true_ranges.append(tr)

        # ATR calculation over last `period` samples
        tr_list = list(self._true_ranges)
        atr_samples = tr_list[-self.period:] if len(tr_list) >= self.period else tr_list
        atr_value = float(np.mean(atr_samples)) if atr_samples else tr

        # Percentile rank within historical True Ranges
        if len(tr_list) >= 5:
            pct = float(np.sum(np.array(tr_list) < tr) / len(tr_list) * 100.0)
        else:
            pct = 50.0

        # Classify Volatility Level
        if pct >= 90.0:
            level = VolatilityLevel.EXTREME
        elif pct >= 70.0:
            level = VolatilityLevel.HIGH
        elif pct <= 20.0:
            level = VolatilityLevel.LOW
        else:
            level = VolatilityLevel.NORMAL

        # Candle efficiency: Body progression vs total range
        bar_range = high - low
        body_progression = abs(close - bar.open)
        efficiency = (body_progression / bar_range) if bar_range > 0 else 1.0

        return VolatilityState(
            level=level,
            percentile=round(pct, 1),
            atr_value=round(atr_value, 3),
            candle_efficiency=round(efficiency, 2)
        )
