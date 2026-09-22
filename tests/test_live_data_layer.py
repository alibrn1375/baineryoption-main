"""Comprehensive test suite for the FO-X 5M Live Data Integration Layer."""

import asyncio
from datetime import datetime, timezone
import pytest

from app.data_layer.connection_manager import ConnectionManager
from app.data_layer.data_quality import DataQualityMonitor
from app.data_layer.event_bus import RealTimeEventBus
from app.data_layer.providers.base_provider import MarketDataProvider, ProviderConnectionStatus
from app.data_layer.tick_normalizer import TickNormalizer
from app.models.tick import MarketTick, TickSide


class DummyMockProvider(MarketDataProvider):
    """Mock provider for unit testing callbacks and connection events."""

    def __init__(self) -> None:
        super().__init__(name="MOCK_PROVIDER")

    async def connect(self) -> bool:
        self.status = ProviderConnectionStatus.CONNECTED
        return True

    async def disconnect(self) -> None:
        self.status = ProviderConnectionStatus.DISCONNECTED
        self._emit_disconnect()

    async def subscribe(self, symbols) -> bool:
        return True

    async def unsubscribe(self, symbols) -> bool:
        return True

    def get_status(self) -> ProviderConnectionStatus:
        return self.status

    def inject_tick(self, tick: MarketTick) -> None:
        self._emit_tick(tick)


class TestTickNormalizer:
    """Test suite verifying payload normalization, symbol translation, and tick conversion."""

    def test_normalize_raw_tick(self) -> None:
        raw_payload = {
            "symbol": "GC",
            "last": 2750.25,
            "best_bid": 2750.20,
            "best_ask": 2750.30,
            "qty": 5.0,
            "side": "BUY",
            "timestamp": "2026-08-30T10:00:00Z",
            "seq": 101
        }

        tick = TickNormalizer.normalize_raw_tick(raw_payload, provider_name="TEST")
        assert tick.symbol == "GC_FUT"
        assert tick.price == 2750.25
        assert tick.bid == 2750.20
        assert tick.ask == 2750.30
        assert tick.volume == 5.0
        assert tick.side == TickSide.BUY
        assert tick.sequence_number == 101

        # Test standard tick conversion
        std_tick = tick.to_standard_tick()
        assert std_tick.symbol == "GC_FUT"
        assert std_tick.side == TickSide.BUY


class TestDataQualityMonitor:
    """Test suite for quality scores, gap detection, and spread anomalies."""

    def test_quality_score_and_gap_detection(self) -> None:
        monitor = DataQualityMonitor(max_acceptable_latency_ms=100.0, max_acceptable_spread_points=1.0)
        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)

        # 1. Clean Tick (Seq 1)
        tick_clean = MarketTick(
            timestamp=t0, symbol="GC_FUT", price=2750.0, bid=2749.9, ask=2750.1,
            volume=1.0, side=TickSide.BUY, sequence_number=1
        )
        report1 = monitor.inspect_tick(tick_clean, current_time=t0)
        assert report1.quality_score == 100.0
        assert report1.missing_ticks_count == 0

        # 2. Dropped Ticks (Seq jumps from 1 to 5 -> missed 3 ticks)
        tick_jump = MarketTick(
            timestamp=t0, symbol="GC_FUT", price=2750.0, bid=2749.9, ask=2750.1,
            volume=1.0, side=TickSide.BUY, sequence_number=5
        )
        report2 = monitor.inspect_tick(tick_jump, current_time=t0)
        assert report2.missing_ticks_count == 3
        assert report2.quality_score < 100.0
        assert any("Sequence gap" in issue for issue in report2.issues)


@pytest.mark.asyncio
async def test_event_bus_and_connection_manager() -> None:
    """Test async event bus queuing and connection manager status tracking."""
    # 1. Test Event Bus
    bus = RealTimeEventBus(max_queue_size=100)
    received_ticks = []

    bus.subscribe(lambda t: received_ticks.append(t))
    await bus.start()

    t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
    tick = MarketTick(
        timestamp=t0, symbol="GC_FUT", price=2750.0, bid=2749.9, ask=2750.1,
        volume=1.0, side=TickSide.BUY, sequence_number=1
    )

    await bus.publish(tick)
    await asyncio.sleep(0.05)  # Allow async queue consumption
    await bus.stop()

    assert len(received_ticks) == 1
    assert received_ticks[0].symbol == "GC_FUT"

    # 2. Test Connection Manager
    mock_prov = DummyMockProvider()
    mgr = ConnectionManager(mock_prov)
    connected = await mgr.start()
    assert connected is True

    status = mgr.get_status()
    assert status.connected is True
    assert status.status == ProviderConnectionStatus.CONNECTED

    await mgr.stop()
    assert mock_prov.get_status() == ProviderConnectionStatus.DISCONNECTED
