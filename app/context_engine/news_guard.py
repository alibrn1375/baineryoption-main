"""Macroeconomic news quarantine filter guarding against abnormal high-impact volatility."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.market_context import NewsRiskLevel, NewsState


class NewsGuard:
    """Evaluates proximity to scheduled high-impact macroeconomic events and enforces quarantine."""

    def __init__(
        self,
        quarantine_before_minutes: int = 15,
        quarantine_after_minutes: int = 20
    ) -> None:
        self.before_min = quarantine_before_minutes
        self.after_min = quarantine_after_minutes
        self._scheduled_events: List[Dict[str, Any]] = []

    def set_events(self, events: List[Dict[str, Any]]) -> None:
        """Load scheduled macroeconomic news events."""
        self._scheduled_events = events

    def evaluate_news_state(self, current_dt: datetime) -> NewsState:
        """Check if the given timestamp falls inside a news quarantine blackout window."""
        current_utc = current_dt.astimezone(timezone.utc) if current_dt.tzinfo else current_dt.replace(tzinfo=timezone.utc)

        active_events: List[str] = []
        is_blocked = False
        highest_risk = NewsRiskLevel.NONE
        min_minutes_to_next: Optional[int] = None

        for ev in self._scheduled_events:
            ev_time = ev.get("timestamp")
            if isinstance(ev_time, str):
                ev_time = datetime.fromisoformat(ev_time)
            if ev_time.tzinfo is None:
                ev_time = ev_time.replace(tzinfo=timezone.utc)

            diff_sec = (ev_time - current_utc).total_seconds()
            diff_min = diff_sec / 60.0

            impact = str(ev.get("impact", "HIGH")).upper()
            title = ev.get("title", "High Impact Event")

            if diff_min >= 0:
                if min_minutes_to_next is None or diff_min < min_minutes_to_next:
                    min_minutes_to_next = int(diff_min)

            # Quarantine condition: Within [before_min, -after_min]
            if -self.after_min <= diff_min <= self.before_min:
                active_events.append(f"{title} ({impact})")
                if impact in ("HIGH", "CRITICAL"):
                    is_blocked = True
                    highest_risk = NewsRiskLevel.CRITICAL if impact == "CRITICAL" else NewsRiskLevel.HIGH
                elif impact == "MEDIUM":
                    highest_risk = max(highest_risk, NewsRiskLevel.MEDIUM)

        reason = None
        if is_blocked:
            reason = f"Operational halt: Active news quarantine window for: {', '.join(active_events)}"

        return NewsState(
            event_active=len(active_events) > 0,
            risk_level=highest_risk,
            blocked=is_blocked,
            active_events=active_events,
            minutes_to_next=min_minutes_to_next,
            reason=reason
        )
