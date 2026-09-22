"""Test suite for the FO-X 5M Dashboard REST API and WebSocket Streamer."""

import pytest
from app.dashboard.api.models import SystemStatusResponse, MarketContextResponse, OrderFlowCurrentResponse
from app.dashboard.websocket import DashboardWebSocketManager


def test_dashboard_api_models():
    """Verify default schema serialization and constraints of monitoring models."""
    status = SystemStatusResponse()
    assert status.engine_status == "RUNNING"
    assert status.quality_score > 90.0

    context = MarketContextResponse()
    assert context.regime == "TRENDING_BULLISH"
    assert context.news_quarantine_active is False

    of = OrderFlowCurrentResponse()
    assert of.symbol == "GC_FUT"
    assert of.delta > 0
    assert of.stacked_buy_imbalances >= 0


@pytest.mark.asyncio
async def test_websocket_manager():
    """Verify WebSocket manager connection lifecycle tracking."""
    manager = DashboardWebSocketManager()
    assert len(manager.active_connections) == 0
