# FO-X 5M — Paper Trading Engine & Live Monitoring Documentation

## Overview

The **Paper Trading Engine** serves as the live forward-testing simulation environment for the FO-X 5M quantitative system.

It bridges the gap between historical backtesting research and production reality by processing incoming real-time market data, evaluating setups with the Decision Arbiter, and managing virtual 5-minute binary options contracts with full lifecycle accounting and risk controls—**without any real money or live broker execution.**

---

## 1. System Architecture

```text
       [ Live WebSocket / Feed Ingestion ]
                        ↓
       ┌─────────────────────────────────┐
       │     RealTimePipeline Manager    │
       └────────────────┬────────────────┘
                        ↓ (Tick Stream)
       ┌─────────────────────────────────┐
       │   FO-X Core Pipeline (5M Bar)   │  (Footprint -> OrderFlow -> Context -> Decision)
       └────────────────┬────────────────┘
                        ↓
       ┌─────────────────────────────────┐
       │         Paper Risk Guard        │  (Max daily trades, consecutive losses, news block)
       └────────────────┬────────────────┘
                        ↓
       ┌─────────────────────────────────┐
       │    Virtual Execution Engine     │  (PENDING -> OPEN -> SETTLED [WIN/LOSS])
       └────────────────┬────────────────┘
                        ↓
       ┌─────────────────────────────────┐
       │      Virtual Account State      │  (Balance, Peak Equity, Drawdowns, Win Rate)
       └────────────────┬────────────────┘
                        ↓
         ┌──────────────┴──────────────┐
         ▼                             ▼
  [ Live Terminal Monitor ]    [ Journal Storage (Parquet) ]
   - Formatted Telemetry Card   - data/paper_trading/trades/
```

---

## 2. Virtual Contract Lifecycle

A simulated contract undergoes a deterministic lifecycle:
1. `PENDING`: Triggered by a valid `CALL` or `PUT` from the Decision Arbiter and validated by the `PaperRiskGuard`.
2. `OPEN`: Active contract after simulated broker transmission delay (`entry_delay_ms: 200`) and entry slippage.
3. `EXPIRED`: Time reached $T + 5\text{m}$.
4. `WIN` / `LOSS` / `CANCELLED`: PnL settled into the `VirtualAccount`.

---

## 3. Risk Guard Constraints (`app/paper_trading/risk_guard.py`)

The `PaperRiskGuard` enforces strict operational guardrails:
- **Maximum Daily Trades**: Caps session exposure (e.g. 20 trades/session).
- **Consecutive Loss Cooldown**: Halts testing if consecutive losses reach 3.
- **Maximum Drawdown**: Circuit breaker if account equity drops by $\ge 15\%$.
- **Macro News Blackout**: Freezes trade submissions during high-impact news windows.
- **Extreme Volatility Filter**: Halts submissions if ATR percentile $\ge 90\%$.

---

## 4. Live vs. Backtest Divergence Monitoring (`app/paper_trading/comparison.py`)

Continuously quantifies live execution fidelity against backtest models:
- Computes Win Rate drift: $\text{Drift} = \frac{\text{Live WR} - \text{BT WR}}{\text{BT WR}} \times 100\%$.
- Emits warnings if divergence exceeds the $15\%$ statistical drift tolerance.

---

## 5. Storage Layer (`app/storage/paper_trade_storage.py`)

All paper trade logs, entry/exit prices, decisions, and quality scores are saved in date-partitioned Snappy Parquet stores:
```text
data/paper_trading/
└── trades/{YYYY-MM-DD}.parquet
```
