"""Comprehensive test suite for the FO-X 5M Market Context Engine."""

import tempfile
from datetime import datetime, timezone
import pytest

from app.context_engine.liquidity_engine import LiquidityEngine
from app.context_engine.liquidity_sweep import LiquiditySweepDetector
from app.context_engine.news_guard import NewsGuard
from app.context_engine.pipeline import MarketContextPipeline
from app.context_engine.regime_detector import RegimeDetector
from app.context_engine.session_detector import SessionDetector
from app.context_engine.structure_analyzer import StructureAnalyzer
from app.context_engine.swing_detector import SwingDetector
from app.context_engine.volatility_analyzer import VolatilityAnalyzer
from app.models.footprint import FootprintBar
from app.models.liquidity import LiquidityEventType, LiquidityZone, LiquidityZoneType
from app.models.market_context import NewsRiskLevel, TradingSessionName, VolatilityLevel
from app.models.market_structure import StructureEventType, StructureState, SwingType
from app.storage.context_storage import ContextStorage


class TestSwingAndStructure:
    """Test suite for Swing detection and BOS/MSS analysis."""

    def test_swing_pivot_detection(self) -> None:
        detector = SwingDetector(swing_length=2)  # Window size = 5 bars
        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)

        # Build 5 bars with center bar (index 2) having highest high
        highs = [2750.0, 2752.0, 2760.0, 2755.0, 2753.0]
        swings = []
        for i, h in enumerate(highs):
            bar = FootprintBar(
                symbol="GC_FUT",
                start_time=datetime(2026, 8, 30, 10, i * 5, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 8, 30, 10, (i + 1) * 5, 0, tzinfo=timezone.utc),
                open=2750.0, high=h, low=2749.0, close=2750.0, total_volume=100.0
            )
            sw = detector.process_bar(bar)
            if sw:
                swings.append(sw)

        assert len(swings) == 1
        assert swings[0].type == SwingType.SWING_HIGH
        assert swings[0].price == 2760.0

    def test_break_of_structure_bos(self) -> None:
        detector = SwingDetector(swing_length=1)  # Window size = 3
        analyzer = StructureAnalyzer(swing_detector=detector, bos_min_ticks=2, tick_size=0.10)

        # 1. Establish Swing High at 2755.0
        highs = [2750.0, 2755.0, 2752.0]
        for i, h in enumerate(highs):
            bar = FootprintBar(
                symbol="GC_FUT",
                start_time=datetime(2026, 8, 30, 10, i * 5, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 8, 30, 10, (i + 1) * 5, 0, tzinfo=timezone.utc),
                open=2750.0, high=h, low=2749.0, close=h - 1.0, total_volume=100.0
            )
            analyzer.analyze_bar(bar)

        # 2. Break above 2755.0 with close at 2758.0 (> 2755.0 + 0.2)
        break_bar = FootprintBar(
            symbol="GC_FUT",
            start_time=datetime(2026, 8, 30, 10, 20, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 30, 10, 25, 0, tzinfo=timezone.utc),
            open=2752.0, high=2759.0, low=2751.0, close=2758.0, total_volume=200.0
        )
        state = analyzer.analyze_bar(break_bar)
        assert state.current_state == StructureState.TREND_UP
        assert state.last_event is not None
        assert state.last_event.price == 2758.0


class TestLiquidityEngineAndSweep:
    """Test suite for Equal Highs/Lows and Sweep Rejections."""

    def test_liquidity_sweep_rejection(self) -> None:
        sweep_detector = LiquiditySweepDetector(sweep_rejection_pct=0.40, tick_size=0.10)

        # Create active Equal Highs zone at 2760.0
        zone = LiquidityZone(
            price=2760.0,
            upper_price=2760.3,
            lower_price=2759.7,
            zone_type=LiquidityZoneType.EQUAL_HIGHS,
            strength=2.0,
            created_time=datetime(2026, 8, 30, 9, 0, 0, tzinfo=timezone.utc),
            touch_count=2,
            is_mitigated=False
        )

        # Bar pierces 2760.0 reaching 2763.0, but closes back down at 2759.0 (Upper wick = 4.0 / 5.0 range = 80% wick)
        sweep_bar = FootprintBar(
            symbol="GC_FUT",
            start_time=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc),
            open=2758.0, high=2763.0, low=2758.0, close=2759.0, total_volume=300.0
        )

        event, updated_zones = sweep_detector.evaluate_bar(sweep_bar, [zone])
        assert event is not None
        assert event.event_type == LiquidityEventType.SWEEP_HIGH
        assert event.penetration_ticks == 30.0  # (2763 - 2760) / 0.1
        assert event.reaction_score >= 0.70
        assert updated_zones[0].is_mitigated is True


class TestNewsGuardAndSessions:
    """Test suite for Macro news quarantine and trading sessions."""

    def test_news_quarantine_blackout(self) -> None:
        guard = NewsGuard(quarantine_before_minutes=15, quarantine_after_minutes=20)
        nfp_time = datetime(2026, 8, 30, 12, 30, 0, tzinfo=timezone.utc)
        guard.set_events([
            {"timestamp": nfp_time, "title": "US Non-Farm Payrolls", "impact": "CRITICAL"}
        ])

        # Test 10 minutes before event -> Must be blocked
        t_before = datetime(2026, 8, 30, 12, 20, 0, tzinfo=timezone.utc)
        state_before = guard.evaluate_news_state(t_before)
        assert state_before.event_active is True
        assert state_before.blocked is True
        assert state_before.risk_level == NewsRiskLevel.CRITICAL

        # Test 1 hour after event -> Normal operation
        t_after = datetime(2026, 8, 30, 13, 31, 0, tzinfo=timezone.utc)
        state_after = guard.evaluate_news_state(t_after)
        assert state_after.blocked is False
        assert state_after.risk_level == NewsRiskLevel.NONE

    def test_session_detection_london_ny_overlap(self) -> None:
        detector = SessionDetector()
        t_overlap = datetime(2026, 8, 30, 14, 0, 0, tzinfo=timezone.utc)
        session = detector.detect_session(t_overlap)
        assert session.name == TradingSessionName.OVERLAP_LONDON_NY
