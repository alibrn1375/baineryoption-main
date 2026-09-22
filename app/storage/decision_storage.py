"""Decision Storage layer for persisting BinaryDecision records to partitioned Parquet files."""

from pathlib import Path
from typing import List, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.models.binary_decision import BinaryDecision


class DecisionStorage:
    """Manages Parquet-based partitioned storage for FO-X 5M decision logs and setup evaluations."""

    def __init__(self, base_directory: str = "data/decisions") -> None:
        self.base_dir = Path(base_directory)
        self.decisions_dir = self.base_dir / "logs"
        self.evaluations_dir = self.base_dir / "evaluations"

        for d in (self.decisions_dir, self.evaluations_dir):
            d.mkdir(parents=True, exist_ok=True)

    def save_decision(self, decision: BinaryDecision) -> None:
        """Persist a single decision."""
        self.save_decisions([decision])

    def save_decisions(self, decisions: List[BinaryDecision]) -> int:
        """Batch save BinaryDecision objects into partitioned Parquet stores."""
        if not decisions:
            return 0

        dec_records: List[dict] = []
        eval_records: List[dict] = []

        for dec in decisions:
            date_str = dec.timestamp.strftime("%Y-%m-%d")

            dec_records.append({
                "timestamp": dec.timestamp.isoformat(),
                "symbol": dec.symbol,
                "expiry_minutes": dec.expiry_minutes,
                "decision": dec.decision.value,
                "direction": dec.direction.value,
                "payout_rate": dec.payout_rate,
                "quality_score": dec.quality_score,
                "ev": dec.ev_result.expected_value if dec.ev_result else 0.0,
                "rejection_reasons": ",".join([r.value for r in dec.rejection_reasons]),
                "confidence": dec.confidence,
                "date": date_str
            })

            if dec.setup_evaluation:
                se = dec.setup_evaluation
                eval_records.append({
                    "timestamp": se.timestamp.isoformat(),
                    "setup_type": se.setup_type.value,
                    "setup_name": se.setup_name,
                    "direction": se.direction.value,
                    "is_triggered": se.is_triggered,
                    "score": se.score,
                    "confidence": se.confidence,
                    "date": date_str
                })

        self._write_records(dec_records, self.decisions_dir)
        self._write_records(eval_records, self.evaluations_dir)

        return len(decisions)

    def _write_records(self, records: List[dict], base_path: Path) -> None:
        """Write records partitioned by date."""
        if not records:
            return
        df = pd.DataFrame(records)
        for dt_str, group in df.groupby("date"):
            target_file = base_path / f"{dt_str}.parquet"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pandas(group.drop(columns=["date"]))
            pq.write_table(table, target_file, compression="SNAPPY")
