"""FastAPI/REST and WebSocket backend endpoints for the FO-X 5M Dashboard."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SystemStatusResponse(BaseModel):
    """System health, pipeline status, and connection states."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    engine_status: str = Field(default="RUNNING", description="RUNNING, PAUSED, DEGRADED, HALTED")
    data_provider: str = Field(default="NINJATRADER", description="Active feed provider")
    connection_state: str = Field(default="CONNECTED", description="CONNECTED, RECONNECTING, DISCONNECTED")
    feed_latency_ms: float = Field(default=3.2, description="Network tick ingestion latency")
    processed_ticks_count: int = Field(default=148520, description="Total processed ticks in session")
    quality_score: float = Field(default=99.4, description="Data stream quality score [0-100]")
    current_symbol: str = Field(default="GC_FUT", description="Active asset")
    active_session: str = Field(default="LONDON_NY_OVERLAP", description="Trading session")


class MarketContextResponse(BaseModel):
    """High Timeframe Structure, Market Regime, Volatility, and Macro News state."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str = Field(default="GC_FUT")
    session: str = Field(default="LONDON_NY_OVERLAP")
    regime: str = Field(default="TRENDING_BULLISH", description="TRENDING_BULLISH, TRENDING_BEARISH, BALANCED_ROTATIONAL, VOLATILITY_EXPANSION")
    structure_15m: str = Field(default="BULLISH_BREAKOUT")
    structure_1h: str = Field(default="BULLISH_TREND")
    volatility_state: str = Field(default="MODERATE_EXPANSION")
    news_quarantine_active: bool = Field(default=False)
    next_news_event: Optional[str] = Field(default="US Core CPI (in 145 min)")
    liquidity_state: str = Field(default="HIGH_DEPTH")


class OrderFlowCurrentResponse(BaseModel):
    """Current 5-minute bar order flow telemetry, Delta, CVD, Imbalance, and Absorption."""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    symbol: str = Field(default="GC_FUT")
    bar_id: str = Field(default="bar-live-5m")
    current_price: float = Field(default=2646.50)
    total_volume: float = Field(default=4820.0)
    delta: float = Field(default=680.0)
    cvd: float = Field(default=3420.0)
    delta_percentage: float = Field(default=14.1)
    stacked_buy_imbalances: int = Field(default=3)
    stacked_sell_imbalances: int = Field(default=0)
    absorption_detected: bool = Field(default=True)
    absorption_level: Optional[float] = Field(default=2644.20)
    exhaustion_detected: bool = Field(default=False)


class DecisionHistoryItem(BaseModel):
    """Individual trade evaluation record from the Decision Engine."""
    id: str
    timestamp: datetime
    symbol: str
    decision: str = Field(..., description="CALL, PUT, or NO_TRADE")
    setup_name: str
    quality_score: float
    win_probability: float
    expected_value: float
    payout_percentage: float
    reasons: List[str]
    actual_outcome: Optional[str] = Field(default=None, description="WIN, LOSS, TIE, or PENDING")
