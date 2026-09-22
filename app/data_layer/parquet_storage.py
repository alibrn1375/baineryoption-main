"""Parquet-based columnar storage engine for high-throughput tick datasets."""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.core.exceptions import DataValidationError
from app.data_layer.storage.base_storage import BaseStorage
from app.models.tick import Tick, TradeSide


class ParquetStorage(BaseStorage):
    """Stores normalized ticks partitioned by symbol and date in compressed Apache Parquet format."""

    def __init__(self, base_directory: str = "data/ticks") -> None:
        self.base_dir = Path(base_directory)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_partition_path(self, symbol: str, dt: datetime) -> Path:
        """Partition path convention: base_dir / symbol / YYYY-MM-DD.parquet"""
        date_str = dt.strftime("%Y-%m-%d")
        sym_dir = self.base_dir / symbol.upper()
        sym_dir.mkdir(parents=True, exist_ok=True)
        return sym_dir / f"{date_str}.parquet"

    def save_ticks(self, ticks: List[Tick]) -> int:
        """Write a batch of ticks to corresponding date-partitioned Parquet files."""
        if not ticks:
            return 0

        # Group ticks by symbol and date
        grouped: dict[tuple[str, str], list[dict]] = {}
        for t in ticks:
            date_key = t.timestamp.strftime("%Y-%m-%d")
            key = (t.symbol, date_key)
            if key not in grouped:
                grouped[key] = []
            grouped[key].append({
                "symbol": t.symbol,
                "timestamp": t.timestamp.isoformat(),
                "price": t.price,
                "volume": t.volume,
                "bid": t.bid,
                "ask": t.ask,
                "trade_side": t.trade_side.value,
                "source": t.source
            })

        total_saved = 0
        for (sym, date_str), records in grouped.items():
            df_new = pd.DataFrame(records)
            file_path = self.base_dir / sym.upper() / f"{date_str}.parquet"
            file_path.parent.mkdir(parents=True, exist_ok=True)

            if file_path.exists():
                try:
                    df_existing = pd.read_parquet(file_path)
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                    df_combined.drop_duplicates(subset=["timestamp", "price", "volume"], keep="last", inplace=True)
                    df_combined.sort_values(by="timestamp", inplace=True)
                    df_to_save = df_combined
                except Exception:
                    df_to_save = df_new
            else:
                df_to_save = df_new.sort_values(by="timestamp")

            table = pa.Table.from_pandas(df_to_save)
            pq.write_table(table, file_path, compression="SNAPPY")
            total_saved += len(records)

        return total_saved

    def load_ticks(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> Generator[Tick, None, None]:
        """Stream ticks matching the query time window in chronological sequence."""
        sym_dir = self.base_dir / symbol.upper()
        if not sym_dir.exists():
            return

        # Ensure start and end are UTC
        start_utc = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        end_utc = end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)

        # Collect relevant files
        parquet_files = sorted(list(sym_dir.glob("*.parquet")))
        for pfile in parquet_files:
            try:
                # Extract date from filename
                date_str = pfile.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                if file_date < start_utc.date() or file_date > end_utc.date():
                    continue

                table = pq.read_table(pfile)
                df = table.to_pandas()
                df["dt"] = pd.to_datetime(df["timestamp"])
                mask = (df["dt"] >= start_utc) & (df["dt"] <= end_utc)
                filtered_df = df.loc[mask]

                for _, row in filtered_df.iterrows():
                    yield Tick(
                        symbol=str(row["symbol"]),
                        timestamp=datetime.fromisoformat(str(row["timestamp"])),
                        price=float(row["price"]),
                        volume=float(row["volume"]),
                        bid=float(row["bid"]) if pd.notna(row["bid"]) else None,
                        ask=float(row["ask"]) if pd.notna(row["ask"]) else None,
                        trade_side=TradeSide(str(row["trade_side"])),
                        source=str(row.get("source", "parquet"))
                    )
            except Exception as err:
                raise DataValidationError(f"Error reading Parquet file {pfile}: {err}") from err

    def get_tick_count(self, symbol: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> int:
        """Count ticks stored for the symbol."""
        count = 0
        sym_dir = self.base_dir / symbol.upper()
        if not sym_dir.exists():
            return 0
        for pfile in sym_dir.glob("*.parquet"):
            try:
                table = pq.read_table(pfile, columns=["timestamp"])
                count += table.num_rows
            except Exception:
                pass
        return count

    def delete_range(self, symbol: str, start_time: datetime, end_time: datetime) -> int:
        """Remove ticks in range. For simplicity, deletes files wholly within the range."""
        deleted_count = 0
        sym_dir = self.base_dir / symbol.upper()
        if not sym_dir.exists():
            return 0
        for pfile in sym_dir.glob("*.parquet"):
            date_str = pfile.stem
            file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if start_time.date() <= file_date <= end_time.date():
                table = pq.read_table(pfile)
                deleted_count += table.num_rows
                pfile.unlink()
        return deleted_count
