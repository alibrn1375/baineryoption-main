"""Unit and integration test suite for the market data layer."""

import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Generator
import pytest

from app.data_layer.interfaces import DataSourceMetadata, HistoricalDataProvider, TickType
from app.data_layer.tick_validator import TickValidator
from app.data_layer.tick_normalizer import TickNormalizer
from app.data_layer.data_quality import DataQualityMonitor
from app.data_layer.parquet_storage import ParquetStorage
from app.data_layer.database import DuckDBAnalytics
from app.data_layer.pipeline import DataPipelineManager
from app.models.tick import Tick, TradeSide


class MockHistoricalProvider(HistoricalDataProvider):
    """Test mock historical data stream provider."""

    def __init__(self, raw_ticks: list) -> None:
        self.raw_ticks = raw_ticks
        self.is_connected = False

    def connect(self) -> None:
        self.is_connected = True

    def get_metadata(self) -> DataSourceMetadata:
        return DataSourceMetadata(
            source_name="mock_cme",
            symbol="GC_FUT",
            tick_type=TickType.TRADE_AND_QUOTE
        )

    def get_ticks(self, symbol: str, start_time: datetime, end_time: datetime) -> Generator[dict, None, None]:
        for r in self.raw_ticks:
            yield r

    def close(self) -> None:
        self.is_connected = False


class TestTickValidator:
    """Tests for tick validation engine."""

    def test_valid_tick_pass(self) -> None:
        validator = TickValidator()
        raw = {
            "symbol": "XAU/USD",
            "timestamp": "2026-08-30T10:00:00Z",
            "price": 2750.50,
            "volume": 2.0,
            "bid": 2750.40,
            "ask": 2750.60
        }
        res = validator.validate_raw(raw)
        assert res.valid is True
        assert res.quality_score == 1.0
        assert len(res.errors) == 0

    def test_invalid_negative_price(self) -> None:
        validator = TickValidator()
        raw = {
            "symbol": "GC",
            "timestamp": "2026-08-30T10:00:00Z",
            "price": -100.0,
            "volume": 1.0
        }
        res = validator.validate_raw(raw)
        assert res.valid is False
        assert any("strictly positive" in err for err in res.errors)

    def test_inverted_book_rejection(self) -> None:
        validator = TickValidator()
        raw = {
            "symbol": "GC",
            "timestamp": "2026-08-30T10:00:00Z",
            "price": 2750.0,
            "volume": 1.0,
            "bid": 2755.0,
            "ask": 2750.0  # Ask < Bid
        }
        res = validator.validate_raw(raw)
        assert res.valid is False
        assert any("Crossed/Inverted book" in err for err in res.errors)

    def test_out_of_order_timestamps(self) -> None:
        validator = TickValidator()
        t1 = datetime(2026, 8, 30, 10, 0, 5, tzinfo=timezone.utc)
        t2 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)  # In the past

        raw1 = {"symbol": "GC", "timestamp": t1, "price": 2750.0, "volume": 1.0}
        raw2 = {"symbol": "GC", "timestamp": t2, "price": 2750.0, "volume": 1.0}

        r1 = validator.validate_raw(raw1)
        assert r1.valid is True
        validator.record_validated_tick(t1, 2750.0)

        r2 = validator.validate_raw(raw2)
        assert r2.valid is False
        assert any("Out-of-order" in err for err in r2.errors)


class TestTickNormalizer:
    """Tests for tick normalizer engine."""

    def test_normalize_symbol_and_aggressor(self) -> None:
        normalizer = TickNormalizer()
        raw = {
            "symbol": "GOLD_SPOT",
            "timestamp": 1788084000000,  # Milliseconds epoch
            "price": "2750.80",
            "volume": "10",
            "bid": 2750.50,
            "ask": 2750.80  # Traded at Ask -> BUY
        }
        tick = normalizer.normalize(raw, default_source="test")
        assert tick.symbol == "XAUUSD"
        assert tick.price == 2750.8
        assert tick.volume == 10.0
        assert tick.trade_side == TradeSide.BUY
        assert tick.timestamp.tzinfo is not None


class TestStorageAndDuckDB:
    """Integration tests for Parquet storage and DuckDB analytical queries."""

    def test_parquet_roundtrip_and_analytics(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = ParquetStorage(base_directory=tmp_dir)
            t0 = datetime(2026, 8, 30, 12, 0, 0, tzinfo=timezone.utc)

            ticks = [
                Tick(
                    symbol="XAUUSD",
                    timestamp=t0 + timedelta(seconds=i),
                    price=2750.0 + (i * 0.1),
                    volume=1.0 + i,
                    bid=2749.9,
                    ask=2750.1,
                    trade_side=TradeSide.BUY,
                    source="unit_test"
                )
                for i in range(10)
            ]

            saved = storage.save_ticks(ticks)
            assert saved == 10

            # Stream back
            loaded = list(storage.load_ticks("XAUUSD", t0, t0 + timedelta(seconds=15)))
            assert len(loaded) == 10
            assert loaded[0].price == 2750.0
            assert loaded[-1].price == 2750.9

            # Query with DuckDB
            duck = DuckDBAnalytics(tick_base_dir=tmp_dir)
            summary = duck.get_symbol_summary("XAUUSD")
            assert summary["total_ticks"] == 10
            assert summary["min_price"] == 2750.0
            assert summary["max_price"] == 2750.9
            duck.close()


class TestDataPipelineManager:
    """Full end-to-end pipeline ingestion test."""

    def test_pipeline_ingestion_and_quality_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = ParquetStorage(base_directory=tmp_dir)
            pipeline = DataPipelineManager(storage=storage)

            raw_stream = [
                {"symbol": "GC_FUT", "timestamp": "2026-08-30T10:00:00Z", "price": 2750.0, "volume": 5.0},
                {"symbol": "GC_FUT", "timestamp": "2026-08-30T10:00:01Z", "price": -99.0, "volume": 1.0},  # Invalid
                {"symbol": "GC_FUT", "timestamp": "2026-08-30T10:00:02Z", "price": 2750.5, "volume": 2.0},
            ]

            provider = MockHistoricalProvider(raw_stream)
            t_start = datetime(2026, 8, 30, 9, 0, 0, tzinfo=timezone.utc)
            t_end = datetime(2026, 8, 30, 11, 0, 0, tzinfo=timezone.utc)

            ingested = pipeline.ingest_historical_stream(provider, "GC_FUT", t_start, t_end)
            assert ingested == 2  # 1 invalid tick dropped

            report = pipeline.get_quality_report()
            assert report.total_ticks == 3
            assert report.valid_ticks == 2
            assert report.invalid_ticks == 1
            assert report.quality_score == pytest.approx(0.6667, rel=1e-2)
