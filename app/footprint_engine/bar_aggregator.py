"""Bar Aggregation Engine turning tick streams into strictly-bounded FootprintBars."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from app.core.exceptions import DataValidationError
from app.footprint_engine.delta_calculator import DeltaCalculator
from app.footprint_engine.price_ladder import PriceLadder
from app.footprint_engine.trade_classifier import TradeClassifier
from app.models.footprint import FootprintBar, FootprintQuality
from app.models.tick import Tick, TradeSide


class BarAggregator:
    """Aggregates chronologically-ordered market ticks into discrete timeframe footprint bars."""

    def __init__(
        self,
        symbol: str,
        timeframe_seconds: int = 300,  # 5 minutes default
        tick_size: float = 0.1,
        price_precision: int = 1,
        timeframe_str: str = "5m"
    ) -> None:
        self.symbol = symbol
        self.timeframe_sec = timeframe_seconds
        self.timeframe_str = timeframe_str
        self.tick_size = tick_size
        self.price_precision = price_precision

        self.classifier = TradeClassifier()
        self.ladder = PriceLadder(tick_size=tick_size, price_precision=price_precision)

        # Bar boundary state
        self.current_bar_start: Optional[datetime] = None
        self.current_bar_end: Optional[datetime] = None

        # OHLC state
        self.open: Optional[float] = None
        self.high: Optional[float] = None
        self.low: Optional[float] = None
        self.close: Optional[float] = None

        # Intra-bar delta tracking
        self.running_delta: float = 0.0
        self.min_delta: float = 0.0
        self.max_delta: float = 0.0

        # Quality tracking
        self.total_ticks: int = 0
        self.unknown_classified_ticks: int = 0

    def compute_bar_boundaries(self, dt: datetime) -> tuple[datetime, datetime]:
        """Compute exact floor interval start and exclusive end for a timestamp."""
        ts = dt.timestamp()
        floor_ts = (int(ts) // self.timeframe_sec) * self.timeframe_sec
        bar_start = datetime.fromtimestamp(floor_ts, tz=timezone.utc)
        bar_end = datetime.fromtimestamp(floor_ts + self.timeframe_sec, tz=timezone.utc)
        return bar_start, bar_end

    def add_tick(self, tick: Tick) -> Optional[FootprintBar]:
        """Add a single validated tick to the aggregator.
        
        Returns:
            Completed FootprintBar if this tick crosses into a new bar window, otherwise None.
        """
        tick_time = tick.timestamp if tick.timestamp.tzinfo else tick.timestamp.replace(tzinfo=timezone.utc)
        bar_start, bar_end = self.compute_bar_boundaries(tick_time)

        completed_bar: Optional[FootprintBar] = None

        # If current bar is open and incoming tick is beyond its boundary -> close & emit
        if self.current_bar_start is not None and tick_time >= self.current_bar_end:
            completed_bar = self.finalize_bar()
            self._start_new_bar(bar_start, bar_end)
        elif self.current_bar_start is None:
            self._start_new_bar(bar_start, bar_end)

        # Classify trade
        classification = self.classifier.classify(tick)
        side = classification.side

        # Accumulate metrics
        self.total_ticks += 1
        if side == TradeSide.UNKNOWN:
            self.unknown_classified_ticks += 1

        price = tick.price
        vol = tick.volume

        # Update OHLC
        if self.open is None:
            self.open = price
            self.high = price
            self.low = price
        else:
            self.high = max(self.high, price)
            self.low = min(self.low, price)
        self.close = price

        # Update running delta excursions
        if side == TradeSide.BUY:
            self.running_delta += vol
        elif side == TradeSide.SELL:
            self.running_delta -= vol

        self.min_delta = min(self.min_delta, self.running_delta)
        self.max_delta = max(self.max_delta, self.running_delta)

        # Accumulate in price ladder
        self.ladder.add_trade(price=price, volume=vol, side=side)

        return completed_bar

    def _start_new_bar(self, start_time: datetime, end_time: datetime) -> None:
        """Reset internal accumulator state for a new bar window."""
        self.current_bar_start = start_time
        self.current_bar_end = end_time
        self.open = None
        self.high = None
        self.low = None
        self.close = None
        self.running_delta = 0.0
        self.min_delta = 0.0
        self.max_delta = 0.0
        self.total_ticks = 0
        self.unknown_classified_ticks = 0
        self.ladder.clear()

    def finalize_bar(self) -> Optional[FootprintBar]:
        """Finalize and seal the current active bar into an immutable FootprintBar."""
        if self.current_bar_start is None or self.open is None:
            return None

        levels = self.ladder.build_levels()
        delta_res = DeltaCalculator.calculate_from_levels(
            levels=levels,
            running_min_delta=self.min_delta,
            running_max_delta=self.max_delta
        )
        poc = self.ladder.get_poc_price()

        # Assess quality integrity
        unknown_ratio = (self.unknown_classified_ticks / self.total_ticks) if self.total_ticks > 0 else 0.0
        if unknown_ratio > 0.25:
            quality = FootprintQuality.DEGRADED
        elif unknown_ratio > 0.75:
            quality = FootprintQuality.CORRUPT
        else:
            quality = FootprintQuality.HIGH_PRECISION

        bar = FootprintBar(
            symbol=self.symbol,
            timeframe=self.timeframe_str,
            start_time=self.current_bar_start,
            end_time=self.current_bar_end,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            total_volume=delta_res.total_volume,
            total_bid_volume=delta_res.total_bid_volume,
            total_ask_volume=delta_res.total_ask_volume,
            total_unknown_volume=delta_res.total_unknown_volume,
            bar_delta=delta_res.bar_delta,
            min_delta=delta_res.min_delta,
            max_delta=delta_res.max_delta,
            delta_percentage=delta_res.delta_percentage,
            poc_price=poc,
            levels=levels,
            quality=quality
        )

        return bar
