"""Session-aware Cumulative Volume Delta (CVD) Engine with configurable multi-session resets."""

from datetime import datetime, time, timezone
from typing import Any, Dict, Optional
from app.models.footprint import CVDPoint


class CVDEngine:
    """Computes running Cumulative Volume Delta with automatic session detection and reset."""

    def __init__(self, sessions_config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize CVD engine with custom or default session boundary configuration."""
        self.sessions = sessions_config or {
            "asia": {"name": "ASIA", "start_utc": "00:00:00", "end_utc": "08:00:00"},
            "london": {"name": "LONDON", "start_utc": "08:00:00", "end_utc": "13:30:00"},
            "new_york": {"name": "NEW_YORK", "start_utc": "13:30:00", "end_utc": "20:00:00"},
            "post_market": {"name": "POST_MARKET", "start_utc": "20:00:00", "end_utc": "23:59:59"},
        }
        self.current_session: Optional[str] = None
        self.cumulative_delta: float = 0.0
        self.last_timestamp: Optional[datetime] = None

    def get_session_for_time(self, dt: datetime) -> str:
        """Determine active trading session for a given UTC timestamp based on config boundaries."""
        t_val = dt.time() if dt.tzinfo else dt.replace(tzinfo=timezone.utc).time()

        for sess_key, sess_info in self.sessions.items():
            start_parts = [int(p) for p in sess_info["start_utc"].split(":")]
            end_parts = [int(p) for p in sess_info["end_utc"].split(":")]
            start_t = time(*start_parts)
            end_t = time(*end_parts)

            if start_t <= t_val < end_t:
                return sess_info["name"]

        return "UNKNOWN_SESSION"

    def reset_session(self, new_session_name: str) -> None:
        """Reset running cumulative delta upon entering a new trading session."""
        self.current_session = new_session_name
        self.cumulative_delta = 0.0

    def update(self, symbol: str, timestamp: datetime, bar_delta: float) -> CVDPoint:
        """Incorporate bar delta into running CVD and handle session boundaries without lookahead."""
        session_name = self.get_session_for_time(timestamp)

        # Detect session rollover or initial start
        if self.current_session is None:
            self.current_session = session_name
            self.cumulative_delta = bar_delta
        elif session_name != self.current_session:
            # Session transition -> Reset running CVD for the new session
            self.reset_session(session_name)
            self.cumulative_delta = bar_delta
        else:
            self.cumulative_delta += bar_delta

        self.last_timestamp = timestamp

        return CVDPoint(
            timestamp=timestamp,
            symbol=symbol,
            session=session_name,
            cumulative_delta=round(self.cumulative_delta, 4),
            bar_delta=round(bar_delta, 4)
        )
