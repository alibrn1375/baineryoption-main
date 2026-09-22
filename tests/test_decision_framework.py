"""Comprehensive test suite for the FO-X 5M Setup Engine and Decision Framework."""

import tempfile
from datetime import datetime, timezone
import pytest

from app.models.binary_decision import DecisionType, ExpectancyStatus, NoTradeReason
from app.models.footprint import FootprintBar, FootprintQuality
from app.models.liquidity import LiquidityEvent, LiquidityEventType, LiquidityZone, LiquidityZoneType
from app.models.market_context import (
    MarketContext,
    MarketRegime,
    MarketRegimeState,
    NewsRiskLevel,
    NewsState,
    TradingSession,
    TradingSessionName,
    VolatilityLevel,
    VolatilityState,
)
from app.models.market_structure import MarketStructureState, StructureState
from app.models.orderflow_context import OrderFlowContext
from app.models.orderflow_features import AbsorptionFeature, DeltaFeature, StackedImbalanceFeature
from app.models.setup import SetupType
from app.orderflow_engine.base import FeatureDirection
from app.setup_engine.decision_arbiter import DecisionArbiter
from app.setup_engine.ev_calculator import EVCalculator
from app.setup_engine.probability_estimator import ProbabilityEstimator
from app.setup_engine.quality_scorer import SetupQualityScorer
from app.setup_engine.setup_evaluators import SetupEvaluators


def create_mock_contexts(
    direction: FeatureDirection = FeatureDirection.BUY,
    news_blocked: bool = False,
    sweep_event: bool = True
) -> tuple[FootprintBar, OrderFlowContext, MarketContext]:
    """Helper creating realistic, verified multi-pillar context fixtures."""
    t0 = datetime(2026, 8, 30, 14, 0, 0, tzinfo=timezone.utc)

    # Footprint Bar
    bar = FootprintBar(
        symbol="GC_FUT",
        start_time=t0,
        end_time=datetime(2026, 8, 30, 14, 5, 0, tzinfo=timezone.utc),
        open=2750.0, high=2755.0, low=2749.0, close=2754.0,
        total_volume=250.0, total_bid_volume=80.0, total_ask_volume=170.0,
        bar_delta=90.0, quality=FootprintQuality.HIGH_PRECISION
    )

    # Order Flow Context
    delta_feat = DeltaFeature(
        timestamp=t0, symbol="GC_FUT", timeframe="5m",
        direction=direction, bar_delta=90.0, delta_percentage=36.0,
        strength=1.5, acceleration=20.0, persistence=2, percentile=85.0, is_extreme=False
    )
    abs_feat = AbsorptionFeature(
        timestamp=t0, symbol="GC_FUT", timeframe="5m",
        direction=FeatureDirection.SELL if direction == FeatureDirection.BUY else FeatureDirection.BUY,
        aggressive_volume=180.0, price_progress=1.0, range_efficiency=0.20,
        rejection_score=0.80, absorption_score=0.85, absorbed_price_level=2749.0
    )
    of_ctx = OrderFlowContext(
        timestamp=t0, symbol="GC_FUT", timeframe="5m",
        delta_feature=delta_feat,
        absorption_feature=abs_feat,
        dominant_direction=direction,
        quality=FootprintQuality.HIGH_PRECISION
    )

    # Market Context
    zone = LiquidityZone(
        price=2749.0, upper_price=2749.3, lower_price=2748.7,
        zone_type=LiquidityZoneType.EQUAL_LOWS, strength=2.0,
        created_time=t0, touch_count=2, is_mitigated=False
    )
    liq_ev = LiquidityEvent(
        timestamp=t0, symbol="GC_FUT", zone=zone,
        event_type=LiquidityEventType.SWEEP_LOW if direction == FeatureDirection.BUY else LiquidityEventType.SWEEP_HIGH,
        penetration_ticks=3.0, reaction_score=0.75
    ) if sweep_event else None

    mkt_ctx = MarketContext(
        timestamp=t0, symbol="GC_FUT", timeframe="5m",
        structure=MarketStructureState(
            timestamp=t0, symbol="GC_FUT", timeframe="5m",
            current_state=StructureState.TREND_UP if direction == FeatureDirection.BUY else StructureState.TREND_DOWN
        ),
        active_liquidity_zones=[zone],
        recent_liquidity_event=liq_ev,
        regime=MarketRegime(state=MarketRegimeState.TRENDING_BULLISH if direction == FeatureDirection.BUY else MarketRegimeState.TRENDING_BEARISH, strength=1.2),
        session=TradingSession(name=TradingSessionName.NEW_YORK, start_time="13:30:00", end_time="20:00:00"),
        volatility=VolatilityState(level=VolatilityLevel.NORMAL, percentile=55.0, atr_value=2.1),
        news=NewsState(event_active=news_blocked, risk_level=NewsRiskLevel.HIGH if news_blocked else NewsRiskLevel.NONE, blocked=news_blocked),
        data_quality=FootprintQuality.HIGH_PRECISION,
        overall_confidence=1.0
    )

    return bar, of_ctx, mkt_ctx


