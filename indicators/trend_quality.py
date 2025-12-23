"""
Trend-Quality Indicator (Standalone)

Measures trend strength by comparing smoothed price change to noise.
Can be used independently in any QuantConnect algorithm.

Usage:
    from indicators.trend_quality import TrendQualityIndicator
    
    tq = TrendQualityIndicator(
        symbol, 
        fast_length=7, 
        slow_length=13, 
        trend_length=4, 
        noise_length=250,
        correction_factor=2.0, 
        noise_type="LINEAR"
    )
    self.RegisterIndicator(symbol, tq, consolidator)
    
    # In your handler:
    if tq.IsReady:
        trend_quality = tq.Current.Value
        # High positive = strong uptrend
        # High negative = strong downtrend
        # Near zero = ranging

Author: Anonymous
License: MIT
"""

from AlgorithmImports import *
from collections import deque


class TrendQualityIndicator(PythonIndicator):
    """
    Trend-Quality (TQ) Indicator
    
    Concept:
    TQ = Smoothed_Cumulative_Price_Change / Average_Noise
    
    High positive values = strong, clean uptrend
    High negative values = strong, clean downtrend
    Values near zero = choppy, ranging market
    
    Parameters:
    -----------
    symbol : Symbol
        The symbol this indicator is for
    fast_length : int
        Period for fast EMA (default: 7)
    slow_length : int
        Period for slow EMA (default: 13)
    trend_length : int
        Smoothing factor for trend calculation (default: 4)
    noise_length : int
        Lookback period for noise calculation (default: 250)
    correction_factor : float
        Multiplier for noise scaling (default: 2.0)
    noise_type : str
        "LINEAR" for mean absolute deviation, "SQUARED" for RMS
    """
    
    def __init__(self, symbol, fast_length=7, slow_length=13, trend_length=4, 
                 noise_length=250, correction_factor=2.0, noise_type="LINEAR"):
        self.Name = "TrendQuality"
        self.Value = 0
        self.symbol = symbol

        # EMA indicators for crossover detection
        self.ema_fast = ExponentialMovingAverage(fast_length)
        self.ema_slow = ExponentialMovingAverage(slow_length)

        # TQ parameters
        self.trend_length = trend_length
        self.noise_length = noise_length
        self.correction_factor = correction_factor
        self.noise_type = noise_type.upper()
        
        # Smoothing factor: standard EMA formula
        self.smf = 2.0 / (1.0 + trend_length)

        # State variables
        self.cpc = 0  # Cumulative price change
        self.trend = 0  # Smoothed trend
        self.prev_close = None
        self.prev_reversal = None
        self.diff_history = deque(maxlen=noise_length)
        
        # Warm-up period
        self.WarmUpPeriod = max(fast_length, slow_length) + noise_length

    @property
    def IsReady(self):
        """Indicator is ready when we have enough data for noise calculation."""
        return len(self.diff_history) == self.noise_length

    def Update(self, input):
        """
        Update the indicator with new data.
        
        Parameters:
        -----------
        input : TradeBar or QuoteBar
            Price data with Close property
            
        Returns:
        --------
        bool
            True if indicator is ready, False otherwise
        """
        close = input.Close
        
        # Update EMAs
        self.ema_fast.Update(input)
        self.ema_slow.Update(input)

        # Need both EMAs ready before calculating
        if not (self.ema_fast.IsReady and self.ema_slow.IsReady):
            self.prev_close = close
            return False

        # Determine trend direction based on EMA crossover
        # 1 = bullish (fast > slow), -1 = bearish (fast < slow), 0 = equal
        reversal = 1 if self.ema_fast.Current.Value > self.ema_slow.Current.Value else \
                  (-1 if self.ema_fast.Current.Value < self.ema_slow.Current.Value else 0)

        # Update cumulative price change and trend
        if self.prev_close is not None:
            # Reset on reversal (EMA crossover)
            if self.prev_reversal is None or self.prev_reversal != reversal:
                self.cpc = 0
                self.trend = 0
            else:
                # Accumulate price change
                self.cpc += close - self.prev_close
                # Smooth the cumulative change
                self.trend = self.trend * (1 - self.smf) + self.cpc * self.smf

        # Calculate deviation from trend (for noise)
        diff = abs(self.cpc - self.trend)
        self.diff_history.append(diff)

        # Calculate TQ when we have enough history
        if len(self.diff_history) == self.noise_length:
            if self.noise_type == "LINEAR":
                # Mean absolute deviation
                noise = self.correction_factor * sum(self.diff_history) / self.noise_length
            elif self.noise_type == "SQUARED":
                # Root mean square deviation
                noise = self.correction_factor * (sum(d * d for d in self.diff_history) / self.noise_length) ** 0.5
            else:
                raise ValueError("noise_type must be 'LINEAR' or 'SQUARED'")
            
            # Final TQ value: trend strength relative to noise
            self.Value = self.trend / noise if noise != 0 else 0
            
            self.prev_close = close
            self.prev_reversal = reversal
            return True

        self.prev_close = close
        self.prev_reversal = reversal
        return False

    def Reset(self):
        """Reset the indicator to its initial state."""
        self.cpc = 0
        self.trend = 0
        self.prev_close = None
        self.prev_reversal = None
        self.diff_history.clear()
        self.ema_fast.Reset()
        self.ema_slow.Reset()
        self.Value = 0
