"""Delta Intelligence Engine measuring delta strength, acceleration, persistence, and rolling percentiles."""

from collections import deque
from typing import Any, Deque, Dict, Optional
import numpy as np

from app.models.footprint import FootprintBar
from app.models.orderflow_features import DeltaFeature
from app.orderflow_engine.base import FeatureDirection


class DeltaAnalyzer:
    """Analyzes footprint delta streams without lookahead, tracking rolling statistics and behavioral shifts."""

    def __init__(
        self,
        lookback_period: int = 20,
        extreme_percentile_high: float = 90.0,
        extreme_percentile_low: float = 10.0,
        min_samples: int = 5
    ) -> None:
        self.lookback_period = lookback_period
        self.pct_high = extreme_percentile_high
        self.pct_low = extreme_percentile_low
        self.min_samples = min_samples

        # Rolling history of delta metrics
        self._history_delta: Deque[float] = deque(maxlen=self.lookback_period)
        self._last_delta: Optional[float] = None
        self._last_direction: Optional[FeatureDirection] = None
        self._persistence_count: int = 0

    def reset(self) -> None:
        """Reset internal rolling state."""
        self._history_delta.clear()
        self._last_delta = None
        self._last_direction = None
        self._persistence_count = 0

    def analyze(self, bar: FootprintBar) -> DeltaFeature:
        """Analyze the delta characteristics of a completed FootprintBar."""
        bar_delta = bar.bar_delta
        delta_pct = bar.delta_percentage

        # 1. Determine Direction
        if bar_delta > 0:
            direction = FeatureDirection.BUY
        elif bar_delta < 0:
            direction = FeatureDirection.SELL
        else:
            direction = FeatureDirection.NEUTRAL

        # 2. Delta Persistence
        if self._last_direction is not None and direction == self._last_direction and direction != FeatureDirection.NEUTRAL:
            self._persistence_count += 1
        else:
            self._persistence_count = 1 if direction != FeatureDirection.NEUTRAL else 0

        # 3. Delta Acceleration (Rate of change)
        acceleration = 0.0
        if self._last_delta is not None:
            acceleration = bar_delta - self._last_delta

        # 4. Rolling Percentile & Strength
        hist_deltas = list(self._history_delta)
        if len(hist_deltas) >= self.min_samples:
            # Calculate percentile rank of current bar_delta within historical distribution
            percentile = float(np.sum(np.array(hist_deltas) < bar_delta) / len(hist_deltas) * 100.0)
            mean_abs_delta = float(np.mean(np.abs(hist_deltas)))
            strength = abs(bar_delta) / mean_abs_delta if mean_abs_delta > 0 else 1.0
        else:
            percentile = 50.0
            strength = 1.0

        # 5. Delta Extremes Detection
        is_extreme = False
        if len(hist_deltas) >= self.min_samples:
            if percentile >= self.pct_high or percentile <= self.pct_low:
                is_extreme = True

        # Confidence based on sample depth and footprint quality
        confidence = 1.0 if bar.quality.value == "HIGH_PRECISION" else 0.5

        # Update historical state
        self._history_delta.append(bar_delta)
        self._last_delta = bar_delta
        self._last_direction = direction

        return DeltaFeature(
            timestamp=bar.start_time,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            direction=direction,
            confidence=confidence,
            calculation_version="1.0.0",
            bar_delta=round(bar_delta, 4),
            delta_percentage=round(delta_pct, 2),
            strength=round(strength, 3),
            acceleration=round(acceleration, 4),
            persistence=self._persistence_count,
            percentile=round(percentile, 1),
            is_extreme=is_extreme,
            details={
                "min_delta": bar.min_delta,
                "max_delta": bar.max_delta,
                "historical_samples": len(hist_deltas)
            }
        )
