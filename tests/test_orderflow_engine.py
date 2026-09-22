"""Comprehensive test suite for the FO-X 5M Order Flow Intelligence Engine."""

import tempfile
from datetime import datetime, timezone
import pytest

from app.models.footprint import FootprintBar, FootprintQuality, PriceLevel
from app.orderflow_engine.absorption_detector import AbsorptionDetector
from app.orderflow_engine.base import FeatureDirection
from app.orderflow_engine.delta_analyzer import DeltaAnalyzer
from app.orderflow_engine.exhaustion_detector import ExhaustionDetector
from app.orderflow_engine.imbalance_detector import ImbalanceDetector
from app.orderflow_engine.pipeline import OrderFlowFeaturePipeline
from app.orderflow_engine.stacked_imbalance import StackedImbalanceDetector
from app.storage.orderflow_storage import OrderFlowStorage


class TestDeltaAnalyzer:
    """Test suite for Delta Intelligence measurements."""

    def test_delta_strength_and_persistence(self) -> None:
        analyzer = DeltaAnalyzer(lookback_period=10, min_samples=3)
        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)

        # Bar 1: Positive Delta
        bar1 = FootprintBar(
            symbol="GC_FUT",
            start_time=t0,
            end_time=datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc),
            open=2750.0, high=2755.0, low=2750.0, close=2754.0,
            total_volume=100.0, total_bid_volume=30.0, total_ask_volume=70.0,
            bar_delta=40.0, delta_percentage=40.0
        )
        res1 = analyzer.analyze(bar1)
        assert res1.direction == FeatureDirection.BUY
        assert res1.persistence == 1
        assert res1.acceleration == 0.0

        # Bar 2: Continuing Positive Delta -> Persistence=2, Acceleration=+10
        bar2 = FootprintBar(
            symbol="GC_FUT",
            start_time=datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 30, 10, 10, 0, tzinfo=timezone.utc),
            open=2754.0, high=2760.0, low=2753.0, close=2759.0,
            total_volume=120.0, total_bid_volume=35.0, total_ask_volume=85.0,
            bar_delta=50.0, delta_percentage=41.67
        )
        res2 = analyzer.analyze(bar2)
        assert res2.direction == FeatureDirection.BUY
        assert res2.persistence == 2
        assert res2.acceleration == 10.0


class TestImbalanceDetector:
    """Test suite for Diagonal and Stacked Imbalance detection."""

    def test_diagonal_buy_imbalance(self) -> None:
        detector = ImbalanceDetector(ratio_threshold=3.0, minimum_volume=10.0, minimum_delta=5.0)

        # Price Levels (Ascending):
        # 2750.0: Bid=2.0, Ask=10.0
        # 2750.1: Bid=5.0, Ask=30.0 (Ask 30 vs diagonal Bid 2 at 2750.0 -> Ratio = 15.0 >= 3.0) -> BUY Imbalance!
        levels = [
            PriceLevel(price=2750.0, bid_volume=2.0, ask_volume=10.0),
            PriceLevel(price=2750.1, bid_volume=5.0, ask_volume=30.0),
        ]
        bar = FootprintBar(
            symbol="GC_FUT",
            start_time=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc),
            open=2750.0, high=2750.1, low=2750.0, close=2750.1,
            total_volume=47.0, total_bid_volume=7.0, total_ask_volume=40.0,
            bar_delta=33.0, levels=levels
        )

        imbalances = detector.detect_imbalances(bar)
        assert len(imbalances) == 1
        assert imbalances[0].direction == FeatureDirection.BUY
        assert imbalances[0].price_level == 2750.1
        assert imbalances[0].ratio == 15.0

    def test_stacked_imbalance_detection(self) -> None:
        detector = ImbalanceDetector(ratio_threshold=3.0, minimum_volume=10.0, minimum_delta=5.0)
        stacked_detector = StackedImbalanceDetector(min_consecutive_levels=3, max_level_gap_ticks=1, imbalance_detector=detector)

        # 4 consecutive BUY imbalances
        levels = [
            PriceLevel(price=2750.0, bid_volume=2.0, ask_volume=10.0),
            PriceLevel(price=2750.1, bid_volume=2.0, ask_volume=20.0), # Ask 20 vs Bid 2 (2750.0) -> Buy Imbalance 1
            PriceLevel(price=2750.2, bid_volume=2.0, ask_volume=25.0), # Ask 25 vs Bid 2 (2750.1) -> Buy Imbalance 2
            PriceLevel(price=2750.3, bid_volume=2.0, ask_volume=30.0), # Ask 30 vs Bid 2 (2750.2) -> Buy Imbalance 3
        ]
        bar = FootprintBar(
            symbol="GC_FUT",
            start_time=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc),
            open=2750.0, high=2750.3, low=2750.0, close=2750.3,
            total_volume=100.0, total_bid_volume=8.0, total_ask_volume=85.0,
            bar_delta=77.0, levels=levels
        )

        imbalances = detector.detect_imbalances(bar)
        assert len(imbalances) == 3

        stacked = stacked_detector.detect_stacked(bar, tick_size=0.1, existing_imbalances=imbalances)
        assert len(stacked) == 1
        assert stacked[0].direction == FeatureDirection.BUY
        assert stacked[0].levels_count == 3
        assert stacked[0].top_price == 2750.3
        assert stacked[0].bottom_price == 2750.1


