"""Footprint and Order Flow aggregated candlestick domain models."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class FootprintQuality(str, Enum):
    """Integrity status of footprint calculation based on underlying source data."""
    HIGH_PRECISION = "HIGH_PRECISION"  # True Bid/Ask real traded volume
    DEGRADED = "DEGRADED"              # Missing or partially inferred Bid/Ask volume
    CORRUPT = "CORRUPT"                # Inconsistent volume or broken ticks
    INTERPOLATED = "INTERPOLATED"


class PriceLevel(BaseModel):
    """Bid x Ask traded volume distribution at a discrete price tick."""
    price: float = Field(..., gt=0.0, description="Discrete rounded price level")
    bid_volume: float = Field(default=0.0, ge=0.0, description="Volume sold into bid (Aggressive Sell)")
    ask_volume: float = Field(default=0.0, ge=0.0, description="Volume bought from ask (Aggressive Buy)")
    unknown_volume: float = Field(default=0.0, ge=0.0, description="Volume with unclassifiable trade side")
    total_volume: float = Field(default=0.0, ge=0.0, description="Total traded volume: bid + ask + unknown")
    delta: float = Field(default=0.0, description="Net directional delta: ask_volume - bid_volume")

    @model_validator(mode="before")
    @classmethod
    def compute_defaults(cls, values: Dict[str, float]) -> Dict[str, float]:
        bid = float(values.get("bid_volume", 0.0))
        ask = float(values.get("ask_volume", 0.0))
        unknown = float(values.get("unknown_volume", 0.0))
        if "delta" not in values:
            values["delta"] = ask - bid
        if "total_volume" not in values:
            values["total_volume"] = ask + bid + unknown
        return values

    model_config = {
        "frozen": True
    }


# Backwards compatibility alias for PriceLevel
FootprintLevel = PriceLevel


class CVDPoint(BaseModel):
    """Cumulative Volume Delta observation point."""
    timestamp: datetime = Field(..., description="Timestamp of the CVD observation (UTC)")
    symbol: str = Field(..., description="Instrument symbol (e.g. GC_FUT, XAUUSD)")
    session: str = Field(..., description="Active session name (e.g. ASIA, LONDON, NEW_YORK)")
    cumulative_delta: float = Field(..., description="Running cumulative delta within current session")
    bar_delta: float = Field(..., description="Delta of the single bar")

    model_config = {
        "frozen": True
    }


class FootprintBar(BaseModel):
    """Full 5-minute candlestick containing OHLC metrics, granular price levels, and delta distribution."""
    symbol: str = Field(..., description="Instrument symbol (e.g. GC_FUT, XAUUSD)")
    timeframe: str = Field(default="5m", description="Bar timeframe, default 5m")
    start_time: datetime = Field(..., description="Start timestamp of the bar (UTC, inclusive)")
    end_time: datetime = Field(..., description="End timestamp of the bar (UTC, exclusive)")
    open: float = Field(..., gt=0.0, description="Opening price")
    high: float = Field(..., gt=0.0, description="Highest price of the bar")
    low: float = Field(..., gt=0.0, description="Lowest price of the bar")
    close: float = Field(..., gt=0.0, description="Closing price of the bar")
    total_volume: float = Field(default=0.0, ge=0.0, description="Total accumulated volume across all levels")
    total_bid_volume: float = Field(default=0.0, ge=0.0, description="Total aggressive sell volume")
    total_ask_volume: float = Field(default=0.0, ge=0.0, description="Total aggressive buy volume")
    total_unknown_volume: float = Field(default=0.0, ge=0.0, description="Total unclassified volume")
    bar_delta: float = Field(default=0.0, description="Bar net delta: total_ask_volume - total_bid_volume")
    min_delta: float = Field(default=0.0, description="Intra-bar lowest delta excursion")
    max_delta: float = Field(default=0.0, description="Intra-bar highest delta excursion")
    delta_percentage: float = Field(default=0.0, description="Bar delta as percentage of total volume")
    poc_price: Optional[float] = Field(None, gt=0.0, description="Point of Control (price level with max volume)")
    levels: List[PriceLevel] = Field(default_factory=list, description="Sorted list of price levels")
    quality: FootprintQuality = Field(default=FootprintQuality.HIGH_PRECISION, description="Quality integrity status")

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_inputs(cls, values: Dict[str, object]) -> Dict[str, object]:
        values = dict(values)
        timestamp = values.get("timestamp")
        if "start_time" not in values and timestamp is not None:
            values["start_time"] = timestamp
        if "end_time" not in values and timestamp is not None:
            values["end_time"] = timestamp + timedelta(minutes=5)
        if "bar_delta" not in values and "delta" in values:
            values["bar_delta"] = values["delta"]
        if "total_ask_volume" not in values and "total_bid_volume" not in values:
            total_volume = float(values.get("total_volume", 0.0))
            bar_delta = float(values.get("bar_delta", 0.0))
            values["total_ask_volume"] = (total_volume + bar_delta) / 2.0
            values["total_bid_volume"] = (total_volume - bar_delta) / 2.0
        return values

    @property
    def timestamp(self) -> datetime:
        """Alias for start_time for backwards compatibility."""
        return self.start_time

    @property
    def delta(self) -> float:
        """Alias for bar_delta for backwards compatibility."""
        return self.bar_delta

    @model_validator(mode="after")
    def validate_ohlc_consistency(self) -> "FootprintBar":
        if self.high < max(self.open, self.close, self.low):
            raise ValueError(f"High ({self.high}) cannot be lower than Open ({self.open}), Close ({self.close}), or Low ({self.low})")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError(f"Low ({self.low}) cannot be higher than Open ({self.open}), Close ({self.close}), or High ({self.high})")
        if self.end_time <= self.start_time:
            raise ValueError(f"End time ({self.end_time}) must be strictly after start time ({self.start_time})")
        return self

    model_config = {
        "frozen": True
    }
