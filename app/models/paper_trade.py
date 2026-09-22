"""Paper Trading domain models defining virtual trade states, lifecycles, and account representations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.orderflow_engine.base import FeatureDirection


class PaperTradeStatus(str, Enum):
    """Lifecycle states of a simulated paper contract."""
    PENDING = "PENDING"      # Order generated, awaiting simulated entry fill
    OPEN = "OPEN"            # Active contract, awaiting 5M expiry
    EXPIRED = "EXPIRED"      # Reached expiry, awaiting settlement
    WIN = "WIN"              # Settled in profit
    LOSS = "LOSS"            # Settled in loss
    CANCELLED = "CANCELLED"  # Aborted prior to fill (e.g. risk guard block)


class PaperTrade(BaseModel):
    """Discrete simulated binary options contract record."""
    trade_id: str = Field(..., description="Unique paper trade identifier")
    timestamp: datetime = Field(..., description="Trade signal generation timestamp (UTC)")
    symbol: str = Field(..., description="Asset symbol (GC_FUT, XAUUSD)")
    direction: FeatureDirection = Field(..., description="Directional polarity (BUY/CALL or SELL/PUT)")
    expiry_minutes: int = Field(default=5, ge=1, description="Expiry duration in minutes")
    stake_amount: float = Field(default=10.0, gt=0.0, description="Virtual stake amount in USD")
    payout_percentage: float = Field(default=0.85, ge=0.0, description="Broker payout percentage")
    entry_price: Optional[float] = Field(default=None, description="Actual simulated fill price")
    entry_time: Optional[datetime] = Field(default=None, description="Simulated order execution timestamp")
    expiry_time: Optional[datetime] = Field(default=None, description="Scheduled expiry timestamp")
    expiry_price: Optional[float] = Field(default=None, description="Price at expiry settlement")
    setup_name: str = Field(default="N/A", description="Name of triggering setup")
    probability: float = Field(default=0.0, description="Estimated statistical win probability")
    quality_score: float = Field(default=0.0, description="Composite setup quality score [0-100]")
    pnl: float = Field(default=0.0, description="Net dollar PnL realized")
    status: PaperTradeStatus = Field(default=PaperTradeStatus.PENDING, description="Current trade lifecycle status")
    explanation: Optional[str] = Field(default=None, description="Full multi-pillar decision rationale")
    notes: Dict[str, Any] = Field(default_factory=dict, description="Diagnostic telemetry")

    model_config = {
        "frozen": True
    }


class VirtualAccountState(BaseModel):
    """Snapshot of virtual paper account equity, exposure, and performance metrics."""
    balance: float = Field(..., description="Current virtual cash balance")
    starting_balance: float = Field(..., description="Initial starting balance")
    equity: float = Field(..., description="Total equity (balance + open position values)")
    total_trades: int = Field(default=0, description="Total completed virtual trades")
    wins: int = Field(default=0, description="Total winning trades")
    losses: int = Field(default=0, description="Total losing trades")
    ties: int = Field(default=0, description="Total tied / refunded trades")
    win_rate: float = Field(default=0.0, description="Historical win rate")
    consecutive_losses: int = Field(default=0, description="Current active consecutive loss count")
    max_consecutive_losses: int = Field(default=0, description="Peak consecutive losses observed")
    peak_balance: float = Field(..., description="Highest historical balance achieved")
    drawdown_amount: float = Field(default=0.0, description="Current peak-to-valley dollar drawdown")
    drawdown_percentage: float = Field(default=0.0, description="Current percentage drawdown from peak")
    max_drawdown_percentage: float = Field(default=0.0, description="Maximum historical drawdown percentage")

    model_config = {
        "frozen": True
    }
