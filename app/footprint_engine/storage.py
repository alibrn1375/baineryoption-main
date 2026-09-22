"""Columnar Parquet storage engine for persisting and querying Footprint Bars, Price Levels, and CVD Points."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.core.exceptions import DataValidationError
from app.models.footprint import CVDPoint, FootprintBar, FootprintQuality, PriceLevel


class FootprintStorage:
    """Handles date-partitioned storage for footprint bars, granular price levels, and CVD timeseries."""

    def __init__(self, base_directory: str = "data/footprint") -> None:
        self.base_dir = Path(base_directory)
        self.bars_dir = self.base_dir / "bars"
        self.levels_dir = self.base_dir / "levels"
        self.cvd_dir = self.base_dir / "cvd"

        for d in (self.bars_dir, self.levels_dir, self.cvd_dir):
            d.mkdir(parents=True, exist_ok=True)

    def save_footprint_bars(self, bars: List[FootprintBar]) -> int:
        """Persist a batch of FootprintBar objects and their constituent PriceLevels."""
        if not bars:
            return 0

        bar_records: List[dict] = []
        level_records: List[dict] = []

        for bar in bars:
            date_str = bar.start_time.strftime("%Y-%m-%d")
            bar_records.append({
                "symbol": bar.symbol,
                "timeframe": bar.timeframe,
                "start_time": bar.start_time.isoformat(),
                "end_time": bar.end_time.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "total_volume": bar.total_volume,
                "total_bid_volume": bar.total_bid_volume,
                "total_ask_volume": bar.total_ask_volume,
                "total_unknown_volume": bar.total_unknown_volume,
                "bar_delta": bar.bar_delta,
                "min_delta": bar.min_delta,
                "max_delta": bar.max_delta,
                "delta_percentage": bar.delta_percentage,
                "poc_price": bar.poc_price,
                "quality": bar.quality.value,
                "date": date_str
            })

            for lvl in bar.levels:
                level_records.append({
                    "symbol": bar.symbol,
                    "bar_start_time": bar.start_time.isoformat(),
                    "price": lvl.price,
                    "bid_volume": lvl.bid_volume,
                    "ask_volume": lvl.ask_volume,
                    "unknown_volume": lvl.unknown_volume,
                    "total_volume": lvl.total_volume,
                    "delta": lvl.delta,
                    "date": date_str
                })

        # Write partitioned bars
        df_bars = pd.DataFrame(bar_records)
        for (sym, dt_str), group in df_bars.groupby(["symbol", "date"]):
            target_file = self.bars_dir / str(sym) / f"{dt_str}.parquet"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pandas(group.drop(columns=["date"]))
            pq.write_table(table, target_file, compression="SNAPPY")

        # Write partitioned levels
        if level_records:
            df_levels = pd.DataFrame(level_records)
            for (sym, dt_str), group in df_levels.groupby(["symbol", "date"]):
                target_file = self.levels_dir / str(sym) / f"{dt_str}.parquet"
                target_file.parent.mkdir(parents=True, exist_ok=True)
                table = pa.Table.from_pandas(group.drop(columns=["date"]))
                pq.write_table(table, target_file, compression="SNAPPY")

        return len(bars)

    def save_cvd_points(self, cvd_points: List[CVDPoint]) -> int:
        """Persist session CVD points."""
        if not cvd_points:
            return 0

        records = [
            {
                "timestamp": p.timestamp.isoformat(),
                "symbol": p.symbol,
                "session": p.session,
                "cumulative_delta": p.cumulative_delta,
                "bar_delta": p.bar_delta,
                "date": p.timestamp.strftime("%Y-%m-%d")
            }
            for p in cvd_points
        ]

        df_cvd = pd.DataFrame(records)
        for (sym, dt_str), group in df_cvd.groupby(["symbol", "date"]):
            target_file = self.cvd_dir / str(sym) / f"{dt_str}.parquet"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pandas(group.drop(columns=["date"]))
            pq.write_table(table, target_file, compression="SNAPPY")

        return len(cvd_points)

    def load_footprint_bars(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> Generator[FootprintBar, None, None]:
        """Stream stored footprint bars with their corresponding reconstructed price levels."""
        sym_dir = self.bars_dir / symbol.upper()
        if not sym_dir.exists():
            return

        start_utc = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)
        end_utc = end_time if end_time.tzinfo else end_time.replace(tzinfo=timezone.utc)

        # Load levels lookup if exists
        levels_map: dict[str, list[PriceLevel]] = {}
        sym_levels_dir = self.levels_dir / symbol.upper()
        if sym_levels_dir.exists():
            for lfile in sorted(sym_levels_dir.glob("*.parquet")):
                try:
                    df_lvl = pq.read_table(lfile).to_pandas()
                    for _, r in df_lvl.iterrows():
                        key = str(r["bar_start_time"])
                        if key not in levels_map:
                            levels_map[key] = []
                        levels_map[key].append(PriceLevel(
                            price=float(r["price"]),
                            bid_volume=float(r["bid_volume"]),
                            ask_volume=float(r["ask_volume"]),
                            unknown_volume=float(r.get("unknown_volume", 0.0)),
                            total_volume=float(r["total_volume"]),
                            delta=float(r["delta"])
                        ))
                except Exception:
                    pass

        for pfile in sorted(sym_dir.glob("*.parquet")):
            try:
                table = pq.read_table(pfile)
                df = table.to_pandas()
                df["dt"] = pd.to_datetime(df["start_time"])
                filtered = df.loc[(df["dt"] >= start_utc) & (df["dt"] <= end_utc)]

                for _, row in filtered.iterrows():
                    bar_start_iso = str(row["start_time"])
                    bar_lvls = levels_map.get(bar_start_iso, [])
                    yield FootprintBar(
                        symbol=str(row["symbol"]),
                        timeframe=str(row["timeframe"]),
                        start_time=datetime.fromisoformat(bar_start_iso),
                        end_time=datetime.fromisoformat(str(row["end_time"])),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        total_volume=float(row["total_volume"]),
                        total_bid_volume=float(row["total_bid_volume"]),
                        total_ask_volume=float(row["total_ask_volume"]),
                        total_unknown_volume=float(row.get("total_unknown_volume", 0.0)),
                        bar_delta=float(row["bar_delta"]),
                        min_delta=float(row["min_delta"]),
                        max_delta=float(row["max_delta"]),
                        delta_percentage=float(row["delta_percentage"]),
                        poc_price=float(row["poc_price"]) if pd.notna(row["poc_price"]) else None,
                        levels=bar_lvls,
                        quality=FootprintQuality(str(row["quality"]))
                    )
            except Exception as err:
                raise DataValidationError(f"Failed to load footprint bars from {pfile}: {err}") from err
