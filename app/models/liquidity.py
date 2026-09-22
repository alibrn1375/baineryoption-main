"""Liquidity zones and liquidity sweep domain models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LiquidityZoneType(str, Enum):
    """Classification of the liquidity pool origin."""
    EQUAL_HIGHS = "EQUAL_HIGHS"        # Buy-side liquidity pool formed by matching swing highs
    EQUAL_LOWS = "EQUAL_LOWS"          # Sell-side liquidity pool formed by matching swing lows
    SESSION_HIGH = "SESSION_HIGH"      # Major liquidity at prior session high
    SESSION_LOW = "SESSION_LOW"        # Major liquidity at prior session low
    RANGE_HIGH = "RANGE_HIGH"          # Upper boundary of multi-hour range
    RANGE_LOW = "RANGE_LOW"            # Lower boundary of multi-hour range
    PREV_DAY_HIGH = "PREV_DAY_HIGH"    # Previous Day High (PDH)
    PREV_DAY_LOW = "PREV_DAY_LOW"      # Previous Day Low (PDL)


class LiquidityZone(BaseModel):
    """Discrete resting liquidity cluster level or zone."""
    price: float = Field(..., gt=0.0, description="Central price level of liquidity pool")
    upper_price: float = Field(..., gt=0.0, description="Upper bound of the liquidity tolerance area")
    lower_price: float = Field(..., gt=0.0, description="Lower bound of the liquidity tolerance area")
    zone_type: LiquidityZoneType = Field(..., description="EQUAL_HIGHS, EQUAL_LOWS, etc.")
    strength: float = Field(default=1.0, ge=0.0, description="Quantitative strength / touch count")
    created_time: datetime = Field(..., description="Timestamp when zone was established (UTC)")
    touch_count: int = Field(default=1, ge=1, description="Number of touches confirming this level")
    is_mitigated: bool = Field(default=False, description="True if liquidity has already been swept/penetrated")

    model_config = {
        "frozen": True
    }


class LiquidityEventType(str, Enum):
    """Categorization of price interaction with resting liquidity."""
    SWEEP_HIGH = "SWEEP_HIGH"      # Price pierced Buy-side liquidity pool and closed back below
    SWEEP_LOW = "SWEEP_LOW"        # Price pierced Sell-side liquidity pool and closed back above
    FAILED_BREAK = "FAILED_BREAK"  # Attempted breakout immediately rejected back into range
    EXPANSION = "EXPANSION"        # Strong breakout holding beyond the liquidity pool
    UNKNOWN = "UNKNOWN"


class LiquidityEvent(BaseModel):
    """Recorded interaction between real-time price action and a resting liquidity zone."""
    timestamp: datetime = Field(..., description="Timestamp of the interaction bar (UTC)")
    symbol: str = Field(..., description="Instrument symbol")
    zone: LiquidityZone = Field(..., description="The interacting liquidity zone")
    event_type: LiquidityEventType = Field(..., description="SWEEP_HIGH, SWEEP_LOW, FAILED_BREAK")
    penetration_ticks: float = Field(..., ge=0.0, description="Depth of penetration beyond the zone price in ticks")
    reaction_score: float = Field(..., ge=0.0, le=1.0, description="Degree of rejection / wick closure back inside")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Measurement reliability score")
    details: Dict[str, Any] = Field(default_factory=dict, description="Metadata, volume on sweep, wick ratios")

    model_config = {
        "frozen": True
    }
