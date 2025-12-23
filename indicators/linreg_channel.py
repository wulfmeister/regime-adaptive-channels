"""
Linear Regression Channel Indicator (Standalone)

Calculates a linear regression line over the lookback period with
upper and lower bands based on standard deviation of residuals.

Matches TradingView's Linear Regression indicator implementation.

Usage:
    from indicators.linreg_channel import LinearRegressionChannel
    
    linreg = LinearRegressionChannel(count=22, upper_deviation=2.0, lower_deviation=2.0)
    self.RegisterIndicator(symbol, linreg, consolidator)
    
    # In your handler:
    if linreg.IsReady:
        center = linreg.Value  # Regression line value
        upper = linreg.UpperBand
        lower = linreg.LowerBand

Author: Anonymous
License: MIT
"""

from AlgorithmImports import *
from collections import deque
import math


class LinearRegressionChannel(PythonIndicator):
    """
    Linear Regression Channel Indicator
    
    Concept:
    The center line is the linear regression value at the current bar.
    Upper and lower bands are X standard deviations away from the regression line,
    where standard deviation is calculated from the residuals (actual - predicted).
    
    This differs from Bollinger Bands which use moving average ± price std dev.
    Linear regression captures trend direction, making bands more adaptive.
    
    Parameters:
    -----------
    count : int
        Number of bars for linear regression calculation (default: 20)
    upper_deviation : float
        Number of standard deviations for upper band (default: 2.0)
    lower_deviation : float
        Number of standard deviations for lower band (default: 2.0)
    """
    
    def __init__(self, count=20, upper_deviation=2.0, lower_deviation=2.0):
        self.Name = "LinearRegressionChannel"
        self.Value = 0  # Center line (regression value at current bar)
        self.UpperBand = 0
        self.LowerBand = 0
        self.Slope = 0  # Exposed for additional analysis
        self.Intercept = 0
        self.StdDev = 0  # Standard deviation of residuals
        
        self.count = count
        self.upper_deviation = upper_deviation
        self.lower_deviation = lower_deviation
        self.prices = deque(maxlen=count)
        
        # Warm-up period
        self.WarmUpPeriod = count
        
    @property
    def IsReady(self):
        """Indicator is ready when we have enough price history."""
        return len(self.prices) == self.count

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
        self.prices.append(close)

        if len(self.prices) < self.count:
            return False

        n = self.count
        prices_list = list(self.prices)
        
        # Calculate sums for linear regression
        # x values are 0, 1, 2, ..., n-1 (bar indices)
        # Using closed-form formulas for efficiency
        sum_x = n * (n - 1) / 2  # Sum of 0 to n-1: n(n-1)/2
        sum_x2 = (n - 1) * n * (2 * n - 1) / 6  # Sum of squares: (n-1)n(2n-1)/6
        sum_y = sum(prices_list)
        sum_xy = sum(i * prices_list[i] for i in range(n))
        
        # Calculate slope and intercept using least squares formula
        # y = slope * x + intercept
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return False
            
        self.Slope = (n * sum_xy - sum_x * sum_y) / denominator
        self.Intercept = (sum_y - self.Slope * sum_x) / n
        
        # Calculate the regression value at the current bar (x = n-1)
        regression_value = self.Slope * (n - 1) + self.Intercept
        self.Value = regression_value
        
        # Calculate residuals (actual - predicted) for each bar
        residuals = []
        for i in range(n):
            predicted = self.Slope * i + self.Intercept
            residual = prices_list[i] - predicted
            residuals.append(residual)
        
        # Calculate standard deviation of residuals
        # Using sample standard deviation (N-1 denominator) to match TradingView
        mean_residual = sum(residuals) / n
        variance = sum((r - mean_residual) ** 2 for r in residuals) / (n - 1) if n > 1 else 0
        self.StdDev = math.sqrt(variance) if variance > 0 else 0
        
        # Calculate upper and lower bands
        self.UpperBand = regression_value + self.upper_deviation * self.StdDev
        self.LowerBand = regression_value - self.lower_deviation * self.StdDev
        
        return True

    def Reset(self):
        """Reset the indicator to its initial state."""
        self.prices.clear()
        self.Value = 0
        self.UpperBand = 0
        self.LowerBand = 0
        self.Slope = 0
        self.Intercept = 0
        self.StdDev = 0
        

class LinearRegressionValue(PythonIndicator):
    """
    Simple Linear Regression Value indicator.
    
    Returns only the regression line value at the current bar,
    without the channel bands. Useful when you only need the
    trend line for analysis.
    
    Parameters:
    -----------
    period : int
        Number of bars for linear regression calculation
    """
    
    def __init__(self, period=20):
        self.Name = "LinearRegressionValue"
        self.Value = 0
        self.Slope = 0
        self.period = period
        self.prices = deque(maxlen=period)
        self.WarmUpPeriod = period
        
    @property
    def IsReady(self):
        return len(self.prices) == self.period

    def Update(self, input):
        close = input.Close
        self.prices.append(close)

        if len(self.prices) < self.period:
            return False

        n = self.period
        prices_list = list(self.prices)
        
        sum_x = n * (n - 1) / 2
        sum_x2 = (n - 1) * n * (2 * n - 1) / 6
        sum_y = sum(prices_list)
        sum_xy = sum(i * prices_list[i] for i in range(n))
        
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return False
            
        self.Slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - self.Slope * sum_x) / n
        
        self.Value = self.Slope * (n - 1) + intercept
        return True

    def Reset(self):
        self.prices.clear()
        self.Value = 0
        self.Slope = 0
