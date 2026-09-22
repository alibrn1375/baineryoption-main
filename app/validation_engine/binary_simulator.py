"""Binary Options Simulator with realistic execution delays, slippage, spread, and tie handling."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from app.models.binary_decision import BinaryDecision, DecisionType
from app.orderflow_engine.base import FeatureDirection


class SimulationOutcome(str, Enum):
    """Standardized binary option expiry outcome."""
    WIN = "WIN"
    LOSS = "LOSS"
    TIE = "TIE"


class TieHandlingRule(str, Enum):
    """Execution policy when expiry_price == entry_price."""
    REFUND = "REFUND"  # Return 100% investment ($0 profit/loss)
    LOSS = "LOSS"      # Treated as complete loss (-$1.0)
    HALF_LOSS = "HALF_LOSS"  # Return 50% of investment (-$0.5)


class BinarySimulationConfig(BaseModel):
    """Configurable execution assumptions for binary contract simulation."""
    entry_delay_ms: int = Field(default=200, ge=0, description="Broker transmission and order processing delay in milliseconds")
    expiry_minutes: int = Field(default=5, ge=1, description="Expiry duration in minutes")
    payout_percentage: float = Field(default=0.85, ge=0.0, le=1.0, description="Broker payout percentage (0.85 = 85%)")
    spread_assumption: float = Field(default=0.10, ge=0.0, description="Bid/Ask spread penalty in price points")
    execution_slippage: float = Field(default=0.05, ge=0.0, description="Adverse slippage applied on entry in price points")
    tie_handling: TieHandlingRule = Field(default=TieHandlingRule.REFUND, description="Rule when expiry_price == entry_price")

    model_config = {
        "frozen": True
    }


class BinarySimulationResult(BaseModel):
    """Result record of an executed binary options trade simulation."""
    symbol: str = Field(..., description="Asset symbol")
    direction: FeatureDirection = Field(..., description="Trade direction (BUY/CALL or SELL/PUT)")
    entry_time: datetime = Field(..., description="Simulated order fill timestamp (UTC)")
    expiry_time: datetime = Field(..., description="Contract expiry timestamp (UTC)")
    entry_price: float = Field(..., description="Adjusted fill price (including slippage & spread)")
    expiry_price: float = Field(..., description="Exact price at expiry")
    pnl: float = Field(..., description="Net dollar PnL per $1.0 stake")
    outcome: SimulationOutcome = Field(..., description="WIN, LOSS, or TIE")
    payout_rate: float = Field(..., description="Payout percentage applied")
    decision: DecisionType = Field(..., description="Original decision trigger")
    quality_score: float = Field(default=0.0, description="Quality score of the setup")
    notes: Optional[str] = Field(default=None, description="Diagnostic execution details")

    model_config = {
        "frozen": True
    }


class BinarySimulator:
    """Simulates realistic binary options contract execution without lookahead."""

    def __init__(self, config: Optional[BinarySimulationConfig] = None) -> None:
        self.config = config or BinarySimulationConfig()

    def simulate_trade(
        self,
        decision: BinaryDecision,
        raw_entry_price: float,
        raw_expiry_price: float,
        bar_start_time: datetime
    ) -> Optional[BinarySimulationResult]:
        """Simulate trade entry and expiry outcome with explicit delay, spread, and slippage."""
        if decision.decision not in (DecisionType.CALL, DecisionType.PUT):
            return None

        # 1. Calculate Entry Timestamp with Delay
        entry_time = bar_start_time + timedelta(milliseconds=self.config.entry_delay_ms)
        expiry_time = bar_start_time + timedelta(minutes=self.config.expiry_minutes)

        # 2. Adjust Entry Price with Adverse Slippage & Half-Spread
        half_spread = self.config.spread_assumption / 2.0
        slippage = self.config.execution_slippage

        if decision.decision == DecisionType.CALL:
            # Buying CALL at Ask: raw + half_spread + slippage
            adjusted_entry = raw_entry_price + half_spread + slippage
        else:
            # Buying PUT at Bid: raw - half_spread - slippage
            adjusted_entry = raw_entry_price - half_spread - slippage

        adjusted_entry = round(adjusted_entry, 4)
        expiry_price = round(raw_expiry_price, 4)

        # 3. Determine Outcome
        outcome: SimulationOutcome
        pnl: float

        payout = self.config.payout_percentage

        if decision.decision == DecisionType.CALL:
            if expiry_price > adjusted_entry:
                outcome = SimulationOutcome.WIN
                pnl = payout
            elif expiry_price < adjusted_entry:
                outcome = SimulationOutcome.LOSS
                pnl = -1.0
            else:
                outcome = SimulationOutcome.TIE
                pnl = 0.0 if self.config.tie_handling == TieHandlingRule.REFUND else (-1.0 if self.config.tie_handling == TieHandlingRule.LOSS else -0.5)

        else:  # PUT
            if expiry_price < adjusted_entry:
                outcome = SimulationOutcome.WIN
                pnl = payout
            elif expiry_price > adjusted_entry:
                outcome = SimulationOutcome.LOSS
                pnl = -1.0
            else:
                outcome = SimulationOutcome.TIE
                pnl = 0.0 if self.config.tie_handling == TieHandlingRule.REFUND else (-1.0 if self.config.tie_handling == TieHandlingRule.LOSS else -0.5)

        return BinarySimulationResult(
            symbol=decision.symbol,
            direction=decision.direction,
            entry_time=entry_time,
            expiry_time=expiry_time,
            entry_price=adjusted_entry,
            expiry_price=expiry_price,
            pnl=round(pnl, 4),
            outcome=outcome,
            payout_rate=payout,
            decision=decision.decision,
            quality_score=decision.quality_score,
            notes=f"Delay: {self.config.entry_delay_ms}ms, Spread: {self.config.spread_assumption}, Slippage: {self.config.execution_slippage}"
        )
