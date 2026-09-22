"""Liquidity Engine identifying resting liquidity clusters (Equal Highs, Equal Lows, Session Bounds)."""

from datetime import datetime
from typing import List, Optional
from app.context_engine.swing_detector import SwingDetector
from app.models.footprint import FootprintBar
from app.models.liquidity import LiquidityZone, LiquidityZoneType
from app.models.market_structure import SwingPoint, SwingType


class LiquidityEngine:
    """Detects resting liquidity clusters formed by equal highs, equal lows, and range extremes."""

    def __init__(
        self,
        tolerance_ticks: int = 3,
        tick_size: float = 0.10,
        max_active_zones: int = 20
    ) -> None:
        self.tolerance_ticks = tolerance_ticks
        self.tick_size = tick_size
        self.max_active_zones = max_active_zones
        self.tolerance_distance = tolerance_ticks * tick_size

        self._active_zones: List[LiquidityZone] = []

    def reset(self) -> None:
        """Reset internal liquidity zones."""
        self._active_zones.clear()

    def update_liquidity(self, recent_swings: List[SwingPoint]) -> List[LiquidityZone]:
        """Cluster recent swings to discover Equal Highs and Equal Lows."""
        if len(recent_swings) < 2:
            return list(self._active_zones)

        highs = [s for s in recent_swings if s.type == SwingType.SWING_HIGH]
        lows = [s for s in recent_swings if s.type == SwingType.SWING_LOW]

        discovered_zones: List[LiquidityZone] = []

        # 1. Cluster Equal Highs (Buy-side liquidity)
        for i in range(len(highs)):
            for j in range(i + 1, len(highs)):
                h1, h2 = highs[i], highs[j]
                if abs(h1.price - h2.price) <= self.tolerance_distance:
                    avg_price = (h1.price + h2.price) / 2.0
                    zone = LiquidityZone(
                        price=round(avg_price, 2),
                        upper_price=round(avg_price + self.tolerance_distance, 2),
                        lower_price=round(avg_price - self.tolerance_distance, 2),
                        zone_type=LiquidityZoneType.EQUAL_HIGHS,
                        strength=2.0,
                        created_time=h2.confirmed_timestamp,
                        touch_count=2,
                        is_mitigated=False
                    )
                    discovered_zones.append(zone)

        # 2. Cluster Equal Lows (Sell-side liquidity)
        for i in range(len(lows)):
            for j in range(i + 1, len(lows)):
                l1, l2 = lows[i], lows[j]
                if abs(l1.price - l2.price) <= self.tolerance_distance:
                    avg_price = (l1.price + l2.price) / 2.0
                    zone = LiquidityZone(
                        price=round(avg_price, 2),
                        upper_price=round(avg_price + self.tolerance_distance, 2),
                        lower_price=round(avg_price - self.tolerance_distance, 2),
                        zone_type=LiquidityZoneType.EQUAL_LOWS,
                        strength=2.0,
                        created_time=l2.confirmed_timestamp,
                        touch_count=2,
                        is_mitigated=False
                    )
                    discovered_zones.append(zone)

        # Keep unmitigated zones up to max limit
        self._active_zones = [z for z in discovered_zones if not z.is_mitigated][-self.max_active_zones:]
        return list(self._active_zones)

    def add_session_boundary(self, high: float, low: float, timestamp: datetime) -> None:
        """Add Prior Session High and Low as prime liquidity levels."""
        sh_zone = LiquidityZone(
            price=round(high, 2),
            upper_price=round(high + self.tolerance_distance, 2),
            lower_price=round(high - self.tolerance_distance, 2),
            zone_type=LiquidityZoneType.SESSION_HIGH,
            strength=3.0,
            created_time=timestamp,
            touch_count=1,
            is_mitigated=False
        )
        sl_zone = LiquidityZone(
            price=round(low, 2),
            upper_price=round(low + self.tolerance_distance, 2),
            lower_price=round(low - self.tolerance_distance, 2),
            zone_type=LiquidityZoneType.SESSION_LOW,
            strength=3.0,
            created_time=timestamp,
            touch_count=1,
            is_mitigated=False
        )
        self._active_zones.extend([sh_zone, sl_zone])
