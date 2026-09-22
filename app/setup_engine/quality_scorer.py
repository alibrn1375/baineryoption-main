"""Setup Quality Scorer calculating multi-component empirical scores (0-100)."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.footprint import FootprintBar, FootprintQuality
from app.models.market_context import MarketContext, MarketRegimeState, VolatilityLevel
from app.models.market_structure import StructureState
from app.models.orderflow_context import OrderFlowContext
from app.models.setup import SetupEvaluation
from app.orderflow_engine.base import FeatureDirection


class QualityResult(BaseModel):
    """Detailed multi-pillar score breakdown."""
    total_score: float = Field(..., ge=0.0, le=100.0, description="Overall weighted score [0 - 100]")
    context_score: float = Field(..., ge=0.0, le=30.0, description="Market Context pillar score [0 - 30]")
    orderflow_score: float = Field(..., ge=0.0, le=35.0, description="Order Flow pillar score [0 - 35]")
    data_quality_score: float = Field(..., ge=0.0, le=15.0, description="Data integrity pillar score [0 - 15]")
    risk_score: float = Field(..., ge=0.0, le=20.0, description="News and volatility safety score [0 - 20]")
    explanation: List[str] = Field(default_factory=list, description="Scoring component justifications")

    model_config = {
        "frozen": True
    }


class SetupQualityScorer:
    """Computes comprehensive empirical quality scores across Context, Order Flow, Data, and Risk."""

    def __init__(
        self,
        weight_context: float = 0.30,
        weight_orderflow: float = 0.35,
        weight_data_quality: float = 0.15,
        weight_risk: float = 0.20
    ) -> None:
        self.w_context = weight_context
        self.w_of = weight_orderflow
        self.w_dq = weight_data_quality
        self.w_risk = weight_risk

    def score_setup(
        self,
        setup: SetupEvaluation,
        bar: FootprintBar,
        of_ctx: OrderFlowContext,
        mkt_ctx: MarketContext
    ) -> QualityResult:
        """Evaluate setup quality against 4 pillars and return breakdown."""
        explanations: List[str] = []

        # 1. Market Context Score (Max 30 pts)
        c_score = 0.0
        # Structure compatibility
        if (setup.direction == FeatureDirection.BUY and mkt_ctx.structure.current_state == StructureState.TREND_UP) or \
           (setup.direction == FeatureDirection.SELL and mkt_ctx.structure.current_state == StructureState.TREND_DOWN):
            c_score += 15.0
            explanations.append("Structural trend strongly supports setup direction (+15)")
        elif mkt_ctx.structure.current_state == StructureState.RANGE:
            c_score += 10.0
            explanations.append("Range regime compatible with rejection setups (+10)")
        else:
            c_score += 5.0

        # Liquidity proximity
        if mkt_ctx.recent_liquidity_event:
            c_score += 15.0
            explanations.append("Interacting directly with major liquidity pool (+15)")
        elif mkt_ctx.active_liquidity_zones:
            c_score += 8.0
            explanations.append("Near resting liquidity zones (+8)")
        c_score = min(30.0, c_score)

        # 2. Order Flow Score (Max 35 pts)
        of_score = 0.0
        if of_ctx.stacked_imbalances:
            of_score += 15.0
            explanations.append("Stacked institutional imbalance presence (+15)")
        elif of_ctx.imbalances:
            of_score += 8.0

        if of_ctx.absorption_feature:
            of_score += 12.0
            explanations.append("Quantitative volume absorption confirmed (+12)")

        if of_ctx.delta_feature and of_ctx.delta_feature.direction == setup.direction:
            of_score += 8.0
            explanations.append("Delta acceleration aligned with setup (+8)")
        of_score = min(35.0, of_score)

        # 3. Data Quality Score (Max 15 pts)
        dq_score = 0.0
        if bar.quality == FootprintQuality.HIGH_PRECISION:
            dq_score = 15.0
            explanations.append("High precision microsecond tick data (+15)")
        elif bar.quality == FootprintQuality.INTERPOLATED:
            dq_score = 8.0
            explanations.append("Interpolated tick data (+8)")
        else:
            dq_score = 0.0
            explanations.append("Data quality degraded / missing ticks (0)")

        # 4. Risk / News Score (Max 20 pts)
        r_score = 20.0
        if mkt_ctx.news.blocked:
            r_score = 0.0
            explanations.append("Active news blackout quarantine (-20)")
        elif mkt_ctx.volatility.level == VolatilityLevel.EXTREME:
            r_score = 5.0
            explanations.append("Extreme erratic volatility (-15)")
        elif mkt_ctx.volatility.level == VolatilityLevel.HIGH:
            r_score = 12.0
            explanations.append("Elevated volatility (-8)")
        else:
            explanations.append("Clean risk environment, no news blackout (+20)")

        total = round(c_score + of_score + dq_score + r_score, 1)

        return QualityResult(
            total_score=total,
            context_score=round(c_score, 1),
            orderflow_score=round(of_score, 1),
            data_quality_score=round(dq_score, 1),
            risk_score=round(r_score, 1),
            explanation=explanations
        )
