"""Context storage layer for persisting MarketContext snapshots into partitioned Parquet files."""

from pathlib import Path
from typing import List, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.models.market_context import MarketContext


class ContextStorage:
    """Manages Parquet-based partitioned storage for MarketContext environmental snapshots."""

    def __init__(self, base_directory: str = "data/market_context") -> None:
        self.base_dir = Path(base_directory)
        self.snapshots_dir = self.base_dir / "snapshots"
        self.structure_events_dir = self.base_dir / "structure_events"
        self.liquidity_events_dir = self.base_dir / "liquidity_events"

        for d in (self.snapshots_dir, self.structure_events_dir, self.liquidity_events_dir):
            d.mkdir(parents=True, exist_ok=True)

    def save_context(self, context: MarketContext) -> None:
        """Persist a single MarketContext."""
        self.save_contexts([context])

    def save_contexts(self, contexts: List[MarketContext]) -> int:
        """Save a batch of MarketContext objects into partitioned Parquet stores."""
        if not contexts:
            return 0

        ctx_records: List[dict] = []
        struct_records: List[dict] = []
        liq_records: List[dict] = []

        for ctx in contexts:
            date_str = ctx.timestamp.strftime("%Y-%m-%d")

            ctx_records.append({
                "timestamp": ctx.timestamp.isoformat(),
                "symbol": ctx.symbol,
                "timeframe": ctx.timeframe,
                "structure_state": ctx.structure.current_state.value,
                "regime_state": ctx.regime.state.value,
                "session": ctx.session.name.value,
                "volatility_level": ctx.volatility.level.value,
                "atr": ctx.volatility.atr_value,
                "news_blocked": ctx.news.blocked,
                "overall_confidence": ctx.overall_confidence,
                "date": date_str
            })

            # Structure Event
            if ctx.structure.last_event:
                ev = ctx.structure.last_event
                struct_records.append({
                    "timestamp": ev.timestamp.isoformat(),
                    "symbol": ev.symbol,
                    "event_type": ev.event_type.value,
                    "price": ev.price,
                    "broken_swing_price": ev.broken_swing_price,
                    "strength": ev.strength,
                    "confidence": ev.confidence,
                    "date": date_str
                })

            # Liquidity Event
            if ctx.recent_liquidity_event:
                lev = ctx.recent_liquidity_event
                liq_records.append({
                    "timestamp": lev.timestamp.isoformat(),
                    "symbol": lev.symbol,
                    "event_type": lev.event_type.value,
                    "zone_type": lev.zone.zone_type.value,
                    "zone_price": lev.zone.price,
                    "penetration_ticks": lev.penetration_ticks,
                    "reaction_score": lev.reaction_score,
                    "confidence": lev.confidence,
                    "date": date_str
                })

        self._write_records(ctx_records, self.snapshots_dir)
        self._write_records(struct_records, self.structure_events_dir)
        self._write_records(liq_records, self.liquidity_events_dir)

        return len(contexts)

    def _write_records(self, records: List[dict], base_path: Path) -> None:
        """Write records partitioned by symbol and date."""
        if not records:
            return
        df = pd.DataFrame(records)
        for (sym, dt_str), group in df.groupby(["symbol", "date"]):
            target_file = base_path / str(sym) / f"{dt_str}.parquet"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pandas(group.drop(columns=["date"]))
            pq.write_table(table, target_file, compression="SNAPPY")
