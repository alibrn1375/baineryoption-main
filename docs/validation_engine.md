# FO-X 5M — Validation Engine Documentation

## Overview

The **Validation Engine** provides an empirical, backtesting and statistical verification laboratory for the FO-X 5M system.

Its core mandate is to evaluate system survivability, distribution stability, and statistical significance across historical data without optimization bias, curve fitting, or lookahead leakage.

---

## 1. Validation Architecture & Chronological Pipeline

```text
       [ Historical Tick Feed (Parquet) ]
                        ↓
       ┌─────────────────────────────────┐
       │          ReplayEngine           │  (Tick-by-tick, monotonic timestamp sort)
       └────────────────┬────────────────┘
                        ↓ (MarketEvents)
       ┌─────────────────────────────────┐
       │   FO-X Live Processing Pipeline │  (Footprint -> OrderFlow -> Context -> Arbiter)
       └────────────────┬────────────────┘
                        ↓
       ┌─────────────────────────────────┐
       │        Binary Simulator         │  (5M Expiry, Payout, Slippage, Delay, Spread)
       └────────────────┬────────────────┘
                        ↓
         ┌──────────────┴──────────────┐
         ▼                             ▼
  [ MetricsEngine ]             [ WalkForward ]
   - Win Rate & Wilson CI        - IS / OOS Rolling Windows
   - Expectancy & PnL            - Stability Decay Metric
   - Drawdowns & Streaks               ↓
         │                      [ MonteCarloEngine ]
         │                       - 10,000 Bootstrap Reshuffles
         │                       - Worst 1% Scenarios
         │                       - Tail Risk Probabilities
         └──────────────┬──────────────┘
                        ↓
       ┌─────────────────────────────────┐
       │   Forensic Failure Analyzer     │  (Categorizes Loss Root Causes)
       └────────────────┬────────────────┘
                        ↓
          [ Research Parquet Storage ]
```

---

## 2. Zero Lookahead Enforcement

- **Strict Temporal Barrier**: The `ReplayEngine` only exposes ticks sequentially where $\text{tick.timestamp} \le \text{current\_time}$.
- **No Future Access Test**: Verified by `test_no_future_data_access()`, ensuring that out-of-order data feeds are strictly sorted and that no candle closes or features beyond time $T$ are visible to decision logic at time $T$.

---

## 3. Realistic Binary Execution Simulator

Execution assumptions are fully parameterized in `configs/validation_config.yaml`:
- **Entry Delay**: Configurable milliseconds (`entry_delay_ms: 200`) simulating broker order transmission and fill latency.
- **Spread & Adverse Slippage**: Half-spread and adverse slippage are added on CALL entries and subtracted on PUT entries.
- **Explicit Tie Handling**:
  - `REFUND`: Returns $100\%$ stake ($\text{PnL} = 0.0$).
  - `LOSS`: Deducts $100\%$ stake ($\text{PnL} = -1.0$).
  - `HALF_LOSS`: Deducts $50\%$ stake ($\text{PnL} = -0.5$).

---

## 4. Statistical Validation Models

### A. Walk-Forward Rolling Windows (`app/validation_engine/walk_forward.py`)
- Evaluates out-of-sample (OOS) degradation across sliding in-sample (IS) training windows and unseen testing windows.
- Quantifies strategy robustness through the Stability Ratio:
  $$\text{Stability Ratio} = \frac{\text{Win Rate}_{\text{OOS}}}{\text{Win Rate}_{\text{IS}}}$$

### B. Monte Carlo Reshuffle Analysis (`app/validation_engine/monte_carlo.py`)
- Runs $10,000$ non-parametric bootstrap permutations preserving the exact empirical trade PnL distribution.
- Computes:
  - Median max drawdown and 99th percentile worst-case drawdown.
  - Consecutive losing streak probabilities ($4+, 6+, 8+, 10+$ losses).
  - Mathematical risk of ruin hurdle.

---

## 5. Storage Layer (`app/storage/research_storage.py`)

Simulation results and failure diagnostics are stored in Snappy-compressed Parquet files partitioned by date:
```text
data/research/
├── simulations/{YYYY-MM-DD}.parquet
└── failures/{YYYY-MM-DD}.parquet
```
