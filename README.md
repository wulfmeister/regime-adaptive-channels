# Regime-Adaptive Channels Strategy

A regime-adaptive algorithmic trading strategy that combines **Trend-Quality (TQ) filtering** with **channel-based triggers** (Bollinger Bands or Linear Regression Channels) to dynamically switch between mean-reversion and breakout modes.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-QuantConnect-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

## Table of Contents

- [Strategy Overview](#-strategy-overview)
- [Backtest Results](#-backtest-results)
- [Repository Structure](#-repository-structure)
- [Quick Start](#-quick-start)
- [How It Works](#-how-it-works)
- [Risk Considerations](#-risk-considerations)
- [Potential Improvements](#-potential-improvements)
- [Strategy Logic - Deep Dive](#strategy-logic---deep-dive)
  - [Overview](#overview)
  - [Trend-Quality Indicator](#trend-quality-indicator)
  - [Channel Indicators](#channel-indicators)
  - [Entry Logic](#entry-logic)
  - [Exit Logic](#exit-logic)
  - [Position Management](#position-management)
  - [Example Trade Flow](#example-trade-flow)
- [Parameter Tuning Guide](#parameter-tuning-guide)
  - [Parameter Overview](#parameter-overview)
  - [Sensitivity Analysis](#sensitivity-analysis)
  - [Optimization Approach](#optimization-approach)
  - [Lessons Learned](#lessons-learned)
  - [Future Experiments](#future-experiments)
- [References](#-references)
- [License](#-license)
- [Disclaimer](#-disclaimer)

---

## 📊 Strategy Overview

### The Core Idea

Most strategies are **either** mean-reversion **or** trend-following. This strategy does both by using a **regime classifier** to determine market state:

```
IF price touches channel boundary:
    IF trend quality is weak → Mean Reversion trade
    IF trend quality is strong → Breakout trade
```

### Components

| Component | Purpose |
|-----------|---------|
| **Channel Indicator** | Defines upper/lower trigger boundaries (Bollinger Bands or Linear Regression) |
| **Trend-Quality (TQ)** | Classifies regime: trending vs. ranging |
| **Entry Logic** | Channel touch + TQ reading determines trade direction |
| **Exit Logic** | Price returns inside channel OR regime shifts |

---

## 📈 Backtest Results

### QQQ 5-Minute Bars (2023-01-01 to 2025-09-30 [limited recent data on QC])

| Variant | Sharpe | CAGR | Max DD | Net Profit | Win Rate |
|---------|--------|------|--------|------------|----------|
| **Bollinger Bands** | 1.30 | ~45% | ~26% | ~180% | ~42% |
| **Linear Regression** | 1.40 | 47.7% | 26.1% | 190.5% | 42% |

---

## 🏗️ Repository Structure

```
tq-channel-strategy/
├── README.md                 # This file
├── LICENSE                   # MIT License
├── .gitignore               # Python/QuantConnect ignores
│
├── strategies/
│   ├── bollinger_tq.py      # Bollinger Bands + TQ version
│   └── linreg_tq.py         # Linear Regression Channel + TQ version
│
├── indicators/
│   ├── trend_quality.py     # TQ indicator (standalone)
│   └── linreg_channel.py    # Linear Regression Channel (standalone)
│
├── backtests/
    └── results/             # Backtest output files, charts
```

---

## 🚀 Quick Start

### Prerequisites

- [QuantConnect](https://www.quantconnect.com/) account (free tier works)
- Python 3.8+

### Running on QuantConnect

1. Create a new algorithm on QuantConnect
2. Copy the contents of `strategies/linreg_tq.py` (or `bollinger_tq.py`)
3. Set backtest parameters:
   - Start Date: 2023-01-01
   - End Date: 2025-11-30
   - Cash: $100,000
4. Run backtest

### Parameters

```python
# Channel Settings
linreg_count = 22        # Lookback period for regression/BB
upper_deviation = 2.1    # Standard deviations for upper band
lower_deviation = 2.1    # Standard deviations for lower band

# Trend-Quality Settings
fast_length = 7          # Fast EMA for TQ
slow_length = 13         # Slow EMA for TQ
trend_length = 4         # Trend smoothing factor
noise_length = 250       # Noise calculation window
correction_factor = 2.0  # Noise scaling

# Regime Thresholds
low_threshold = -5       # Below this = strong downtrend
high_threshold = 2.5     # Above this = strong uptrend

# Trade Management
between_factor = 0.0006  # Exit buffer (0.06% from band)
```

---

## 🔬 How It Works

### Trend-Quality Indicator

The TQ indicator measures trend strength by comparing price movement to noise:

```
TQ = Smoothed_Cumulative_Price_Change / Average_Deviation
```

- **TQ > high_threshold**: Strong uptrend → favor long breakouts
- **TQ < low_threshold**: Strong downtrend → favor short breakouts  
- **Between thresholds**: Ranging market → mean reversion trades

### Entry Logic

```python
# Reversion: Price at extreme + weak trend = fade the move
if close > upper_band and TQ < high_threshold:
    SHORT (expect reversion down)

if close < lower_band and TQ > low_threshold:
    LONG (expect reversion up)

# Breakout: Price at extreme + strong trend = ride the move
if close > upper_band and TQ > high_threshold:
    LONG (expecting continuation)

if close < lower_band and TQ < low_threshold:
    SHORT (expecting continuation)
```

### Exit Logic

- **Reversion trades**: Exit when price returns inside channel OR TQ goes extreme
- **Breakout trades**: Exit when price returns inside channel AND TQ normalizes

### Position Management

- Pyramiding: Up to 3 orders per trade type
- 2:1 leverage (50% margin)
- 50% position sizing per entry

---

## 📉 Risk Considerations

1. **Drawdown Risk**: Strategy experienced 49.5% drawdown in 2022
2. **Regime Dependence**: Performs best in bull markets with clear trends
3. **Leverage**: 2:1 leverage amplifies both gains and losses
4. **Slippage**: 91-97% annual turnover means execution quality matters
5. **Single Asset**: Concentrated exposure to QQQ/Nasdaq

---

## 🔧 Potential Improvements

- [ ] Add VIX filter to reduce exposure in high-volatility regimes
- [ ] Add 200-day MA trend filter for directional bias
- [ ] Dynamic leverage based on drawdown/volatility
- [ ] Multi-asset diversification (SPY, IWM, sector ETFs)
- [ ] Walk-forward optimization for parameter robustness

---

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

---

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

---

## 📚 References

- [Linear Regression Channels - TradingView](https://www.tradingview.com/support/solutions/43000502266-linear-regression/)
- [Bollinger Bands - Official Site](https://www.bollingerbands.com/)
- [QuantConnect Documentation](https://www.quantconnect.com/docs/)

---

## ⚖️ License

MIT License - see [LICENSE](LICENSE) file.

---

## ⚠️ Disclaimer

**This is educational/research code, not financial advice.**

- Past backtest performance does not guarantee future results
- Backtests do not account for all real-world frictions (slippage, partial fills, etc.)
- 49.5% drawdowns occurred during testing periods
- Do not trade with money you cannot afford to lose
- The author is not responsible for any financial losses incurred

---

*Built with ☕ and curiosity. Questions? Open an issue.*