class TestSetupEvaluators:
    """Test suite for Setups A, B, C, and D."""

    def test_setup_a_sweep_absorption_triggered(self) -> None:
        bar, of_ctx, mkt_ctx = create_mock_contexts(direction=FeatureDirection.BUY, news_blocked=False, sweep_event=True)
        eval_res = SetupEvaluators.evaluate_setup_a(bar, of_ctx, mkt_ctx)

        assert eval_res.setup_type == SetupType.SETUP_A
        assert eval_res.is_triggered is True
        assert eval_res.direction == FeatureDirection.BUY
        assert eval_res.score >= 75.0

    def test_setup_a_fails_without_sweep(self) -> None:
        bar, of_ctx, mkt_ctx = create_mock_contexts(direction=FeatureDirection.BUY, news_blocked=False, sweep_event=False)
        eval_res = SetupEvaluators.evaluate_setup_a(bar, of_ctx, mkt_ctx)

        assert eval_res.is_triggered is False
        assert "No proximate liquidity sweep event detected" in eval_res.conditions_failed


class TestProbabilityAndEV:
    """Test suite for Wilson Score Confidence Intervals and Mathematical Expectancy."""

    def test_wilson_confidence_interval_and_penalty(self) -> None:
        estimator = ProbabilityEstimator(min_sample_adequate=30)

        # 1. Large sample (40 wins / 50 total = 80%)
        est_large = estimator.estimate(wins=40, total=50)
        assert est_large.historical_rate == 0.80
        assert est_large.reliability == 1.0
        assert est_large.wilson_lower >= 0.65

        # 2. Very small sample (4 wins / 5 total = 80%) -> Must have heavy conservative penalty
        est_small = estimator.estimate(wins=4, total=5)
        assert est_small.historical_rate == 0.80
        assert est_small.reliability < 0.20
        assert est_small.conservative_probability < 0.50  # Wilson lower bound drops due to small sample

    def test_binary_expected_value_calculation(self) -> None:
        calculator = EVCalculator()

        # Win Prob = 65%, Payout = 85% (0.85)
        # Break-even = 1 / (1 + 0.85) = 54.05%
        # EV = (0.65 * 0.85) - (0.35 * 1.0) = 0.5525 - 0.35 = +0.2025
        res = calculator.calculate_ev(win_probability=0.65, conservative_probability=0.65, payout_rate=0.85)
        assert res.status == ExpectancyStatus.POSITIVE_EXPECTANCY
        assert res.expected_value > 0.15
        assert res.break_even_probability < 0.55

        # Negative EV case: Win Prob = 50%, Payout = 80% (Break-even = 55.5%) -> Negative EV
        res_neg = calculator.calculate_ev(win_probability=0.50, conservative_probability=0.50, payout_rate=0.80)
        assert res_neg.status == ExpectancyStatus.NEGATIVE_EXPECTANCY
        assert res_neg.expected_value < 0.0


class TestDecisionArbiter:
    """Test suite for Decision Arbiter CALL, PUT, and NO_TRADE outputs."""

    def test_valid_call_decision(self) -> None:
        arbiter = DecisionArbiter(minimum_score=70.0, minimum_probability=0.55, min_payout_rate=0.80)
        bar, of_ctx, mkt_ctx = create_mock_contexts(direction=FeatureDirection.BUY, news_blocked=False, sweep_event=True)

        decision = arbiter.evaluate(
            bar=bar,
            of_ctx=of_ctx,
            mkt_ctx=mkt_ctx,
            payout_rate=0.85,
            historical_stats={"wins": 22, "total": 30}  # 73.3% win rate
        )

        assert decision.decision == DecisionType.CALL
        assert decision.direction == FeatureDirection.BUY
        assert decision.quality_score >= 70.0
        assert len(decision.rejection_reasons) == 0

    def test_news_quarantine_triggers_no_trade(self) -> None:
        arbiter = DecisionArbiter()
        bar, of_ctx, mkt_ctx = create_mock_contexts(direction=FeatureDirection.BUY, news_blocked=True, sweep_event=True)

        decision = arbiter.evaluate(
            bar=bar,
            of_ctx=of_ctx,
            mkt_ctx=mkt_ctx,
            payout_rate=0.85,
            historical_stats={"wins": 22, "total": 30}
        )

        assert decision.decision == DecisionType.NO_TRADE
        assert NoTradeReason.NEWS_RISK in decision.rejection_reasons
        assert "Operational Rejection Reasons" in decision.explanation
