"""Context aggregator combining multiple order flow features into an unified observation state."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.footprint import FootprintQuality
from app.models.orderflow_features import (
    AbsorptionFeature,
    DeltaFeature,
    ExhaustionFeature,
    ImbalanceFeature,
    StackedImbalanceFeature,
)
from app.orderflow_engine.base import FeatureDirection


class OrderFlowContext(BaseModel):
    """Immutable comprehensive order flow state observation for a single timeframe bar.
    
    NOTE: This is strictly an objective measurement and market observation object,
    NEVER a trade execution signal or decision.
    """
    timestamp: datetime = Field(..., description="Evaluation timestamp of the context (UTC)")
    symbol: str = Field(..., description="Instrument symbol (e.g. GC_FUT, XAUUSD)")
    timeframe: str = Field(default="5m", description="Bar timeframe")

    # Feature observation components
    delta_feature: Optional[DeltaFeature] = Field(default=None, description="Delta strength, acceleration, and percentile")
    imbalances: List[ImbalanceFeature] = Field(default_factory=list, description="List of detected diagonal imbalances")
    stacked_imbalances: List[StackedImbalanceFeature] = Field(default_factory=list, description="List of stacked imbalance zones")
    absorption_feature: Optional[AbsorptionFeature] = Field(default=None, description="Detected absorption metrics if present")
    exhaustion_feature: Optional[ExhaustionFeature] = Field(default=None, description="Detected exhaustion metrics if present")

    # High-level state summaries
    dominant_direction: FeatureDirection = Field(default=FeatureDirection.NEUTRAL, description="Overall observed order flow directional bias")
    quality: FootprintQuality = Field(default=FootprintQuality.HIGH_PRECISION, description="Quality integrity of underlying footprint")
    telemetry: Dict[str, Any] = Field(default_factory=dict, description="Metadata and execution timing telemetry")

    model_config = {
        "frozen": True
    }
