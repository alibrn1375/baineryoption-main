"""Live Terminal Monitor formatting real-time microstructural state and telemetry."""

from datetime import datetime
from typing import Optional
from app.models.binary_decision import BinaryDecision
from app.models.footprint import FootprintBar
from app.models.market_context import MarketContext
from app.models.orderflow_context import OrderFlowContext
from app.models.paper_trade import VirtualAccountState


class LiveDecisionMonitor:
    """Formats and prints live situational terminal cards for operators during paper trading."""

    @staticmethod
    def format_terminal_card(
        bar: FootprintBar,
        of_ctx: OrderFlowContext,
        mkt_ctx: MarketContext,
        decision: BinaryDecision,
        account_state: VirtualAccountState
    ) -> str:
        """Render a clean, high-density situational telemetry string."""
        border = "═" * 60
        sub_border = "─" * 60

        lines = [
            f"╔{border}╗",
            f"║  FO-X 5M — LIVE REAL-TIME TELEMETRY MONITOR               ║",
            f"╠{sub_border}╣",
            f"║  Asset: {bar.symbol:<10}  Time: {bar.start_time.strftime('%Y-%m-%d %H:%M:%S UTC'):<25} ║",
            f"║  Close: {bar.close:<10.2f}  Delta: {bar.bar_delta:<10.1f}  Volume: {bar.total_volume:<10.0f} ║",
            f"╠{sub_border}╣",
            f"║  MARKET CONTEXT:                                          ║",
            f"║  • Session:  {mkt_ctx.session.name.value:<42} ║",
            f"║  • Regime:   {mkt_ctx.regime.state.value:<42} ║",
            f"║  • Volatility: {mkt_ctx.volatility.level.value} (ATR: {mkt_ctx.volatility.atr_value:.2f}){'':<28} ║",
            f"║  • News State: {'BLACKOUT' if mkt_ctx.news.blocked else 'CLEAN':<40} ║",
            f"╠{sub_border}╣",
            f"║  ORDER FLOW SENSORS:                                      ║",
            f"║  • Stacked Imbalances: {len(of_ctx.stacked_imbalances):<33} ║",
            f"║  • Absorption: {'DETECTED (' + of_ctx.absorption_feature.direction.value + ')' if of_ctx.absorption_feature else 'NONE':<40} ║",
            f"║  • Exhaustion: {'DETECTED' if of_ctx.exhaustion_feature else 'NONE':<42} ║",
            f"╠{sub_border}╣",
            f"║  DECISION ARBITER:                                        ║",
            f"║  • Action:  {decision.decision.value:<43} ║",
            f"║  • Quality Score: {decision.quality_score:<5.1f} / 100{'':<30} ║",
            f"║  • Direction: {decision.direction.value:<41} ║",
            f"╠{sub_border}╣",
            f"║  VIRTUAL ACCOUNT:                                         ║",
            f"║  • Balance: ${account_state.balance:<10.2f}  Equity: ${account_state.equity:<10.2f}          ║",
            f"║  • Trades: {account_state.total_trades} (W: {account_state.wins} / L: {account_state.losses})  Win Rate: {account_state.win_rate*100:.1f}%{'':<13} ║",
            f"║  • Drawdown: {account_state.drawdown_percentage:.1f}% (Max: {account_state.max_drawdown_percentage:.1f}%){'':<26} ║",
            f"╚{border}╝"
        ]

        return "\n".join(lines)
