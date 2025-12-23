# Strategy Logic - Deep Dive

This document explains the complete logic behind the TQ Channel Strategy.

## Table of Contents

1. [Overview](#overview)
2. [Trend-Quality Indicator](#trend-quality-indicator)
3. [Channel Indicators](#channel-indicators)
4. [Entry Logic](#entry-logic)
5. [Exit Logic](#exit-logic)
6. [Position Management](#position-management)

---

## Overview

The strategy operates on a simple premise: **price behavior at extremes depends on market regime**.

| Regime | Channel Touch | Action | Rationale |
|--------|---------------|--------|-----------|
| Ranging | Price > Upper | Short | Mean reversion expected |
| Ranging | Price < Lower | Long | Mean reversion expected |
| Trending Up | Price > Upper | Long | Breakout continuation |
| Trending Down | Price < Lower | Short | Breakout continuation |

The key innovation is using the **Trend-Quality (TQ) indicator** as the regime classifier.

---

## Trend-Quality Indicator

### Concept

TQ measures how "clean" a trend is by comparing actual price movement to noise:

```
TQ = Smoothed_Trend / Noise
```

- **High positive TQ**: Strong, clean uptrend
- **High negative TQ**: Strong, clean downtrend
- **TQ near zero**: Choppy, ranging market

### Calculation Steps

1. **EMA Crossover Detection**
   ```python
   reversal = 1 if EMA_fast > EMA_slow else -1
   ```

2. **Cumulative Price Change (CPC)**
   - Resets when EMA cross occurs
   - Accumulates: `CPC += Close - Previous_Close`

3. **Trend Smoothing**
   - Exponential smoothing: `Trend = Trend * (1 - SMF) + CPC * SMF`
   - Where `SMF = 2 / (1 + trend_length)`

4. **Noise Calculation**
   - `Diff = |CPC - Trend|`
   - `Noise = Average(Diff) * correction_factor` over noise_length bars

5. **Final TQ Value**
   - `TQ = Trend / Noise`

### Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| fast_length | 7 | Fast EMA period for crossover |
| slow_length | 15 | Slow EMA period for crossover |
| trend_length | 4 | Trend smoothing factor |
| noise_length | 250 | Lookback for noise calculation |
| correction_factor | 2.0 | Noise scaling multiplier |

### Thresholds

| Threshold | Value | Interpretation |
|-----------|-------|----------------|
| high_threshold | 2.5 | Above = strong uptrend |
| low_threshold | -4 | Below = strong downtrend |
| Between | -4 to 2.5 | Ranging/weak trend |

---

## Channel Indicators

### Bollinger Bands Version

Classic Bollinger Bands with customizations:
- Uses **sample standard deviation** (N-1 denominator) to match TradingView
- Single multiplier for symmetric bands

```python
Upper = SMA(close, length) + mult * StdDev(close, length)
Lower = SMA(close, length) - mult * StdDev(close, length)
```

| Parameter | Default |
|-----------|---------|
| bb_length | 20 |
| bb_mult | 2 |

### Linear Regression Channel Version

Linear regression line with deviation bands:
- Uses least squares regression
- Standard deviation calculated from **residuals** (not raw prices)
- Allows asymmetric upper/lower deviations

```python
Regression = slope * x + intercept  (at current bar)
Upper = Regression + upper_deviation * StdDev(residuals)
Lower = Regression - lower_deviation * StdDev(residuals)
```

| Parameter | Default |
|-----------|---------|
| linreg_count | 20 |
| upper_deviation | 2 |
| lower_deviation | 2 |

### Why Linear Regression Can Outperform

| Aspect | Bollinger Bands | Linear Regression |
|--------|-----------------|-------------------|
| Center line | Moving Average | Regression Line |
| Trend awareness | None (horizontal bias) | Yes (captures slope) |
| Band calculation | Price std dev | Residual std dev |
| In strong trends | Bands lag | Bands align with trend |

The LinReg version achieved Sharpe 1.4 vs BB's 1.3 in testing.

---

## Entry Logic

### Reversion Entries

**Short (Buy Reversion)**
```python
if close > upper_band AND TQ < high_threshold:
    if reversion_short_orders < max_orders:
        MarketOrder(-50% position)
```
- Price is extended above channel
- TQ says trend is NOT strong (weak or ranging)
- Expect price to revert back inside channel

**Long (Sell Reversion)**
```python
if close < lower_band AND TQ > low_threshold:
    if reversion_long_orders < max_orders:
        MarketOrder(+50% position)
```
- Price is extended below channel
- TQ says trend is NOT strong (weak or ranging)
- Expect price to revert back inside channel

### Breakout Entries

**Long (Buy Breakout)**
```python
if close > upper_band AND TQ > high_threshold:
    # Close any shorts first
    if breakout_long_orders < max_orders:
        MarketOrder(+50% position)
```
- Price breaks above channel
- TQ confirms strong uptrend
- Expect continuation higher

**Short (Sell Breakout)**
```python
if close < lower_band AND TQ < low_threshold:
    # Close any longs first
    if breakout_short_orders < max_orders:
        MarketOrder(-50% position)
```
- Price breaks below channel
- TQ confirms strong downtrend
- Expect continuation lower

---

## Exit Logic

### Reversion Exits

Close reversion positions when:
1. Price returns inside channel (success), OR
2. TQ goes extreme (regime changed - stop out)

```python
# Exit reversion short
if close < (upper - close * between_factor) OR TQ extreme:
    close position

# Exit reversion long  
if close > (lower + close * between_factor) OR TQ extreme:
    close position
```

The `between_factor` (0.05%) provides a small buffer to avoid whipsaws.

### Breakout Exits

Close breakout positions when BOTH:
1. Price returns inside channel, AND
2. TQ normalizes (no longer extreme)

```python
# Exit breakout long
if close < (upper - close * between_factor) AND -4 < TQ < 2.5:
    close position

# Exit breakout short
if close > (lower + close * between_factor) AND -4 < TQ < 2.5:
    close position
```

Breakouts require BOTH conditions because:
- Price returning alone might just be a pullback
- TQ normalizing alone doesn't matter if price is still extended

---

## Position Management

### Pyramiding

Each trade type allows up to 3 orders (pyramiding):
- Reversion long: max 3 entries
- Reversion short: max 3 entries
- Breakout long: max 3 entries
- Breakout short: max 3 entries

Order counts reset to 0 when position closes.

### Position Sizing

Each entry is 50% of available capital allocation:
```python
CalculateOrderQuantity(symbol, 0.5)  # 50% for longs
CalculateOrderQuantity(symbol, -0.5)  # 50% for shorts
```

With 2:1 leverage, this means each entry uses 100% notional of equity.

### Leverage

Strategy uses 2:1 leverage (50% margin):
```python
self.AddEquity("QQQ", Resolution.Minute, leverage=2)
```

This amplifies both gains and losses.

---

## Example Trade Flow

### Scenario: Ranging Market → Reversion Short

1. **Setup**: TQ = 1.5 (between -5 and 2.5, ranging)
2. **Signal**: Price spikes above upper band
3. **Entry**: Short 50% position (Buy Reversion)
4. **Price continues**: TQ still ranging, price spikes again
5. **Pyramid**: Short another 50% (2nd reversion entry)
6. **Reversion**: Price drops back inside channel
7. **Exit**: Close all reversion shorts, order count resets

### Scenario: Trending Market → Breakout Long

1. **Setup**: TQ = 3.5 (above 2.5, strong uptrend)
2. **Signal**: Price breaks above upper band
3. **Check shorts**: Close any existing short positions
4. **Entry**: Long 50% position (Buy Breakout)
5. **Continuation**: Price keeps pushing, TQ stays high
6. **Pyramid**: Long another 50% (2nd breakout entry)
7. **Exhaustion**: Price drops inside band AND TQ falls to 1.0
8. **Exit**: Close all breakout longs, order count resets
