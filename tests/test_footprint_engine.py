"""Comprehensive unit and integration test suite for the FO-X 5M Footprint Engine."""

import tempfile
from datetime import datetime, timedelta, timezone
import pytest
import yaml

from app.footprint_engine.bar_aggregator import BarAggregator
from app.footprint_engine.cvd_engine import CVDEngine
from app.footprint_engine.delta_calculator import DeltaCalculator
from app.footprint_engine.pipeline import FootprintPipeline
from app.footprint_engine.price_ladder import PriceLadder
from app.footprint_engine.storage import FootprintStorage
from app.footprint_engine.trade_classifier import TradeClassifier
from app.models.footprint import FootprintQuality, PriceLevel
from app.models.tick import Tick, TradeSide


class TestTradeClassifier:
    """Test suite for aggressive trade side classification."""

    def test_classify_explicit_buy_sell(self) -> None:
        classifier = TradeClassifier()
        t_buy = Tick(
            symbol="GC_FUT",
            timestamp=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
            price=2750.0,
            volume=5.0,
            trade_side=TradeSide.BUY
        )
        res = classifier.classify(t_buy)
        assert res.side == TradeSide.BUY
        assert res.confidence == 1.0

    def test_classify_at_ask_price(self) -> None:
        classifier = TradeClassifier()
        t = Tick(
            symbol="GC_FUT",
            timestamp=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
            price=2750.5,
            volume=1.0,
            bid=2750.4,
            ask=2750.5
        )
        res = classifier.classify(t)
        assert res.side == TradeSide.BUY
        assert res.confidence == 1.0

    def test_classify_at_bid_price(self) -> None:
        classifier = TradeClassifier()
        t = Tick(
            symbol="GC_FUT",
            timestamp=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
            price=2750.4,
            volume=2.0,
            bid=2750.4,
            ask=2750.5
        )
        res = classifier.classify(t)
        assert res.side == TradeSide.SELL
        assert res.confidence == 1.0

    def test_classify_missing_bid_ask_returns_unknown_no_guessing(self) -> None:
        classifier = TradeClassifier()
        t = Tick(
            symbol="GC_FUT",
            timestamp=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
            price=2750.0,
            volume=1.0,
            bid=None,
            ask=None
        )
        res = classifier.classify(t)
        assert res.side == TradeSide.UNKNOWN
        assert res.confidence == 0.0
        assert "unavailable" in res.reason


class TestPriceLadder:
    """Test suite for price ladder discretization and volume accumulation."""

    def test_price_ladder_tick_size_discretization(self) -> None:
        # Tick size 0.1 for GC
        ladder = PriceLadder(tick_size=0.1, price_precision=1)
        ladder.add_trade(2750.04, 10.0, TradeSide.BUY)   # -> 2750.0
        ladder.add_trade(2750.06, 5.0, TradeSide.BUY)    # -> 2750.1
        ladder.add_trade(2750.00, 8.0, TradeSide.SELL)   # -> 2750.0

        levels = ladder.build_levels()
        assert len(levels) == 2
        assert levels[0].price == 2750.0
        assert levels[0].ask_volume == 10.0
        assert levels[0].bid_volume == 8.0
        assert levels[0].delta == 2.0

        assert levels[1].price == 2750.1
        assert levels[1].ask_volume == 5.0
        assert levels[1].bid_volume == 0.0
        assert levels[1].delta == 5.0

    def test_point_of_control_poc(self) -> None:
        ladder = PriceLadder(tick_size=0.1, price_precision=1)
        ladder.add_trade(2750.0, 5.0, TradeSide.BUY)
        ladder.add_trade(2750.1, 50.0, TradeSide.SELL)
        ladder.add_trade(2750.2, 10.0, TradeSide.BUY)

        poc = ladder.get_poc_price()
        assert poc == 2750.1


class TestDeltaCalculator:
    """Test delta calculation formulas."""

    def test_delta_metrics_from_levels(self) -> None:
        levels = [
            PriceLevel(price=2750.0, bid_volume=10.0, ask_volume=20.0),
            PriceLevel(price=2750.1, bid_volume=30.0, ask_volume=5.0),
        ]
        res = DeltaCalculator.calculate_from_levels(levels, running_min_delta=-15.0, running_max_delta=10.0)
        assert res.total_bid_volume == 40.0
        assert res.total_ask_volume == 25.0
        assert res.total_volume == 65.0
        assert res.bar_delta == -15.0
        assert res.delta_percentage == pytest.approx(-23.08, rel=1e-2)
        assert res.min_delta == -15.0


class TestCVDEngine:
    """Test session-aware Cumulative Volume Delta engine."""

    def test_cvd_session_accumulation_and_reset(self) -> None:
        sessions_cfg = {
            "asia": {"name": "ASIA", "start_utc": "00:00:00", "end_utc": "08:00:00"},
            "london": {"name": "LONDON", "start_utc": "08:00:00", "end_utc": "13:30:00"},
        }
        cvd = CVDEngine(sessions_config=sessions_cfg)

        # Bar 1 in Asia
        t1 = datetime(2026, 8, 30, 2, 0, 0, tzinfo=timezone.utc)
        p1 = cvd.update("GC_FUT", t1, 100.0)
        assert p1.session == "ASIA"
        assert p1.cumulative_delta == 100.0

        # Bar 2 in Asia
        t2 = datetime(2026, 8, 30, 2, 5, 0, tzinfo=timezone.utc)
        p2 = cvd.update("GC_FUT", t2, -30.0)
        assert p2.session == "ASIA"
        assert p2.cumulative_delta == 70.0

        # Bar 3 in London -> Session Reset
        t3 = datetime(2026, 8, 30, 8, 0, 0, tzinfo=timezone.utc)
        p3 = cvd.update("GC_FUT", t3, 50.0)
        assert p3.session == "LONDON"
        assert p3.cumulative_delta == 50.0  # Reset to new session start delta


