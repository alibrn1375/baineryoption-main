"""Stacked Imbalance detector identifying consecutive directional imbalances forming institutional clusters."""

from decimal import Decimal
from typing import List, Optional
from app.models.footprint import FootprintBar
from app.models.orderflow_features import ImbalanceFeature, StackedImbalanceFeature
from app.orderflow_engine.base import FeatureDirection
from app.orderflow_engine.imbalance_detector import ImbalanceDetector


class StackedImbalanceDetector:
    """Detects consecutive contiguous price levels possessing unidirectional diagonal imbalances."""

    def __init__(
        self,
        min_consecutive_levels: int = 3,
        max_level_gap_ticks: int = 1,
        imbalance_detector: Optional[ImbalanceDetector] = None
    ) -> None:
        self.min_consecutive_levels = min_consecutive_levels
        self.max_level_gap_ticks = max_level_gap_ticks
        self.imbalance_detector = imbalance_detector or ImbalanceDetector()

    def detect_stacked(
        self,
        bar: FootprintBar,
        tick_size: float = 0.1,
        existing_imbalances: Optional[List[ImbalanceFeature]] = None
    ) -> List[StackedImbalanceFeature]:
        """Group detected individual diagonal imbalances into stacked clusters."""
        imbalances = existing_imbalances if existing_imbalances is not None else self.imbalance_detector.detect_imbalances(bar)
        if not imbalances or len(imbalances) < self.min_consecutive_levels:
            return []

        # Split into BUY and SELL groups
        buy_imb = sorted([imb for imb in imbalances if imb.direction == FeatureDirection.BUY], key=lambda x: x.price_level)
        sell_imb = sorted([imb for imb in imbalances if imb.direction == FeatureDirection.SELL], key=lambda x: x.price_level)

        stacked_features: List[StackedImbalanceFeature] = []

        # Helper to find clusters
        for direction, imb_list in [(FeatureDirection.BUY, buy_imb), (FeatureDirection.SELL, sell_imb)]:
            if len(imb_list) < self.min_consecutive_levels:
                continue

            current_cluster: List[ImbalanceFeature] = [imb_list[0]]
            dec_tick = Decimal(str(tick_size))

            for i in range(1, len(imb_list)):
                prev_price = Decimal(str(imb_list[i - 1].price_level))
                curr_price = Decimal(str(imb_list[i].price_level))
                gap = (curr_price - prev_price) / dec_tick

                # If contiguous within allowed tick gap
                if 1 <= gap <= (self.max_level_gap_ticks + 1):
                    current_cluster.append(imb_list[i])
                else:
                    if len(current_cluster) >= self.min_consecutive_levels:
                        stacked_features.append(self._create_stacked_feature(bar, direction, current_cluster))
                    current_cluster = [imb_list[i]]

            if len(current_cluster) >= self.min_consecutive_levels:
                stacked_features.append(self._create_stacked_feature(bar, direction, current_cluster))

        return stacked_features

    def _create_stacked_feature(
        self,
        bar: FootprintBar,
        direction: FeatureDirection,
        cluster: List[ImbalanceFeature]
    ) -> StackedImbalanceFeature:
        """Build immutable StackedImbalanceFeature object."""
        prices = [imb.price_level for imb in cluster]
        total_vol = sum(imb.aggressive_volume for imb in cluster)
        avg_ratio = sum(imb.ratio for imb in cluster) / len(cluster)
        confidence = min(imb.confidence for imb in cluster)

        return StackedImbalanceFeature(
            timestamp=bar.start_time,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            direction=direction,
            confidence=confidence,
            calculation_version="1.0.0",
            levels_count=len(cluster),
            price_levels=prices,
            total_volume=round(total_vol, 4),
            average_ratio=round(avg_ratio, 2),
            top_price=max(prices),
            bottom_price=min(prices),
            strength=round(len(cluster) * avg_ratio * (total_vol / 10.0), 2),
            details={
                "cluster_levels": [
                    {"price": imb.price_level, "vol": imb.aggressive_volume, "ratio": imb.ratio}
                    for imb in cluster
                ]
            }
        )
