"""
Trend Following Strategy – Breakout + Momentum with SMA bands.
"""
import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class TrendFollowingStrategy(BaseStrategy):
    def __init__(self, lookback_bars=20, entry_threshold=1.5,
                 stop_multiplier=1.5, take_profit_multiplier=2.0,
                 max_trend_bars=10, min_trend_bars=3, atr_period=14):
        super().__init__(
            lookback_bars=lookback_bars,
            entry_threshold=entry_threshold,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier,
            max_trend_bars=max_trend_bars,
            min_trend_bars=min_trend_bars,
            atr_period=atr_period
        )
        self._indicators = None
        self._full_df = None

    def precompute_indicators(self, df):
        """Pre-compute all indicators once."""
        p = self.params
        lookback = p['lookback_bars']
        entry_threshold = p['entry_threshold']
        atr_period = p['atr_period']
        min_trend_bars = p['min_trend_bars']

        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values

        # ATR
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = np.zeros(len(df))
        if len(tr) >= atr_period:
            atr_series = pd.Series(tr).rolling(atr_period).mean()
            atr[atr_period:] = atr_series.values[atr_period-1:]
        else:
            atr = np.full(len(df), np.mean(tr) if len(tr) > 0 else 0)

        # SMA and bands
        sma = pd.Series(close).rolling(lookback).mean().values
        std = pd.Series(close).rolling(lookback).std().values
        upper_band = sma + entry_threshold * std
        lower_band = sma - entry_threshold * std

        # Momentum
        momentum = close / np.roll(close, min_trend_bars) - 1

        return {
            'atr': atr,
            'sma': sma,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'momentum': momentum,
            'close': close,
            'high': high,
            'low': low,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        """Generate signal using pre-computed indicators."""
        p = self.params
        lookback = p['lookback_bars']
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']

        if idx < lookback + 10:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        atr = indicators['atr']
        sma = indicators['sma']
        upper_band = indicators['upper_band']
        momentum = indicators['momentum']

        close_price = close[idx]
        atr_val = atr[idx]
        sma_val = sma[idx]
        upper = upper_band[idx]
        mom = momentum[idx]

        # Buy Signal: Price breaks above upper band with positive momentum
        if close_price > upper and mom > 0.001:
            sl = close_price - stop_multiplier * atr_val
            tp = close_price + tp_multiplier * atr_val
            return {
                'action': 'BUY',
                'entry': close_price,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 70,
                'reason': f'Breakout above upper band, momentum {mom:.3f}'
            }

        # Sell (close long) signal: Price drops below SMA or momentum turns negative
        if close_price < sma_val or mom < -0.0005:
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': 'Trend exhausted'
            }

        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        """Legacy method for incremental backtesting."""
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)