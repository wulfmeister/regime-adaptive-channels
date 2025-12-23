# TQ Channel Strategy

A regime-adaptive algorithmic trading strategy that combines **Trend-Quality (TQ) filtering** with **channel-based triggers** (Bollinger Bands or Linear Regression Channels) to dynamically switch between mean-reversion and breakout modes.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-QuantConnect-green.svg)
![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)

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

## 📈 Backtest Results

### QQQ 5-Minute Bars (2023-01-01 to 2025-11-30)

| Variant | Sharpe | CAGR | Max DD | Net Profit | Win Rate |
|---------|--------|------|--------|------------|----------|
| **Bollinger Bands** | 1.30 | ~45% | ~26% | ~180% | ~42% |
| **Linear Regression** | 1.40 | 47.7% | 26.1% | 190.5% | 42% |

### Full Cycle (2020-01-01 to 2025-11-30)

| Metric | Value |
|--------|-------|
| Net Profit | 193.1% |
| CAGR | 20.6% |
| Max Drawdown | 49.5% |
| Sharpe Ratio | 0.56 |
| Total Trades | 3,567 |

⚠️ **Note:** The 49.5% drawdown occurred during 2022. Extended drawdown recovery of 498 days. Strategy requires strong conviction to hold through adverse periods.

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
│   └── results/             # Backtest output files, charts
│
└── docs/
    ├── strategy_logic.md    # Detailed strategy explanation
    └── parameter_tuning.md  # Notes on optimization
```

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

## 📉 Risk Considerations

1. **Drawdown Risk**: Strategy experienced 49.5% drawdown in 2022
2. **Regime Dependence**: Performs best in bull markets with clear trends
3. **Leverage**: 2:1 leverage amplifies both gains and losses
4. **Slippage**: 91-97% annual turnover means execution quality matters
5. **Single Asset**: Concentrated exposure to QQQ/Nasdaq

## 🔧 Potential Improvements

- [ ] Add VIX filter to reduce exposure in high-volatility regimes
- [ ] Add 200-day MA trend filter for directional bias
- [ ] Dynamic leverage based on drawdown/volatility
- [ ] Multi-asset diversification (SPY, IWM, sector ETFs)
- [ ] Walk-forward optimization for parameter robustness

## 📚 References

- [Linear Regression Channels - TradingView](https://www.tradingview.com/support/solutions/43000502266-linear-regression/)
- [Bollinger Bands - Official Site](https://www.bollingerbands.com/)
- [QuantConnect Documentation](https://www.quantconnect.com/docs/)

## ⚖️ License

MIT License - see [LICENSE](LICENSE) file.

## ⚠️ Disclaimer

**This is educational/research code, not financial advice.**

- Past backtest performance does not guarantee future results
- Backtests do not account for all real-world frictions (slippage, partial fills, etc.)
- 49.5% drawdowns occurred during testing periods
- Do not trade with money you cannot afford to lose
- The author is not responsible for any financial losses incurred

---

*Built with ☕ and curiosity. Questions? Open an issue.*
