"""Trading Session Detector with dynamic timezone mapping and overlap identification."""

from datetime import datetime, time
from typing import Any, Dict, Optional
import pytz

from app.models.market_context import TradingSession, TradingSessionName


class SessionDetector:
    """Identifies active global trading session with configurable UTC boundaries."""

    def __init__(self, timezone_str: str = "UTC", session_config: Optional[Dict[str, Any]] = None) -> None:
        self.tz = pytz.timezone(timezone_str)
        self.session_config = session_config or {
            "asia": {"start": "00:00:00", "end": "08:00:00"},
            "london": {"start": "08:00:00", "end": "13:30:00"},
            "new_york": {"start": "13:30:00", "end": "20:00:00"},
            "overlap_london_ny": {"start": "13:30:00", "end": "16:00:00"},
            "post_market": {"start": "20:00:00", "end": "23:59:59"}
        }

    def detect_session(self, current_dt: datetime) -> TradingSession:
        """Determine the active session for a given UTC datetime."""
        utc_dt = current_dt.astimezone(pytz.utc) if current_dt.tzinfo else pytz.utc.localize(current_dt)
        current_time_str = utc_dt.strftime("%H:%M:%S")

        # 1. Check Overlap first (London + NY)
        ov = self.session_config.get("overlap_london_ny", {})
        if ov and ov.get("start") <= current_time_str <= ov.get("end"):
            return TradingSession(
                name=TradingSessionName.OVERLAP_LONDON_NY,
                start_time=ov["start"],
                end_time=ov["end"],
                confidence=1.0
            )

        # 2. Check New York
        ny = self.session_config.get("new_york", {})
        if ny and ny.get("start") <= current_time_str <= ny.get("end"):
            return TradingSession(
                name=TradingSessionName.NEW_YORK,
                start_time=ny["start"],
                end_time=ny["end"],
                confidence=1.0
            )

        # 3. Check London
        lon = self.session_config.get("london", {})
        if lon and lon.get("start") <= current_time_str <= lon.get("end"):
            return TradingSession(
                name=TradingSessionName.LONDON,
                start_time=lon["start"],
                end_time=lon["end"],
                confidence=1.0
            )

        # 4. Check Asia
        asia = self.session_config.get("asia", {})
        if asia and asia.get("start") <= current_time_str <= asia.get("end"):
            return TradingSession(
                name=TradingSessionName.ASIA,
                start_time=asia["start"],
                end_time=asia["end"],
                confidence=1.0
            )

        # 5. Post Market
        pm = self.session_config.get("post_market", {})
        return TradingSession(
            name=TradingSessionName.POST_MARKET,
            start_time=pm.get("start", "20:00:00"),
            end_time=pm.get("end", "23:59:59"),
            confidence=0.8
        )
