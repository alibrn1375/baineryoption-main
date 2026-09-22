"""Virtual Account tracking balance, equity, drawdowns, and trade histories without real money."""

from typing import List, Optional
from app.models.paper_trade import PaperTrade, PaperTradeStatus, VirtualAccountState


class VirtualAccount:
    """Manages virtual trading account balance, position allocations, and risk state metrics."""

    def __init__(self, starting_balance: float = 10000.0) -> None:
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.peak_balance = starting_balance

        self.total_trades: int = 0
        self.wins: int = 0
        self.losses: int = 0
        self.ties: int = 0

        self.consecutive_losses: int = 0
        self.max_consecutive_losses: int = 0
        self.max_drawdown_pct: float = 0.0

        self._trade_history: List[PaperTrade] = []

    def get_state(self, open_positions_stake: float = 0.0) -> VirtualAccountState:
        """Return an immutable snapshot of current account financial and risk state."""
        dd_amount = max(0.0, self.peak_balance - self.balance)
        dd_pct = (dd_amount / self.peak_balance) * 100.0 if self.peak_balance > 0 else 0.0
        win_rate = (self.wins / self.total_trades) if self.total_trades > 0 else 0.0

        return VirtualAccountState(
            balance=round(self.balance, 2),
            starting_balance=round(self.starting_balance, 2),
            equity=round(self.balance + open_positions_stake, 2),
            total_trades=self.total_trades,
            wins=self.wins,
            losses=self.losses,
            ties=self.ties,
            win_rate=round(win_rate, 4),
            consecutive_losses=self.consecutive_losses,
            max_consecutive_losses=self.max_consecutive_losses,
            peak_balance=round(self.peak_balance, 2),
            drawdown_amount=round(dd_amount, 2),
            drawdown_percentage=round(dd_pct, 2),
            max_drawdown_percentage=round(self.max_drawdown_pct, 2)
        )

    def allocate_stake(self, stake: float) -> bool:
        """Deduct stake from cash balance upon order placement. Returns False if insufficient funds."""
        if stake <= 0.0 or stake > self.balance:
            return False
        self.balance -= stake
        return True

    def settle_trade(self, trade: PaperTrade) -> VirtualAccountState:
        """Settle a completed virtual trade and update performance and drawdown trackers."""
        if trade.status == PaperTradeStatus.WIN:
            # Return original stake + net profit
            net_profit = trade.stake_amount * trade.payout_percentage
            self.balance += (trade.stake_amount + net_profit)
            self.wins += 1
            self.consecutive_losses = 0

        elif trade.status == PaperTradeStatus.LOSS:
            # Stake already deducted on allocation
            self.losses += 1
            self.consecutive_losses += 1
            if self.consecutive_losses > self.max_consecutive_losses:
                self.max_consecutive_losses = self.consecutive_losses

        elif trade.status in (PaperTradeStatus.CANCELLED, PaperTradeStatus.EXPIRED):
            # Refund 100% stake
            self.balance += trade.stake_amount
            self.ties += 1

        self.total_trades += 1
        self._trade_history.append(trade)

        # Update high-water mark & max drawdown
        if self.balance > self.peak_balance:
            self.peak_balance = self.balance

        current_dd = max(0.0, self.peak_balance - self.balance)
        current_dd_pct = (current_dd / self.peak_balance) * 100.0 if self.peak_balance > 0 else 0.0
        if current_dd_pct > self.max_drawdown_pct:
            self.max_drawdown_pct = current_dd_pct

        return self.get_state()
