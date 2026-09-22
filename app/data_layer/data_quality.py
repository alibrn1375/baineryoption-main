"""Market Data Quality Monitor detecting sequence gaps, spread anomalies, and feed latencies."""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.tick import MarketTick


class DataQualityReport(BaseModel):
    """Health diagnostic report summarizing tick stream integrity."""
    timestamp: datetime = Field(..., description="Timestamp of report generation (UTC)")
    symbol: str = Field(..., description="Monitored asset symbol")
    quality_score: float = Field(..., ge=0.0, le=100.0, description="Composite health score [0-100]")
    latency_ms: float = Field(..., description="Observed network ingestion latency in milliseconds")
    missing_ticks_count: int = Field(default=0, description="Total detected sequence number gaps")
    spread_anomalies_count: int = Field(default=0, description="Count of inverted or excessive spread ticks")
    issues: List[str] = Field(default_factory=list, description="Diagnostic warnings and flags")
    total_ticks: int = 0
    valid_ticks: int = 0
    invalid_ticks: int = 0

    model_config = {
        "frozen": True
    }


class DataQualityMonitor:
    """Evaluates incoming tick streams in real-time, penalizing latency spikes, dropped ticks, and bad quotes."""

    def __init__(
        self,
        max_acceptable_latency_ms: float = 500.0,
        max_acceptable_spread_points: float = 2.0
    ) -> None:
        self.max_latency = max_acceptable_latency_ms
        self.max_spread = max_acceptable_spread_points

        self._last_seq_per_symbol: Dict[str, int] = {}
        self._missing_ticks_per_symbol: Dict[str, int] = {}
        self._spread_anomalies_per_symbol: Dict[str, int] = {}
        self._total_ticks = 0
        self._valid_ticks = 0
        self._invalid_ticks = 0

    def record_tick(
        self,
        tick_time: datetime,
        is_valid: bool,
        is_duplicate: bool = False,
        error_msg: Optional[str] = None,
    ) -> None:
        """Record pipeline validation outcomes for the aggregate quality report."""
        self._total_ticks += 1
        if is_valid and not is_duplicate:
            self._valid_ticks += 1
        else:
            self._invalid_ticks += 1

    def generate_report(self) -> DataQualityReport:
        """Return aggregate validation quality for the current ingestion run."""
        score = (self._valid_ticks / self._total_ticks) if self._total_ticks else 1.0
        return DataQualityReport(
            timestamp=datetime.now(timezone.utc),
            symbol="AGGREGATE",
            quality_score=round(score, 4),
            latency_ms=0.0,
            total_ticks=self._total_ticks,
            valid_ticks=self._valid_ticks,
            invalid_ticks=self._invalid_ticks,
        )

    def inspect_tick(self, tick: MarketTick, current_time: Optional[datetime] = None) -> DataQualityReport:
        """Inspect a newly received tick, updating tracking metrics and returning an integrity report."""
        now = current_time or datetime.now(timezone.utc)
        sym = tick.symbol
        issues: List[str] = []
        score = 100.0

        # 1. Latency Measurement
        tick_time = tick.timestamp
        latency_ms = max(0.0, (now.timestamp() - tick_time.timestamp()) * 1000.0)
        if latency_ms > self.max_latency:
            score -= min(40.0, (latency_ms - self.max_latency) / 10.0)
            issues.append(f"High latency: {latency_ms:.1f}ms > {self.max_latency:.1f}ms")

        # 2. Sequence Gaps (Dropped Ticks)
        if sym in self._last_seq_per_symbol and tick.sequence_number > 0:
            expected_seq = self._last_seq_per_symbol[sym] + 1
            if tick.sequence_number > expected_seq:
                gap = tick.sequence_number - expected_seq
                self._missing_ticks_per_symbol[sym] = self._missing_ticks_per_symbol.get(sym, 0) + gap
                score -= min(30.0, gap * 5.0)
                issues.append(f"Sequence gap detected: missed {gap} ticks")

        if tick.sequence_number > 0:
            self._last_seq_per_symbol[sym] = tick.sequence_number

        # 3. Spread Health
        spread = tick.ask - tick.bid
        if spread > self.max_spread:
            self._spread_anomalies_per_symbol[sym] = self._spread_anomalies_per_symbol.get(sym, 0) + 1
            score -= 20.0
            issues.append(f"Excessive spread: {spread:.2f} > {self.max_spread:.2f}")

        # 4. Volume anomaly
        if tick.volume <= 0.0:
            score -= 10.0
            issues.append("Zero volume execution tick")

        score = max(0.0, round(score, 1))

        return DataQualityReport(
            timestamp=now,
            symbol=sym,
            quality_score=score,
            latency_ms=round(latency_ms, 2),
            missing_ticks_count=self._missing_ticks_per_symbol.get(sym, 0),
            spread_anomalies_count=self._spread_anomalies_per_symbol.get(sym, 0),
            issues=issues
        )
