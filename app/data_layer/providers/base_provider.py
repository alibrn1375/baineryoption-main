"""Abstract base class and lifecycle interface for real-time market data providers."""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.tick import MarketTick


class ProviderConnectionStatus(str, Enum):
    """Connection states of a market data provider."""
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class MarketDataProvider(ABC):
    """Abstract interface defining the contract for all real-time market data ingestion providers."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.status: ProviderConnectionStatus = ProviderConnectionStatus.DISCONNECTED
        self._tick_callbacks: List[Callable[[MarketTick], Any]] = []
        self._error_callbacks: List[Callable[[str], Any]] = []
        self._disconnect_callbacks: List[Callable[[], Any]] = []

    def on_tick(self, callback: Callable[[MarketTick], Any]) -> None:
        """Register a callback for incoming normalized MarketTicks."""
        self._tick_callbacks.append(callback)

    def on_error(self, callback: Callable[[str], Any]) -> None:
        """Register a callback for connection/feed errors."""
        self._error_callbacks.append(callback)

    def on_disconnect(self, callback: Callable[[], Any]) -> None:
        """Register a callback triggered upon socket disconnection."""
        self._disconnect_callbacks.append(callback)

    def _emit_tick(self, tick: MarketTick) -> None:
        """Dispatch tick event to all registered listeners."""
        for cb in self._tick_callbacks:
            try:
                cb(tick)
            except Exception as e:
                self._emit_error(f"Error in tick callback: {str(e)}")

    def _emit_error(self, message: str) -> None:
        """Dispatch error message to all registered listeners."""
        for cb in self._error_callbacks:
            try:
                cb(message)
            except Exception:
                pass

    def _emit_disconnect(self) -> None:
        """Dispatch disconnection event to all registered listeners."""
        for cb in self._disconnect_callbacks:
            try:
                cb()
            except Exception:
                pass

    @abstractmethod
    async def connect(self) -> bool:
        """Establish asynchronous connection to the market data feed."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Terminate connection gracefully."""
        pass

    @abstractmethod
    async def subscribe(self, symbols: List[str]) -> bool:
        """Subscribe to real-time tick streams for the specified symbols."""
        pass

    @abstractmethod
    async def unsubscribe(self, symbols: List[str]) -> bool:
        """Unsubscribe from real-time tick streams for the specified symbols."""
        pass

    @abstractmethod
    def get_status(self) -> ProviderConnectionStatus:
        """Return the current operational status of the provider."""
        pass
