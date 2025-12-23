"""
Linear Regression Channel + Trend-Quality Strategy for QuantConnect

A regime-adaptive strategy combining Linear Regression Channel triggers
with Trend-Quality indicator for dynamic mean-reversion/breakout switching.

Author: Anonymous
License: MIT
"""

from AlgorithmImports import *
from datetime import timedelta
from collections import deque
import math


class LinRegTQStrategy(QCAlgorithm):
    """
    Regime-adaptive strategy using Linear Regression Channels + Trend-Quality.
    
    Entry Logic:
    - Price > Upper Channel + Weak TQ → Short (mean reversion)
    - Price < Lower Channel + Weak TQ → Long (mean reversion)
    - Price > Upper Channel + Strong TQ → Long (breakout)
    - Price < Lower Channel + Strong TQ → Short (breakout)
    """
    
    def Initialize(self):
        # Backtest period
        self.SetStartDate(2023, 1, 1)
        self.SetEndDate(2025, 12, 31)
        self.SetCash(100000)

        # Add QQQ with minute resolution and 2:1 leverage
        self.symbol = self.AddEquity("QQQ", Resolution.Minute, leverage=2).Symbol

        # Consolidate to 5-minute bars
        self.consolidator = TradeBarConsolidator(timedelta(minutes=5))
        self.consolidator.DataConsolidated += self.OnFiveMinuteBar
        self.SubscriptionManager.AddConsolidator(self.symbol, self.consolidator)

        # === PARAMETERS ===
        # Linear Regression Channel
        self.linreg_count = int(self.GetParameter("linreg_count", 100))
        self.upper_deviation = float(self.GetParameter("upper_deviation", 2))
        self.lower_deviation = float(self.GetParameter("lower_deviation", 2))
        
        # Exit adjustment
        self.between_factor = float(self.GetParameter("between_factor", 0.0005))
        
        # Trend-Quality
        self.fast_length = int(self.GetParameter("fast_length", 7))
        self.slow_length = int(self.GetParameter("slow_length", 15))
        self.trend_length = int(self.GetParameter("trend_length", 4))
        self.noise_length = int(self.GetParameter("noise_length", 250))
        self.correction_factor = float(self.GetParameter("correction_factor", 2.0))
        
        # Regime thresholds
        self.low_threshold = float(self.GetParameter("low_threshold", -4))
        self.high_threshold = float(self.GetParameter("high_threshold", 2.5))

        # === INDICATORS ===
        # Custom Linear Regression Channel
        self.linreg_channel = LinearRegressionChannel(
            self.linreg_count, 
            self.upper_deviation, 
            self.lower_deviation
        )
        self.RegisterIndicator(self.symbol, self.linreg_channel, self.consolidator)

        # Trend-Quality Indicator
        self.tq = TrendQualityIndicator(
            self.symbol, self.fast_length, self.slow_length,
            self.trend_length, self.noise_length,
            self.correction_factor, noise_type="LINEAR"
        )
        self.RegisterIndicator(self.symbol, self.tq, self.consolidator)

        # === TRADING STATE ===
        self.buy_reversion = True
        self.sell_reversion = True
        self.buy_breakout = True
        self.sell_breakout = True

        # Position tracking for pyramiding
        self.reversion_long_shares = 0
        self.reversion_short_shares = 0
        self.breakout_long_shares = 0
        self.breakout_short_shares = 0
        self.reversion_long_orders = 0
        self.reversion_short_orders = 0
        self.breakout_long_orders = 0
        self.breakout_short_orders = 0
        self.max_orders = 3

    def OnFiveMinuteBar(self, sender, bar):
        """Process each 5-minute bar for trade signals."""
        
        if not (self.linreg_channel.IsReady and self.tq.IsReady):
            return

        close = bar.Close
        upper = self.linreg_channel.UpperBand
        lower = self.linreg_channel.LowerBand
        indicator_q = self.tq.Current.Value

        # === REVERSION ENTRIES ===
        # Short when price > upper channel and trend is weak
        if self.buy_reversion and close > upper and indicator_q < self.high_threshold:
            if self.reversion_short_orders < self.max_orders:
                ticket = self.MarketOrder(
                    self.symbol, 
                    -self.CalculateOrderQuantity(self.symbol, -0.5), 
                    tag="Buy Reversion"
                )
                self.reversion_short_shares += abs(ticket.Quantity)
                self.reversion_short_orders += 1

        # Long when price < lower channel and trend is weak
        if self.sell_reversion and close < lower and indicator_q > self.low_threshold:
            if self.reversion_long_orders < self.max_orders:
                ticket = self.MarketOrder(
                    self.symbol, 
                    self.CalculateOrderQuantity(self.symbol, 0.5), 
                    tag="Sell Reversion"
                )
                self.reversion_long_shares += ticket.Quantity
                self.reversion_long_orders += 1

        # === BREAKOUT ENTRIES ===
        # Long breakout when price > upper channel and trend is strong
        if self.buy_breakout and close > upper and indicator_q > self.high_threshold:
            # Close any short positions first
            total_short_shares = self.reversion_short_shares + self.breakout_short_shares
            if total_short_shares > 0:
                self.MarketOrder(self.symbol, total_short_shares, tag="Close open short trade")
                self.reversion_short_shares = 0
                self.breakout_short_shares = 0
                self.reversion_short_orders = 0
                self.breakout_short_orders = 0
            if self.breakout_long_orders < self.max_orders:
                ticket = self.MarketOrder(
                    self.symbol, 
                    self.CalculateOrderQuantity(self.symbol, 0.5), 
                    tag="Buy Breakout"
                )
                self.breakout_long_shares += ticket.Quantity
                self.breakout_long_orders += 1

        # Short breakout when price < lower channel and trend is strong
        if self.sell_breakout and close < lower and indicator_q < self.low_threshold:
            # Close any long positions first
            total_long_shares = self.reversion_long_shares + self.breakout_long_shares
            if total_long_shares > 0:
                self.MarketOrder(self.symbol, -total_long_shares, tag="Close open long trade")
                self.reversion_long_shares = 0
                self.breakout_long_shares = 0
                self.reversion_long_orders = 0
                self.breakout_long_orders = 0
            if self.breakout_short_orders < self.max_orders:
                ticket = self.MarketOrder(
                    self.symbol, 
                    self.CalculateOrderQuantity(self.symbol, -0.5), 
                    tag="Sell Breakout"
                )
                self.breakout_short_shares += abs(ticket.Quantity)
                self.breakout_short_orders += 1

        # === EXIT CONDITIONS ===
        self._check_exits(close, upper, lower, indicator_q)

    def _check_exits(self, close, upper, lower, indicator_q):
        """Check and execute exit conditions for all position types."""
        
        # Exit reversion shorts
        if self.reversion_short_shares > 0:
            close_cond = (close < (upper - close * self.between_factor)) or \
                         (indicator_q < self.low_threshold or indicator_q > self.high_threshold)
            if close_cond:
                self.MarketOrder(self.symbol, self.reversion_short_shares, tag="Close Buy Reversion")
                self.reversion_short_shares = 0
                self.reversion_short_orders = 0

        # Exit reversion longs
        if self.reversion_long_shares > 0:
            close_cond = (close > (lower + close * self.between_factor)) or \
                         (indicator_q < self.low_threshold or indicator_q > self.high_threshold)
            if close_cond:
                self.MarketOrder(self.symbol, -self.reversion_long_shares, tag="Close Sell Reversion")
                self.reversion_long_shares = 0
                self.reversion_long_orders = 0

        # Exit breakout longs
        if self.breakout_long_shares > 0:
            close_cond = (close < (upper - close * self.between_factor)) and \
                         (self.low_threshold < indicator_q < self.high_threshold)
            if close_cond:
                self.MarketOrder(self.symbol, -self.breakout_long_shares, tag="Close Buy Breakout")
                self.breakout_long_shares = 0
                self.breakout_long_orders = 0

        # Exit breakout shorts
        if self.breakout_short_shares > 0:
            close_cond = (close > (lower + close * self.between_factor)) and \
                         (self.low_threshold < indicator_q < self.high_threshold)
            if close_cond:
                self.MarketOrder(self.symbol, self.breakout_short_shares, tag="Close Sell Breakout")
                self.breakout_short_shares = 0
                self.breakout_short_orders = 0

    def OnOrderEvent(self, orderEvent):
        if orderEvent.Status == OrderStatus.Filled:
            self.Debug(f"Order filled: {orderEvent.Symbol} {orderEvent.Quantity} @ {orderEvent.FillPrice}")


