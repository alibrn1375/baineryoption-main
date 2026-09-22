"""Price Ladder generator grouping trades into discrete price levels based on configurable tick size."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional
from app.models.footprint import PriceLevel
from app.models.tick import TradeSide


class PriceLadder:
    """Manages volume accumulation per discrete price level with strict tick size discretization."""

    def __init__(self, tick_size: float = 0.1, price_precision: int = 1) -> None:
        self.tick_size = tick_size
        self.price_precision = price_precision
        # Dict mapping rounded discrete price -> mutable accumulators [bid_vol, ask_vol, unknown_vol]
        self._levels: Dict[float, List[float]] = {}

    def round_to_tick(self, price: float) -> float:
        """Discretize raw price to the exact configured instrument tick size grid."""
        # Use Decimal to avoid floating point precision artifacts (e.g. 2750.1000000000004)
        dec_price = Decimal(str(price))
        dec_tick = Decimal(str(self.tick_size))
        
        # Calculate number of ticks and quantize
        num_ticks = (dec_price / dec_tick).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        rounded = float(num_ticks * dec_tick)
        return round(rounded, self.price_precision)

    def add_trade(self, price: float, volume: float, side: TradeSide) -> None:
        """Accumulate trade volume at the corresponding price level."""
        discrete_price = self.round_to_tick(price)
        if discrete_price not in self._levels:
            self._levels[discrete_price] = [0.0, 0.0, 0.0]  # [bid_vol, ask_vol, unknown_vol]

        if side == TradeSide.BUY:
            self._levels[discrete_price][1] += volume
        elif side == TradeSide.SELL:
            self._levels[discrete_price][0] += volume
        else:
            self._levels[discrete_price][2] += volume

    def build_levels(self) -> List[PriceLevel]:
        """Construct sorted list of immutable PriceLevel domain objects."""
        sorted_prices = sorted(self._levels.keys())
        price_levels: List[PriceLevel] = []

        for p in sorted_prices:
            bid_vol, ask_vol, unk_vol = self._levels[p]
            lvl = PriceLevel(
                price=p,
                bid_volume=round(bid_vol, 4),
                ask_volume=round(ask_vol, 4),
                unknown_volume=round(unk_vol, 4),
                total_volume=round(bid_vol + ask_vol + unk_vol, 4),
                delta=round(ask_vol - bid_vol, 4)
            )
            price_levels.append(lvl)

        return price_levels

    def get_poc_price(self) -> Optional[float]:
        """Find the Point of Control (POC) price level possessing the highest total volume."""
        if not self._levels:
            return None
        return max(self._levels.keys(), key=lambda p: sum(self._levels[p]))

    def clear(self) -> None:
        """Reset internal accumulator dictionary."""
        self._levels.clear()
