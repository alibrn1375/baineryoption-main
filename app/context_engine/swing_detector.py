"""Swing point detector identifying pivot highs and lows without future data leakage."""

from collections import deque
from datetime import datetime
from typing import Deque, List, Optional
from app.models.footprint import FootprintBar
from app.models.market_structure import SwingPoint, SwingType


class SwingDetector:
    """Detects confirmed swing highs and swing lows using a strict sliding window with zero lookahead."""

    def __init__(self, swing_length: int = 3) -> None:
        self.swing_length = swing_length
        # Window size needed to confirm a swing is (2 * swing_length + 1)
        self.window_size = (2 * self.swing_length) + 1
        self._bar_buffer: Deque[FootprintBar] = deque(maxlen=self.window_size)
        self._confirmed_swings: List[SwingPoint] = []

    def reset(self) -> None:
        """Reset internal buffer and history."""
        self._bar_buffer.clear()
        self._confirmed_swings.clear()

    def process_bar(self, bar: FootprintBar) -> Optional[SwingPoint]:
        """Add completed bar to window and check if the pivot candidate in the center is confirmed."""
        self._bar_buffer.append(bar)

        if len(self._bar_buffer) < self.window_size:
            return None

        bars = list(self._bar_buffer)
        pivot_idx = self.swing_length
        candidate_bar = bars[pivot_idx]
        current_confirmation_bar = bars[-1]

        # 1. Check for Swing High candidate
        candidate_high = candidate_bar.high
        is_swing_high = True
        for i in range(self.window_size):
            if i == pivot_idx:
                continue
            if bars[i].high >= candidate_high:
                is_swing_high = False
                break

        if is_swing_high:
            strength = 1.0 + (candidate_bar.total_volume / 1000.0)
            swing = SwingPoint(
                timestamp=candidate_bar.start_time,
                price=candidate_high,
                type=SwingType.SWING_HIGH,
                strength=round(strength, 2),
                confirmed_timestamp=current_confirmation_bar.start_time
            )
            self._confirmed_swings.append(swing)
            return swing

        # 2. Check for Swing Low candidate
        candidate_low = candidate_bar.low
        is_swing_low = True
        for i in range(self.window_size):
            if i == pivot_idx:
                continue
            if bars[i].low <= candidate_low:
                is_swing_low = False
                break

        if is_swing_low:
            strength = 1.0 + (candidate_bar.total_volume / 1000.0)
            swing = SwingPoint(
                timestamp=candidate_bar.start_time,
                price=candidate_low,
                type=SwingType.SWING_LOW,
                strength=round(strength, 2),
                confirmed_timestamp=current_confirmation_bar.start_time
            )
            self._confirmed_swings.append(swing)
            return swing

        return None

    def get_last_swing_high(self) -> Optional[SwingPoint]:
        """Return most recently confirmed Swing High."""
        for s in reversed(self._confirmed_swings):
            if s.type == SwingType.SWING_HIGH:
                return s
        return None

    def get_last_swing_low(self) -> Optional[SwingPoint]:
        """Return most recently confirmed Swing Low."""
        for s in reversed(self._confirmed_swings):
            if s.type == SwingType.SWING_LOW:
                return s
        return None

    def get_recent_swings(self, count: int = 10) -> List[SwingPoint]:
        """Return list of recent confirmed swings."""
        return self._confirmed_swings[-count:]