class TestBarAggregatorAndParity:
    """Test bar boundary aggregations and live vs replay parity."""

    def test_five_minute_boundary_creation(self) -> None:
        agg = BarAggregator(symbol="XAUUSD", timeframe_seconds=300, tick_size=0.01, price_precision=2)

        t0 = datetime(2026, 8, 30, 10, 0, 1, tzinfo=timezone.utc)
        t1 = datetime(2026, 8, 30, 10, 2, 30, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 30, 10, 4, 59, tzinfo=timezone.utc)
        t_next = datetime(2026, 8, 30, 10, 5, 1, tzinfo=timezone.utc)

        agg.add_tick(Tick(symbol="XAUUSD", timestamp=t0, price=2750.00, volume=1.0, trade_side=TradeSide.BUY))
        agg.add_tick(Tick(symbol="XAUUSD", timestamp=t1, price=2752.50, volume=2.0, trade_side=TradeSide.BUY))
        agg.add_tick(Tick(symbol="XAUUSD", timestamp=t2, price=2749.50, volume=3.0, trade_side=TradeSide.SELL))

        # Adding tick across 10:05 boundary triggers finalize of 10:00-10:05 bar
        completed_bar = agg.add_tick(Tick(symbol="XAUUSD", timestamp=t_next, price=2751.00, volume=1.0, trade_side=TradeSide.BUY))

        assert completed_bar is not None
        assert completed_bar.symbol == "XAUUSD"
        assert completed_bar.start_time == datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
        assert completed_bar.end_time == datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc)
        assert completed_bar.open == 2750.00
        assert completed_bar.high == 2752.50
        assert completed_bar.low == 2749.50
        assert completed_bar.close == 2749.50
        assert completed_bar.total_volume == 6.0
        assert completed_bar.bar_delta == 0.0  # (1 + 2) Buy - 3 Sell = 0

    def test_live_vs_replay_exact_parity(self) -> None:
        """CRITICAL REQUIREMENT:
        Given the identical historical tick sequence, live processing and batch replay
        must produce exactly identical FootprintBars.
        """
        ticks: list[Tick] = []
        base_time = datetime(2026, 8, 30, 14, 0, 0, tzinfo=timezone.utc)

        # Generate realistic tick sequence
        for i in range(50):
            t = base_time + timedelta(seconds=i * 10)  # spans across 14:00 to 14:08 (2 bars)
            price = 2750.0 + (i % 5) * 0.1
            side = TradeSide.BUY if (i % 2 == 0) else TradeSide.SELL
            ticks.append(Tick(
                symbol="GC_FUT",
                timestamp=t,
                price=price,
                volume=1.0 + (i % 3),
                trade_side=side
            ))

        # Pipeline 1: Live (tick-by-tick)
        with tempfile.TemporaryDirectory() as tmp1:
            storage1 = FootprintStorage(base_directory=tmp1)
            p_live = FootprintPipeline(config_path="configs/orderflow_config.yaml", storage=storage1)
            live_bars: list[FootprintBar] = []
            for tick in ticks:
                bar, _ = p_live.process_tick(tick)
                if bar:
                    live_bars.append(bar)
            # Finalize trailing
            final_bar = p_live._aggregators["GC_FUT"].finalize_bar()
            if final_bar:
                live_bars.append(final_bar)

        # Pipeline 2: Batch Replay
        with tempfile.TemporaryDirectory() as tmp2:
            storage2 = FootprintStorage(base_directory=tmp2)
            p_replay = FootprintPipeline(config_path="configs/orderflow_config.yaml", storage=storage2)
            replay_bars = p_replay.process_ticks_batch(ticks)

        assert len(live_bars) == len(replay_bars)
        assert len(live_bars) >= 2

        for b_live, b_rep in zip(live_bars, replay_bars):
            assert b_live.start_time == b_rep.start_time
            assert b_live.end_time == b_rep.end_time
            assert b_live.open == b_rep.open
            assert b_live.high == b_rep.high
            assert b_live.low == b_rep.low
            assert b_live.close == b_rep.close
            assert b_live.total_volume == b_rep.total_volume
            assert b_live.bar_delta == b_rep.bar_delta
            assert b_live.min_delta == b_rep.min_delta
            assert b_live.max_delta == b_rep.max_delta
            assert b_live.poc_price == b_rep.poc_price
            assert len(b_live.levels) == len(b_rep.levels)
            for l_live, l_rep in zip(b_live.levels, b_rep.levels):
                assert l_live.price == l_rep.price
                assert l_live.bid_volume == l_rep.bid_volume
                assert l_live.ask_volume == l_rep.ask_volume
                assert l_live.delta == l_rep.delta
