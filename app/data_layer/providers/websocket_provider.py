"""Generic WebSocket Market Data Provider with auto-reconnect, heartbeats, and latency telemetry."""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import websockets

from app.data_layer.providers.base_provider import MarketDataProvider, ProviderConnectionStatus
from app.data_layer.tick_normalizer import TickNormalizer
from app.models.tick import MarketTick


class WebSocketDataProvider(MarketDataProvider):
    """Real-time market data provider streaming ticks from generic exchange or broker WebSocket APIs."""

    def __init__(
        self,
        uri: str,
        name: str = "WEBSOCKET",
        heartbeat_interval_sec: float = 15.0,
        reconnect_attempts: int = 5
    ) -> None:
        super().__init__(name=name)
        self.uri = uri
        self.heartbeat_interval = heartbeat_interval_sec
        self.reconnect_attempts = reconnect_attempts
        self.ws: Optional[Any] = None
        self._subscribed_symbols: List[str] = []
        self._worker_task: Optional[asyncio.Task] = None
        self._is_active: bool = False
        self.last_latency_ms: float = 0.0

    async def connect(self) -> bool:
        """Connect to the WebSocket server with automatic background listener and reconnection."""
        self._is_active = True
        self.status = ProviderConnectionStatus.CONNECTING
        self._worker_task = asyncio.create_task(self._connection_manager_loop())
        return True

    async def disconnect(self) -> None:
        """Gracefully disconnect WebSocket feed."""
        self._is_active = False
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass

        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()

        self.status = ProviderConnectionStatus.DISCONNECTED
        self._emit_disconnect()

    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to live symbol channels."""
        self._subscribed_symbols.extend([s for s in symbols if s not in self._subscribed_symbols])
        if self.ws and self.status == ProviderConnectionStatus.CONNECTED:
            sub_msg = json.dumps({"op": "subscribe", "args": symbols})
            await self.ws.send(sub_msg)
            return True
        return False

    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from symbol channels."""
        self._subscribed_symbols = [s for s in self._subscribed_symbols if s not in symbols]
        if self.ws and self.status == ProviderConnectionStatus.CONNECTED:
            unsub_msg = json.dumps({"op": "unsubscribe", "args": symbols})
            await self.ws.send(unsub_msg)
            return True
        return False

    def get_status(self) -> ProviderConnectionStatus:
        return self.status

    async def _connection_manager_loop(self) -> None:
        """Resilient connection loop supporting auto-reconnect and heartbeat ping/pongs."""
        attempt = 0
        while self._is_active:
            try:
                self.status = ProviderConnectionStatus.CONNECTING
                async with websockets.connect(self.uri, ping_interval=self.heartbeat_interval) as ws:
                    self.ws = ws
                    self.status = ProviderConnectionStatus.CONNECTED
                    attempt = 0  # Reset counter on successful connection

                    # Re-subscribe existing symbols on reconnect
                    if self._subscribed_symbols:
                        await self.subscribe(self._subscribed_symbols)

                    # Continuous message receive loop
                    async for raw_message in ws:
                        recv_time = time.time()
                        try:
                            data = json.loads(raw_message)
                            market_tick = TickNormalizer.normalize_raw_tick(data, provider_name=self.name)

                            # Calculate feed latency
                            tick_epoch = market_tick.timestamp.timestamp()
                            self.last_latency_ms = max(0.0, (recv_time - tick_epoch) * 1000.0)

                            self._emit_tick(market_tick)
                        except Exception as parse_err:
                            self._emit_error(f"WebSocket parse error: {str(parse_err)}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.status = ProviderConnectionStatus.RECONNECTING
                self._emit_error(f"WebSocket connection lost ({str(e)}). Reconnecting...")
                attempt += 1
                if attempt > self.reconnect_attempts:
                    self.status = ProviderConnectionStatus.ERROR
                    self._emit_error("Max reconnection attempts exceeded.")
                    break
                await asyncio.sleep(min(2 ** attempt, 30))  # Exponential backoff

        self.status = ProviderConnectionStatus.DISCONNECTED
        self._emit_disconnect()
