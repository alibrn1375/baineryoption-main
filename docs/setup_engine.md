# FO-X 5M — Setup Engine & Decision Framework Documentation

## Overview

The **Setup Engine and Decision Framework** constitutes the analytical decision layer of the FO-X 5M quantitative architecture.

Its role is to synthesize multi-sensor Footprint data, Order Flow features, and Market Context observations into statistically validated trade setups, evaluate their Expected Value ($EV$), and render definitive `CALL`, `PUT`, or `NO_TRADE` decisions.

---

## 1. Core Mathematical Decision Architecture

```text
       [ FootprintBar + OrderFlowContext + MarketContext + Historical Stats ]
                                         ↓
                           ┌───────────────────────────┐
                           │   Setup Evaluators (A-D)  │
                           └─────────────┬─────────────┘
                                         ↓
                           ┌───────────────────────────┐
                           │   Quality Scorer (0-100)  │
                           │ - Context (30 pts)        │
                           │ - Order Flow (35 pts)     │
                           │ - Data Quality (15 pts)   │
                           │ - Risk Safety (20 pts)    │
                           └─────────────┬─────────────┘
                                         ↓
                           ┌───────────────────────────┐
                           │   Probability Estimator   │
                           │ - Wilson Confidence Bound │
                           │ - Sample Adequacy Penalty │
                           └─────────────┬─────────────┘
                                         ↓
                           ┌───────────────────────────┐
                           │       EV Calculator       │
                           │ EV = (P * Payout) - (Q *1)│
                           └─────────────┬─────────────┘
                                         ↓
                           ┌───────────────────────────┐
                           │     Decision Arbiter      │
                           │ - Min Score ≥ 75.0        │
                           │ - Min Probability ≥ 0.58  │
                           │ - EV > 0.0 (Positive)     │
                           │ - News / Volatility Clean │
                           └─────────────┬─────────────┘
                                         ↓
                        [ BinaryDecision: CALL / PUT / NO_TRADE ]
                                         ↓
                           [ Explainability & Storage ]
```

---

## 2. Research Setup Archetypes

- **Setup A: Liquidity Sweep + Absorption Reversal**
  - Identifies interactions where price pierces a key liquidity pool (Equal Highs, Equal Lows, or Prior Session High/Low) and displays aggressive volume absorption by passive limit liquidity, closing with a significant rejection wick ($\ge 40\%$).
- **Setup B: Imbalance Momentum Continuation**
  - Identifies stacked diagonal imbalances ($\ge 3$ consecutive price levels) aligned with directional delta acceleration and higher-timeframe structural trend.
- **Setup C: Aggressive Momentum Exhaustion**
  - Identifies severe delta depletion ($\ge 50\%$ drop) and failed follow-through after an aggressive volume push into new extremes.
- **Setup D: Failed Auction Range Rejection**
  - Identifies failed breakout attempts outside balance areas, accompanied by strong opposing delta rotation back into value.

---

## 3. Mathematical Expectancy & Wilson Confidence Bound

### A. Wilson Score Interval with Continuity Discount
$$\hat{p} = \frac{n_w + \frac{z^2}{2}}{n + z^2} \pm \frac{z}{n + z^2}\sqrt{\frac{n_w n_l}{n} + \frac{z^2}{4}}$$
For small historical samples ($n < 30$), the conservative lower bound ($\text{Wilson}_{\text{lower}}$) is enforced to penalize small sample overfitting.

### B. Binary Options Expected Value ($EV$) Formula
$$\text{EV} = (P_{\text{win}} \times \text{Payout}) - ((1 - P_{\text{win}}) \times \text{Risk})$$
$$\text{Break-Even Win Rate} = \frac{1.0}{1.0 + \text{Payout}}$$
A setup is strictly rejected with `NO_TRADE` if $\text{EV} \le 0$ or if the offered broker payout does not satisfy the minimum hurdle rate ($\ge 80\%$).

---

## 4. Decision Arbiter & Rejection Safeguards

If any safeguard is violated, the Arbiter defaults to `NO_TRADE` with explicit categorical reasons:
- `LOW_SCORE`: Composite score $< 75/100$.
- `LOW_CONFIDENCE`: Wilson conservative probability $< 58\%$.
- `INSUFFICIENT_SAMPLE`: Historical sample size $< 15$ observations.
- `NEWS_RISK`: Active macroeconomic blackout window.
- `HIGH_VOLATILITY`: Extreme erratic volatility ($\ge 90$th percentile).
- `DATA_QUALITY_FAILURE`: Missing or corrupt tick feed.
- `NEGATIVE_EXPECTED_VALUE`: $\text{EV} \le 0$.
- `LOW_PAYOUT`: Offered payout $< 80\%$.

---

## 5. Storage Layer (`app/storage/decision_storage.py`)

All decision objects and evaluation logs are persisted in Snappy-compressed Parquet stores partitioned by date:
```text
data/decisions/
├── logs/{YYYY-MM-DD}.parquet
└── evaluations/{YYYY-MM-DD}.parquet
```
