"""Exhaustion detector identifying fading momentum and failed follow-through after aggressive volume peaks."""

from collections import deque
from typing import Deque, Optional
from app.models.footprint import FootprintBar
from app.models.orderflow_features import ExhaustionFeature
from app.orderflow_engine.base import FeatureDirection


class ExhaustionDetector:
    """Detects order flow exhaustion where an extreme aggressive burst fails to continue or expand range."""

    def __init__(
        self,
        delta_drop_ratio: float = 0.50,
        thin_volume_threshold: float = 0.30,
        lookback_period: int = 10
    ) -> None:
        self.delta_drop_ratio = delta_drop_ratio
        self.thin_volume_threshold = thin_volume_threshold
        self.lookback_period = lookback_period

        # Rolling state
        self._prev_bar: Optional[FootprintBar] = None

    def reset(self) -> None:
        """Reset internal sequential state."""
        self._prev_bar = None

    def detect(self, current_bar: FootprintBar) -> Optional[ExhaustionFeature]:
        """Compare current FootprintBar with previous bar to measure exhaustion dynamics."""
        if self._prev_bar is None:
            self._prev_bar = current_bar
            return None

        prev = self._prev_bar
        curr = current_bar
        self._prev_bar = curr  # Update for next cycle

        # Scenario 1: Buying Exhaustion
        # Previous bar had large positive delta, but current bar exhibits severe delta depletion/collapse at new high
        if prev.bar_delta > 0 and curr.high >= prev.high:
            prev_delta = prev.bar_delta
            curr_delta = curr.bar_delta
            delta_drop = (prev_delta - curr_delta) / prev_delta if prev_delta > 0 else 0.0

            # Failed follow-through condition (Delta collapsed > threshold or reversed)
            if delta_drop >= self.delta_drop_ratio or curr_delta <= 0:
                score = min(1.0, max(0.1, delta_drop))
                return ExhaustionFeature(
                    timestamp=curr.start_time,
                    symbol=curr.symbol,
                    timeframe=curr.timeframe,
                    direction=FeatureDirection.BUY,
                    confidence=1.0 if curr.quality.value == "HIGH_PRECISION" else 0.5,
                    calculation_version="1.0.0",
                    extreme_volume=round(prev.total_volume, 4),
                    current_volume=round(curr.total_volume, 4),
                    delta_depletion_ratio=round(delta_drop, 2),
                    follow_through_failed=True,
                    exhaustion_score=round(score, 2),
                    details={
                        "prev_delta": prev.bar_delta,
                        "curr_delta": curr.bar_delta,
                        "type": "BUYING_EXHAUSTION"
                    }
                )

        # Scenario 2: Selling Exhaustion
        # Previous bar had large negative delta, but current bar exhibits severe delta depletion at new low
        elif prev.bar_delta < 0 and curr.low <= prev.low:
            prev_abs_delta = abs(prev.bar_delta)
            curr_sell_delta = abs(curr.bar_delta) if curr.bar_delta < 0 else 0.0
            delta_drop = (prev_abs_delta - curr_sell_delta) / prev_abs_delta if prev_abs_delta > 0 else 0.0

            if delta_drop >= self.delta_drop_ratio or curr.bar_delta >= 0:
                score = min(1.0, max(0.1, delta_drop))
                return ExhaustionFeature(
                    timestamp=curr.start_time,
                    symbol=curr.symbol,
                    timeframe=curr.timeframe,
                    direction=FeatureDirection.SELL,
                    confidence=1.0 if curr.quality.value == "HIGH_PRECISION" else 0.5,
                    calculation_version="1.0.0",
                    extreme_volume=round(prev.total_volume, 4),
                    current_volume=round(curr.total_volume, 4),
                    delta_depletion_ratio=round(delta_drop, 2),
                    follow_through_failed=True,
                    exhaustion_score=round(score, 2),
                    details={
                        "prev_delta": prev.bar_delta,
                        "curr_delta": curr.bar_delta,
                        "type": "SELLING_EXHAUSTION"
                    }
                )

        return None
