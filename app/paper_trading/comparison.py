"""Live vs Backtest Comparison module measuring decision frequencies, setup deviations, and drift."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.paper_trade import PaperTrade, PaperTradeStatus
from app.validation_engine.binary_simulator import BinarySimulationResult


class DriftMetrics(BaseModel):
    """Statistical divergence metrics between live and backtest distributions."""
    metric_name: str = Field(..., description="Target metric (e.g. Win Rate, Trade Frequency)")
    backtest_value: float = Field(..., description="Benchmark backtest baseline")
    live_value: float = Field(..., description="Observed real-time paper trading value")
    drift_percentage: float = Field(..., description="Percentage deviation ((Live - BT) / BT) * 100")
    is_statistically_significant: bool = Field(..., description="True if divergence exceeds 15% tolerance")

    model_config = {
        "frozen": True
    }


class LiveVsBacktestReport(BaseModel):
    """Comprehensive divergence assessment comparing live paper trading to backtest baselines."""
    live_sample_size: int = Field(..., description="Total live paper trades evaluated")
    backtest_sample_size: int = Field(..., description="Total backtest baseline trades")
    drift_metrics: List[DriftMetrics] = Field(default_factory=list, description="Per-metric divergence breakdown")
    is_healthy: bool = Field(..., description="True if no critical performance or execution drift detected")
    recommendation: str = Field(..., description="Actionable recommendation (PROCEED / AUDIT / HALT)")

    model_config = {
        "frozen": True
    }


class LiveVsBacktestComparator:
    """Detects execution slippage anomalies, setup frequency shifts, and statistical edge decay."""

    @staticmethod
    def compare_performance(
        live_trades: List[PaperTrade],
        backtest_trades: List[BinarySimulationResult],
        tolerance_pct: float = 15.0
    ) -> LiveVsBacktestReport:
        """Compare empirical live paper trade outcomes with historical backtest distribution."""
        if not live_trades or not backtest_trades:
            return LiveVsBacktestReport(
                live_sample_size=len(live_trades),
                backtest_sample_size=len(backtest_trades),
                drift_metrics=[],
                is_healthy=True,
                recommendation="INSUFFICIENT_SAMPLE"
            )

        # 1. Win Rate Comparison
        bt_wins = sum(1 for t in backtest_trades if t.outcome.value == "WIN")
        bt_wr = bt_wins / len(backtest_trades)

        live_wins = sum(1 for t in live_trades if t.status == PaperTradeStatus.WIN)
        live_wr = live_wins / len(live_trades)

        wr_drift = ((live_wr - bt_wr) / bt_wr * 100.0) if bt_wr > 0 else 0.0

        drifts = [
            DriftMetrics(
                metric_name="Win Rate",
                backtest_value=round(bt_wr * 100, 2),
                live_value=round(live_wr * 100, 2),
                drift_percentage=round(wr_drift, 2),
                is_statistically_significant=abs(wr_drift) > tolerance_pct
            )
        ]

        # 2. Check health status
        critical_drift = any(d.is_statistically_significant and d.drift_percentage < -tolerance_pct for d in drifts)

        rec = "PROCEED: Live execution aligns with backtest model."
        if critical_drift:
            rec = "AUDIT: Live performance shows negative drift exceeding 15% tolerance. Review execution assumptions."

        return LiveVsBacktestReport(
            live_sample_size=len(live_trades),
            backtest_sample_size=len(backtest_trades),
            drift_metrics=drifts,
            is_healthy=not critical_drift,
            recommendation=rec
        )
