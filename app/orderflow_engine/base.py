"""Base abstraction models for Order Flow intelligence features."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class FeatureDirection(str, Enum):
    """Directional polarity of an observed order flow behavior."""
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"
    UNKNOWN = "UNKNOWN"


class OrderFlowFeatureBase(BaseModel):
    """Abstract base class for all measurable order flow features."""
    timestamp: datetime = Field(..., description="Timestamp of the footprint bar or feature evaluation (UTC)")
    symbol: str = Field(..., description="Instrument symbol (e.g. GC_FUT, XAUUSD)")
    timeframe: str = Field(default="5m", description="Evaluation timeframe (e.g. 5m)")
    feature_name: str = Field(..., description="Unique descriptive identifier of the feature")
    direction: FeatureDirection = Field(default=FeatureDirection.NEUTRAL, description="Directional polarity")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Normalized measurement confidence [0.0, 1.0]")
    calculation_version: str = Field(default="1.0.0", description="Algorithm implementation version")
    details: Dict[str, Any] = Field(default_factory=dict, description="Detailed quantitative metrics and telemetry")

    model_config = {
        "frozen": True
    }
