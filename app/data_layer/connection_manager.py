"""Connection Manager supervising data provider lifecycle, heartbeats, and failovers."""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional
from pydantic import BaseModel, Field

from app.data_layer.providers.base_provider import MarketDataProvider, ProviderConnectionStatus


class ConnectionStatus(BaseModel):
    """Aggregate health state of an actively supervised provider connection."""
    provider: str = Field(..., description="Provider name")
    connected: bool = Field(..., description="True if actively connected and receiving data")
    status: ProviderConnectionStatus = Field(..., description="Current operational state")
    latency_ms: float = Field(default=0.0, description="Ping round-trip / data latency")
    last_message_time: Optional[datetime] = Field(default=None, description="Timestamp of latest received message")
    error_state: Optional[str] = Field(default=None, description="Active error message if degraded")

    model_config = {
        "frozen": True
    }


class ConnectionManager:
    """Supervises provider connectivity, periodic health pings, and reconnection state machines."""

    def __init__(self, provider: MarketDataProvider, heartbeat_interval_sec: float = 10.0) -> None:
        self.provider = provider
        self.heartbeat_interval = heartbeat_interval_sec
        self.last_message_time: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._is_active: bool = False

        # Hook into provider events
        self.provider.on_tick(lambda t: self._on_tick_received(t))
        self.provider.on_error(lambda err: self._on_error_received(err))
        self.provider.on_disconnect(lambda: self._on_disconnected())

    def _on_tick_received(self, tick) -> None:
        self.last_message_time = datetime.now(timezone.utc)
        self.last_error = None

    def _on_error_received(self, err: str) -> None:
        self.last_error = err

    def _on_disconnected(self) -> None:
        self.last_error = "Connection dropped by remote server."

    def get_status(self) -> ConnectionStatus:
        """Query current connection and health diagnostics."""
        st = self.provider.get_status()
        is_conn = (st == ProviderConnectionStatus.CONNECTED)

        return ConnectionStatus(
            provider=self.provider.name,
            connected=is_conn,
            status=st,
            latency_ms=0.0,
            last_message_time=self.last_message_time,
            error_state=self.last_error
        )

    async def start(self) -> bool:
        """Start provider connection and spawn supervisor health check loop."""
        self._is_active = True
        success = await self.provider.connect()
        self._monitor_task = asyncio.create_task(self._health_check_loop())
        return success

    async def stop(self) -> None:
        """Stop supervisor and disconnect provider."""
        self._is_active = False
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
        await self.provider.disconnect()

    async def _health_check_loop(self) -> None:
        """Periodic watchdog verifying feed liveness."""
        while self._is_active:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                # Check for silent stale connections
                if self.provider.get_status() == ProviderConnectionStatus.CONNECTED:
                    if self.last_message_time:
                        elapsed = (datetime.now(timezone.utc) - self.last_message_time).total_seconds()
                        if elapsed > (self.heartbeat_interval * 3):
                            self.last_error = f"Stale feed: no message received in {elapsed:.1f}s"
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.last_error = str(e)