class TestAbsorptionDetector:
    """Test suite for Quantitative Absorption detection."""

    def test_buying_absorption_at_highs(self) -> None:
        detector = AbsorptionDetector(
            volume_percentile_threshold=50.0,
            price_efficiency_max=0.35,
            rejection_return_pct=0.40,
            min_absorption_volume=50.0
        )

        # High volume (200), strong positive delta (+60), but long upper wick rejection (High=2760, Close=2752, Open=2750)
        # Bar range = 10 (2750 to 2760), Upper Wick = 2760 - 2752 = 8 -> 80% upper wick!
        bar = FootprintBar(
            symbol="GC_FUT",
            start_time=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc),
            open=2750.0, high=2760.0, low=2750.0, close=2752.0,
            total_volume=200.0, total_bid_volume=70.0, total_ask_volume=130.0,
            bar_delta=60.0
        )

        absorption = detector.detect(bar)
        assert absorption is not None
        assert absorption.direction == FeatureDirection.BUY
        assert absorption.rejection_score >= 0.8
        assert absorption.absorbed_price_level == 2760.0

    def test_low_volume_not_absorbed(self) -> None:
        detector = AbsorptionDetector(min_absorption_volume=100.0)
        bar = FootprintBar(
            symbol="GC_FUT",
            start_time=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc),
            open=2750.0, high=2755.0, low=2750.0, close=2751.0,
            total_volume=20.0, total_bid_volume=5.0, total_ask_volume=15.0,  # Below threshold
            bar_delta=10.0
        )
        assert detector.detect(bar) is None


class TestExhaustionDetector:
    """Test suite for Momentum Exhaustion detection."""

    def test_buying_exhaustion_at_new_high(self) -> None:
        detector = ExhaustionDetector(delta_drop_ratio=0.50)

        t0 = datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc)

        # Bar 1: Strong buying push (Delta = +100)
        bar1 = FootprintBar(
            symbol="GC_FUT",
            start_time=t0, end_time=t1,
            open=2750.0, high=2755.0, low=2750.0, close=2755.0,
            total_volume=200.0, total_bid_volume=50.0, total_ask_volume=150.0,
            bar_delta=100.0
        )
        detector.detect(bar1)

        # Bar 2: Makes new high (2756.0), but Delta severely collapses to +10 (90% drop)
        bar2 = FootprintBar(
            symbol="GC_FUT",
            start_time=t1,
            end_time=datetime(2026, 8, 30, 10, 10, 0, tzinfo=timezone.utc),
            open=2755.0, high=2756.0, low=2754.0, close=2754.5,
            total_volume=80.0, total_bid_volume=35.0, total_ask_volume=45.0,
            bar_delta=10.0
        )
        exhaustion = detector.detect(bar2)
        assert exhaustion is not None
        assert exhaustion.direction == FeatureDirection.BUY
        assert exhaustion.delta_depletion_ratio >= 0.50
        assert exhaustion.follow_through_failed is True


class TestOrderFlowPipelineAndStorage:
    """Integration test for complete Order Flow Pipeline and Parquet storage."""

    def test_pipeline_processing_and_storage(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            storage = OrderFlowStorage(base_directory=tmp_dir)
            pipeline = OrderFlowFeaturePipeline(config_path="configs/orderflow_config.yaml", storage=storage)

            bar = FootprintBar(
                symbol="GC_FUT",
                start_time=datetime(2026, 8, 30, 10, 0, 0, tzinfo=timezone.utc),
                end_time=datetime(2026, 8, 30, 10, 5, 0, tzinfo=timezone.utc),
                open=2750.0, high=2755.0, low=2750.0, close=2754.0,
                total_volume=100.0, total_bid_volume=20.0, total_ask_volume=80.0,
                bar_delta=60.0,
                levels=[
                    PriceLevel(price=2750.0, bid_volume=5.0, ask_volume=10.0),
                    PriceLevel(price=2750.1, bid_volume=5.0, ask_volume=20.0),
                ]
            )

            context = pipeline.process_bar(bar)
            assert context.symbol == "GC_FUT"
            assert context.delta_feature is not None
            assert context.delta_feature.bar_delta == 60.0
            assert context.dominant_direction == FeatureDirection.BUY
