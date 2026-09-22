"""Unit test suite for FO-X 5M domain models and validation boundaries."""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from app.models.tick import Tick, TradeSide
from app.models.footprint import FootprintBar, FootprintLevel
from app.models.orderflow_features import (
    DeltaFeature,
    ImbalanceFeature,
    DiagonalImbalance,
    ImbalanceSide,
    AbsorptionFeature,
)
from app.models.market_context import (
    MarketContext,
    MarketRegime,
    MarketStructure,
    TradingSession,
    VolatilityState,
    NewsState,
)
from app.models.decision import Setup, SetupType, Decision, DecisionAction
from app.models.trade_result import TradeResult, TradeOutcome


class TestTickModel:
    """Tests for the Tick model."""

    def test_valid_tick(self) -> None:
        now = datetime.now(timezone.utc)
        tick = Tick(
            symbol="GC_FUT",
            timestamp=now,
            price=2750.5,
            volume=10.0,
            bid=2750.4,
            ask=2750.5,
            trade_side=TradeSide.BUY,
            source="cme"
        )
        assert tick.symbol == "GC_FUT"
        assert tick.price == 2750.5
        assert tick.trade_side == TradeSide.BUY

    def test_invalid_negative_price(self) -> None:
        with pytest.raises(ValidationError):
            Tick(
                symbol="GC_FUT",
                timestamp=datetime.now(timezone.utc),
                price=-10.0,  # Invalid
                volume=1.0
            )

    def test_invalid_bid_ask_spread(self) -> None:
        with pytest.raises(ValidationError):
            Tick(
                symbol="GC_FUT",
                timestamp=datetime.now(timezone.utc),
                price=2750.0,
                volume=1.0,
                bid=2755.0,  # Bid > Ask is invalid
                ask=2750.0
            )


class TestFootprintModels:
    """Tests for FootprintLevel and FootprintBar models."""

    def test_footprint_level_delta_auto_computation(self) -> None:
        lvl = FootprintLevel(price=2750.0, bid_volume=10.0, ask_volume=25.0)
        assert lvl.delta == 15.0
        assert lvl.total_volume == 35.0

    def test_footprint_bar_consistency(self) -> None:
        now = datetime.now(timezone.utc)
        level1 = FootprintLevel(price=2750.0, bid_volume=5.0, ask_volume=15.0)
        level2 = FootprintLevel(price=2751.0, bid_volume=12.0, ask_volume=8.0)

        bar = FootprintBar(
            symbol="GC_FUT",
            timeframe="5m",
            timestamp=now,
            open=2750.0,
            high=2752.0,
            low=2749.0,
            close=2751.0,
            total_volume=40.0,
            delta=6.0,
            levels=[level1, level2]
        )
        assert bar.high >= bar.close
        assert len(bar.levels) == 2

    def test_invalid_ohlc_bar(self) -> None:
        with pytest.raises(ValidationError):
            FootprintBar(
                symbol="GC_FUT",
                timestamp=datetime.now(timezone.utc),
                open=2750.0,
                high=2740.0,  # High lower than open
                low=2745.0,
                close=2748.0
            )


class TestOrderFlowFeatures:
    """Tests for order flow intelligence models."""

    def test_delta_feature(self) -> None:
        now = datetime.now(timezone.utc)
        df = DeltaFeature(
            timestamp=now,
            symbol="GC_FUT",
            feature_name="delta_exhaustion",
            confidence=0.88,
            bar_delta=-150.0,
            delta_percentage=-25.5,
            cvd=1240.0,
            delta_divergence=True
        )
        assert df.delta_divergence is True
        assert df.confidence == 0.88

    def test_imbalance_feature(self) -> None:
        now = datetime.now(timezone.utc)
        imb = DiagonalImbalance(
            price=2750.5,
            side=ImbalanceSide.ASK_IMBALANCE,
            ratio=3.8,
            volume=120.0
        )
        feature = ImbalanceFeature(
            timestamp=now,
            symbol="GC_FUT",
            feature_name="stacked_buy_imbalance",
            confidence=0.92,
            stacked_buy_imbalances=3,
            stacked_sell_imbalances=0,
            imbalances=[imb]
        )
        assert feature.stacked_buy_imbalances == 3
        assert feature.imbalances[0].ratio == 3.8


class TestMarketContext:
    """Tests for MarketContext model."""

    def test_valid_context(self) -> None:
        now = datetime.now(timezone.utc)
        ctx = MarketContext(
            timestamp=now,
            symbol="GC_FUT",
            regime=MarketRegime.TRENDING_BULLISH,
            structure=MarketStructure.BULLISH_MSS,
            session=TradingSession.LONDON,
            volatility=VolatilityState.NORMAL,
            news_state=NewsState.CLEAR,
            data_quality_score=0.98
        )
        assert ctx.regime == MarketRegime.TRENDING_BULLISH
        assert ctx.news_state == NewsState.CLEAR


class TestDecisionAndSettlement:
    """Tests for Decision and TradeResult models."""

    def test_actionable_decision(self) -> None:
        now = datetime.now(timezone.utc)
        setup = Setup(
            setup_type=SetupType.SETUP_A_ABSORPTION_REVERSAL,
            direction=DecisionAction.CALL,
            quality_score=88.5,
            estimated_win_prob=0.68,
            wilson_lower_bound=0.61,
            confluence_factors=["Stacked absorption at support", "Bullish CVD Divergence"]
        )
        decision = Decision(
            timestamp=now,
            symbol="GC_FUT",
            action=DecisionAction.CALL,
            setup=setup,
            expected_value=0.258,
            payout_rate=0.85,
            confidence=0.88,
            reason="High quality Absorption Reversal at H4 Key Support"
        )
        assert decision.action == DecisionAction.CALL
        assert decision.setup.quality_score == 88.5

    def test_trade_result_settlement_win(self) -> None:
        entry = datetime.now(timezone.utc)
        expiry = datetime.now(timezone.utc)
        tr = TradeResult(
            trade_id="TR-1001",
            symbol="GC_FUT",
            direction=DecisionAction.CALL,
            entry_time=entry,
            expiry_time=expiry,
            entry_price=2750.0,
            exit_price=2751.5,
            stake=100.0,
            payout_rate=0.85,
            outcome=TradeOutcome.WIN,
            pnl=85.0
        )
        assert tr.outcome == TradeOutcome.WIN
        assert tr.pnl == 85.0

    def test_invalid_trade_result_pnl_mismatch(self) -> None:
        entry = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            TradeResult(
                trade_id="TR-1002",
                symbol="GC_FUT",
                direction=DecisionAction.PUT,
                entry_time=entry,
                expiry_time=entry,
                entry_price=2750.0,
                exit_price=2752.0,
                stake=100.0,
                payout_rate=0.85,
                outcome=TradeOutcome.LOSS,
                pnl=85.0  # Invalid positive PnL for LOSS outcome
            )
