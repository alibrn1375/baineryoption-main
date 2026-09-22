"""Real-Time Async Event Bus connecting ingestion providers with analytical and decision engines."""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from app.models.tick import MarketTick


class RealTimeEventBus:
    """Non-blocking asynchronous event bus with queue buffering and consumer error isolation."""

    def __init__(self, max_queue_size: int = 10000) -> None:
        self.queue: asyncio.Queue[MarketTick] = asyncio.Queue(maxsize=max_queue_size)
        self._subscribers: List[Callable[[MarketTick], Any]] = []
        self._worker_task: Optional[asyncio.Task] = None
        self._is_running: bool = False

    def subscribe(self, handler: Callable[[MarketTick], Any]) -> None:
        """Register an asynchronous or synchronous subscriber to receive ticks from the bus."""
        self._subscribers.append(handler)

    def unsubscribe(self, handler: Callable[[MarketTick], Any]) -> None:
        """Remove a previously registered subscriber."""
        if handler in self._subscribers:
            self._subscribers.remove(handler)

    async def publish(self, tick: MarketTick) -> bool:
        """Publish a tick to the bus without blocking producer feeds."""
        try:
            self.queue.put_nowait(tick)
            return True
        except asyncio.QueueFull:
            # Drop oldest or log backpressure
            try:
                self.queue.get_nowait()  # Drop oldest tick to maintain real-time freshness
                self.queue.put_nowait(tick)
                return True
            except Exception:
                return False

    async def start(self) -> None:
        """Start the background consumer dispatch loop."""
        if not self._is_running:
            self._is_running = True
            self._worker_task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        """Stop the event bus cleanly."""
        self._is_running = False
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()

    async def _dispatch_loop(self) -> None:
        """Continuous event distribution worker."""
        while self._is_running:
            try:
                tick = await self.queue.get()
                for handler in self._subscribers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(tick)
                        else:
                            handler(tick)
                    except Exception:
                        # Isolate consumer errors to prevent crashing the event bus
                        pass
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                pass
