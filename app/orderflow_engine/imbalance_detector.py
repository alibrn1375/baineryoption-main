"""Diagonal Imbalance detector identifying bid/ask volume dominance across adjacent price levels."""

from decimal import Decimal
from typing import List, Optional
from app.models.footprint import FootprintBar, PriceLevel
from app.models.orderflow_features import ImbalanceFeature
from app.orderflow_engine.base import FeatureDirection


class ImbalanceDetector:
    """Detects aggressive volume dominance comparing diagonal price levels:
    - BUY Imbalance: Ask volume at Level P compared against Bid volume at Level P - tick_size
    - SELL Imbalance: Bid volume at Level P compared against Ask volume at Level P + tick_size
    """

    def __init__(
        self,
        ratio_threshold: float = 3.0,
        minimum_volume: float = 10.0,
        minimum_delta: float = 5.0
    ) -> None:
        self.ratio_threshold = ratio_threshold
        self.minimum_volume = minimum_volume
        self.minimum_delta = minimum_delta

    def detect_imbalances(self, bar: FootprintBar) -> List[ImbalanceFeature]:
        """Scan price levels in FootprintBar and return detected diagonal imbalances sorted by price."""
        if not bar.levels or len(bar.levels) < 2:
            return []

        # Sort levels ascending by price
        levels: List[PriceLevel] = sorted(bar.levels, key=lambda l: l.price)
        imbalances: List[ImbalanceFeature] = []

        confidence = 1.0 if bar.quality.value == "HIGH_PRECISION" else 0.4

        for i in range(len(levels)):
            current_lvl = levels[i]

            # 1. BUY Imbalance Check (Ask at level i vs Bid at level i-1)
            if i > 0:
                lower_lvl = levels[i - 1]
                ask_vol = current_lvl.ask_volume
                opposing_bid_vol = lower_lvl.bid_volume
                delta_diff = ask_vol - opposing_bid_vol

                if ask_vol >= self.minimum_volume and delta_diff >= self.minimum_delta:
                    ratio = (ask_vol / opposing_bid_vol) if opposing_bid_vol > 0.0 else (ask_vol / 0.1)
                    if ratio >= self.ratio_threshold:
                        imbalances.append(ImbalanceFeature(
                            timestamp=bar.start_time,
                            symbol=bar.symbol,
                            timeframe=bar.timeframe,
                            direction=FeatureDirection.BUY,
                            confidence=confidence,
                            calculation_version="1.0.0",
                            price_level=current_lvl.price,
                            compared_price_level=lower_lvl.price,
                            ratio=round(ratio, 2),
                            aggressive_volume=round(ask_vol, 4),
                            opposing_volume=round(opposing_bid_vol, 4),
                            strength=round(ratio * (ask_vol / self.minimum_volume), 2),
                            details={"type": "DIAGONAL_BUY_IMBALANCE"}
                        ))

            # 2. SELL Imbalance Check (Bid at level i vs Ask at level i+1)
            if i < len(levels) - 1:
                upper_lvl = levels[i + 1]
                bid_vol = current_lvl.bid_volume
                opposing_ask_vol = upper_lvl.ask_volume
                delta_diff = bid_vol - opposing_ask_vol

                if bid_vol >= self.minimum_volume and delta_diff >= self.minimum_delta:
                    ratio = (bid_vol / opposing_ask_vol) if opposing_ask_vol > 0.0 else (bid_vol / 0.1)
                    if ratio >= self.ratio_threshold:
                        imbalances.append(ImbalanceFeature(
                            timestamp=bar.start_time,
                            symbol=bar.symbol,
                            timeframe=bar.timeframe,
                            direction=FeatureDirection.SELL,
                            confidence=confidence,
                            calculation_version="1.0.0",
                            price_level=current_lvl.price,
                            compared_price_level=upper_lvl.price,
                            ratio=round(ratio, 2),
                            aggressive_volume=round(bid_vol, 4),
                            opposing_volume=round(opposing_ask_vol, 4),
                            strength=round(ratio * (bid_vol / self.minimum_volume), 2),
                            details={"type": "DIAGONAL_SELL_IMBALANCE"}
                        ))

        return imbalances
