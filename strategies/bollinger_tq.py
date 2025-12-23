"""
Bollinger Bands + Trend-Quality Strategy for QuantConnect

A regime-adaptive strategy combining Bollinger Bands channel triggers
with Trend-Quality indicator for dynamic mean-reversion/breakout switching.

Author: Anonymous
License: MIT
"""

from AlgorithmImports import *
from datetime import timedelta
from collections import deque
import math


class BollingerTQStrategy(QCAlgorithm):
    """
    Regime-adaptive strategy using Bollinger Bands + Trend-Quality.
    
    Entry Logic:
    - Price > Upper BB + Weak TQ → Short (mean reversion)
    - Price < Lower BB + Weak TQ → Long (mean reversion)
    - Price > Upper BB + Strong TQ → Long (breakout)
    - Price < Lower BB + Strong TQ → Short (breakout)
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
        # Bollinger Bands
        self.bb_length = int(self.GetParameter("bb_length", 20))
        self.bb_mult = float(self.GetParameter("bb_mult", 2))
        
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
        # Custom Bollinger Bands with sample standard deviation
        self.bb_sma = SimpleMovingAverage(self.bb_length)
        self.bb_std = CustomStandardDeviation(self.bb_length)
        self.RegisterIndicator(self.symbol, self.bb_sma, self.consolidator)
        self.RegisterIndicator(self.symbol, self.bb_std, self.consolidator)

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
        
        if not (self.bb_sma.IsReady and self.bb_std.IsReady and self.tq.IsReady):
            return

        close = bar.Close
        upper = self.bb_sma.Current.Value + self.bb_mult * self.bb_std.Current.Value
        lower = self.bb_sma.Current.Value - self.bb_mult * self.bb_std.Current.Value
        indicator_q = self.tq.Current.Value

        # === REVERSION ENTRIES ===
        # Short when price > upper band and trend is weak
        if self.buy_reversion and close > upper and indicator_q < self.high_threshold:
            if self.reversion_short_orders < self.max_orders:
                ticket = self.MarketOrder(
                    self.symbol, 
                    -self.CalculateOrderQuantity(self.symbol, -0.5), 
                    tag="Buy Reversion"
                )
                self.reversion_short_shares += abs(ticket.Quantity)
                self.reversion_short_orders += 1

        # Long when price < lower band and trend is weak
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
        # Long breakout when price > upper band and trend is strong
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

        # Short breakout when price < lower band and trend is strong
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


class CustomStandardDeviation(PythonIndicator):
    """
    Sample Standard Deviation indicator.
    Uses N-1 denominator to match TradingView's stdev() function.
    """
    
    def __init__(self, period):
        self.Name = "CustomStandardDeviation"
        self.Value = 0
        self.period = period
        self.values = deque(maxlen=period)

    def Update(self, input):
        close = input.Close
        self.values.append(close)

        if len(self.values) == self.period:
            mean = sum(self.values) / self.period
            variance = sum((x - mean) ** 2 for x in self.values) / (self.period - 1)
            self.Value = math.sqrt(variance) if variance > 0 else 0
            return True

        return False
