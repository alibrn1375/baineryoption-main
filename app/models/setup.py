"""Setup domain models defining analytical setup definitions and evaluation states."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.orderflow_engine.base import FeatureDirection


class SetupType(str, Enum):
    """Analytical order flow setup archetypes."""
    SETUP_A = "SETUP_A"  # Liquidity Sweep + Absorption
    SETUP_B = "SETUP_B"  # Imbalance Continuation
    SETUP_C = "SETUP_C"  # Momentum Exhaustion Event
    SETUP_D = "SETUP_D"  # Failed Auction Rejection


class SetupDefinition(BaseModel):
    """Declarative definition and operational parameters of a trading setup archetype."""
    setup_id: str = Field(..., description="Unique setup identifier (e.g. SETUP_A)")
    name: str = Field(..., description="Human-readable setup title")
    description: str = Field(..., description="Detailed analytical description of mechanics")
    version: str = Field(default="1.0.0", description="Rule set version")
    required_features: List[str] = Field(default_factory=list, description="Required sensor features")

    model_config = {
        "frozen": True
    }


class SetupEvaluation(BaseModel):
    """Evaluation result of a discrete setup archetype on a completed 5M bar."""
    timestamp: datetime = Field(..., description="Evaluation timestamp (UTC)")
    setup_type: SetupType = Field(..., description="SETUP_A, SETUP_B, SETUP_C, SETUP_D")
    setup_name: str = Field(..., description="Name of the setup")
    direction: FeatureDirection = Field(..., description="Directional setup polarity (BUY/SELL/NEUTRAL)")
    is_triggered: bool = Field(..., description="True if all critical conditions are satisfied")
    conditions_met: List[str] = Field(default_factory=list, description="List of passed empirical conditions")
    conditions_failed: List[str] = Field(default_factory=list, description="List of unmet criteria")
    score: float = Field(default=0.0, ge=0.0, le=100.0, description="Normalized setup score [0.0 - 100.0]")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Measurement validity confidence")
    details: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic metrics, levels, volumes")

    model_config = {
        "frozen": True
    }
