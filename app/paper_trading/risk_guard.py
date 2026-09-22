"""Paper Trading Risk Guard preventing unrealistic testing and enforcing account limits."""

from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.footprint import FootprintQuality
from app.models.market_context import MarketContext, NewsRiskLevel, VolatilityLevel
from app.models.paper_trade import VirtualAccountState


class RiskStatus(BaseModel):
    """Result of paper trading risk and health check."""
    allowed: bool = Field(..., description="True if safe to execute new virtual trade")
    blocked: bool = Field(..., description="True if halted by risk guard")
    reason: Optional[str] = Field(default=None, description="Detailed halt reason")

    model_config = {
        "frozen": True
    }


class PaperRiskGuard:
    """Monitors live testing constraints, preventing catastrophic drawdown and bad-data trading."""

    def __init__(
        self,
        max_daily_trades: int = 20,
        max_consecutive_losses: int = 3,
        max_drawdown_pct: float = 15.0
    ) -> None:
        self.max_daily_trades = max_daily_trades
        self.max_consecutive_losses = max_consecutive_losses
        self.max_drawdown_pct = max_drawdown_pct

    def check_trade_safety(
        self,
        account_state: VirtualAccountState,
        mkt_ctx: MarketContext,
        daily_trades_count: int
    ) -> RiskStatus:
        """Validate whether a new virtual trade passes all risk constraints."""
        # 1. Daily Trade Cap
        if daily_trades_count >= self.max_daily_trades:
            return RiskStatus(
                allowed=False,
                blocked=True,
                reason=f"Daily trade limit ({self.max_daily_trades}) reached. Trading halted for session."
            )

        # 2. Consecutive Loss Limit
        if account_state.consecutive_losses >= self.max_consecutive_losses:
            return RiskStatus(
                allowed=False,
                blocked=True,
                reason=f"Consecutive losses ({account_state.consecutive_losses}) hit maximum threshold ({self.max_consecutive_losses}). Cooldown engaged."
            )

        # 3. Maximum Drawdown
        if account_state.drawdown_percentage >= self.max_drawdown_pct:
            return RiskStatus(
                allowed=False,
                blocked=True,
                reason=f"Account drawdown ({account_state.drawdown_percentage:.1f}%) breached limit ({self.max_drawdown_pct:.1f}%)."
            )

        # 4. News Blackout
        if mkt_ctx.news.blocked or mkt_ctx.news.risk_level in (NewsRiskLevel.HIGH, NewsRiskLevel.CRITICAL):
            return RiskStatus(
                allowed=False,
                blocked=True,
                reason="Macroeconomic news blackout active."
            )

        # 5. Volatility Shock
        if mkt_ctx.volatility.level == VolatilityLevel.EXTREME:
            return RiskStatus(
                allowed=False,
                blocked=True,
                reason="Extreme market volatility detected. Paper trading suspended."
            )

        # 6. Data Integrity
        if mkt_ctx.data_quality not in (FootprintQuality.HIGH_PRECISION, FootprintQuality.INTERPOLATED):
            return RiskStatus(
                allowed=False,
                blocked=True,
                reason="Degraded tick feed data quality."
            )

        return RiskStatus(allowed=True, blocked=False, reason=None)
