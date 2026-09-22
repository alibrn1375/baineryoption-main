"""Abstract provider interfaces and metadata models for the data layer."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import AsyncGenerator, Generator, List, Optional
from pydantic import BaseModel, Field


class TickType(str, Enum):
    """Granularity and type of market data."""
    TRADE = "TRADE"              # Executed transactions (Price, Volume)
    QUOTE = "QUOTE"              # BBO updates (Bid, Ask, BidSize, AskSize)
    TRADE_AND_QUOTE = "TRADE_AND_QUOTE"  # Full Level 1 trade + quote feed


class DataSourceMetadata(BaseModel):
    """Metadata describing a historical or live market data source."""
    source_name: str = Field(..., description="Provider or broker identifier (e.g. CME, LMAX, Dukascopy)")
    symbol: str = Field(..., description="Market symbol (e.g. XAUUSD, GC)")
    timezone: str = Field(default="UTC", description="Reference data timezone")
    tick_type: TickType = Field(default=TickType.TRADE_AND_QUOTE, description="Data type granularity")
    start_date: Optional[datetime] = Field(None, description="Start timestamp of available records")
    end_date: Optional[datetime] = Field(None, description="End timestamp of available records")
    total_records: Optional[int] = Field(None, ge=0, description="Total count of ticks if known")

    model_config = {
        "frozen": True
    }


class HistoricalDataProvider(ABC):
    """Abstract interface for historical tick data providers."""

    @abstractmethod
    def connect(self) -> None:
        """Establish connection or initialize file reader handles."""
        pass

    @abstractmethod
    def get_metadata(self) -> DataSourceMetadata:
        """Retrieve dataset metadata."""
        pass

    @abstractmethod
    def get_ticks(
        self,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> Generator[dict, None, None]:
        """Stream historical raw tick records in strict chronological order."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Release underlying resources and file pointers."""
        pass


class LiveDataProvider(ABC):
    """Abstract interface for real-time live market data stream providers."""

    @abstractmethod
    async def connect(self) -> None:
        """Establish asynchronous socket / network connection."""
        pass

    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> None:
        """Subscribe to real-time market data feed for specified symbols."""
        pass

    @abstractmethod
    async def stream_ticks(self) -> AsyncGenerator[dict, None]:
        """Asynchronously stream live incoming raw market ticks."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Gracefully disconnect and terminate streams."""
        pass
