"""Liquidity sweep detector measuring price penetration and rejection across liquidity zones."""

from typing import List, Optional, Tuple
from app.models.footprint import FootprintBar
from app.models.liquidity import (
    LiquidityEvent,
    LiquidityEventType,
    LiquidityZone,
    LiquidityZoneType,
)


class LiquiditySweepDetector:
    """Detects liquidity sweep interactions where price pierces a liquidity zone and displays immediate rejection."""

    def __init__(
        self,
        sweep_rejection_pct: float = 0.40,
        tick_size: float = 0.10
    ) -> None:
        self.sweep_rejection_pct = sweep_rejection_pct
        self.tick_size = tick_size

    def evaluate_bar(
        self,
        bar: FootprintBar,
        active_zones: List[LiquidityZone]
    ) -> Tuple[Optional[LiquidityEvent], List[LiquidityZone]]:
        """Check if current FootprintBar interacted with any active liquidity zones."""
        if not active_zones:
            return None, active_zones

        detected_event: Optional[LiquidityEvent] = None
        updated_zones: List[LiquidityZone] = []

        bar_range = bar.high - bar.low
        upper_wick = bar.high - max(bar.open, bar.close)
        lower_wick = min(bar.open, bar.close) - bar.low

        upper_wick_ratio = (upper_wick / bar_range) if bar_range > 0 else 0.0
        lower_wick_ratio = (lower_wick / bar_range) if bar_range > 0 else 0.0

        for zone in active_zones:
            is_mitigated = zone.is_mitigated

            # 1. Check Sweep of High / Equal Highs / Session High (Buy-side liquidity)
            if zone.zone_type in (LiquidityZoneType.EQUAL_HIGHS, LiquidityZoneType.SESSION_HIGH, LiquidityZoneType.RANGE_HIGH):
                if bar.high >= zone.price:
                    penetration = (bar.high - zone.price) / self.tick_size
                    # Price penetrated the zone high, but closed back below the zone price (Rejection wick)
                    if bar.close <= zone.upper_price and upper_wick_ratio >= self.sweep_rejection_pct:
                        detected_event = LiquidityEvent(
                            timestamp=bar.start_time,
                            symbol=bar.symbol,
                            zone=zone,
                            event_type=LiquidityEventType.SWEEP_HIGH,
                            penetration_ticks=round(penetration, 1),
                            reaction_score=round(upper_wick_ratio, 2),
                            confidence=1.0,
                            details={
                                "zone_price": zone.price,
                                "bar_high": bar.high,
                                "bar_close": bar.close,
                                "upper_wick_ratio": round(upper_wick_ratio, 2)
                            }
                        )
                        is_mitigated = True

            # 2. Check Sweep of Low / Equal Lows / Session Low (Sell-side liquidity)
            elif zone.zone_type in (LiquidityZoneType.EQUAL_LOWS, LiquidityZoneType.SESSION_LOW, LiquidityZoneType.RANGE_LOW):
                if bar.low <= zone.price:
                    penetration = (zone.price - bar.low) / self.tick_size
                    # Price penetrated the zone low, but closed back above the zone price (Rejection wick)
                    if bar.close >= zone.lower_price and lower_wick_ratio >= self.sweep_rejection_pct:
                        detected_event = LiquidityEvent(
                            timestamp=bar.start_time,
                            symbol=bar.symbol,
                            zone=zone,
                            event_type=LiquidityEventType.SWEEP_LOW,
                            penetration_ticks=round(penetration, 1),
                            reaction_score=round(lower_wick_ratio, 2),
                            confidence=1.0,
                            details={
                                "zone_price": zone.price,
                                "bar_low": bar.low,
                                "bar_close": bar.close,
                                "lower_wick_ratio": round(lower_wick_ratio, 2)
                            }
                        )
                        is_mitigated = True

            updated_zone = LiquidityZone(
                price=zone.price,
                upper_price=zone.upper_price,
                lower_price=zone.lower_price,
                zone_type=zone.zone_type,
                strength=zone.strength,
                created_time=zone.created_time,
                touch_count=zone.touch_count + (1 if bar.low <= zone.price <= bar.high else 0),
                is_mitigated=is_mitigated
            )
            updated_zones.append(updated_zone)

        return detected_event, updated_zones
