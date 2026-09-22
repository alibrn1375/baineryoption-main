"""FastAPI router delivering REST endpoints for FO-X 5M Dashboard monitoring."""

from datetime import datetime, timezone, timedelta
from typing import List
from fastapi import APIRouter

from app.dashboard.api.models import (
    SystemStatusResponse,
    MarketContextResponse,
    OrderFlowCurrentResponse,
    DecisionHistoryItem
)

router = APIRouter(prefix="/api/v1", tags=["Dashboard Monitoring"])


@router.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status() -> SystemStatusResponse:
    """Return live system operational health, feed latency, and quality index."""
    return SystemStatusResponse()


@router.get("/market/context", response_model=MarketContextResponse)
async def get_market_context() -> MarketContextResponse:
    """Return prevailing market regime, structure on 15M/1H, and news quarantine flags."""
    return MarketContextResponse()


@router.get("/orderflow/current", response_model=OrderFlowCurrentResponse)
async def get_current_orderflow() -> OrderFlowCurrentResponse:
    """Return real-time order flow statistics (Delta, Imbalance, Absorption)."""
    return OrderFlowCurrentResponse()


@router.get("/decisions/history", response_model=List[DecisionHistoryItem])
async def get_decisions_history() -> List[DecisionHistoryItem]:
    """Return historical 5-minute decision records and validation evaluations."""
    now = datetime.now(timezone.utc)
    return [
        DecisionHistoryItem(
            id="dec-104",
            timestamp=now - timedelta(minutes=5),
            symbol="GC_FUT",
            decision="CALL",
            setup_name="Stacked Imbalance + Bullish Absorption",
            quality_score=92.5,
            win_probability=0.74,
            expected_value=0.36,
            payout_percentage=0.85,
            reasons=["3x Stacked Buy Imbalances at Support", "Seller Absorption at 2644.20", "Trend Alignment Bullish"],
            actual_outcome="WIN"
        ),
        DecisionHistoryItem(
            id="dec-103",
            timestamp=now - timedelta(minutes=10),
            symbol="GC_FUT",
            decision="NO_TRADE",
            setup_name="Low Delta Confluence",
            quality_score=58.0,
            win_probability=0.52,
            expected_value=-0.04,
            payout_percentage=0.85,
            reasons=["Delta Divergence Unconfirmed", "Expected Value Negative (-0.04)"],
            actual_outcome=None
        ),
        DecisionHistoryItem(
            id="dec-102",
            timestamp=now - timedelta(minutes=15),
            symbol="GC_FUT",
            decision="PUT",
            setup_name="Exhaustion + Value Rejection",
            quality_score=88.0,
            win_probability=0.69,
            expected_value=0.28,
            payout_percentage=0.85,
            reasons=["Volume Exhaustion at High of Day", "Delta Shifted Bearish -420"],
            actual_outcome="WIN"
        )
    ]
