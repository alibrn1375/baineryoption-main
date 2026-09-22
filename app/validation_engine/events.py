"""Validation Event models representing chronological ticks, footprint completion, and decision triggers."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Categorical types of market and analytical stream events."""
    TICK = "TICK"
    FOOTPRINT_READY = "FOOTPRINT_READY"
    ORDERFLOW_READY = "ORDERFLOW_READY"
    CONTEXT_READY = "CONTEXT_READY"
    SETUP_EVALUATED = "SETUP_EVALUATED"
    DECISION_READY = "DECISION_READY"
    SIMULATION_COMPLETED = "SIMULATION_COMPLETED"


class MarketEvent(BaseModel):
    """Discrete market data or analytical event emitted chronologically during replay."""
    timestamp: datetime = Field(..., description="UTC timestamp of event generation")
    event_type: EventType = Field(..., description="TICK, FOOTPRINT_READY, DECISION_READY, etc.")
    symbol: str = Field(..., description="Asset symbol")
    sequence_id: int = Field(default=0, description="Monotonically increasing sequence identifier")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Event data object payload")

    model_config = {
        "frozen": True
    }
