"""Binary options decision domain models, EV calculation outputs, and arbiter states."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.setup import SetupEvaluation
from app.orderflow_engine.base import FeatureDirection


class DecisionType(str, Enum):
    """Actionable decision output for a 5M binary contract evaluation."""
    CALL = "CALL"          # Upward expiry evaluation
    PUT = "PUT"            # Downward expiry evaluation
    NO_TRADE = "NO_TRADE"  # Quantitative rejection / operational hold


class NoTradeReason(str, Enum):
    """Categorical reasons for issuing a NO_TRADE decision."""
    LOW_SCORE = "LOW_SCORE"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    NEWS_RISK = "NEWS_RISK"
    HIGH_VOLATILITY = "HIGH_VOLATILITY"
    DATA_QUALITY_FAILURE = "DATA_QUALITY_FAILURE"
    CONFLICTING_FEATURES = "CONFLICTING_FEATURES"
    NEGATIVE_EXPECTED_VALUE = "NEGATIVE_EXPECTED_VALUE"
    LOW_PAYOUT = "LOW_PAYOUT"
    NO_SETUP_TRIGGERED = "NO_SETUP_TRIGGERED"


class ExpectancyStatus(str, Enum):
    """Mathematical expectancy state."""
    POSITIVE_EXPECTANCY = "POSITIVE_EXPECTANCY"
    NEGATIVE_EXPECTANCY = "NEGATIVE_EXPECTANCY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class EVResult(BaseModel):
    """Binary Options Expected Value analysis result."""
    probability: float = Field(..., ge=0.0, le=1.0, description="Estimated base historical win rate")
    conservative_probability: float = Field(..., ge=0.0, le=1.0, description="Lower Wilson confidence bound")
    payout: float = Field(..., ge=0.0, description="Broker payout percentage (e.g. 0.85 for 85%)")
    expected_value: float = Field(..., description="Mathematical expected return per $1 risked")
    break_even_probability: float = Field(..., ge=0.0, le=1.0, description="Minimum win rate for breakeven: 1/(1+payout)")
    status: ExpectancyStatus = Field(..., description="POSITIVE, NEGATIVE, or INSUFFICIENT_DATA")

    model_config = {
        "frozen": True
    }


class BinaryDecision(BaseModel):
    """Final, unhedged decision object emitted by the Decision Arbiter for a 5M bar expiry."""
    timestamp: datetime = Field(..., description="Decision timestamp (UTC)")
    symbol: str = Field(..., description="Asset symbol (GC_FUT, XAUUSD)")
    expiry_minutes: int = Field(default=5, ge=1, description="Binary option expiry duration in minutes")
    decision: DecisionType = Field(..., description="CALL, PUT, or NO_TRADE")
    direction: FeatureDirection = Field(default=FeatureDirection.NEUTRAL, description="Directional polarity")
    payout_rate: float = Field(..., ge=0.0, description="Offered broker payout rate")
    setup_evaluation: Optional[SetupEvaluation] = Field(default=None, description="Triggered setup details")
    quality_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Composite setup quality score [0-100]")
    ev_result: Optional[EVResult] = Field(default=None, description="Expected value breakdown")
    rejection_reasons: List[NoTradeReason] = Field(default_factory=list, description="Categorical rejection flags")
    explanation: str = Field(..., description="Structured multi-point diagnostic rationale")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Decision confidence")

    model_config = {
        "frozen": True
    }
