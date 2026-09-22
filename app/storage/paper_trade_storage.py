"""Paper Trading Journal Storage persisting virtual trade executions and context in Parquet."""

from pathlib import Path
from typing import List, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.models.paper_trade import PaperTrade


class PaperTradeStorage:
    """Manages Parquet-based partitioned storage for FO-X 5M virtual paper trading journals."""

    def __init__(self, base_directory: str = "data/paper_trading") -> None:
        self.base_dir = Path(base_directory)
        self.trades_dir = self.base_dir / "trades"
        self.trades_dir.mkdir(parents=True, exist_ok=True)

    def save_trade(self, trade: PaperTrade) -> None:
        """Persist a single paper trade record."""
        self.save_trades([trade])

    def save_trades(self, trades: List[PaperTrade]) -> int:
        """Batch save PaperTrade objects into partitioned Parquet files."""
        if not trades:
            return 0

        records: List[dict] = []
        for t in trades:
            date_str = t.timestamp.strftime("%Y-%m-%d")

            records.append({
                "trade_id": t.trade_id,
                "timestamp": t.timestamp.isoformat(),
                "symbol": t.symbol,
                "direction": t.direction.value,
                "expiry_minutes": t.expiry_minutes,
                "stake_amount": t.stake_amount,
                "payout_percentage": t.payout_percentage,
                "entry_price": t.entry_price or 0.0,
                "entry_time": t.entry_time.isoformat() if t.entry_time else "",
                "expiry_time": t.expiry_time.isoformat() if t.expiry_time else "",
                "expiry_price": t.expiry_price or 0.0,
                "setup_name": t.setup_name,
                "probability": t.probability,
                "quality_score": t.quality_score,
                "pnl": t.pnl,
                "status": t.status.value,
                "date": date_str
            })

        df = pd.DataFrame(records)
        for dt_str, group in df.groupby("date"):
            target_file = self.trades_dir / f"{dt_str}.parquet"
            table = pa.Table.from_pandas(group.drop(columns=["date"]))
            pq.write_table(table, target_file, compression="SNAPPY")

        return len(records)
