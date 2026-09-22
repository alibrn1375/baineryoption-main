"""Market Structure Analyzer detecting Break of Structure (BOS) and Market Structure Shift (MSS)."""

from typing import List, Optional
from app.context_engine.swing_detector import SwingDetector
from app.models.footprint import FootprintBar
from app.models.market_structure import (
    MarketStructureState,
    StructureEvent,
    StructureEventType,
    StructureState,
    SwingPoint,
    SwingType,
)


class StructureAnalyzer:
    """Analyzes confirmed swing progressions to identify BOS, MSS, and overarching trend state."""

    def __init__(
        self,
        swing_detector: Optional[SwingDetector] = None,
        bos_min_ticks: int = 2,
        tick_size: float = 0.10
    ) -> None:
        self.swing_detector = swing_detector or SwingDetector()
        self.bos_min_ticks = bos_min_ticks
        self.tick_size = tick_size

        self._last_event: Optional[StructureEvent] = None
        self._current_state: StructureState = StructureState.UNKNOWN

    def reset(self) -> None:
        """Reset internal structure state."""
        self.swing_detector.reset()
        self._last_event = None
        self._current_state = StructureState.UNKNOWN

    def analyze_bar(self, bar: FootprintBar) -> MarketStructureState:
        """Process bar, update swings, and detect structure events."""
        # 1. Update swing detector
        new_swing = self.swing_detector.process_bar(bar)

        last_high = self.swing_detector.get_last_swing_high()
        last_low = self.swing_detector.get_last_swing_low()

        min_break_dist = self.bos_min_ticks * self.tick_size
        event: Optional[StructureEvent] = None

        # 2. Check for Bullish Break of Structure (BOS) or Shift (MSS)
        # Price closes above previous confirmed Swing High
        if last_high is not None and bar.close >= (last_high.price + min_break_dist):
            break_dist = bar.close - last_high.price
            event_type = StructureEventType.BOS if self._current_state == StructureState.TREND_UP else StructureEventType.MSS
            self._current_state = StructureState.TREND_UP

            event = StructureEvent(
                timestamp=bar.start_time,
                symbol=bar.symbol,
                timeframe=bar.timeframe,
                event_type=event_type,
                price=bar.close,
                broken_swing_price=last_high.price,
                strength=round(break_dist / self.tick_size, 2),
                confidence=1.0,
                details={
                    "break_distance": round(break_dist, 4),
                    "previous_swing_time": last_high.timestamp.isoformat(),
                    "bar_volume": bar.total_volume
                }
            )
            self._last_event = event

        # 3. Check for Bearish Break of Structure (BOS) or Shift (MSS)
        # Price closes below previous confirmed Swing Low
        elif last_low is not None and bar.close <= (last_low.price - min_break_dist):
            break_dist = last_low.price - bar.close
            event_type = StructureEventType.BOS if self._current_state == StructureState.TREND_DOWN else StructureEventType.MSS
            self._current_state = StructureState.TREND_DOWN

            event = StructureEvent(
                timestamp=bar.start_time,
                symbol=bar.symbol,
                timeframe=bar.timeframe,
                event_type=event_type,
                price=bar.close,
                broken_swing_price=last_low.price,
                strength=round(break_dist / self.tick_size, 2),
                confidence=1.0,
                details={
                    "break_distance": round(break_dist, 4),
                    "previous_swing_time": last_low.timestamp.isoformat(),
                    "bar_volume": bar.total_volume
                }
            )
            self._last_event = event

        # 4. If contained within high and low, check if in Range
        elif last_high is not None and last_low is not None:
            if last_low.price <= bar.close <= last_high.price:
                if self._current_state == StructureState.UNKNOWN:
                    self._current_state = StructureState.RANGE

        # Return comprehensive state
        return MarketStructureState(
            timestamp=bar.start_time,
            symbol=bar.symbol,
            timeframe=bar.timeframe,
            current_state=self._current_state,
            last_swing_high=last_high,
            last_swing_low=last_low,
            last_event=self._last_event,
            structure_quality=1.0,
            confidence=1.0 if bar.quality.value == "HIGH_PRECISION" else 0.5
        )
