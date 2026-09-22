"""Delta calculation engine computing bar net delta, min/max intra-bar excursions, and percentage."""

from typing import List, Tuple
from pydantic import BaseModel, Field
from app.models.footprint import PriceLevel


class DeltaResult(BaseModel):
    """Calculated delta metrics for a footprint bar."""
    total_bid_volume: float = Field(..., ge=0.0, description="Sum of aggressive sell volume")
    total_ask_volume: float = Field(..., ge=0.0, description="Sum of aggressive buy volume")
    total_unknown_volume: float = Field(default=0.0, ge=0.0, description="Sum of unclassified volume")
    total_volume: float = Field(..., ge=0.0, description="Total bar volume")
    bar_delta: float = Field(..., description="Net bar delta: Ask Volume - Bid Volume")
    min_delta: float = Field(..., description="Minimum intra-bar delta excursion")
    max_delta: float = Field(..., description="Maximum intra-bar delta excursion")
    delta_percentage: float = Field(..., description="Delta as percentage of total volume")

    model_config = {
        "frozen": True
    }


class DeltaCalculator:
    """Calculates order flow delta metrics from aggregated levels and running tick sequences."""

    @staticmethod
    def calculate_from_levels(
        levels: List[PriceLevel],
        running_min_delta: float = 0.0,
        running_max_delta: float = 0.0
    ) -> DeltaResult:
        """Compute delta result from finalized PriceLevel ladder."""
        total_bid = sum(lvl.bid_volume for lvl in levels)
        total_ask = sum(lvl.ask_volume for lvl in levels)
        total_unk = sum(lvl.unknown_volume for lvl in levels)
        total_vol = total_bid + total_ask + total_unk

        bar_delta = total_ask - total_bid
        delta_pct = (bar_delta / total_vol * 100.0) if total_vol > 0 else 0.0

        # Ensure min/max delta bound the final bar delta
        final_min = min(running_min_delta, min(0.0, bar_delta))
        final_max = max(running_max_delta, max(0.0, bar_delta))

        return DeltaResult(
            total_bid_volume=round(total_bid, 4),
            total_ask_volume=round(total_ask, 4),
            total_unknown_volume=round(total_unk, 4),
            total_volume=round(total_vol, 4),
            bar_delta=round(bar_delta, 4),
            min_delta=round(final_min, 4),
            max_delta=round(final_max, 4),
            delta_percentage=round(delta_pct, 2)
        )
