"""Tick data models representing real-time and historical price-volume events."""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import AliasChoices, BaseModel, Field, field_validator, model_validator


class TickSide(str, Enum):
    """Directional aggressive side of trade execution."""
    BUY = "BUY"
    SELL = "SELL"
    UNKNOWN = "UNKNOWN"
    # Backward compatibility alias
TradeSide = TickSide


class Tick(BaseModel):
    """Discrete trade execution event containing price, volume, and aggressor side."""
    timestamp: datetime = Field(..., description="UTC timestamp of the trade execution")
    symbol: str = Field(..., description="Trading instrument identifier (e.g., GC_FUT, EURUSD)")
    price: float = Field(..., gt=0, description="Trade execution price")
    volume: float = Field(..., gt=0, description="Executed trade quantity/contracts")
    side: TickSide = Field(
        default=TickSide.UNKNOWN,
        validation_alias=AliasChoices("side", "trade_side"),
        description="Aggressive party (BUY/SELL)",
    )
    source: str = Field(default="UNKNOWN", description="Originating data source")

    @property
    def trade_side(self) -> TickSide:
        return self.side

    bid: Optional[float] = None
    ask: Optional[float] = None

    @model_validator(mode="after")
    def validate_spread(self) -> "Tick":
        if self.bid is not None and self.ask is not None and self.bid > self.ask:
            raise ValueError("Bid cannot exceed Ask")
        return self

    model_config = {
        "frozen": True
    }


class MarketTick(BaseModel):
    """Full-depth market tick containing top-of-book quotes, trade execution, and provider metadata."""
    timestamp: datetime = Field(..., description="UTC timestamp of the trade event")
    symbol: str = Field(..., description="Normalized asset symbol (e.g., GC_FUT, XAUUSD)")
    price: float = Field(..., gt=0, description="Execution price of the tick")
    bid: float = Field(..., gt=0, description="Best prevailing bid price")
    ask: float = Field(..., gt=0, description="Best prevailing ask price")
    volume: float = Field(..., ge=0, description="Executed volume quantity")
    side: TickSide = Field(default=TickSide.UNKNOWN, description="Aggressor trade side (BUY/SELL)")
    provider: str = Field(default="GENERIC", description="Originating market data provider (NINJATRADER, WEBSOCKET, etc.)")
    sequence_number: int = Field(default=0, ge=0, description="Monotonically increasing feed sequence number")

    @field_validator("ask")
    @classmethod
    def validate_bid_ask_spread(cls, ask: float, info) -> float:
        """Ensure bid price does not exceed ask price (no crossed market quotes)."""
        bid = info.data.get("bid")
        if bid is not None and bid > ask:
            raise ValueError(f"Crossed market quote: Bid ({bid}) > Ask ({ask})")
        return ask

    def to_standard_tick(self) -> Tick:
        """Convert MarketTick to standard internal FO-X Tick."""
        # Derive aggressor side from price vs bid/ask if UNKNOWN
        resolved_side = self.side
        if resolved_side == TickSide.UNKNOWN:
            if self.price >= self.ask:
                resolved_side = TickSide.BUY
            elif self.price <= self.bid:
                resolved_side = TickSide.SELL
            else:
                mid = (self.bid + self.ask) / 2.0
                resolved_side = TickSide.BUY if self.price >= mid else TickSide.SELL

        return Tick(
            timestamp=self.timestamp,
            symbol=self.symbol,
            price=self.price,
            volume=self.volume,
            side=resolved_side
        )

    model_config = {
        "frozen": True
    }
