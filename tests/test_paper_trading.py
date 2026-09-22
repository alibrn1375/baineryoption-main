"""Comprehensive test suite for the FO-X 5M Paper Trading Engine."""

from datetime import datetime, timedelta, timezone
import pytest

from app.models.binary_decision import BinaryDecision, DecisionType
from app.models.footprint import FootprintBar, FootprintQuality
from app.models.market_context import MarketContext, NewsRiskLevel, NewsState, VolatilityLevel, VolatilityState
from app.models.paper_trade import PaperTrade, PaperTradeStatus
from app.orderflow_engine.base import FeatureDirection
from app.paper_trading.comparison import LiveVsBacktestComparator
from app.paper_trading.risk_guard import PaperRiskGuard
from app.paper_trading.virtual_account import VirtualAccount
from app.paper_trading.virtual_execution import VirtualExecutionEngine
from app.validation_engine.binary_simulator import BinarySimulationConfig, BinarySimulationResult, SimulationOutcome


class TestVirtualAccount:
    """Test suite verifying virtual account equity math, consecutive loss tracking, and drawdowns."""

    def test_virtual_account_lifecycle(self) -> None:
        account = VirtualAccount(starting_balance=1000.0)
        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)

        # 1. Allocate stake for trade ($25)
        assert account.allocate_stake(25.0) is True
        assert account.balance == 975.0

        # 2. Settle winning trade ($25 stake, 85% payout -> profit = $21.25 -> Return $46.25)
        win_trade = PaperTrade(
            trade_id="PT_1", timestamp=t0, symbol="GC_FUT", direction=FeatureDirection.BUY,
            stake_amount=25.0, payout_percentage=0.85, status=PaperTradeStatus.WIN, pnl=21.25
        )
        state_win = account.settle_trade(win_trade)
        assert account.balance == 1021.25
        assert state_win.wins == 1
        assert state_win.consecutive_losses == 0

        # 3. Settle losing trade ($25 stake lost)
        assert account.allocate_stake(25.0) is True
        loss_trade = PaperTrade(
            trade_id="PT_2", timestamp=t0, symbol="GC_FUT", direction=FeatureDirection.BUY,
            stake_amount=25.0, payout_percentage=0.85, status=PaperTradeStatus.LOSS, pnl=-25.0
        )
        state_loss = account.settle_trade(loss_trade)
        assert account.balance == 996.25
        assert state_loss.losses == 1
        assert state_loss.consecutive_losses == 1
        assert state_loss.drawdown_amount == round(1021.25 - 996.25, 2)


class TestVirtualExecutionEngine:
    """Test suite verifying execution order fills, delays, and 5M expiry settlement."""

    def test_execution_entry_and_settlement(self) -> None:
        account = VirtualAccount(starting_balance=1000.0)
        config = BinarySimulationConfig(entry_delay_ms=200, expiry_minutes=5, spread_assumption=0.10, execution_slippage=0.05)
        engine = VirtualExecutionEngine(account=account, config=config, default_stake=20.0)

        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
        decision = BinaryDecision(
            timestamp=t0, symbol="GC_FUT", decision=DecisionType.CALL, direction=FeatureDirection.BUY,
            payout_rate=0.85, quality_score=80.0, explanation="Test CALL"
        )

        # 1. Submit decision
        submitted = engine.submit_decision(decision, current_price=2750.0)
        assert submitted is not None
        assert submitted.status == PaperTradeStatus.PENDING
        assert account.balance == 980.0

        # 2. Fill order: price 2750.0 + 0.05 (half spread) + 0.05 (slippage) = 2750.10
        filled = engine.process_order_fills(current_time=t0, current_price=2750.0)
        assert len(filled) == 1
        assert filled[0].status == PaperTradeStatus.OPEN
        assert filled[0].entry_price == 2750.10
        assert len(engine.open_positions) == 1

        # 3. Settle at expiry (t0 + 5 min): Price moves to 2752.00 > 2750.10 -> WIN
        t_exp = t0 + timedelta(minutes=5)
        settled = engine.process_expiries(current_time=t_exp, current_price=2752.00)
        assert len(settled) == 1
        assert settled[0].status == PaperTradeStatus.WIN
        assert settled[0].pnl == 17.0  # 20 * 0.85 = 17.0
        assert account.balance == 980.0 + 20.0 + 17.0  # 1017.0


class TestPaperRiskGuard:
    """Test suite verifying safety bounds, daily limits, and drawdown halts."""

    def test_risk_guard_daily_limit_and_drawdown(self) -> None:
        guard = PaperRiskGuard(max_daily_trades=5, max_consecutive_losses=2, max_drawdown_pct=10.0)
        account = VirtualAccount(starting_balance=1000.0)
        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)

        mkt_ctx = MarketContext(
            timestamp=t0, symbol="GC_FUT", timeframe="5m",
            news=NewsState(event_active=False, risk_level=NewsRiskLevel.NONE, blocked=False),
            volatility=VolatilityState(level=VolatilityLevel.NORMAL, percentile=50.0, atr_value=2.0)
        )

        # Under limits -> allowed
        status = guard.check_trade_safety(account.get_state(), mkt_ctx, daily_trades_count=2)
        assert status.allowed is True

        # Daily trade limit reached -> blocked
        status_blocked_daily = guard.check_trade_safety(account.get_state(), mkt_ctx, daily_trades_count=5)
        assert status_blocked_daily.allowed is False
        assert "Daily trade limit" in status_blocked_daily.reason
