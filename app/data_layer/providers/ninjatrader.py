"""NinjaTrader 8 Bridge Adapter ingesting microsecond tick feeds over TCP / ZeroMQ socket."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.data_layer.providers.base_provider import MarketDataProvider, ProviderConnectionStatus
from app.data_layer.tick_normalizer import TickNormalizer
from app.models.tick import MarketTick


class NinjaTraderBridge(MarketDataProvider):
    """Bridge client connecting to the NinjaTrader FO-X 5M Export Bridge over local/remote TCP socket."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8088,
        name: str = "NINJATRADER"
    ) -> None:
        super().__init__(name=name)
        self.host = host
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self._subscribed_symbols: List[str] = []
        self._read_task: Optional[asyncio.Task] = None
        self._is_active: bool = False

    async def connect(self) -> bool:
        """Establish asynchronous TCP connection to the NinjaTrader Add-On bridge."""
        self.status = ProviderConnectionStatus.CONNECTING
        try:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
            self.status = ProviderConnectionStatus.CONNECTED
            self._is_active = True
            self._read_task = asyncio.create_task(self._listen_loop())
            return True
        except Exception as e:
            self.status = ProviderConnectionStatus.ERROR
            self._emit_error(f"Failed to connect to NinjaTrader bridge at {self.host}:{self.port}: {str(e)}")
            return False

    async def disconnect(self) -> None:
        """Gracefully disconnect from NinjaTrader bridge."""
        self._is_active = False
        if self._read_task and not self._read_task.done():
            self._read_task.cancel()

        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass

        self.status = ProviderConnectionStatus.DISCONNECTED
        self._emit_disconnect()

    async def subscribe(self, symbols: List[str]) -> bool:
        """Send subscription request for symbols to NinjaTrader bridge."""
        self._subscribed_symbols.extend([s for s in symbols if s not in self._subscribed_symbols])
        if self.writer and self.status == ProviderConnectionStatus.CONNECTED:
            msg = json.dumps({"action": "SUBSCRIBE", "symbols": symbols}) + "\n"
            self.writer.write(msg.encode("utf-8"))
            await self.writer.drain()
            return True
        return False

    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe symbols from NinjaTrader bridge."""
        self._subscribed_symbols = [s for s in self._subscribed_symbols if s not in symbols]
        if self.writer and self.status == ProviderConnectionStatus.CONNECTED:
            msg = json.dumps({"action": "UNSUBSCRIBE", "symbols": symbols}) + "\n"
            self.writer.write(msg.encode("utf-8"))
            await self.writer.drain()
            return True
        return False

    def get_status(self) -> ProviderConnectionStatus:
        return self.status

    async def _listen_loop(self) -> None:
        """Asynchronous worker loop continuously reading lines from the socket and emitting MarketTicks."""
        while self._is_active and self.reader:
            try:
                line = await self.reader.readline()
                if not line:
                    break  # Remote end closed connection

                payload_str = line.decode("utf-8").strip()
                if not payload_str:
                    continue

                raw_data = json.loads(payload_str)
                market_tick = TickNormalizer.normalize_raw_tick(raw_data, provider_name=self.name)
                self._emit_tick(market_tick)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self._emit_error(f"Error parsing NinjaTrader payload: {str(e)}")

        self.status = ProviderConnectionStatus.DISCONNECTED
        self._emit_disconnect()
