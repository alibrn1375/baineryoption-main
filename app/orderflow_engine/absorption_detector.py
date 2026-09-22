"""Quantitative Absorption detector identifying aggressive order absorption by passive liquidity."""

from collections import deque
from typing import Deque, Optional
import numpy as np

from app.models.footprint import FootprintBar
from app.models.orderflow_features import AbsorptionFeature
from app.orderflow_engine.base import FeatureDirection


class AbsorptionDetector:
    """Detects institutional absorption when heavy aggressive volume fails to make price progress."""

    def __init__(
        self,
        volume_percentile_threshold: float = 80.0,
        price_efficiency_max: float = 0.35,
        rejection_return_pct: float = 0.40,
        min_absorption_volume: float = 50.0,
        lookback_period: int = 20
    ) -> None:
        self.vol_pct_thresh = volume_percentile_threshold
        self.price_efficiency_max = price_efficiency_max
        self.rejection_return_pct = rejection_return_pct
        self.min_volume = min_absorption_volume
        self.lookback_period = lookback_period

        self._volume_history: Deque[float] = deque(maxlen=self.lookback_period)

    def reset(self) -> None:
        """Reset internal history."""
        self._volume_history.clear()

    def detect(self, bar: FootprintBar) -> Optional[AbsorptionFeature]:
        """Evaluate FootprintBar for quantitative absorption behavior."""
        total_vol = bar.total_volume
        bar_range = bar.high - bar.low
        body_range = abs(bar.close - bar.open)

        # Update historical volume
        vol_hist = list(self._volume_history)
        self._volume_history.append(total_vol)

        # Require minimal volume baseline
        if total_vol < self.min_volume:
            return None

        # 1. Volume Condition: Is volume historically elevated?
        is_elevated_volume = True
        if len(vol_hist) >= 5:
            vol_pct = float(np.sum(np.array(vol_hist) < total_vol) / len(vol_hist) * 100.0)
            if vol_pct < self.vol_pct_thresh:
                is_elevated_volume = False

        if not is_elevated_volume:
            return None

        # 2. Price Inefficiency: High volume but disproportionately small price progression
        # Efficiency = Price Progress (Body) / Total Volume
        efficiency = (body_range / total_vol) * 100.0 if total_vol > 0 else 0.0

        # 3. Direction and Rejection Condition
        # BUY Absorption: Heavy buy aggression at high of bar, but price closes lower (Upper Wick rejection)
        # SELL Absorption: Heavy sell aggression at low of bar, but price closes higher (Lower Wick rejection)
        upper_wick = bar.high - max(bar.open, bar.close)
        lower_wick = min(bar.open, bar.close) - bar.low

        upper_wick_ratio = (upper_wick / bar_range) if bar_range > 0 else 0.0
        lower_wick_ratio = (lower_wick / bar_range) if bar_range > 0 else 0.0

        absorption_direction: Optional[FeatureDirection] = None
        rejection_score = 0.0
        absorbed_level = None

        # Scenario A: Buying Absorption (Buyers trapped/absorbed by passive sellers at highs)
        if bar.bar_delta > 0 and upper_wick_ratio >= self.rejection_return_pct:
            absorption_direction = FeatureDirection.BUY
            rejection_score = upper_wick_ratio
            absorbed_level = bar.high

        # Scenario B: Selling Absorption (Sellers trapped/absorbed by passive buyers at lows)
        elif bar.bar_delta < 0 and lower_wick_ratio >= self.rejection_return_pct:
            absorption_direction = FeatureDirection.SELL
            rejection_score = lower_wick_ratio
            absorbed_level = bar.low

        # Scenario C: Inefficient bar with delta divergence (e.g. positive delta, red candle)
        elif bar.bar_delta > 0 and bar.close < bar.open and efficiency <= self.price_efficiency_max:
            absorption_direction = FeatureDirection.BUY
            rejection_score = upper_wick_ratio
            absorbed_level = bar.high
        elif bar.bar_delta < 0 and bar.close > bar.open and efficiency <= self.price_efficiency_max:
            absorption_direction = FeatureDirection.SELL
            rejection_score = lower_wick_ratio
            absorbed_level = bar.low

        if absorption_direction is None:
            return None

        # Composite absorption score [0.0, 1.0]
        absorption_score = min(1.0, (rejection_score * 0.5) + (max(0.0, 1.0 - efficiency) * 0.5))
        confidence = 1.0 if bar.quality.value == "HIGH_PRECISION" else 0.5

        return AbsorptionFeature(
            timestamp=bar.start_time,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            direction=absorption_direction,
            confidence=confidence,
            calculation_version="1.0.0",
            aggressive_volume=round(total_vol, 4),
            price_progress=round(bar_range, 4),
            range_efficiency=round(efficiency, 4),
            rejection_score=round(rejection_score, 2),
            absorption_score=round(absorption_score, 2),
            absorbed_price_level=absorbed_level,
            details={
                "upper_wick_ratio": round(upper_wick_ratio, 2),
                "lower_wick_ratio": round(lower_wick_ratio, 2),
                "bar_delta": bar.bar_delta,
                "poc_price": bar.poc_price
            }
        )
