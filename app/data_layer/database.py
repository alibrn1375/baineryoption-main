"""DuckDB SQL analytical interface for querying raw tick datasets and parquet archives."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import duckdb
import pandas as pd

from app.core.exceptions import DataProviderError
from app.core.logging import app_logger


class DuckDBAnalytics:
    """Provides ultra-fast in-process vectorized SQL execution over partitioned Parquet tick archives."""

    def __init__(self, db_path: str = ":memory:", tick_base_dir: str = "data/ticks") -> None:
        self.db_path = db_path
        self.tick_base_dir = Path(tick_base_dir)
        try:
            self.conn = duckdb.connect(database=self.db_path)
            app_logger.info(f"DuckDB initialized at '{self.db_path}' (base tick path: {self.tick_base_dir})")
        except Exception as e:
            raise DataProviderError(f"Failed to initialize DuckDB connection: {e}") from e

    def close(self) -> None:
        """Close connection."""
        if self.conn:
            self.conn.close()

    def query_df(self, sql_query: str, params: Optional[List[Any]] = None) -> pd.DataFrame:
        """Execute parameterized analytical SQL query returning a Pandas DataFrame."""
        try:
            if params:
                return self.conn.execute(sql_query, params).fetchdf()
            return self.conn.execute(sql_query).fetchdf()
        except Exception as err:
            raise DataProviderError(f"DuckDB query execution failed: {err} | Query: {sql_query}") from err

    def get_symbol_summary(self, symbol: str) -> Dict[str, Any]:
        """Compute aggregated volume, tick count, and price range directly over Parquet files."""
        glob_path = str(self.tick_base_dir / symbol.upper() / "*.parquet")
        query = f"""
            SELECT
                count(*) AS total_ticks,
                min(price) AS min_price,
                max(price) AS max_price,
                sum(volume) AS total_volume,
                min(timestamp) AS earliest_tick,
                max(timestamp) AS latest_tick
            FROM read_parquet('{glob_path}')
        """
        try:
            df = self.conn.execute(query).fetchdf()
            if df.empty or df["total_ticks"].iloc[0] == 0:
                return {"symbol": symbol, "total_ticks": 0}
            return df.to_dict(orient="records")[0]
        except Exception as e:
            app_logger.warning(f"Could not compute summary for {symbol}: {e}")
            return {"symbol": symbol, "total_ticks": 0, "error": str(e)}

    def get_time_slice(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime,
        limit: Optional[int] = None
    ) -> pd.DataFrame:
        """Fast SQL filter query across date-partitioned parquet files."""
        glob_path = str(self.tick_base_dir / symbol.upper() / "*.parquet")
        limit_clause = f"LIMIT {limit}" if limit else ""
        query = f"""
            SELECT *
            FROM read_parquet('{glob_path}')
            WHERE timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            {limit_clause}
        """
        return self.query_df(query, [start_time.isoformat(), end_time.isoformat()])
