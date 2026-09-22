"""Domain models for extracted Order Flow features."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum

from app.orderflow_engine.base import FeatureDirection, OrderFlowFeatureBase


class DeltaFeature(OrderFlowFeatureBase):
    """Measurable delta characteristics of a footprint bar."""
    feature_name: str = Field(default="delta_intelligence", description="Feature identifier")
    bar_delta: float = Field(..., description="Net bar delta: Ask Volume - Bid Volume")
    delta_percentage: float = Field(..., description="Delta percentage relative to bar total volume")
    strength: float = Field(default=0.0, ge=0.0, description="Absolute delta strength normalized or relative to historical baseline")
    acceleration: float = Field(default=0.0, description="Rate of delta change relative to prior bar (acceleration / deceleration)")
    persistence: int = Field(default=1, description="Count of consecutive bars with matching delta polarity")
    percentile: float = Field(default=50.0, ge=0.0, le=100.0, description="Rolling historical percentile rank of bar delta")
    is_extreme: bool = Field(default=False, description="True if delta exceeds upper or lower statistical extreme thresholds")
    delta_divergence: bool = Field(default=False, description="Whether delta diverges from price movement")


class ImbalanceFeature(OrderFlowFeatureBase):
    """Diagonal price level bid/ask aggressive imbalance."""
    feature_name: str = Field(default="diagonal_imbalance", description="Feature identifier")
    price_level: float = Field(default=0.0, ge=0.0, description="Price level where aggressive volume occurred")
    compared_price_level: float = Field(default=0.0, ge=0.0, description="Diagonal opposite price level")
    ratio: float = Field(default=0.0, ge=0.0, description="Aggressive volume ratio relative to opposing volume")
    aggressive_volume: float = Field(default=0.0, ge=0.0, description="Dominant aggressive volume traded at this level")
    opposing_volume: float = Field(default=0.0, ge=0.0, description="Opposing passive/counter volume traded diagonally")
    strength: float = Field(default=1.0, ge=0.0, description="Normalized imbalance strength metric")
    stacked_buy_imbalances: int = Field(default=0, ge=0)
    stacked_sell_imbalances: int = Field(default=0, ge=0)
    imbalances: List["DiagonalImbalance"] = Field(default_factory=list)
    
class ImbalanceSide(str, Enum):
    """Direction of diagonal imbalance."""
    
    BUY = "BUY"
    SELL = "SELL"

class DiagonalImbalance(OrderFlowFeatureBase):
    """
    Diagonal bid/ask imbalance observation.
    Compatible with FO-X 5M orderflow detectors.
    """

    feature_name: str = Field(
        default="diagonal_imbalance",
        description="Feature identifier"
    )

    price_level: float = Field(
        ...,
        gt=0.0,
        description="Affected price level"
    )

    side: ImbalanceSide = Field(
        ...,
        description="Imbalance direction"
    )

    bid_volume: float = Field(
        ...,
        ge=0.0,
        description="Bid volume"
    )

    ask_volume: float = Field(
        ...,
        ge=0.0,
        description="Ask volume"
    )

    ratio: float = Field(
        ...,
        ge=0.0,
        description="Ask/Bid or Bid/Ask imbalance ratio"
    )

    strength: float = Field(
        default=1.0,
        ge=0.0,
        description="Normalized imbalance strength"
    )        


class StackedImbalanceFeature(OrderFlowFeatureBase):
    """Cluster of contiguous consecutive diagonal imbalance levels."""
    feature_name: str = Field(default="stacked_imbalance", description="Feature identifier")
    levels_count: int = Field(..., ge=2, description="Number of contiguous stacked imbalance levels")
    price_levels: List[float] = Field(..., description="List of price levels forming the stacked zone")
    total_volume: float = Field(..., ge=0.0, description="Total aggressive volume across the stacked levels")
    average_ratio: float = Field(..., ge=0.0, description="Average imbalance ratio across the zone")
    top_price: float = Field(..., gt=0.0, description="Highest price level in the stacked zone")
    bottom_price: float = Field(..., gt=0.0, description="Lowest price level in the stacked zone")
    strength: float = Field(default=1.0, ge=0.0, description="Composite institutional presence score")


class AbsorptionFeature(OrderFlowFeatureBase):
    """Quantitative measurement of aggressive volume absorption by passive limit orders."""
    feature_name: str = Field(default="absorption", description="Feature identifier")
    aggressive_volume: float = Field(..., ge=0.0, description="Aggressive buy or sell volume observed in the bar/zone")
    price_progress: float = Field(..., ge=0.0, description="Price range or progression achieved by the volume (ticks or USD)")
    range_efficiency: float = Field(..., ge=0.0, description="Ratio of price movement achieved per unit of volume")
    rejection_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Extent of price rejection/wick closing back inside range")
    absorption_score: float = Field(..., ge=0.0, le=1.0, description="Composite absorption index")
    absorbed_price_level: Optional[float] = Field(default=None, description="Price level where heavy absorption occurred (e.g. at extremes)")


class ExhaustionFeature(OrderFlowFeatureBase):
    """Quantitative detection of order flow momentum exhaustion and aggressive volume depletion."""
    feature_name: str = Field(default="exhaustion", description="Feature identifier")
    extreme_volume: float = Field(..., ge=0.0, description="Peak volume or delta prior to exhaustion")
    current_volume: float = Field(..., ge=0.0, description="Subsequent bar or level volume demonstrating depletion")
    delta_depletion_ratio: float = Field(..., ge=0.0, description="Ratio of delta reduction indicating fading aggression")
    follow_through_failed: bool = Field(default=True, description="True if aggressive volume failed to expand range or push new high/low")
    exhaustion_score: float = Field(..., ge=0.0, le=1.0, description="Normalized exhaustion confidence score")

from enum import Enum


class ImbalanceSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

    ASK_IMBALANCE = "ASK_IMBALANCE"
    BID_IMBALANCE = "BID_IMBALANCE"


class DiagonalImbalance(OrderFlowFeatureBase):
    """
    Diagonal bid/ask imbalance feature.
    """

    feature_name: str = Field(
        default="diagonal_imbalance"
    )

    timestamp: datetime = Field(default_factory=datetime.now)
    symbol: str = Field(default="UNKNOWN")
    price_level: float = Field(..., gt=0, validation_alias="price")

    compared_price_level: float = Field(
        0.0,
        gt=0
    )

    ratio: float = Field(
        ...,
        ge=0
    )

    aggressive_volume: float = Field(
        0.0,
        validation_alias="volume",
        ge=0
    )

    opposing_volume: float = Field(
        0.0,
        ge=0
    )

    side: ImbalanceSide = Field(
        default=ImbalanceSide.BUY
    )

    @property
    def price(self) -> float:
        return self.price_level

    @property
    def volume(self) -> float:
        return self.aggressive_volume