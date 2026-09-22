"""Performance metrics engine computing statistical, risk, and binary-specific return metrics."""

from typing import Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field

from app.setup_engine.probability_estimator import ProbabilityEstimator
from app.validation_engine.binary_simulator import BinarySimulationResult, SimulationOutcome


class RiskMetrics(BaseModel):
    """Risk and drawdown characteristics."""
    max_consecutive_losses: int = Field(..., description="Maximum streak of consecutive losing trades")
    max_drawdown_units: float = Field(..., description="Maximum peak-to-trough equity drawdown in risk units")
    max_drawdown_percentage: float = Field(..., description="Maximum drawdown percentage assuming 100-unit initial capital")
    profit_factor: float = Field(..., description="Gross Profits / Gross Losses")
    sharpe_ratio: float = Field(..., description="Trade-by-trade annualized Sharpe estimate")

    model_config = {
        "frozen": True
    }


class PerformanceReport(BaseModel):
    """Comprehensive statistical validation report."""
    total_decisions: int = Field(..., description="Total evaluated 5M bars")
    total_trades: int = Field(..., description="Total trades executed (CALL/PUT)")
    wins: int = Field(..., description="Winning trade count")
    losses: int = Field(..., description="Losing trade count")
    ties: int = Field(..., description="Tied trade count")
    win_rate: float = Field(..., ge=0.0, le=1.0, description="Raw Win Rate = wins / total_trades")
    wilson_lower_ci: float = Field(..., ge=0.0, le=1.0, description="95% Wilson confidence lower bound")
    wilson_upper_ci: float = Field(..., ge=0.0, le=1.0, description="95% Wilson confidence upper bound")
    expectancy_per_trade: float = Field(..., description="Net expected return per $1 risked")
    break_even_win_rate: float = Field(..., description="Required win rate: 1 / (1 + payout)")
    net_pnl: float = Field(..., description="Cumulative net PnL across all trades")
    risk_metrics: RiskMetrics = Field(..., description="Streak and drawdown analysis")

    model_config = {
        "frozen": True
    }


class MetricsEngine:
    """Calculates rigorous quantitative performance, risk, and binary metrics."""

    def __init__(self, prob_estimator: Optional[ProbabilityEstimator] = None) -> None:
        self.prob_estimator = prob_estimator or ProbabilityEstimator()

    def calculate_metrics(
        self,
        simulations: List[BinarySimulationResult],
        total_bars_evaluated: int,
        payout_rate: float = 0.85
    ) -> PerformanceReport:
        """Compute full statistical and risk report over a sequence of trade simulations."""
        if not simulations:
            break_even = 1.0 / (1.0 + payout_rate)
            return PerformanceReport(
                total_decisions=total_bars_evaluated,
                total_trades=0,
                wins=0,
                losses=0,
                ties=0,
                win_rate=0.0,
                wilson_lower_ci=0.0,
                wilson_upper_ci=0.0,
                expectancy_per_trade=-1.0,
                break_even_win_rate=round(break_even, 4),
                net_pnl=0.0,
                risk_metrics=RiskMetrics(
                    max_consecutive_losses=0,
                    max_drawdown_units=0.0,
                    max_drawdown_percentage=0.0,
                    profit_factor=0.0,
                    sharpe_ratio=0.0
                )
            )

        total_trades = len(simulations)
        wins = sum(1 for s in simulations if s.outcome == SimulationOutcome.WIN)
        losses = sum(1 for s in simulations if s.outcome == SimulationOutcome.LOSS)
        ties = sum(1 for s in simulations if s.outcome == SimulationOutcome.TIE)

        win_rate = wins / total_trades if total_trades > 0 else 0.0
        prob_est = self.prob_estimator.estimate(wins, total_trades)

        # Cumulative PnL and Drawdown
        pnls = [s.pnl for s in simulations]
        net_pnl = float(np.sum(pnls))
        cum_pnl = np.cumsum(pnls)

        # Drawdown calculation
        peak = 0.0
        max_dd = 0.0
        current_eq = 0.0
        for p in pnls:
            current_eq += p
            if current_eq > peak:
                peak = current_eq
            dd = peak - current_eq
            if dd > max_dd:
                max_dd = dd

        # Consecutive losing streak
        max_streak = 0
        current_streak = 0
        for s in simulations:
            if s.outcome == SimulationOutcome.LOSS:
                current_streak += 1
                if current_streak > max_streak:
                    max_streak = current_streak
            else:
                current_streak = 0

        # Profit Factor
        gross_profit = float(np.sum([s.pnl for s in simulations if s.pnl > 0]))
        gross_loss = float(abs(np.sum([s.pnl for s in simulations if s.pnl < 0])))
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (99.0 if gross_profit > 0 else 0.0)

        # Sharpe ratio estimate
        std_pnl = float(np.std(pnls)) if len(pnls) > 1 else 1.0
        mean_pnl = float(np.mean(pnls)) if pnls else 0.0
        sharpe = round((mean_pnl / std_pnl) * np.sqrt(252 * 50), 2) if std_pnl > 0 else 0.0

        break_even = 1.0 / (1.0 + payout_rate)
        loss_rate = losses / total_trades if total_trades > 0 else 0.0
        expectancy = (win_rate * payout_rate) - (loss_rate * 1.0)

        return PerformanceReport(
            total_decisions=total_bars_evaluated,
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            ties=ties,
            win_rate=round(win_rate, 4),
            wilson_lower_ci=prob_est.wilson_lower,
            wilson_upper_ci=prob_est.wilson_upper,
            expectancy_per_trade=round(expectancy, 4),
            break_even_win_rate=round(break_even, 4),
            net_pnl=round(net_pnl, 2),
            risk_metrics=RiskMetrics(
                max_consecutive_losses=max_streak,
                max_drawdown_units=round(max_dd, 2),
                max_drawdown_percentage=round((max_dd / 100.0) * 100.0, 2),
                profit_factor=profit_factor,
                sharpe_ratio=sharpe
            )
        )
