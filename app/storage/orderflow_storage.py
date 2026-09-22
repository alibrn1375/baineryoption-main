"""Storage layer for persisting and retrieving extracted Order Flow features."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Generator, List, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.core.exceptions import DataValidationError
from app.models.orderflow_context import OrderFlowContext
from app.models.orderflow_features import (
    AbsorptionFeature,
    DeltaFeature,
    ExhaustionFeature,
    ImbalanceFeature,
    StackedImbalanceFeature,
)


class OrderFlowStorage:
    """Manages Parquet-based partitioned storage for all Order Flow features and context objects."""

    def __init__(self, base_directory: str = "data/orderflow") -> None:
        self.base_dir = Path(base_directory)
        self.context_dir = self.base_dir / "contexts"
        self.delta_dir = self.base_dir / "deltas"
        self.imbalance_dir = self.base_dir / "imbalances"
        self.stacked_dir = self.base_dir / "stacked"
        self.absorption_dir = self.base_dir / "absorptions"
        self.exhaustion_dir = self.base_dir / "exhaustions"

        for d in (
            self.context_dir,
            self.delta_dir,
            self.imbalance_dir,
            self.stacked_dir,
            self.absorption_dir,
            self.exhaustion_dir
        ):
            d.mkdir(parents=True, exist_ok=True)

    def save_context(self, context: OrderFlowContext) -> None:
        """Persist a single OrderFlowContext and its constituent features."""
        self.save_contexts([context])

    def save_contexts(self, contexts: List[OrderFlowContext]) -> int:
        """Batch save multiple OrderFlowContext snapshots to partitioned Parquet files."""
        if not contexts:
            return 0

        ctx_records: List[dict] = []
        delta_records: List[dict] = []
        imb_records: List[dict] = []
        stacked_records: List[dict] = []
        abs_records: List[dict] = []
        exh_records: List[dict] = []

        for ctx in contexts:
            date_str = ctx.timestamp.strftime("%Y-%m-%d")
            ctx_records.append({
                "timestamp": ctx.timestamp.isoformat(),
                "symbol": ctx.symbol,
                "timeframe": ctx.timeframe,
                "dominant_direction": ctx.dominant_direction.value,
                "quality": ctx.quality.value,
                "has_delta": ctx.delta_feature is not None,
                "imbalances_count": len(ctx.imbalances),
                "stacked_count": len(ctx.stacked_imbalances),
                "has_absorption": ctx.absorption_feature is not None,
                "has_exhaustion": ctx.exhaustion_feature is not None,
                "date": date_str
            })

            # 1. Delta
            if ctx.delta_feature:
                df = ctx.delta_feature
                delta_records.append({
                    "timestamp": df.timestamp.isoformat(),
                    "symbol": df.symbol,
                    "direction": df.direction.value,
                    "bar_delta": df.bar_delta,
                    "delta_percentage": df.delta_percentage,
                    "strength": df.strength,
                    "acceleration": df.acceleration,
                    "persistence": df.persistence,
                    "percentile": df.percentile,
                    "is_extreme": df.is_extreme,
                    "confidence": df.confidence,
                    "date": date_str
                })

            # 2. Imbalances
            for imb in ctx.imbalances:
                imb_records.append({
                    "timestamp": imb.timestamp.isoformat(),
                    "symbol": imb.symbol,
                    "direction": imb.direction.value,
                    "price_level": imb.price_level,
                    "compared_price_level": imb.compared_price_level,
                    "ratio": imb.ratio,
                    "aggressive_volume": imb.aggressive_volume,
                    "opposing_volume": imb.opposing_volume,
                    "strength": imb.strength,
                    "confidence": imb.confidence,
                    "date": date_str
                })

            # 3. Stacked Imbalances
            for stk in ctx.stacked_imbalances:
                stacked_records.append({
                    "timestamp": stk.timestamp.isoformat(),
                    "symbol": stk.symbol,
                    "direction": stk.direction.value,
                    "levels_count": stk.levels_count,
                    "top_price": stk.top_price,
                    "bottom_price": stk.bottom_price,
                    "total_volume": stk.total_volume,
                    "average_ratio": stk.average_ratio,
                    "strength": stk.strength,
                    "confidence": stk.confidence,
                    "date": date_str
                })

            # 4. Absorptions
            if ctx.absorption_feature:
                af = ctx.absorption_feature
                abs_records.append({
                    "timestamp": af.timestamp.isoformat(),
                    "symbol": af.symbol,
                    "direction": af.direction.value,
                    "aggressive_volume": af.aggressive_volume,
                    "price_progress": af.price_progress,
                    "range_efficiency": af.range_efficiency,
                    "rejection_score": af.rejection_score,
                    "absorption_score": af.absorption_score,
                    "absorbed_price_level": af.absorbed_price_level,
                    "confidence": af.confidence,
                    "date": date_str
                })

            # 5. Exhaustions
            if ctx.exhaustion_feature:
                ef = ctx.exhaustion_feature
                exh_records.append({
                    "timestamp": ef.timestamp.isoformat(),
                    "symbol": ef.symbol,
                    "direction": ef.direction.value,
                    "extreme_volume": ef.extreme_volume,
                    "current_volume": ef.current_volume,
                    "delta_depletion_ratio": ef.delta_depletion_ratio,
                    "follow_through_failed": ef.follow_through_failed,
                    "exhaustion_score": ef.exhaustion_score,
                    "confidence": ef.confidence,
                    "date": date_str
                })

        # Save partitioned tables
        self._write_records(ctx_records, self.context_dir)
        self._write_records(delta_records, self.delta_dir)
        self._write_records(imb_records, self.imbalance_dir)
        self._write_records(stacked_records, self.stacked_dir)
        self._write_records(abs_records, self.absorption_dir)
        self._write_records(exh_records, self.exhaustion_dir)

        return len(contexts)

    def _write_records(self, records: List[dict], base_path: Path) -> None:
        """Helper to write records grouped by symbol and date into Parquet files."""
        if not records:
            return
        df = pd.DataFrame(records)
        for (sym, dt_str), group in df.groupby(["symbol", "date"]):
            target_file = base_path / str(sym) / f"{dt_str}.parquet"
            target_file.parent.mkdir(parents=True, exist_ok=True)
            table = pa.Table.from_pandas(group.drop(columns=["date"]))
            pq.write_table(table, target_file, compression="SNAPPY")
