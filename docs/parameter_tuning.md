# Parameter Tuning Guide

Notes on optimizing strategy parameters and lessons learned from backtesting.

## Table of Contents

1. [Parameter Overview](#parameter-overview)
2. [Sensitivity Analysis](#sensitivity-analysis)
3. [Optimization Approach](#optimization-approach)
4. [Lessons Learned](#lessons-learned)
5. [Future Experiments](#future-experiments)

---

## Parameter Overview

### Channel Parameters

| Parameter | Range Tested | Optimal | Notes |
|-----------|--------------|---------|-------|
| `linreg_count` / `bb_length` | 10-50 | 20 | Shorter = more signals, more noise |
| `upper_deviation` | 1.5-3.0 | 2 | Tighter = more frequent triggers |
| `lower_deviation` | 1.5-3.0 | 2 | Can be asymmetric for biased markets |

### Trend-Quality Parameters

| Parameter | Range Tested | Optimal | Notes |
|-----------|--------------|---------|-------|
| `fast_length` | 5-15 | 7 | Standard short-term EMA |
| `slow_length` | 10-25 | 15 | Standard medium-term EMA |
| `trend_length` | 2-10 | 4 | Lower = more reactive to changes |
| `noise_length` | 100-500 | 250 | Longer = more stable noise estimate |
| `correction_factor` | 1.0-3.0 | 2.0 | Scales noise calculation |

### Threshold Parameters

| Parameter | Range Tested | Optimal | Notes |
|-----------|--------------|---------|-------|
| `high_threshold` | 1.5-5.0 | 2.5 | Higher = stricter breakout confirmation |
| `low_threshold` | -10 to -2 | -4 | Lower = stricter downtrend confirmation |

### Trade Management

| Parameter | Value | Notes |
|-----------|-------|-------|
| `between_factor` | 0.0005 | 0.05% buffer for exits |
| `max_orders` | 3 | Pyramiding limit per trade type |
| Leverage | 2:1 | 50% margin |
| Position size | 50% | Per entry |

---

## Sensitivity Analysis

### Most Sensitive Parameters

1. **`high_threshold` / `low_threshold`**
   - Small changes significantly affect trade frequency
   - Tighter range = more reversion trades
   - Wider range = more breakout trades
   - Asymmetry (e.g., -4 / +2.5) reflects bull market bias

2. **`upper_deviation` / `lower_deviation`**
   - Directly controls trigger frequency
   - 2.0-2.5 seems optimal for 5-min QQQ
   - Below 1.8 = too many false signals
   - Above 3 = misses good entries

3. **`linreg_count` / `bb_length`**
   - Affects channel responsiveness
   - 20-25 balances smoothness and reactivity
   - Shorter periods for scalping, longer for swing

### Least Sensitive Parameters

1. **`fast_length` / `slow_length`**
   - Classic 7/13 or 12/26 both work
   - Main purpose is crossover detection for TQ reset

2. **`noise_length`**
   - 200-300 all produce similar results
   - Just needs to be "long enough" for stable estimate

3. **`correction_factor`**
   - 1.5-2.5 range is robust
   - Mainly affects TQ scale, not direction

---

## Optimization Approach

### Walk-Forward Testing (Recommended)

Instead of optimizing over the full period:

1. **In-Sample**: Optimize on 2020-2022
2. **Out-of-Sample**: Test on 2023-2024
3. **Validate**: Check 2024-2025

This prevents overfitting to recent bull market.

### Grid Search Results

Example grid search on 2023-2024:

| Channel Length | Deviation | High Thresh | Sharpe |
|----------------|-----------|-------------|--------|
| 18 | 2.0 | 2.0 | 1.21 |
| 20 | 2.0 | 2.5 | 1.32 |
| 22 | 2.1 | 2.5 | **1.40** |
| 22 | 2.2 | 3.0 | 1.28 |
| 25 | 2.5 | 3.0 | 1.15 |

### What NOT to Do

❌ **Over-optimize** - Finding the "perfect" parameters for historical data
❌ **Cherry-pick periods** - Only testing bull markets
❌ **Ignore transaction costs** - Results include fees, but slippage is estimated
❌ **Trust single backtest** - Monte Carlo simulation needed for confidence

---

## Lessons Learned

### 1. EXAMPLE Bull vs Bear Performance

| Period | Market | Sharpe | CAGR | Max DD |
|--------|--------|--------|------|--------|
| 2023-2025 | Bull | 1.40 | 47.7% | 26.1% |
| 2020-2022 | Mixed | 0.16 | 0.7% | 49.5% |
| Full Cycle | Both | 0.56 | 20.6% | 49.5% |

**Insight**: Strategy is currently long-biased and struggles in bear markets.

### 2. Drawdown Characteristics

- Max drawdown of 49.5% occurred during 2022
- Recovery took 498 days (1.4 years)
- Psychologically very difficult to hold through

**Insight**: Position sizing and leverage need reduction for real trading.

### 3. Trade Frequency

- ~3,567 trades over 6 years ≈ 2.4 trades/day
- 91-97% annual portfolio turnover
- Execution quality matters significantly

**Insight**: Strategy is sensitive to slippage and execution.

### 4. Asymmetric Thresholds

Default thresholds are asymmetric: `low=-4`, `high=2.5`

This means:
- Easier to trigger breakout longs (TQ just needs >2.5)
- Harder to trigger breakout shorts (TQ needs < -4)
- Reflects inherent long bias of equity markets

**Insight**: Consider symmetric thresholds for neutral exposure.

---

## Future Experiments

### 1. Volatility Filter

Add VIX-based filter to reduce exposure in high volatility:

```python
if vix > 25:
    reduce_position_size()
    # or skip_reversion_trades()
```

**Hypothesis**: Reduces drawdown during volatility spikes.

### 2. Trend Filter

Add 200-day MA filter for directional bias:

```python
if close > ma_200:
    only_long_trades()
elif close < ma_200:
    only_short_trades()
```

**Hypothesis**: Avoids fighting major trends.

### 3. Dynamic Thresholds

Scale thresholds based on recent volatility:

```python
high_threshold = base_threshold * (current_vol / average_vol)
```

**Hypothesis**: Adapts to changing market conditions.

### 4. Multi-Asset Diversification

Test on:
- SPY (S&P 500)
- IWM (Russell 2000)
- Sector ETFs (XLK, XLF, XLE)

**Hypothesis**: Reduces single-asset concentration risk.

### 5. Alternative Timeframes

Test on:
- 15-minute bars
- 1-hour bars
- Daily bars

**Hypothesis**: Longer timeframes may reduce noise and transaction costs.

---

## Parameter Interaction Matrix

Understanding how parameters interact:

```
                    Channel Width
                    Tight    |    Wide
                 ┌───────────┼───────────┐
  TQ Threshold   │ Many      │ Moderate  │
     Tight       │ signals,  │ signals,  │
                 │ high noise│ balanced  │
                 ├───────────┼───────────┤
  TQ Threshold   │ Moderate  │ Few       │
     Wide        │ signals,  │ signals,  │
                 │ selective │ miss moves│
                 └───────────┴───────────┘
```

The optimal is usually in the "Moderate signals, balanced" quadrant.

---

## Reproducibility Notes

All backtests run on:
- Platform: QuantConnect
- Asset: QQQ
- Resolution: 5-minute bars
- Leverage: 2:1
- Commission model: QuantConnect default
- Slippage model: QuantConnect default

YMMV, and results may vary with:
- Different brokers
- Different commission structures
- Different slippage assumptions
- Live vs paper trading
