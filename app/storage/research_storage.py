"""Research Storage layer persisting full simulation runs, setups, features, and failure reports."""

from pathlib import Path
from typing import List, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.validation_engine.binary_simulator import BinarySimulationResult
from app.validation_engine.failure_analyzer import FailureReport


class ResearchStorage:
    """Manages Snappy-compressed Parquet storage for backtesting simulations, trades, and diagnostics."""

    def __init__(self, base_directory: str = "data/research") -> None:
        self.base_dir = Path(base_directory)
        self.simulations_dir = self.base_dir / "simulations"
        self.failures_dir = self.base_dir / "failures"

        for d in (self.simulations_dir, self.failures_dir):
            d.mkdir(parents=True, exist_ok=True)

    def save_simulations(self, results: List[BinarySimulationResult], session_id: str) -> int:
        """Persist trade simulations to Parquet."""
        if not results:
            return 0

        records: List[dict] = []
        for r in results:
            records.append({
                "session_id": session_id,
                "symbol": r.symbol,
                "direction": r.direction.value,
                "entry_time": r.entry_time.isoformat(),
                "expiry_time": r.expiry_time.isoformat(),
                "entry_price": r.entry_price,
                "expiry_price": r.expiry_price,
                "pnl": r.pnl,
                "outcome": r.outcome.value,
                "payout_rate": r.payout_rate,
                "decision": r.decision.value,
                "quality_score": r.quality_score,
                "date": r.entry_time.strftime("%Y-%m-%d")
            })

        df = pd.DataFrame(records)
        for dt_str, group in df.groupby("date"):
            target_file = self.simulations_dir / f"{dt_str}.parquet"
            table = pa.Table.from_pandas(group.drop(columns=["date"]))
            pq.write_table(table, target_file, compression="SNAPPY")

        return len(records)

    def save_failure_reports(self, reports: List[FailureReport]) -> int:
        """Persist forensic failure reports to Parquet."""
        if not reports:
            return 0

        records: List[dict] = []
        for rep in reports:
            records.append({
                "trade_id": rep.trade_id,
                "timestamp": rep.timestamp,
                "failure_reason": rep.failure_reason.value,
                "explanation": rep.explanation,
                "improvement_area": rep.improvement_area,
                "date": rep.timestamp[:10]
            })

        df = pd.DataFrame(records)
        for dt_str, group in df.groupby("date"):
            target_file = self.failures_dir / f"{dt_str}.parquet"
            table = pa.Table.from_pandas(group.drop(columns=["date"]))
            pq.write_table(table, target_file, compression="SNAPPY")

        return len(records)
