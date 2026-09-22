"""Historical Replay Engine processing market data in strict chronological order with zero future leakage."""

import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional
import pandas as pd
from pydantic import BaseModel, Field

from app.models.tick import Tick
from app.validation_engine.events import EventType, MarketEvent


class ReplaySpeedMode(str, Enum):
    """Replay execution speed modes."""
    REAL_TIME = "REAL_TIME"
    FAST = "FAST"
    STEP_BY_STEP = "STEP_BY_STEP"


class ReplaySession(BaseModel):
    """Replay session configuration and execution metadata."""
    session_id: str = Field(..., description="Unique replay execution ID")
    start_time: datetime = Field(..., description="Replay start boundary (UTC)")
    end_time: datetime = Field(..., description="Replay end boundary (UTC)")
    symbol: str = Field(..., description="Target asset symbol")
    data_source: str = Field(default="parquet", description="Source data format / path")
    speed_mode: ReplaySpeedMode = Field(default=ReplaySpeedMode.FAST, description="REAL_TIME, FAST, STEP_BY_STEP")

    model_config = {
        "frozen": True
    }


class ReplayEngine:
    """Streams historical tick feeds sequentially with strict temporal barriers preventing lookahead."""

    def __init__(self, session: ReplaySession) -> None:
        self.session = session
        self._current_time: Optional[datetime] = None
        self._sequence: int = 0
        self._is_paused: bool = False

    @property
    def current_time(self) -> Optional[datetime]:
        """Return the current replay timestamp. Any access to data > current_time is strictly forbidden."""
        return self._current_time

    def stream_ticks(self, ticks: List[Tick]) -> Generator[MarketEvent, None, None]:
        """Stream ticks sequentially, filtering strictly within [start_time, end_time] and sorted by timestamp."""
        # Ensure strict ascending chronological order
        sorted_ticks = sorted(ticks, key=lambda t: t.timestamp)

        for tick in sorted_ticks:
            # Enforce start and end boundary filters
            if tick.timestamp < self.session.start_time:
                continue
            if tick.timestamp > self.session.end_time:
                break

            # Advance current simulation clock to current tick timestamp
            self._current_time = tick.timestamp
            self._sequence += 1

            if self.session.speed_mode == ReplaySpeedMode.REAL_TIME:
                time.sleep(0.001)

            yield MarketEvent(
                timestamp=tick.timestamp,
                event_type=EventType.TICK,
                symbol=tick.symbol,
                sequence_id=self._sequence,
                payload={"tick": tick}
            )
