"""Market Structure and Swing domain models."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class StructureState(str, Enum):
    """Current high-level directional market structure state."""
    TREND_UP = "TREND_UP"          # Consecutive Higher Highs & Higher Lows
    TREND_DOWN = "TREND_DOWN"      # Consecutive Lower Lows & Lower Highs
    RANGE = "RANGE"                # Contained between established swing boundaries
    TRANSITION = "TRANSITION"      # Structure break or shift occurring
    UNKNOWN = "UNKNOWN"            # Insufficient swings to establish state


class SwingType(str, Enum):
    """Type of pivot swing extreme."""
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"


class SwingPoint(BaseModel):
    """Validated price swing pivot point."""
    timestamp: datetime = Field(..., description="Timestamp of the swing pivot bar (UTC)")
    price: float = Field(..., gt=0.0, description="Exact price level of the pivot extreme")
    type: SwingType = Field(..., description="SWING_HIGH or SWING_LOW")
    strength: float = Field(default=1.0, ge=0.0, description="Relative pivot prominence/strength")
    confirmed_timestamp: datetime = Field(..., description="Timestamp when the swing was definitively confirmed (No lookahead)")

    model_config = {
        "frozen": True
    }


class StructureEventType(str, Enum):
    """Types of market structure boundary events."""
    BOS = "BOS"                # Break of Structure (Trend continuation break)
    MSS = "MSS"                # Market Structure Shift (Change of Character / Shift in structure)
    SWING_HIGH = "SWING_HIGH"  # Confirmed new swing high
    SWING_LOW = "SWING_LOW"    # Confirmed new swing low


class StructureEvent(BaseModel):
    """Discrete market structure milestone event."""
    timestamp: datetime = Field(..., description="Timestamp of the event observation (UTC)")
    symbol: str = Field(..., description="Instrument symbol (e.g. GC_FUT, XAUUSD)")
    timeframe: str = Field(default="5m", description="Evaluation timeframe")
    event_type: StructureEventType = Field(..., description="BOS, MSS, SWING_HIGH, SWING_LOW")
    price: float = Field(..., gt=0.0, description="Price level at which the event or break occurred")
    broken_swing_price: Optional[float] = Field(default=None, description="Previous swing price that was broken")
    strength: float = Field(default=1.0, ge=0.0, description="Quantitative significance score")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Measurement confidence [0.0, 1.0]")
    details: Dict[str, Any] = Field(default_factory=dict, description="Metadata, break distance, volume ratio")

    model_config = {
        "frozen": True
    }


class MarketStructureState(BaseModel):
    """Comprehensive snapshot of market structure at a specific bar."""
    timestamp: datetime = Field(..., description="Evaluation timestamp (UTC)")
    symbol: str = Field(..., description="Instrument symbol")
    timeframe: str = Field(default="5m", description="Timeframe")
    current_state: StructureState = Field(default=StructureState.UNKNOWN, description="TREND_UP, TREND_DOWN, RANGE, etc.")
    last_swing_high: Optional[SwingPoint] = Field(default=None, description="Most recent confirmed Swing High")
    last_swing_low: Optional[SwingPoint] = Field(default=None, description="Most recent confirmed Swing Low")
    last_event: Optional[StructureEvent] = Field(default=None, description="Most recent structure event (BOS/MSS)")
    structure_quality: float = Field(default=1.0, ge=0.0, le=1.0, description="Cleanliness of swing progressions")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Overall structure evaluation confidence")

    model_config = {
        "frozen": True
    }
