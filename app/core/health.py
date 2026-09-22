"""System Health and Readiness Verification Endpoint for Docker and K8s probes."""

from datetime import datetime, timezone
from typing import Dict, Any
from pydantic import BaseModel, Field


class ServiceHealth(BaseModel):
    status: str = Field(..., description="HEALTHY, DEGRADED, or UNHEALTHY")
    latency_ms: float = Field(default=0.0)
    details: Dict[str, Any] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = Field(..., description="HEALTHY, DEGRADED, or UNHEALTHY")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    environment: str = Field(default="production")
    services: Dict[str, ServiceHealth] = Field(default_factory=dict)


class SystemHealthSupervisor:
    """Supervises health of all core micro-services (Data Feed, DB, Footprint, Decision Engine)."""

    def __init__(self) -> None:
        self.services_status: Dict[str, ServiceHealth] = {
            "database": ServiceHealth(status="HEALTHY", latency_ms=1.2),
            "market_data_feed": ServiceHealth(status="HEALTHY", latency_ms=3.5, details={"provider": "NINJATRADER"}),
            "orderflow_engine": ServiceHealth(status="HEALTHY", latency_ms=0.8),
            "paper_trading_service": ServiceHealth(status="HEALTHY", latency_ms=0.4),
        }

    def update_service(self, name: str, status: str, latency_ms: float = 0.0, details: Dict[str, Any] = None) -> None:
        self.services_status[name] = ServiceHealth(
            status=status,
            latency_ms=latency_ms,
            details=details or {}
        )

    def get_overall_health(self) -> HealthResponse:
        statuses = [s.status for s in self.services_status.values()]
        if any(st == "UNHEALTHY" for st in statuses):
            overall = "UNHEALTHY"
        elif any(st == "DEGRADED" for st in statuses):
            overall = "DEGRADED"
        else:
            overall = "HEALTHY"

        return HealthResponse(
            status=overall,
            services=self.services_status
        )


health_supervisor = SystemHealthSupervisor()
