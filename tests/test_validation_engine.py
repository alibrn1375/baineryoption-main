"""Comprehensive test suite for the FO-X 5M Validation Engine."""

from datetime import datetime, timezone
import pytest

from app.models.binary_decision import BinaryDecision, DecisionType
from app.models.tick import Tick, TickSide
from app.orderflow_engine.base import FeatureDirection
from app.validation_engine.binary_simulator import (
    BinarySimulationConfig,
    BinarySimulator,
    SimulationOutcome,
    TieHandlingRule,
)
from app.validation_engine.metrics_engine import MetricsEngine
from app.validation_engine.monte_carlo import MonteCarloEngine
from app.validation_engine.replay_engine import ReplayEngine, ReplaySession, ReplaySpeedMode
from app.validation_engine.walk_forward import WalkForwardValidator


class TestReplayAndNoFutureDataAccess:
    """Test suite ensuring strict chronological streaming and zero future information leakage."""

    def test_no_future_data_access(self) -> None:
        """Verify that at timestamp T, the system only has access to ticks where timestamp <= T."""
        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 8, 30, 10, 1, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 30, 10, 2, 0, tzinfo=timezone.utc)
        t3 = datetime(2026, 8, 30, 10, 3, 0, tzinfo=timezone.utc)

        # Intentionally feed unordered ticks to verify chronological sorting enforcement
        raw_ticks = [
            Tick(timestamp=t2, symbol="GC_FUT", price=2752.0, volume=1.0, side=TickSide.BUY),
            Tick(timestamp=t0, symbol="GC_FUT", price=2750.0, volume=1.0, side=TickSide.BUY),
            Tick(timestamp=t3, symbol="GC_FUT", price=2753.0, volume=1.0, side=TickSide.SELL),
            Tick(timestamp=t1, symbol="GC_FUT", price=2751.0, volume=1.0, side=TickSide.SELL),
        ]

        session = ReplaySession(
            session_id="test_seq",
            start_time=t0,
            end_time=t3,
            symbol="GC_FUT",
            speed_mode=ReplaySpeedMode.FAST
        )
        replay = ReplayEngine(session)

        emitted_timestamps = []
        for event in replay.stream_ticks(raw_ticks):
            # Assert that replay clock exactly matches the current event timestamp
            assert replay.current_time == event.timestamp

            # Assert that current timestamp is monotonically >= previous timestamp (no future lookahead)
            if emitted_timestamps:
                assert event.timestamp >= emitted_timestamps[-1]

            emitted_timestamps.append(event.timestamp)

        assert emitted_timestamps == [t0, t1, t2, t3]


class TestBinarySimulator:
    """Test suite verifying execution assumptions, slippage, spread, and tie handling."""

    def test_call_win_and_loss(self) -> None:
        config = BinarySimulationConfig(
            entry_delay_ms=200,
            expiry_minutes=5,
            payout_percentage=0.85,
            spread_assumption=0.10,
            execution_slippage=0.05
        )
        sim = BinarySimulator(config)
        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)

        decision = BinaryDecision(
            timestamp=t0,
            symbol="GC_FUT",
            decision=DecisionType.CALL,
            direction=FeatureDirection.BUY,
            payout_rate=0.85,
            quality_score=80.0,
            explanation="Test CALL"
        )

        # 1. Win Scenario: Raw Entry 2750.0 -> Adjusted Entry = 2750.0 + 0.05 + 0.05 = 2750.10
        # Expiry Price = 2752.00 > 2750.10 -> WIN
        res_win = sim.simulate_trade(decision, raw_entry_price=2750.0, raw_expiry_price=2752.0, bar_start_time=t0)
        assert res_win is not None
        assert res_win.outcome == SimulationOutcome.WIN
        assert res_win.pnl == 0.85
        assert res_win.entry_price == 2750.10

        # 2. Loss Scenario: Expiry Price = 2749.00 < 2750.10 -> LOSS
        res_loss = sim.simulate_trade(decision, raw_entry_price=2750.0, raw_expiry_price=2749.0, bar_start_time=t0)
        assert res_loss is not None
        assert res_loss.outcome == SimulationOutcome.LOSS
        assert res_loss.pnl == -1.0

    def test_tie_handling_modes(self) -> None:
        # Test REFUND vs LOSS on exact tie
        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
        decision = BinaryDecision(
            timestamp=t0,
            symbol="GC_FUT",
            decision=DecisionType.CALL,
            direction=FeatureDirection.BUY,
            payout_rate=0.85,
            quality_score=80.0,
            explanation="Test CALL"
        )

        # Refund mode (spread=0, slippage=0 for exact match testing)
        cfg_refund = BinarySimulationConfig(spread_assumption=0.0, execution_slippage=0.0, tie_handling=TieHandlingRule.REFUND)
        sim_ref = BinarySimulator(cfg_refund)
        res_ref = sim_ref.simulate_trade(decision, raw_entry_price=2750.0, raw_expiry_price=2750.0, bar_start_time=t0)
        assert res_ref is not None
        assert res_ref.outcome == SimulationOutcome.TIE
        assert res_ref.pnl == 0.0

        # Loss mode on tie
        cfg_loss = BinarySimulationConfig(spread_assumption=0.0, execution_slippage=0.0, tie_handling=TieHandlingRule.LOSS)
        sim_loss = BinarySimulator(cfg_loss)
        res_loss = sim_loss.simulate_trade(decision, raw_entry_price=2750.0, raw_expiry_price=2750.0, bar_start_time=t0)
        assert res_loss is not None
        assert res_loss.outcome == SimulationOutcome.TIE
        assert res_loss.pnl == -1.0


class TestMonteCarloAndMetrics:
    """Test suite for Monte Carlo reshuffling and performance reports."""

    def test_monte_carlo_distribution_preservation(self) -> None:
        mc = MonteCarloEngine(iterations=1000)

        # Generate sample trade results: 60 wins (+0.85), 40 losses (-1.0)
        from app.validation_engine.binary_simulator import BinarySimulationResult
        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)

        sample_trades = []
        for i in range(60):
            sample_trades.append(BinarySimulationResult(
                symbol="GC_FUT", direction=FeatureDirection.BUY,
                entry_time=t0, expiry_time=t0,
                entry_price=2750.0, expiry_price=2751.0,
                pnl=0.85, outcome=SimulationOutcome.WIN, payout_rate=0.85,
                decision=DecisionType.CALL
            ))
        for i in range(40):
            sample_trades.append(BinarySimulationResult(
                symbol="GC_FUT", direction=FeatureDirection.BUY,
                entry_time=t0, expiry_time=t0,
                entry_price=2750.0, expiry_price=2749.0,
                pnl=-1.0, outcome=SimulationOutcome.LOSS, payout_rate=0.85,
                decision=DecisionType.CALL
            ))

        mc_res = mc.run_simulation(sample_trades)
        assert mc_res.simulations_count == 1000
        assert mc_res.median_max_drawdown >= 0.0
        assert mc_res.worst_1_pct_drawdown >= mc_res.median_max_drawdown
        assert "streak_4_plus" in mc_res.losing_streak_probability
