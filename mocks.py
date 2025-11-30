import logging
import numpy as np
import pandas as pd

# Mock Data Structures
class Bar:
    def __init__(self, close, timestamp=None):
        self.close = close
        self.timestamp = timestamp

class QuoteTick:
    def __init__(self, bid, ask, timestamp=None):
        self.bid = bid
        self.ask = ask
        self.timestamp = timestamp

# Mock Strategy Base Classes
class StrategyConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class Strategy:
    def __init__(self, config):
        self.config = config
        self.log = logging.getLogger("Strategy")
        self.log.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        if not self.log.handlers:
            self.log.addHandler(handler)

    def on_start(self):
        pass

    def on_stop(self):
        pass

# Mock Indicators
class Indicator:
    def __init__(self, period):
        self.period = period
        self.values = []
        self.value = 0.0
        self.is_initialized = False

    def update(self, value):
        self.values.append(value)
        if len(self.values) >= self.period:
            self.is_initialized = True
            self._calculate()

    def _calculate(self):
        pass

class ExponentialMovingAverage(Indicator):
    def _calculate(self):
        # Simple EMA calculation
        if len(self.values) < self.period:
            return
        # Use pandas for easy EMA
        series = pd.Series(self.values)
        self.value = series.ewm(span=self.period, adjust=False).mean().iloc[-1]

class RelativeStrengthIndex(Indicator):
    def _calculate(self):
        if len(self.values) < self.period + 1:
            return
        series = pd.Series(self.values)
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()
        rs = gain / loss
        self.value = 100 - (100 / (1 + rs.iloc[-1]))

class MovingAverageConvergenceDivergence:
    def __init__(self, fast=12, slow=26, signal=9):
        self.fast_period = fast
        self.slow_period = slow
        self.signal_period = signal
        self.values = []
        self.value = 0.0 # Histogram value usually, or tuple? Nautilus MACD usually exposes .value as the histogram or signal?
        # Let's assume .value is the histogram for simplicity in this mock
        self.is_initialized = False

    def update(self, value):
        self.values.append(value)
        if len(self.values) > self.slow_period + self.signal_period:
            self.is_initialized = True
            series = pd.Series(self.values)
            exp1 = series.ewm(span=self.fast_period, adjust=False).mean()
            exp2 = series.ewm(span=self.slow_period, adjust=False).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=self.signal_period, adjust=False).mean()
            self.value = (macd - signal).iloc[-1] # Histogram
