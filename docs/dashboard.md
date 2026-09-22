# FO-X 5M — Dashboard & Visual Monitoring System Documentation

## Overview

The **FO-X 5M Dashboard & Visual Monitoring System** provides an institutional-grade quantitative trading interface for observing real-time futures order flow, multi-timeframe market structure, execution quality, and three-state decision intelligence (`CALL | PUT | NO TRADE`).

---

## 1. Target Architecture

```text
       ┌────────────────────────────────────────────────────────┐
       │             FO-X 5M Core Processing Engine            │
       │   (Footprint Engine, Order Flow, Decision Pipeline)   │
       └───────────────────────────┬────────────────────────────┘
                                   │
                   ┌───────────────┴───────────────┐
                   ▼                               ▼
       ┌────────────────────────┐      ┌────────────────────────┐
       │   FastAPI REST Layer   │      │ WebSocket Stream Layer │
       │  (GET /api/v1/system)  │      │ (ws://.../stream)      │
       └───────────┬────────────┘      └───────────┬────────────┘
                   │                               │
                   └───────────────┬───────────────┘
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │             Quant Terminal Frontend (React)            │
       │  - Header & Health Watchdog                            │
       │  - Live Decision Arbiter Master Card                  │
       │  - Footprint Chart & Bid/Ask Price Ladder              │
       │  - Order Flow Diagnostics (Delta, CVD, Absorption)     │
       │  - Validation Lab & Monte Carlo Analytics              │
       │  - Paper Trade Journal                                 │
       └────────────────────────────────────────────────────────┘
```

---

## 2. API Endpoints

- `GET /api/v1/system/status`: Engine operational state, data feed provider, latency, and quality index.
- `GET /api/v1/market/context`: Market regime, 15M/1H structures, liquidity level, and macroeconomic news quarantine status.
- `GET /api/v1/orderflow/current`: Real-time Delta, CVD, stacked imbalances, and absorption detection.
- `GET /api/v1/decisions/history`: Historical stream of evaluated setups, expected values (EV), and win probabilities.

---

## 3. Real-Time Streaming & Health Watchdog

- **WebSocket Stream**: Broadcasts microsecond tick events, newly formed 5-minute footprint bars, and real-time decision evaluations.
- **Data Quality & Feed Latency Guard**: Continuously visualizes feed jitter, missing ticks, spread anomalies, and halts processing if quality drops below acceptable thresholds.
