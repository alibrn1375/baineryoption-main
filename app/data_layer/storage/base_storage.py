"""Abstract base class interface for timeseries tick storage backends."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Generator, List, Optional
from app.models.tick import Tick


class BaseStorage(ABC):
    """Abstract storage interface for writing and retrieving normalized tick data."""

    @abstractmethod
    def save_ticks(self, ticks: List[Tick]) -> int:
        """Persist a batch of validated ticks. Returns number of saved records."""
        pass

    @abstractmethod
    def load_ticks(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> Generator[Tick, None, None]:
        """Stream stored ticks within a chronological time window."""
        pass

    @abstractmethod
    def get_tick_count(self, symbol: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> int:
        """Get the total count of ticks for a symbol."""
        pass

    @abstractmethod
    def delete_range(self, symbol: str, start_time: datetime, end_time: datetime) -> int:
        """Delete ticks within a specified time range. Returns deleted count."""
        pass
