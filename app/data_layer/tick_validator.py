"""Market tick validation engine for enforcing strict data sanity rules."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from app.core.logging import app_logger


class ValidationResult(BaseModel):
    """Validation outcome report for an individual or batch of ticks."""
    valid: bool = Field(..., description="True if tick passes all critical validation checks")
    quality_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Normalized health score [0.0, 1.0]")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings (e.g. minor time jitter)")
    errors: List[str] = Field(default_factory=list, description="Fatal rejection errors")

    model_config = {
        "frozen": True
    }


class TickValidator:
    """Stateful tick validation engine detecting anomalies, out-of-order timestamps, and corrupt quotes."""

    ALLOWED_SYMBOLS: Set[str] = {"XAUUSD", "GC", "GC_FUT", "GOLD"}

    def __init__(
        self,
        max_allowed_price_jump_pct: float = 5.0,
        max_allowed_spread_pct: float = 1.0
    ) -> None:
        self.max_price_jump_pct = max_allowed_price_jump_pct
        self.max_spread_pct = max_allowed_spread_pct
        self._last_timestamp: Optional[datetime] = None
        self._last_price: Optional[float] = None

    def reset_state(self) -> None:
        """Reset internal sequential memory."""
        self._last_timestamp = None
        self._last_price = None

    def validate_raw(self, raw: Dict[str, Any]) -> ValidationResult:
        """Validate an unparsed external raw dictionary before normalization."""
        errors: List[str] = []
        warnings: List[str] = []
        deductions = 0.0

        # 1. Symbol Check
        symbol = str(raw.get("symbol", "")).upper().replace("/", "").replace("_", "")
        normalized_match = any(allowed.replace("_", "") == symbol for allowed in self.ALLOWED_SYMBOLS)
        if not normalized_match:
            errors.append(f"Disallowed or unrecognized symbol: '{raw.get('symbol')}'")
            deductions += 1.0

        # 2. Price Sanity Check
        price = raw.get("price")
        if price is None:
            errors.append("Missing mandatory 'price' field")
            deductions += 1.0
        else:
            try:
                price_val = float(price)
                if price_val <= 0.0:
                    errors.append(f"Price must be strictly positive, got {price_val}")
                    deductions += 1.0
                elif self._last_price is not None:
                    # Detect unreasonable price teleportation (> 5% single-tick jump)
                    jump_pct = abs(price_val - self._last_price) / self._last_price * 100.0
                    if jump_pct > self.max_price_jump_pct:
                        warnings.append(f"Abnormal single-tick price jump: {jump_pct:.2f}% (from {self._last_price} to {price_val})")
                        deductions += 0.3
            except (ValueError, TypeError):
                errors.append(f"Non-numeric price received: {price}")
                deductions += 1.0

        # 3. Volume Check
        volume = raw.get("volume", 0.0)
        try:
            vol_val = float(volume)
            if vol_val < 0.0:
                errors.append(f"Volume cannot be negative, got {vol_val}")
                deductions += 0.5
        except (ValueError, TypeError):
            errors.append(f"Non-numeric volume: {volume}")
            deductions += 0.5

        # 4. Timestamp & Sequence Checks
        ts = raw.get("timestamp")
        if ts is None:
            errors.append("Missing mandatory 'timestamp' field")
            deductions += 1.0
        else:
            ts_obj: Optional[datetime] = None
            if isinstance(ts, datetime):
                ts_obj = ts
            elif isinstance(ts, (int, float)):
                # Milliseconds or seconds epoch
                ts_sec = ts / 1000.0 if ts > 1e11 else float(ts)
                ts_obj = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
            elif isinstance(ts, str):
                try:
                    ts_obj = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    errors.append(f"Unparseable ISO timestamp string: {ts}")
                    deductions += 0.8

            if ts_obj is not None:
                if self._last_timestamp is not None:
                    if ts_obj < self._last_timestamp:
                        errors.append(f"Out-of-order tick received: {ts_obj} is prior to last seen {self._last_timestamp}")
                        deductions += 1.0
                    elif ts_obj == self._last_timestamp:
                        warnings.append(f"Duplicate timestamp sequence at {ts_obj}")
                        deductions += 0.1

        # 5. Bid / Ask Spread Check
        bid = raw.get("bid")
        ask = raw.get("ask")
        if bid is not None and ask is not None:
            try:
                b_val, a_val = float(bid), float(ask)
                if a_val < b_val:
                    errors.append(f"Crossed/Inverted book: Ask ({a_val}) < Bid ({b_val})")
                    deductions += 0.7
                elif b_val > 0.0:
                    spread_pct = (a_val - b_val) / b_val * 100.0
                    if spread_pct > self.max_spread_pct:
                        warnings.append(f"Abnormal wide bid-ask spread: {spread_pct:.3f}%")
                        deductions += 0.2
            except (ValueError, TypeError):
                errors.append(f"Non-numeric Bid/Ask values: bid={bid}, ask={ask}")
                deductions += 0.5

        is_valid = len(errors) == 0
        final_score = max(0.0, 1.0 - deductions) if is_valid else 0.0

        if not is_valid:
            app_logger.warning(f"Tick validation rejected tick: {errors} | Raw: {raw}")

        return ValidationResult(
            valid=is_valid,
            quality_score=final_score,
            warnings=warnings,
            errors=errors
        )

    def record_validated_tick(self, timestamp: datetime, price: float) -> None:
        """Update sequential state tracker upon successful downstream consumption."""
        self._last_timestamp = timestamp
        self._last_price = price
