"""Walk Forward statistical validation engine with rolling In-Sample (IS) and Out-of-Sample (OOS) splits."""

from typing import List, Optional, Tuple
from pydantic import BaseModel, Field

from app.validation_engine.binary_simulator import BinarySimulationResult, SimulationOutcome
from app.validation_engine.metrics_engine import MetricsEngine, PerformanceReport


class WalkForwardWindowResult(BaseModel):
    """Result of a single sliding In-Sample vs Out-of-Sample evaluation window."""
    window_id: int = Field(..., description="Window index")
    in_sample_trades: int = Field(..., description="Trade count in training window")
    in_sample_win_rate: float = Field(..., description="In-sample win rate")
    out_of_sample_trades: int = Field(..., description="Trade count in unseen testing window")
    out_of_sample_win_rate: float = Field(..., description="Out-of-sample win rate")
    stability_ratio: float = Field(..., description="OOS Win Rate / IS Win Rate")

    model_config = {
        "frozen": True
    }


class WalkForwardResult(BaseModel):
    """Aggregate Walk-Forward validation report across all rolling time slices."""
    total_windows: int = Field(..., description="Number of evaluated windows")
    average_is_win_rate: float = Field(..., description="Mean in-sample win rate")
    average_oos_win_rate: float = Field(..., description="Mean out-of-sample win rate")
    overall_stability_score: float = Field(..., ge=0.0, le=2.0, description="Mean OOS/IS stability ratio")
    window_breakdowns: List[WalkForwardWindowResult] = Field(default_factory=list, description="Per-window details")

    model_config = {
        "frozen": True
    }


class WalkForwardValidator:
    """Executes chronological rolling window validation to detect overfitting and stability decay."""

    def __init__(
        self,
        in_sample_size: int = 50,
        out_of_sample_size: int = 20,
        step_size: int = 20
    ) -> None:
        self.is_size = in_sample_size
        self.oos_size = out_of_sample_size
        self.step = step_size

    def validate(self, trades: List[BinarySimulationResult]) -> WalkForwardResult:
        """Run sequential rolling walk-forward test across chronological trades."""
        total_len = len(trades)
        window_size = self.is_size + self.oos_size

        if total_len < window_size:
            return WalkForwardResult(
                total_windows=0,
                average_is_win_rate=0.0,
                average_oos_win_rate=0.0,
                overall_stability_score=0.0,
                window_breakdowns=[]
            )

        windows: List[WalkForwardWindowResult] = []
        is_rates: List[float] = []
        oos_rates: List[float] = []

        window_id = 1
        start_idx = 0
        while (start_idx + window_size) <= total_len:
            is_trades = trades[start_idx : start_idx + self.is_size]
            oos_trades = trades[start_idx + self.is_size : start_idx + window_size]

            is_wins = sum(1 for t in is_trades if t.outcome == SimulationOutcome.WIN)
            oos_wins = sum(1 for t in oos_trades if t.outcome == SimulationOutcome.WIN)

            is_wr = is_wins / len(is_trades) if is_trades else 0.0
            oos_wr = oos_wins / len(oos_trades) if oos_trades else 0.0

            stability = (oos_wr / is_wr) if is_wr > 0 else 0.0

            windows.append(WalkForwardWindowResult(
                window_id=window_id,
                in_sample_trades=len(is_trades),
                in_sample_win_rate=round(is_wr, 4),
                out_of_sample_trades=len(oos_trades),
                out_of_sample_win_rate=round(oos_wr, 4),
                stability_ratio=round(stability, 4)
            ))

            is_rates.append(is_wr)
            oos_rates.append(oos_wr)

            window_id += 1
            start_idx += self.step

        avg_is = float(sum(is_rates) / len(is_rates)) if is_rates else 0.0
        avg_oos = float(sum(oos_rates) / len(oos_rates)) if oos_rates else 0.0
        avg_stability = float(avg_oos / avg_is) if avg_is > 0 else 0.0

        return WalkForwardResult(
            total_windows=len(windows),
            average_is_win_rate=round(avg_is, 4),
            average_oos_win_rate=round(avg_oos, 4),
            overall_stability_score=round(avg_stability, 4),
            window_breakdowns=windows
        )
