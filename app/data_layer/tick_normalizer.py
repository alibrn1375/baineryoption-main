"""Tick Normalizer standardizing symbol formats, timestamp representations, decimal scales, and volume."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import dateutil.parser

from app.models.tick import MarketTick, Tick, TickSide


class TickNormalizer:
    """Normalizes heterogeneous raw payload formats from various exchanges/brokers into standardized MarketTicks."""

    SYMBOL_MAP = {
        "GC": "GC_FUT",
        "GC=F": "GC_FUT",
        "GOLD": "GC_FUT",
        "GOLD_SPOT": "XAUUSD",
        "XAUUSD": "XAUUSD",
        "XAU/USD": "XAUUSD",
        "EURUSD": "EURUSD",
        "EUR/USD": "EURUSD",
        "6E": "6E_FUT",
    }

    DECIMAL_PRECISION = {
        "GC_FUT": 2,
        "XAUUSD": 2,
        "EURUSD": 5,
        "6E_FUT": 5,
    }

    def normalize(
        self,
        raw_data: Dict[str, Any],
        default_source: str = "GENERIC",
        default_symbol: Optional[str] = None,
    ) -> Tick:
        """Normalize a raw payload into the storage-layer Tick contract."""
        market_tick = self.normalize_raw_tick(
            raw_data,
            provider_name=default_source,
            default_symbol=default_symbol,
        )
        return market_tick.to_standard_tick().model_copy(update={"source": default_source})

    @classmethod
    def normalize_symbol(cls, raw_symbol: str) -> str:
        """Map provider-specific symbol strings to unified FO-X 5M asset identifiers."""
        cleaned = raw_symbol.strip().upper().replace(" ", "")
        return cls.SYMBOL_MAP.get(cleaned, cleaned)

    @classmethod
    def parse_timestamp(cls, raw_ts: Any) -> datetime:
        """Robustly parse Unix epochs (s/ms/ns) or ISO strings to timezone-aware UTC datetime."""
        if isinstance(raw_ts, datetime):
            return raw_ts.astimezone(timezone.utc) if raw_ts.tzinfo else raw_ts.replace(tzinfo=timezone.utc)

        if isinstance(raw_ts, (int, float)):
            # Epoch detection
            if raw_ts > 1e16:  # Nanoseconds
                return datetime.fromtimestamp(raw_ts / 1e9, tz=timezone.utc)
            elif raw_ts > 1e12:  # Milliseconds
                return datetime.fromtimestamp(raw_ts / 1e3, tz=timezone.utc)
            else:  # Seconds
                return datetime.fromtimestamp(raw_ts, tz=timezone.utc)

        if isinstance(raw_ts, str):
            dt = dateutil.parser.parse(raw_ts)
            return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc)

    @classmethod
    def normalize_raw_tick(
        cls,
        raw_data: Dict[str, Any],
        provider_name: str = "GENERIC",
        default_symbol: Optional[str] = None
    ) -> MarketTick:
        """Convert a raw dictionary of price, bid, ask, volume, and timestamp into a validated MarketTick."""
        raw_sym = raw_data.get("symbol") or raw_data.get("instrument") or default_symbol or "UNKNOWN"
        symbol = cls.normalize_symbol(raw_sym)

        price = float(raw_data.get("price") or raw_data.get("last_price") or raw_data.get("last", 0.0))
        bid = float(raw_data.get("bid") or raw_data.get("best_bid") or price)
        ask = float(raw_data.get("ask") or raw_data.get("best_ask") or price)
        volume = float(raw_data.get("volume") or raw_data.get("size") or raw_data.get("qty", 1.0))
        seq = int(raw_data.get("sequence_number") or raw_data.get("seq") or 0)

        # Enforce Bid <= Ask constraint defensively
        if bid > ask:
            # Rebalance if quotes are crossed due to microsecond misalignment
            mid = (bid + ask) / 2.0
            bid = min(bid, ask)
            ask = max(bid, ask)

        # Rounding precision based on instrument
        precision = cls.DECIMAL_PRECISION.get(symbol, 4)
        price = round(price, precision)
        bid = round(bid, precision)
        ask = round(ask, precision)

        # Determine side
        raw_side = str(raw_data.get("side", "")).upper()
        side = TickSide.BUY if "BUY" in raw_side or "BID" in raw_side else (
            TickSide.SELL if "SELL" in raw_side or "ASK" in raw_side else TickSide.UNKNOWN
        )

        ts = cls.parse_timestamp(raw_data.get("timestamp") or raw_data.get("time"))

        return MarketTick(
            timestamp=ts,
            symbol=symbol,
            price=price,
            bid=bid,
            ask=ask,
            volume=volume,
            side=side,
            provider=provider_name,
            sequence_number=seq
        )
