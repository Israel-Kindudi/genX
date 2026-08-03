"""
Scalping Strategy – Mean Reversion based on RSI and standard deviation bands.
"""
import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class ScalpingStrategy(BaseStrategy):
    def __init__(self, lookback_bars=10, entry_threshold=0.5,
                 stop_multiplier=0.8, take_profit_multiplier=1.0,
                 max_hold_bars=5, min_profit_bp=0.5, atr_period=14):
        super().__init__(
            lookback_bars=lookback_bars,
            entry_threshold=entry_threshold,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier,
            max_hold_bars=max_hold_bars,
            min_profit_bp=min_profit_bp,
            atr_period=atr_period
        )
        self._indicators = None
        self._full_df = None

    def precompute_indicators(self, df):
        """Pre-compute all indicators once."""
        p = self.params
        lookback = p['lookback_bars']
        atr_period = p['atr_period']

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

        # Rolling mean and std
        mean = pd.Series(close).rolling(lookback).mean().values
        std = pd.Series(close).rolling(lookback).std().values

        # RSI
        returns = np.diff(close)
        returns = np.append([0], returns)
        gain = np.where(returns > 0, returns, 0)
        loss = np.where(returns < 0, -returns, 0)
        avg_gain = pd.Series(gain).rolling(14).mean().values
        avg_loss = pd.Series(loss).rolling(14).mean().values
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))

        return {
            'atr': atr,
            'mean': mean,
            'std': std,
            'rsi': rsi,
            'close': close,
            'low': low,
            'high': high,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        """Generate signal using pre-computed indicators."""
        p = self.params
        lookback = p['lookback_bars']
        entry_threshold = p['entry_threshold']
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']
        min_profit_bp = p['min_profit_bp']

        if idx < max(lookback, 14) + 10:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        atr = indicators['atr']
        mean = indicators['mean']
        std = indicators['std']
        rsi = indicators['rsi']

        close_price = close[idx]
        atr_val = atr[idx]
        mean_val = mean[idx]
        std_val = std[idx]
        rsi_val = rsi[idx]

        # Buy signal
        if close_price <= mean_val - entry_threshold * std_val and rsi_val < 35:
            entry = close_price
            sl = entry - stop_multiplier * atr_val
            tp = entry + tp_multiplier * atr_val

            profit_bp = (tp - entry) / entry * 10000
            if profit_bp < min_profit_bp:
                tp = entry + (min_profit_bp / 10000) * entry

            return {
                'action': 'BUY',
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': min(85, 60 + (35 - rsi_val) / 35 * 25),
                'reason': f'Buy at lower band (RSI: {rsi_val:.1f})'
            }

        # Sell signal
        elif close_price >= mean_val + entry_threshold * std_val and rsi_val > 65:
            entry = close_price
            sl = entry + stop_multiplier * atr_val
            tp = entry - tp_multiplier * atr_val

            profit_bp = (entry - tp) / entry * 10000
            if profit_bp < min_profit_bp:
                tp = entry - (min_profit_bp / 10000) * entry

            return {
                'action': 'SELL',
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': min(85, 60 + (rsi_val - 65) / 35 * 25),
                'reason': f'Sell at upper band (RSI: {rsi_val:.1f})'
            }

        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        """Legacy method for incremental backtesting."""
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)