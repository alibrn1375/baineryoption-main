"""Setup evaluation, mathematical scoring, and trade decision domain models."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class SetupType(str, Enum):
    """Core trade setup categories."""
    SETUP_A_ABSORPTION_REVERSAL = "SETUP_A_ABSORPTION_REVERSAL"
    SETUP_B_EXHAUSTION_FADE = "SETUP_B_EXHAUSTION_FADE"
    SETUP_C_IMBALANCE_BREAKOUT_PULLBACK = "SETUP_C_IMBALANCE_BREAKOUT_PULLBACK"
    SETUP_D_VALUE_AREA_FAILED_AUCTION = "SETUP_D_VALUE_AREA_FAILED_AUCTION"
    NONE = "NONE"


class DecisionAction(str, Enum):
    """Final actionable trading signal."""
    CALL = "CALL"          # Enter 5-minute Call Option (Bullish)
    PUT = "PUT"            # Enter 5-minute Put Option (Bearish)
    NO_TRADE = "NO_TRADE"  # Ineligible conditions or filters active


class Setup(BaseModel):
    """Detected candidate setup instance."""
    setup_type: SetupType = Field(..., description="Setup archetype")
    direction: DecisionAction = Field(..., description="Target direction: CALL or PUT")
    quality_score: float = Field(..., ge=0.0, le=100.0, description="Rule-based composite quality score [0, 100]")
    estimated_win_prob: float = Field(..., ge=0.0, le=1.0, description="Calibrated win probability [0.0, 1.0]")
    wilson_lower_bound: float = Field(..., ge=0.0, le=1.0, description="95% Wilson confidence lower bound")
    confluence_factors: List[str] = Field(default_factory=list, description="Triggered confluence points")
    invalidation_rules: List[str] = Field(default_factory=list, description="Conditions that would invalidate setup")

    model_config = {
        "frozen": True
    }


class Decision(BaseModel):
    """Final discrete actionable trade output emitted by the engine."""
    timestamp: datetime = Field(..., description="Decision timestamp (UTC)")
    symbol: str = Field(..., description="Traded asset symbol (e.g. GC_FUT)")
    action: DecisionAction = Field(..., description="CALL, PUT, or NO_TRADE")
    setup: Optional[Setup] = Field(None, description="Triggering setup details if actionable")
    expected_value: float = Field(default=0.0, description="Expected value: (p * payout) - ((1-p) * 1.0)")
    payout_rate: float = Field(default=0.85, ge=0.5, le=1.0, description="Broker payout percentage")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Aggregate confidence score")
    reason: str = Field(..., description="Human-explainable justification or filter rejection cause")
    diagnostics: Dict[str, float] = Field(default_factory=dict, description="Numerical sub-scores and feature vectors")

    model_config = {
        "frozen": True
    }
