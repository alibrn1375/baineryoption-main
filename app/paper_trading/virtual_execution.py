"""Virtual Execution Engine simulating order fills, entry slippage, delays, and 5M expiry settlement."""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import uuid

from app.models.binary_decision import BinaryDecision, DecisionType
from app.models.paper_trade import PaperTrade, PaperTradeStatus
from app.orderflow_engine.base import FeatureDirection
from app.paper_trading.virtual_account import VirtualAccount
from app.validation_engine.binary_simulator import BinarySimulationConfig, TieHandlingRule


class VirtualExecutionEngine:
    """Manages simulated live execution, order fill emulation, active positions, and contract settlements."""

    def __init__(
        self,
        account: VirtualAccount,
        config: Optional[BinarySimulationConfig] = None,
        default_stake: float = 25.0
    ) -> None:
        self.account = account
        self.config = config or BinarySimulationConfig()
        self.default_stake = default_stake

        self._pending_orders: List[PaperTrade] = []
        self._open_positions: List[PaperTrade] = []
        self._settled_trades: List[PaperTrade] = []

    @property
    def open_positions(self) -> List[PaperTrade]:
        return list(self._open_positions)

    def submit_decision(self, decision: BinaryDecision, current_price: float) -> Optional[PaperTrade]:
        """Convert an actionable DecisionArbiter decision into a simulated pending paper trade."""
        if decision.decision not in (DecisionType.CALL, DecisionType.PUT):
            return None

        # Check account funds
        if not self.account.allocate_stake(self.default_stake):
            return None

        trade_id = f"PT_{uuid.uuid4().hex[:8].upper()}"

        trade = PaperTrade(
            trade_id=trade_id,
            timestamp=decision.timestamp,
            symbol=decision.symbol,
            direction=decision.direction,
            expiry_minutes=decision.expiry_minutes,
            stake_amount=self.default_stake,
            payout_percentage=self.config.payout_percentage,
            setup_name=decision.setup_evaluation.setup_name if decision.setup_evaluation else "N/A",
            probability=decision.confidence,
            quality_score=decision.quality_score,
            status=PaperTradeStatus.PENDING,
            explanation=decision.explanation
        )

        self._pending_orders.append(trade)
        return trade

    def process_order_fills(self, current_time: datetime, current_price: float) -> List[PaperTrade]:
        """Transition PENDING orders into OPEN positions with simulated broker delay and slippage."""
        filled: List[PaperTrade] = []
        remaining_pending: List[PaperTrade] = []

        half_spread = self.config.spread_assumption / 2.0
        slippage = self.config.execution_slippage

        for trade in self._pending_orders:
            # Entry price adjustment based on direction
            if trade.direction == FeatureDirection.BUY:
                fill_price = current_price + half_spread + slippage
            else:
                fill_price = current_price - half_spread - slippage

            entry_time = current_time + timedelta(milliseconds=self.config.entry_delay_ms)
            expiry_time = current_time + timedelta(minutes=trade.expiry_minutes)

            open_trade = PaperTrade(
                trade_id=trade.trade_id,
                timestamp=trade.timestamp,
                symbol=trade.symbol,
                direction=trade.direction,
                expiry_minutes=trade.expiry_minutes,
                stake_amount=trade.stake_amount,
                payout_percentage=trade.payout_percentage,
                entry_price=round(fill_price, 4),
                entry_time=entry_time,
                expiry_time=expiry_time,
                setup_name=trade.setup_name,
                probability=trade.probability,
                quality_score=trade.quality_score,
                status=PaperTradeStatus.OPEN,
                explanation=trade.explanation
            )

            self._open_positions.append(open_trade)
            filled.append(open_trade)

        self._pending_orders = remaining_pending
        return filled

    def process_expiries(self, current_time: datetime, current_price: float) -> List[PaperTrade]:
        """Check open positions against current timestamp and settle expired contracts."""
        settled_now: List[PaperTrade] = []
        remaining_open: List[PaperTrade] = []

        for trade in self._open_positions:
            if trade.expiry_time and current_time >= trade.expiry_time:
                # Settle trade
                outcome_status: PaperTradeStatus
                pnl: float = 0.0

                if trade.direction == FeatureDirection.BUY:  # CALL
                    if current_price > trade.entry_price:
                        outcome_status = PaperTradeStatus.WIN
                        pnl = trade.stake_amount * trade.payout_percentage
                    elif current_price < trade.entry_price:
                        outcome_status = PaperTradeStatus.LOSS
                        pnl = -trade.stake_amount
                    else:
                        outcome_status = PaperTradeStatus.EXPIRED if self.config.tie_handling == TieHandlingRule.REFUND else PaperTradeStatus.LOSS
                        pnl = 0.0 if self.config.tie_handling == TieHandlingRule.REFUND else -trade.stake_amount

                else:  # PUT
                    if current_price < trade.entry_price:
                        outcome_status = PaperTradeStatus.WIN
                        pnl = trade.stake_amount * trade.payout_percentage
                    elif current_price > trade.entry_price:
                        outcome_status = PaperTradeStatus.LOSS
                        pnl = -trade.stake_amount
                    else:
                        outcome_status = PaperTradeStatus.EXPIRED if self.config.tie_handling == TieHandlingRule.REFUND else PaperTradeStatus.LOSS
                        pnl = 0.0 if self.config.tie_handling == TieHandlingRule.REFUND else -trade.stake_amount

                settled_trade = PaperTrade(
                    trade_id=trade.trade_id,
                    timestamp=trade.timestamp,
                    symbol=trade.symbol,
                    direction=trade.direction,
                    expiry_minutes=trade.expiry_minutes,
                    stake_amount=trade.stake_amount,
                    payout_percentage=trade.payout_percentage,
                    entry_price=trade.entry_price,
                    entry_time=trade.entry_time,
                    expiry_time=trade.expiry_time,
                    expiry_price=round(current_price, 4),
                    setup_name=trade.setup_name,
                    probability=trade.probability,
                    quality_score=trade.quality_score,
                    pnl=round(pnl, 2),
                    status=outcome_status,
                    explanation=trade.explanation
                )

                # Update virtual account state
                self.account.settle_trade(settled_trade)
                self._settled_trades.append(settled_trade)
                settled_now.append(settled_trade)

            else:
                remaining_open.append(trade)

        self._open_positions = remaining_open
        return settled_now
