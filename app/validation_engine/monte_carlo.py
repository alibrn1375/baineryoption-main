"""Monte Carlo simulation engine preserving trade distributions and measuring streak risks."""

from typing import Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field

from app.validation_engine.binary_simulator import BinarySimulationResult


class MonteCarloResult(BaseModel):
    """Statistical summary of 10,000+ Monte Carlo reshuffle trials."""
    simulations_count: int = Field(..., description="Number of Monte Carlo iterations")
    median_max_drawdown: float = Field(..., description="50th percentile (median) max drawdown")
    worst_1_pct_drawdown: float = Field(..., description="99th percentile worst-case max drawdown")
    drawdown_percentile_distribution: Dict[str, float] = Field(..., description="5th, 25th, 50th, 75th, 95th, 99th drawdown percentiles")
    median_max_losing_streak: int = Field(..., description="Median maximum consecutive losses")
    worst_case_losing_streak: int = Field(..., description="Worst-case 99th percentile losing streak")
    losing_streak_probability: Dict[str, float] = Field(..., description="Probability of streaks >= 4, 6, 8, 10")
    failure_probability: float = Field(..., description="Probability of experiencing drawdown > initial capital hurdle (e.g. 20 units)")

    model_config = {
        "frozen": True
    }


class MonteCarloEngine:
    """Performs non-parametric Bootstrap / Reshuffle simulations preserving empirical trade PnL distribution."""

    def __init__(self, iterations: int = 10000, ruin_hurdle_units: float = 20.0) -> None:
        self.iterations = iterations
        self.ruin_hurdle = ruin_hurdle_units

    def run_simulation(self, trades: List[BinarySimulationResult]) -> MonteCarloResult:
        """Run Monte Carlo reshuffle over trade PnLs to measure variance, streaks, and tail risks."""
        if not trades:
            return MonteCarloResult(
                simulations_count=0,
                median_max_drawdown=0.0,
                worst_1_pct_drawdown=0.0,
                drawdown_percentile_distribution={"p50": 0.0, "p95": 0.0, "p99": 0.0},
                median_max_losing_streak=0,
                worst_case_losing_streak=0,
                losing_streak_probability={"streak_4_plus": 0.0, "streak_6_plus": 0.0},
                failure_probability=0.0
            )

        pnls = np.array([t.pnl for t in trades], dtype=np.float64)
        n_trades = len(pnls)

        all_max_dds = np.zeros(self.iterations, dtype=np.float64)
        all_max_streaks = np.zeros(self.iterations, dtype=np.int32)
        ruin_count = 0

        streak_4_count = 0
        streak_6_count = 0
        streak_8_count = 0
        streak_10_count = 0

        # Run vector-friendly loop
        for i in range(self.iterations):
            # Reshuffle trades without replacement to maintain exact empirical distribution
            shuffled_pnls = np.random.permutation(pnls)

            # Compute max drawdown
            cum_pnl = np.cumsum(shuffled_pnls)
            peak = np.maximum.accumulate(cum_pnl)
            drawdowns = peak - cum_pnl
            max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0
            all_max_dds[i] = max_dd

            if max_dd >= self.ruin_hurdle:
                ruin_count += 1

            # Compute max losing streak
            is_loss = shuffled_pnls < 0
            max_s = 0
            curr_s = 0
            for loss in is_loss:
                if loss:
                    curr_s += 1
                    if curr_s > max_s:
                        max_s = curr_s
                else:
                    curr_s = 0
            all_max_streaks[i] = max_s

            if max_s >= 4:
                streak_4_count += 1
            if max_s >= 6:
                streak_6_count += 1
            if max_s >= 8:
                streak_8_count += 1
            if max_s >= 10:
                streak_10_count += 1

        # Calculate Percentiles
        p5 = float(np.percentile(all_max_dds, 5))
        p25 = float(np.percentile(all_max_dds, 25))
        p50 = float(np.percentile(all_max_dds, 50))
        p75 = float(np.percentile(all_max_dds, 75))
        p95 = float(np.percentile(all_max_dds, 95))
        p99 = float(np.percentile(all_max_dds, 99))

        return MonteCarloResult(
            simulations_count=self.iterations,
            median_max_drawdown=round(p50, 2),
            worst_1_pct_drawdown=round(p99, 2),
            drawdown_percentile_distribution={
                "p05": round(p5, 2),
                "p25": round(p25, 2),
                "p50": round(p50, 2),
                "p75": round(p75, 2),
                "p95": round(p95, 2),
                "p99": round(p99, 2),
            },
            median_max_losing_streak=int(np.median(all_max_streaks)),
            worst_case_losing_streak=int(np.percentile(all_max_streaks, 99)),
            losing_streak_probability={
                "streak_4_plus": round(streak_4_count / self.iterations, 4),
                "streak_6_plus": round(streak_6_count / self.iterations, 4),
                "streak_8_plus": round(streak_8_count / self.iterations, 4),
                "streak_10_plus": round(streak_10_count / self.iterations, 4),
            },
            failure_probability=round(ruin_count / self.iterations, 4)
        )
