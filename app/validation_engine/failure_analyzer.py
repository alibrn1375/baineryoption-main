"""Failure analysis engine diagnosing and attributing losses to specific microstructure flaws."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.market_context import MarketContext, VolatilityLevel
from app.models.orderflow_context import OrderFlowContext
from app.validation_engine.binary_simulator import BinarySimulationResult, SimulationOutcome


class LossAttributionCategory(str, Enum):
    """Root-cause classification of an expired losing trade."""
    WRONG_CONTEXT = "WRONG_CONTEXT"
    WEAK_ORDER_FLOW = "WEAK_ORDER_FLOW"
    NEWS_PROXIMITY = "NEWS_PROXIMITY"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    SLIPPAGE_SPREAD_DRAG = "SLIPPAGE_SPREAD_DRAG"
    DATA_QUALITY_DEGRADATION = "DATA_QUALITY_DEGRADATION"
    PURE_STATISTICAL_VARIANCE = "PURE_STATISTICAL_VARIANCE"


class FailureReport(BaseModel):
    """Detailed forensic analysis for a single losing trade."""
    trade_id: str = Field(..., description="Unique trade identifier")
    timestamp: str = Field(..., description="Timestamp of trade execution")
    failure_reason: LossAttributionCategory = Field(..., description="Primary attributed failure category")
    feature_state: Dict[str, Any] = Field(default_factory=dict, description="Snapshot of order flow metrics at entry")
    explanation: str = Field(..., description="Forensic rationale")
    improvement_area: str = Field(..., description="Suggested heuristic or rule refinement")

    model_config = {
        "frozen": True
    }


class FailureAnalyzer:
    """Forensic diagnosis engine analyzing every losing trade to isolate system vulnerability patterns."""

    @staticmethod
    def analyze_loss(
        trade: BinarySimulationResult,
        of_ctx: OrderFlowContext,
        mkt_ctx: MarketContext
    ) -> Optional[FailureReport]:
        """Classify losing outcome into a discrete root cause category."""
        if trade.outcome != SimulationOutcome.LOSS:
            return None

        trade_id = f"{trade.symbol}_{trade.entry_time.strftime('%Y%m%d_%H%M%S')}"
        reason = LossAttributionCategory.PURE_STATISTICAL_VARIANCE
        explanation = "Loss within standard binomial variance boundaries."
        improvement = "Maintain current rule set; sample within expected confidence intervals."

        # Check 1: News proximity
        if mkt_ctx.news.event_active or mkt_ctx.news.blocked:
            reason = LossAttributionCategory.NEWS_PROXIMITY
            explanation = "Trade executed near or within active news quarantine blackout."
            improvement = "Expand pre-news quarantine window by +5 minutes."

        # Check 2: Volatility Spike
        elif mkt_ctx.volatility.level in (VolatilityLevel.HIGH, VolatilityLevel.EXTREME):
            reason = LossAttributionCategory.VOLATILITY_EXPANSION
            explanation = f"Elevated volatility ({mkt_ctx.volatility.percentile}th percentile) generated wide adverse wicks."
            improvement = "Tighten ATR percentile filter threshold for setup validation."

        # Check 3: Weak Order Flow follow-through
        elif of_ctx.delta_feature and abs(of_ctx.delta_feature.bar_delta) < 30.0:
            reason = LossAttributionCategory.WEAK_ORDER_FLOW
            explanation = "Delta momentum was insufficient to sustain continuation beyond entry."
            improvement = "Raise minimum delta strength hurdle."

        # Check 4: Price moved favorably initially but slippage/spread caused loss
        elif abs(trade.expiry_price - trade.entry_price) < 0.15:
            reason = LossAttributionCategory.SLIPPAGE_SPREAD_DRAG
            explanation = f"Price difference ({abs(trade.expiry_price - trade.entry_price):.2f}) was eclipsed by spread and execution slippage."
            improvement = "Enforce stricter minimum payout and spread filters."

        return FailureReport(
            trade_id=trade_id,
            timestamp=trade.entry_time.isoformat(),
            failure_reason=reason,
            feature_state={
                "delta": of_ctx.delta_feature.bar_delta if of_ctx.delta_feature else 0.0,
                "volatility_level": mkt_ctx.volatility.level.value,
                "regime": mkt_ctx.regime.state.value
            },
            explanation=explanation,
            improvement_area=improvement
        )
