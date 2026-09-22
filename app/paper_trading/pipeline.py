"""Real-Time Pipeline Manager orchestrating live tick feeds, order execution, risk guards, and monitoring."""

import asyncio
from datetime import datetime, timezone
from typing import Callable, List, Optional
from pydantic import BaseModel, Field

from app.context_engine.pipeline import MarketContextPipeline
from app.footprint_engine.builder import FootprintBuilder
from app.models.binary_decision import BinaryDecision, DecisionType
from app.models.footprint import FootprintBar
from app.models.market_context import MarketContext
from app.models.orderflow_context import OrderFlowContext
from app.models.paper_trade import PaperTrade, VirtualAccountState
from app.models.tick import Tick
from app.orderflow_engine.pipeline import OrderFlowFeaturePipeline
from app.paper_trading.live_monitor import LiveDecisionMonitor
from app.paper_trading.risk_guard import PaperRiskGuard, RiskStatus
from app.paper_trading.virtual_account import VirtualAccount
from app.paper_trading.virtual_execution import VirtualExecutionEngine
from app.setup_engine.decision_arbiter import DecisionArbiter
from app.storage.paper_trade_storage import PaperTradeStorage
from app.validation_engine.binary_simulator import BinarySimulationConfig


class RealTimePipeline:
    """Orchestrates live market ingestion, feature computation, decision arbitration, and virtual paper execution."""

    def __init__(
        self,
        starting_balance: float = 10000.0,
        default_stake: float = 25.0,
        simulation_config: Optional[BinarySimulationConfig] = None,
        arbiter: Optional[DecisionArbiter] = None,
        risk_guard: Optional[PaperRiskGuard] = None,
        storage: Optional[PaperTradeStorage] = None
    ) -> None:
        self.account = VirtualAccount(starting_balance=starting_balance)
        self.sim_config = simulation_config or BinarySimulationConfig()
        self.execution_engine = VirtualExecutionEngine(
            account=self.account,
            config=self.sim_config,
            default_stake=default_stake
        )
        self.arbiter = arbiter or DecisionArbiter()
        self.risk_guard = risk_guard or PaperRiskGuard()
        self.storage = storage or PaperTradeStorage()

        # Core FO-X 5M Engines
        self.fp_builder = FootprintBuilder(timeframe_seconds=300)
        self.of_pipeline = OrderFlowFeaturePipeline()
        self.mkt_pipeline = MarketContextPipeline()

        self._daily_trades_count: int = 0
        self._is_running: bool = True

    def stop(self) -> None:
        """Gracefully stop the live paper trading pipeline."""
        self._is_running = False

    def process_tick(self, tick: Tick) -> Optional[dict]:
        """Process incoming real-time tick, build footprint bar, evaluate decisions, and manage trade lifecycle."""
        if not self._is_running:
            return None

        # 1. Update active open positions and settle any expired contracts
        settled_trades = self.execution_engine.process_expiries(
            current_time=tick.timestamp,
            current_price=tick.price
        )
        if settled_trades:
            self.storage.save_trades(settled_trades)

        # 2. Fill any pending orders with execution delay/slippage
        self.execution_engine.process_order_fills(
            current_time=tick.timestamp,
            current_price=tick.price
        )

        # 3. Add tick to footprint builder
        completed_bar = self.fp_builder.add_tick(tick)
        if completed_bar is None:
            return None

        # 4. Bar Completed -> Run full analytical pipeline
        of_ctx = self.of_pipeline.process_bar(completed_bar)
        mkt_ctx = self.mkt_pipeline.process_bar(completed_bar, of_ctx)

        # 5. Evaluate Decision Arbiter
        decision = self.arbiter.evaluate(
            bar=completed_bar,
            of_ctx=of_ctx,
            mkt_ctx=mkt_ctx,
            payout_rate=self.sim_config.payout_percentage
        )

        # 6. Check Risk Guard before executing
        account_state = self.account.get_state()
        risk_status = self.risk_guard.check_trade_safety(
            account_state=account_state,
            mkt_ctx=mkt_ctx,
            daily_trades_count=self._daily_trades_count
        )

        executed_trade: Optional[PaperTrade] = None
        if decision.decision in (DecisionType.CALL, DecisionType.PUT) and risk_status.allowed:
            executed_trade = self.execution_engine.submit_decision(decision, current_price=completed_bar.close)
            if executed_trade:
                self._daily_trades_count += 1
                self.storage.save_trade(executed_trade)

        # 7. Render Telemetry Card
        telemetry_card = LiveDecisionMonitor.format_terminal_card(
            bar=completed_bar,
            of_ctx=of_ctx,
            mkt_ctx=mkt_ctx,
            decision=decision,
            account_state=self.account.get_state()
        )

        return {
            "bar": completed_bar,
            "orderflow_context": of_ctx,
            "market_context": mkt_ctx,
            "decision": decision,
            "risk_status": risk_status,
            "executed_trade": executed_trade,
            "settled_trades": settled_trades,
            "account_state": self.account.get_state(),
            "telemetry_card": telemetry_card
        }
