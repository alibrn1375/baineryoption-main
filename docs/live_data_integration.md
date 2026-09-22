# FO-X 5M — Live Data Integration Layer Documentation

## Overview

The **Live Data Integration Layer** provides a normalized market data abstraction layer for the FO-X 5M algorithmic system.

It receives raw microsecond tick feeds from external execution platforms (e.g. **NinjaTrader 8 Bridge**, **Generic WebSockets**) and transforms them into strictly validated, normalized `MarketTick` objects without modifying price history or reconstructing synthetic footprint bars from candles.

---

## 1. System Ingestion Architecture

```text
       ┌────────────────────────┐      ┌────────────────────────┐
       │   NinjaTrader 8 Bridge │      │  Generic WebSocket     │
       │    (TCP / ZeroMQ)      │      │     (Crypto/Feed)      │
       └───────────┬────────────┘      └───────────┬────────────┘
                   ▼                               ▼
       ┌────────────────────────────────────────────────────────┐
       │          Provider Adapter (MarketDataProvider)         │
       │      - Reconnection & Exponential Backoff              │
       │      - Heartbeat Watchdog                              │
       └───────────────────────────┬────────────────────────────┘
                                   ▼ (Raw Dict Payload)
       ┌────────────────────────────────────────────────────────┐
       │              Tick Normalizer (TickNormalizer)          │
       │      - Symbol Mapping (GC -> GC_FUT)                   │
       │      - UTC Timezone & Epoch Parser                     │
       │      - Price/Bid/Ask Decimal Alignment                 │
       └───────────────────────────┬────────────────────────────┘
                                   ▼ (Standard MarketTick)
       ┌────────────────────────────────────────────────────────┐
       │         Data Quality Monitor (DataQualityMonitor)      │
       │      - Sequence Gap / Dropped Tick Detection           │
       │      - Inverted / Excessive Spread Alert               │
       │      - Feed Latency Telemetry                          │
       └───────────────────────────┬────────────────────────────┘
                                   ▼ (Validated MarketTick)
       ┌────────────────────────────────────────────────────────┐
       │             Real-Time Event Bus (RealTimeEventBus)     │
       │      - Async In-Memory Buffering (10,000 Queue)        │
       │      - Non-blocking Producer Dispatch                  │
       └───────────────────────────┬────────────────────────────┘
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │         FO-X 5M Core Processing & Paper Trading        │
       └────────────────────────────────────────────────────────┘
```

---

## 2. Core Components

### A. `MarketTick` Data Model (`app/models/tick.py`)
- Represents tick events with exact execution prices, top-of-book bid/ask quotes, volume quantities, aggressor side classifications, and feed sequence numbers.
- **Pydantic Validation**: Strict enforcement that Bid $\le$ Ask.

### B. Provider Interface (`app/data_layer/providers/base_provider.py`)
- Standardized asynchronous lifecycle contract: `connect()`, `disconnect()`, `subscribe()`, `unsubscribe()`, and `get_status()`.
- Event dispatch mechanisms: `on_tick()`, `on_error()`, and `on_disconnect()`.

### C. NinjaTrader 8 Bridge (`app/data_layer/providers/ninjatrader.py`)
- Asynchronous TCP socket client communicating with NinjaTrader 8 Add-On bridge over `127.0.0.1:8088`.
- Transmits raw execution prints and quote changes as newline-delimited JSON payloads.

### D. Data Quality Monitor (`app/data_layer/data_quality.py`)
- Tracks missing ticks via sequence number gaps.
- Flags spread anomalies exceeding acceptable thresholds.
- Scores feed integrity from $0$ to $100$ and triggers safety warnings.

### E. Real-Time Event Bus (`app/data_layer/event_bus.py`)
- High-throughput asynchronous queue isolating producer feeds from analytical engine processing latency.
- Protects memory through controlled backpressure buffering.
