"""Unified Validation Pipeline orchestrating Replay, Feature extraction, Decisions, Simulation, and Metrics."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.context_engine.pipeline import MarketContextPipeline
from app.footprint_engine.builder import FootprintBuilder
from app.models.binary_decision import BinaryDecision, DecisionType
from app.models.footprint import FootprintBar
from app.models.market_context import MarketContext
from app.models.orderflow_context import OrderFlowContext
from app.models.tick import Tick
from app.orderflow_engine.pipeline import OrderFlowFeaturePipeline
from app.setup_engine.decision_arbiter import DecisionArbiter
from app.storage.research_storage import ResearchStorage
from app.validation_engine.binary_simulator import (
    BinarySimulationConfig,
    BinarySimulationResult,
    BinarySimulator,
)
from app.validation_engine.events import EventType, MarketEvent
from app.validation_engine.failure_analyzer import FailureAnalyzer, FailureReport
from app.validation_engine.metrics_engine import MetricsEngine, PerformanceReport
from app.validation_engine.monte_carlo import MonteCarloEngine, MonteCarloResult
from app.validation_engine.replay_engine import ReplayEngine, ReplaySession
from app.validation_engine.walk_forward import WalkForwardResult, WalkForwardValidator


class ValidationRunSummary(BaseModel):
    """Complete results summary from an orchestrated validation run."""
    session_id: str = Field(..., description="Replay session ID")
    total_bars_evaluated: int = Field(..., description="Number of completed 5M bars evaluated")
    performance: PerformanceReport = Field(..., description="Standard and binary metrics")
    walk_forward: WalkForwardResult = Field(..., description="Walk-forward stability results")
    monte_carlo: MonteCarloResult = Field(..., description="Monte Carlo simulation results")
    failures_count: int = Field(..., description="Number of losses analyzed")

    model_config = {
        "frozen": True
    }


class ValidationPipeline:
    """Orchestrates the entire FO-X 5M validation pipeline in strict chronological order with zero lookahead."""

    def __init__(
        self,
        simulation_config: Optional[BinarySimulationConfig] = None,
        arbiter: Optional[DecisionArbiter] = None,
        storage: Optional[ResearchStorage] = None
    ) -> None:
        self.sim_config = simulation_config or BinarySimulationConfig()
        self.simulator = BinarySimulator(config=self.sim_config)
        self.arbiter = arbiter or DecisionArbiter()
        self.metrics_engine = MetricsEngine()
        self.walk_forward_validator = WalkForwardValidator()
        self.monte_carlo_engine = MonteCarloEngine(iterations=10000)
        self.failure_analyzer = FailureAnalyzer()
        self.storage = storage or ResearchStorage()

        # FO-X 5M Live Processing Core Engines
        self.fp_builder = FootprintBuilder(timeframe_seconds=300)
        self.of_pipeline = OrderFlowFeaturePipeline()
        self.mkt_pipeline = MarketContextPipeline()

    def run_validation(
        self,
        session: ReplaySession,
        ticks: List[Tick]
    ) -> Tuple[ValidationRunSummary, List[BinarySimulationResult]]:
        """Execute replay stream and pass through live-identical pipeline."""
        replay = ReplayEngine(session)

        completed_bars: List[FootprintBar] = []
        of_contexts: List[OrderFlowContext] = []
        mkt_contexts: List[MarketContext] = []
        decisions: List[BinaryDecision] = []
        simulations: List[BinarySimulationResult] = []
        failure_reports: List[FailureReport] = []

        pending_trade_decision: Optional[BinaryDecision] = None
        pending_trade_of_ctx: Optional[OrderFlowContext] = None
        pending_trade_mkt_ctx: Optional[MarketContext] = None

        # Replay ticks one by one chronologically
        for event in replay.stream_ticks(ticks):
            tick: Tick = event.payload["tick"]

            # 1. Update footprint builder with the tick
            completed_bar = self.fp_builder.add_tick(tick)

            if completed_bar is not None:
                completed_bars.append(completed_bar)

                # 2. Extract Order Flow Context for the completed bar
                of_ctx = self.of_pipeline.process_bar(completed_bar)
                of_contexts.append(of_ctx)

                # 3. Extract Market Context for the completed bar
                mkt_ctx = self.mkt_pipeline.process_bar(completed_bar, of_ctx)
                mkt_contexts.append(mkt_ctx)

                # If there was a pending decision from previous bar, resolve its entry price at open of this bar
                if pending_trade_decision is not None:
                    # In 5M binary trading, trade enters at start of next bar, expires at close of this bar
                    sim_res = self.simulator.simulate_trade(
                        decision=pending_trade_decision,
                        raw_entry_price=completed_bar.open,
                        raw_expiry_price=completed_bar.close,
                        bar_start_time=completed_bar.start_time
                    )
                    if sim_res is not None:
                        simulations.append(sim_res)

                        # Failure forensic analysis
                        if sim_res.outcome.value == "LOSS" and pending_trade_of_ctx and pending_trade_mkt_ctx:
                            fail_rep = self.failure_analyzer.analyze_loss(
                                trade=sim_res,
                                of_ctx=pending_trade_of_ctx,
                                mkt_ctx=pending_trade_mkt_ctx
                            )
                            if fail_rep:
                                failure_reports.append(fail_rep)

                    pending_trade_decision = None
                    pending_trade_of_ctx = None
                    pending_trade_mkt_ctx = None

                # 4. Evaluate Decision Arbiter on completed bar
                decision = self.arbiter.evaluate(
                    bar=completed_bar,
                    of_ctx=of_ctx,
                    mkt_ctx=mkt_ctx,
                    payout_rate=self.sim_config.payout_percentage
                )
                decisions.append(decision)

                # If actionable CALL or PUT, queue it for next bar simulation
                if decision.decision in (DecisionType.CALL, DecisionType.PUT):
                    pending_trade_decision = decision
                    pending_trade_of_ctx = of_ctx
                    pending_trade_mkt_ctx = mkt_ctx

        # Calculate Performance Metrics
        perf_report = self.metrics_engine.calculate_metrics(
            simulations=simulations,
            total_bars_evaluated=len(completed_bars),
            payout_rate=self.sim_config.payout_percentage
        )

        # Walk-Forward Validation
        wf_result = self.walk_forward_validator.validate(simulations)

        # Monte Carlo Simulation
        mc_result = self.monte_carlo_engine.run_simulation(simulations)

        # Persist results
        self.storage.save_simulations(simulations, session.session_id)
        self.storage.save_failure_reports(failure_reports)

        summary = ValidationRunSummary(
            session_id=session.session_id,
            total_bars_evaluated=len(completed_bars),
            performance=perf_report,
            walk_forward=wf_result,
            monte_carlo=mc_result,
            failures_count=len(failure_reports)
        )

        return summary, simulations