class LinearRegressionChannel(PythonIndicator):
    """
    Linear Regression Channel indicator matching TradingView's implementation.
    
    The center line is the linear regression value calculated over the lookback period.
    Upper and lower bands are X standard deviations away from the regression line,
    where the standard deviation is calculated from the residuals (price - regression value).
    
    Parameters:
    - count: Number of bars for linear regression calculation
    - upper_deviation: Number of standard deviations for the upper band
    - lower_deviation: Number of standard deviations for the lower band
    """
    
    def __init__(self, count, upper_deviation=2.0, lower_deviation=2.0):
        self.Name = "LinearRegressionChannel"
        self.Value = 0  # Center line (regression value)
        self.UpperBand = 0
        self.LowerBand = 0
        self.count = count
        self.upper_deviation = upper_deviation
        self.lower_deviation = lower_deviation
        self.prices = deque(maxlen=count)
        
    @property
    def IsReady(self):
        return len(self.prices) == self.count

    def Update(self, input):
        close = input.Close
        self.prices.append(close)

        if len(self.prices) < self.count:
            return False

        n = self.count
        prices_list = list(self.prices)
        
        # Calculate sums for linear regression
        # x values are 0, 1, 2, ..., n-1 (bar indices)
        sum_x = n * (n - 1) / 2
        sum_x2 = (n - 1) * n * (2 * n - 1) / 6
        sum_y = sum(prices_list)
        sum_xy = sum(i * prices_list[i] for i in range(n))
        
        # Calculate slope and intercept using least squares
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return False
            
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate the regression value at the current bar (x = n-1)
        regression_value = slope * (n - 1) + intercept
        self.Value = regression_value
        
        # Calculate standard deviation of residuals
        residuals = []
        for i in range(n):
            predicted = slope * i + intercept
            residual = prices_list[i] - predicted
            residuals.append(residual)
        
        # Use sample standard deviation (N-1 denominator) to match TradingView
        mean_residual = sum(residuals) / n
        variance = sum((r - mean_residual) ** 2 for r in residuals) / (n - 1) if n > 1 else 0
        std_dev = math.sqrt(variance) if variance > 0 else 0
        
        # Calculate upper and lower bands
        self.UpperBand = regression_value + self.upper_deviation * std_dev
        self.LowerBand = regression_value - self.lower_deviation * std_dev
        
        return True


