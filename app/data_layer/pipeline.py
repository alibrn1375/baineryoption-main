"""Comprehensive unified market data pipeline manager."""

from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

from app.core.exceptions import DataValidationError
from app.core.logging import app_logger, log_event
from app.data_layer.data_quality import DataQualityMonitor, DataQualityReport
from app.data_layer.interfaces import HistoricalDataProvider
from app.data_layer.storage.base_storage import BaseStorage
from app.data_layer.tick_normalizer import TickNormalizer
from app.data_layer.tick_validator import TickValidator
from app.models.tick import Tick


class DataPipelineManager:
    """Manages the full lifecycle: Source -> Validation -> Normalization -> Storage."""

    def __init__(
        self,
        storage: Optional[BaseStorage] = None,
        validator: Optional[TickValidator] = None,
        normalizer: Optional[TickNormalizer] = None,
        quality_monitor: Optional[DataQualityMonitor] = None,
        batch_size: int = 5000
    ) -> None:
        self.storage = storage
        self.validator = validator or TickValidator()
        self.normalizer = normalizer or TickNormalizer()
        self.quality_monitor = quality_monitor or DataQualityMonitor()
        self.batch_size = batch_size

    def process_raw_tick(self, raw_data: Dict[str, Any]) -> Optional[Tick]:
        """Validate and normalize a single incoming raw tick dictionary."""
        val_result = self.validator.validate_raw(raw_data)
        now_utc = datetime.now(timezone.utc)

        if not val_result.valid:
            self.quality_monitor.record_tick(
                tick_time=now_utc,
                is_valid=False,
                error_msg="; ".join(val_result.errors)
            )
            return None

        try:
            tick = self.normalizer.normalize(raw_data)
            self.validator.record_validated_tick(tick.timestamp, tick.price)
            self.quality_monitor.record_tick(
                tick_time=tick.timestamp,
                is_valid=True,
                is_duplicate=bool("duplicate" in " ".join(val_result.warnings).lower())
            )
            return tick
        except DataValidationError as e:
            app_logger.warning(f"Normalization failed: {e}")
            self.quality_monitor.record_tick(
                tick_time=now_utc,
                is_valid=False,
                error_msg=str(e)
            )
            return None

    def ingest_historical_stream(
        self,
        provider: HistoricalDataProvider,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> int:
        """Stream from a historical provider, validate, normalize, and commit to storage."""
        log_event("INGESTION_START", f"Starting historical ingestion for {symbol}", {
            "symbol": symbol,
            "start": start_time.isoformat(),
            "end": end_time.isoformat()
        })

        provider.connect()
        batch: List[Tick] = []
        total_ingested = 0

        try:
            for raw_tick in provider.get_ticks(symbol, start_time, end_time):
                tick = self.process_raw_tick(raw_tick)
                if tick:
                    batch.append(tick)
                    if len(batch) >= self.batch_size:
                        if self.storage:
                            self.storage.save_ticks(batch)
                        total_ingested += len(batch)
                        batch.clear()

            # Flush remaining
            if batch and self.storage:
                self.storage.save_ticks(batch)
                total_ingested += len(batch)
                batch.clear()

            log_event("INGESTION_COMPLETE", f"Finished ingestion for {symbol}", {
                "symbol": symbol,
                "total_ingested": total_ingested
            })
            return total_ingested
        finally:
            provider.close()

    def get_quality_report(self) -> DataQualityReport:
        """Fetch current data stream quality metrics."""
        return self.quality_monitor.generate_report()
