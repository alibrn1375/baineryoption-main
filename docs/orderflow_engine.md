# FO-X 5M — Order Flow Intelligence Engine Documentation

## Overview

The **Order Flow Intelligence Engine** transforms raw and aggregated Footprint bar data into quantitative, objective order flow features without generating trade signals, biases, or entry/exit recommendations.

Every feature adheres to the tenet of **microstructure measurability** and statistical validation.

---

## 1. Feature Architecture

All features inherit from `OrderFlowFeatureBase` (`app/orderflow_engine/base.py`), establishing common metadata:
- `timestamp`: UTC bar evaluation timestamp.
- `symbol`: Target asset symbol (`GC_FUT`, `XAUUSD`).
- `timeframe`: Evaluation period (default `5m`).
- `feature_name`: Explicit feature identifier.
- `direction`: Directional polarity (`BUY`, `SELL`, `NEUTRAL`).
- `confidence`: Range `[0.0, 1.0]`.
- `calculation_version`: Version identifier (`1.0.0`).

---

## 2. Quantitative Subsystems

### A. Delta Intelligence (`app/orderflow_engine/delta_analyzer.py`)
- **Delta Strength**: Normalized absolute delta relative to rolling baseline.
- **Delta Acceleration**: Rate of delta change between consecutive bars ($\Delta_t - \Delta_{t-1}$).
- **Delta Persistence**: Count of continuous consecutive bars preserving identical delta polarity.
- **Rolling Percentiles**: Historical percentile rank evaluated over configurable lookback windows (`lookback_period: 20`).
- **Statistical Extremes**: Flagging upper/lower percentile thresholds (e.g., $\ge 90\%$ or $\le 10\%$).

### B. Diagonal Imbalance Detector (`app/orderflow_engine/imbalance_detector.py`)
- Evaluates aggressive bid/ask imbalances across adjacent diagonal price ticks:
  $$\text{BUY Imbalance: } \frac{\text{Ask}_P}{\text{Bid}_{P - \text{tick}}} \ge \text{ratio\_threshold}$$
  $$\text{SELL Imbalance: } \frac{\text{Bid}_P}{\text{Ask}_{P + \text{tick}}} \ge \text{ratio\_threshold}$$
- Filters by minimum volume threshold and minimum absolute delta delta difference.

### C. Stacked Imbalance Detector (`app/orderflow_engine/stacked_imbalance.py`)
- Detects contiguous clusters of consecutive diagonal imbalance levels ($\ge 3$ levels).
- Quantifies institutional footprint zones, aggregate volume, average ratios, and boundaries.

### D. Absorption Detector (`app/orderflow_engine/absorption_detector.py`)
- Identifies aggressive order absorption by passive limit liquidity:
  - High volume percentile ($\ge 80\%$).
  - Low price efficiency (large volume traded relative to candle body progression).
  - Price rejection wick ($\ge 40\%$ return into bar).
  - Flags trapped buyers at highs or trapped sellers at lows.

### E. Exhaustion Detector (`app/orderflow_engine/exhaustion_detector.py`)
- Quantifies sudden momentum depletion after aggressive volume bursts:
  - Fading delta progression at new session highs/lows.
  - Follow-through failure ($\ge 50\%$ delta collapse).

---

## 3. Order Flow Context Object

`OrderFlowContext` (`app/models/orderflow_context.py`) unifies all sensory feature states for a 5M bar into an immutable snapshot:
- `delta_feature`
- `imbalances`
- `stacked_imbalances`
- `absorption_feature`
- `exhaustion_feature`
- `dominant_direction`
- `quality`

---

## 4. Parquet Partitioned Storage

`OrderFlowStorage` (`app/storage/orderflow_storage.py`) persists all features into columnar Snappy-compressed Parquet files partitioned by symbol and date:
```text
data/orderflow/
├── contexts/{SYMBOL}/{YYYY-MM-DD}.parquet
├── deltas/{SYMBOL}/{YYYY-MM-DD}.parquet
├── imbalances/{SYMBOL}/{YYYY-MM-DD}.parquet
├── stacked/{SYMBOL}/{YYYY-MM-DD}.parquet
├── absorptions/{SYMBOL}/{YYYY-MM-DD}.parquet
└── exhaustions/{SYMBOL}/{YYYY-MM-DD}.parquet
```

---

## 5. Configuration Reference (`configs/orderflow_config.yaml`)

```yaml
orderflow:
  delta:
    lookback_period: 20
    extreme_percentile_high: 90.0
    extreme_percentile_low: 10.0
    min_samples: 5
  imbalance:
    ratio_threshold: 3.0
    minimum_volume: 10.0
    minimum_delta: 5.0
  stacked_imbalance:
    min_consecutive_levels: 3
    max_level_gap_ticks: 1
  absorption:
    volume_percentile_threshold: 80.0
    price_efficiency_max: 0.35
    rejection_return_pct: 0.40
    min_absorption_volume: 50.0
  exhaustion:
    delta_drop_ratio: 0.50
    thin_volume_threshold: 0.30
    lookback_period: 10
```
