# FO-X 5M — Market Context Engine Documentation

## Overview

The **Market Context Engine** serves as the environmental awareness layer of the FO-X 5M system. It provides real-time situational awareness by interpreting price structures, liquidity pools, market regimes, active sessions, statistical volatility, and macroeconomic news quarantine states.

This engine does **NOT** generate trade signals, entry triggers, or predictive forecasts. It strictly produces quantitative environmental observations.

---

## 1. Architectural Pipeline

```text
       [ Price Data + Footprint Bars + UTC Clock ]
                            ↓
  ┌────────────────────────────────────────────────────────┐
  │                 MarketContextPipeline                  │
  └────────────────────────────────────────────────────────┘
                            ↓
  ┌──────────────┬──────────────┬──────────────┬───────────┐
  ▼              ▼              ▼              ▼           ▼
[SwingDetector] [Liquidity]  [Regime]      [Session]   [NewsGuard]
  - Pivot High/L  - Eq Highs/L  - Trend/Range - Asia/Lon/NY - Quarantine Window
  - No Leakage    - Sweeps      - ATR Expansion - Overlap   - Risk Block
        │              │              │              │           │
        ▼              ▼              │              │           │
[StructureAnalyzer] [LiquiditySweep]  │              │           │
  - BOS (Break)   - Piercing & Rej    │              │           │
  - MSS (Shift)   - Liquidity Grab    │              │           │
        │              │              │              │           │
        └──────────────┴──────────────┴──────────────┴───────────┘
                            ↓
                     [ MarketContext ]
                            ↓
                   [ ContextStorage ] (Parquet)
```

---

## 2. Core Subsystems

### A. Swing Detector & Market Structure (`app/context_engine/swing_detector.py` & `structure_analyzer.py`)
- **Pivot Swing High/Low**: Strictly sliding-window pivot detection without lookahead bias.
- **Break of Structure (BOS)**: Confirms structural continuation when price closes beyond previous confirmed swings by $\ge \text{bos\_min\_ticks}$.
- **Market Structure Shift (MSS)**: Identifies character shifts when counter-trend swing levels are broken.

### B. Liquidity Engine & Sweep Detector (`app/context_engine/liquidity_engine.py` & `liquidity_sweep.py`)
- **Equal Highs / Equal Lows (EQH/EQL)**: Discovers resting buy-side/sell-side liquidity pools within configurable tick proximity (`tolerance_ticks: 3`).
- **Liquidity Sweeps**: Measures price interaction where a level is penetrated but immediately rejected ($\ge 40\%$ wick closure back inside range).

### C. Market Regime Detection (`app/context_engine/regime_detector.py`)
- Categorizes current state into:
  - `TRENDING_BULLISH` / `TRENDING_BEARISH`
  - `RANGING`
  - `HIGH_VOLATILITY` / `LOW_VOLATILITY`
  - `TRANSITION`

### D. Session & Timezone Engine (`app/context_engine/session_detector.py`)
- Dynamically maps UTC timestamps to `ASIA`, `LONDON`, `NEW_YORK`, `OVERLAP_LONDON_NY`, and `POST_MARKET`.

### E. Volatility Analyzer (`app/context_engine/volatility_analyzer.py`)
- Computes True Range, rolling ATR, rolling percentile rank, and candle progression efficiency.
- Categorizes into `LOW`, `NORMAL`, `HIGH`, `EXTREME`.

### F. News Guard & Quarantine Filter (`app/context_engine/news_guard.py`)
- Enforces an operational blackout during scheduled high-impact releases (e.g. 15 minutes before, 20 minutes after).

---

## 3. Storage Layer (`app/storage/context_storage.py`)

Persists unified `MarketContext` snapshots and discrete structural/liquidity events in Snappy-compressed columnar Parquet files partitioned by symbol and date:
```text
data/market_context/
├── snapshots/{SYMBOL}/{YYYY-MM-DD}.parquet
├── structure_events/{SYMBOL}/{YYYY-MM-DD}.parquet
└── liquidity_events/{SYMBOL}/{YYYY-MM-DD}.parquet
```
