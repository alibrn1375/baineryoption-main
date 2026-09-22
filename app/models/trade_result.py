"""Binary options settlement and trade result domain models."""

from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from pydantic import BaseModel, Field, model_validator
from app.models.decision import DecisionAction


class TradeOutcome(str, Enum):
    """Discrete binary settlement outcome."""
    WIN = "WIN"        # Profit realized (+ payout * stake)
    LOSS = "LOSS"      # Loss of stake (- 1.0 * stake)
    TIE = "TIE"        # At-the-money refund (0.0 PnL)


class TradeResult(BaseModel):
    """Full lifecycle execution and expiration record of a 5-minute trade."""
    trade_id: str = Field(..., description="Unique trade execution identifier")
    symbol: str = Field(..., description="Traded symbol (e.g. GC_FUT)")
    direction: DecisionAction = Field(..., description="CALL or PUT direction")
    entry_time: datetime = Field(..., description="Trade entry timestamp (UTC)")
    expiry_time: datetime = Field(..., description="Trade settlement timestamp (5m expiry, UTC)")
    entry_price: float = Field(..., gt=0.0, description="Price at execution fill")
    exit_price: float = Field(..., gt=0.0, description="Final price at expiration tick")
    stake: float = Field(default=100.0, gt=0.0, description="Capital staked on the trade")
    payout_rate: float = Field(default=0.85, ge=0.5, le=1.0, description="Broker payout rate")
    outcome: TradeOutcome = Field(..., description="WIN, LOSS, or TIE")
    pnl: float = Field(..., description="Realized profit or loss in currency units")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Execution round-trip latency in ms")
    slippage_ticks: float = Field(default=0.0, description="Slippage incurred at entry in ticks")
    meta: Dict[str, str] = Field(default_factory=dict, description="Diagnostic tags (setup, session, regime)")

    @model_validator(mode="after")
    def validate_pnl_consistency(self) -> "TradeResult":
        if self.outcome == TradeOutcome.WIN and self.pnl <= 0.0:
            raise ValueError(f"Outcome WIN must have positive pnl, got {self.pnl}")
        if self.outcome == TradeOutcome.LOSS and self.pnl >= 0.0:
            raise ValueError(f"Outcome LOSS must have negative pnl, got {self.pnl}")
        if self.outcome == TradeOutcome.TIE and self.pnl != 0.0:
            raise ValueError(f"Outcome TIE must have 0.0 pnl, got {self.pnl}")
        return self

    model_config = {
        "frozen": True
    }
