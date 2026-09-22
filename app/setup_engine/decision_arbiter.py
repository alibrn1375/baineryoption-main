"""Decision Arbiter implementing definitive unhedged statistical evaluations for binary options."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from app.models.binary_decision import (
    BinaryDecision,
    DecisionType,
    EVResult,
    ExpectancyStatus,
    NoTradeReason,
)
from app.models.footprint import FootprintBar, FootprintQuality
from app.models.market_context import MarketContext, NewsRiskLevel, VolatilityLevel
from app.models.orderflow_context import OrderFlowContext
from app.models.setup import SetupEvaluation, SetupType
from app.orderflow_engine.base import FeatureDirection
from app.setup_engine.ev_calculator import EVCalculator
from app.setup_engine.explanation import ExplainabilityEngine
from app.setup_engine.probability_estimator import ProbabilityEstimate, ProbabilityEstimator
from app.setup_engine.quality_scorer import QualityResult, SetupQualityScorer
from app.setup_engine.setup_evaluators import SetupEvaluators


class DecisionArbiter:
    """Final analytical arbiter uniting multi-sensor footprints, statistical EV, and risk guards."""

    def __init__(
        self,
        minimum_score: float = 75.0,
        minimum_probability: float = 0.58,
        minimum_sample_size: int = 15,
        min_payout_rate: float = 0.80,
        max_news_risk: str = "LOW"
    ) -> None:
        self.min_score = minimum_score
        self.min_prob = minimum_probability
        self.min_samples = minimum_sample_size
        self.min_payout = min_payout_rate
        self.max_news_risk = max_news_risk

        self.quality_scorer = SetupQualityScorer()
        self.prob_estimator = ProbabilityEstimator(min_sample_adequate=minimum_sample_size)
        self.ev_calculator = EVCalculator()
        self.explain_engine = ExplainabilityEngine()

    def evaluate(
        self,
        bar: FootprintBar,
        of_ctx: OrderFlowContext,
        mkt_ctx: MarketContext,
        payout_rate: float = 0.85,
        historical_stats: Optional[Dict[str, Any]] = None
    ) -> BinaryDecision:
        """Evaluate completed 5M bar and emit CALL, PUT, or NO_TRADE."""
        rejection_reasons: List[NoTradeReason] = []
        custom_notes: List[str] = []

        # 1. Evaluate Candidate Setups (A, B, C, D)
        eval_a = SetupEvaluators.evaluate_setup_a(bar, of_ctx, mkt_ctx)
        eval_b = SetupEvaluators.evaluate_setup_b(bar, of_ctx, mkt_ctx)
        eval_c = SetupEvaluators.evaluate_setup_c(bar, of_ctx, mkt_ctx)
        eval_d = SetupEvaluators.evaluate_setup_d(bar, of_ctx, mkt_ctx)

        candidates = [eval_a, eval_b, eval_c, eval_d]
        triggered_setups = [s for s in candidates if s.is_triggered]

        # Select primary candidate setup
        best_setup: Optional[SetupEvaluation] = None
        if triggered_setups:
            best_setup = max(triggered_setups, key=lambda s: s.score)
        else:
            best_setup = max(candidates, key=lambda s: s.score)
            rejection_reasons.append(NoTradeReason.NO_SETUP_TRIGGERED)

        # 2. Score Setup Quality
        quality_res: QualityResult = self.quality_scorer.score_setup(best_setup, bar, of_ctx, mkt_ctx)
        if quality_res.total_score < self.min_score:
            rejection_reasons.append(NoTradeReason.LOW_SCORE)

        # 3. Check Risk / News Blackout
        if mkt_ctx.news.blocked or mkt_ctx.news.risk_level in (NewsRiskLevel.HIGH, NewsRiskLevel.CRITICAL):
            rejection_reasons.append(NoTradeReason.NEWS_RISK)
            custom_notes.append("Macro news quarantine window active")

        # 4. Check Volatility
        if mkt_ctx.volatility.level == VolatilityLevel.EXTREME:
            rejection_reasons.append(NoTradeReason.HIGH_VOLATILITY)
            custom_notes.append("Extreme erratic volatility condition")

        # 5. Check Data Integrity
        if bar.quality not in (FootprintQuality.HIGH_PRECISION, FootprintQuality.INTERPOLATED):
            rejection_reasons.append(NoTradeReason.DATA_QUALITY_FAILURE)

        # 6. Check Broker Payout
        if payout_rate < self.min_payout:
            rejection_reasons.append(NoTradeReason.LOW_PAYOUT)
            custom_notes.append(f"Payout rate ({payout_rate*100}%) below minimum hurdle ({self.min_payout*100}%)")

        # 7. Probability Estimation
        stats = historical_stats or {"wins": 18, "total": 25}  # Default benchmark baseline
        wins = stats.get("wins", 0)
        total = stats.get("total", 0)

        if total < self.min_samples:
            rejection_reasons.append(NoTradeReason.INSUFFICIENT_SAMPLE)
            custom_notes.append(f"Sample size ({total}) below statistical significance hurdle ({self.min_samples})")

        prob_est: ProbabilityEstimate = self.prob_estimator.estimate(wins, total)
        if prob_est.conservative_probability < self.min_prob:
            rejection_reasons.append(NoTradeReason.LOW_CONFIDENCE)
            custom_notes.append(f"Conservative Wilson probability ({prob_est.conservative_probability:.3f}) below required ({self.min_prob:.3f})")

        # 8. Expected Value (EV) Calculation
        ev_res: EVResult = self.ev_calculator.calculate_ev(
            win_probability=prob_est.historical_rate,
            conservative_probability=prob_est.conservative_probability,
            payout_rate=payout_rate
        )

        if ev_res.status != ExpectancyStatus.POSITIVE_EXPECTANCY:
            rejection_reasons.append(NoTradeReason.NEGATIVE_EXPECTANCED_VALUE if hasattr(NoTradeReason, "NEGATIVE_EXPECTANCED_VALUE") else NoTradeReason.NEGATIVE_EXPECTED_VALUE)
            custom_notes.append(f"Negative mathematical expectancy: EV = {ev_res.expected_value:.3f}")

        # 9. Final Decision Determination
        decision = DecisionType.NO_TRADE
        direction = FeatureDirection.NEUTRAL

        if len(rejection_reasons) == 0 and best_setup is not None and best_setup.is_triggered:
            if best_setup.direction == FeatureDirection.BUY:
                decision = DecisionType.CALL
                direction = FeatureDirection.BUY
            elif best_setup.direction == FeatureDirection.SELL:
                decision = DecisionType.PUT
                direction = FeatureDirection.SELL

        explanation = self.explain_engine.generate_explanation(
            decision=decision,
            setup=best_setup,
            quality_score=quality_res.total_score,
            ev_val=ev_res.expected_value if ev_res else None,
            rejection_reasons=rejection_reasons,
            custom_notes=custom_notes + quality_res.explanation
        )

        return BinaryDecision(
            timestamp=bar.start_time,
            symbol=bar.symbol,
            expiry_minutes=5,
            decision=decision,
            direction=direction,
            payout_rate=payout_rate,
            setup_evaluation=best_setup,
            quality_score=quality_res.total_score,
            ev_result=ev_res,
            rejection_reasons=rejection_reasons,
            explanation=explanation,
            confidence=prob_est.conservative_probability if decision != DecisionType.NO_TRADE else 0.5
        )