class TrendQualityIndicator(PythonIndicator):
    """
    Trend-Quality Indicator
    
    Measures trend strength by comparing smoothed price change to noise.
    High positive values = strong uptrend
    High negative values = strong downtrend
    Values near zero = ranging/choppy market
    """
    
    def __init__(self, symbol, fast_length, slow_length, trend_length, 
                 noise_length, correction_factor, noise_type):
        self.Name = "TrendQuality"
        self.Value = 0
        self.symbol = symbol

        self.ema_fast = ExponentialMovingAverage(fast_length)
        self.ema_slow = ExponentialMovingAverage(slow_length)

        self.trend_length = trend_length
        self.noise_length = noise_length
        self.correction_factor = correction_factor
        self.noise_type = noise_type.upper()
        self.smf = 2.0 / (1.0 + trend_length)

        self.cpc = 0
        self.trend = 0
        self.prev_close = None
        self.prev_reversal = None
        self.diff_history = deque(maxlen=noise_length)

    def Update(self, input):
        close = input.Close
        self.ema_fast.Update(input)
        self.ema_slow.Update(input)

        if not (self.ema_fast.IsReady and self.ema_slow.IsReady):
            self.prev_close = close
            return False

        reversal = 1 if self.ema_fast.Current.Value > self.ema_slow.Current.Value else \
                  (-1 if self.ema_fast.Current.Value < self.ema_slow.Current.Value else 0)

        if self.prev_close is not None:
            if self.prev_reversal is None or self.prev_reversal != reversal:
                self.cpc = 0
                self.trend = 0
            else:
                self.cpc += close - self.prev_close
                self.trend = self.trend * (1 - self.smf) + self.cpc * self.smf

        diff = abs(self.cpc - self.trend)
        self.diff_history.append(diff)

        if len(self.diff_history) == self.noise_length:
            if self.noise_type == "LINEAR":
                noise = self.correction_factor * sum(self.diff_history) / self.noise_length
            elif self.noise_type == "SQUARED":
                noise = self.correction_factor * (sum(d * d for d in self.diff_history) / self.noise_length) ** 0.5
            else:
                raise ValueError("noise_type must be 'LINEAR' or 'SQUARED'")
            self.Value = self.trend / noise if noise != 0 else 0
            self.prev_close = close
            self.prev_reversal = reversal
            return True

        self.prev_close = close
        self.prev_reversal = reversal
        return False
