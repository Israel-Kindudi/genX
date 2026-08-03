"""
Scalping Strategy #5: Hull Moving Average (HMA) + Stochastic

Buy Conditions:
- Stochastic %K crosses above %D and both are below 50 (oversold)
- Candle closes above HMA

Sell Conditions:
- Candle closes below HMA
"""

import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class ScalpingStrategyHMA_Stoch(BaseStrategy):
    def __init__(self,
                 hma_period=30,
                 stoch_k=14,
                 stoch_d=3,
                 stoch_smooth=6,
                 atr_period=14,
                 stop_multiplier=1.5,
                 take_profit_multiplier=2.0):
        super().__init__(
            hma_period=hma_period,
            stoch_k=stoch_k,
            stoch_d=stoch_d,
            stoch_smooth=stoch_smooth,
            atr_period=atr_period,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier
        )
        self._indicators = None
        self._full_df = None

    def _hull_moving_average(self, close, period):
        """Compute Hull Moving Average."""
        half_period = int(period / 2)
        sqrt_period = int(np.sqrt(period))
        
        # WMA(price, n/2) and WMA(price, n)
        wma_half = pd.Series(close).rolling(half_period).apply(
            lambda x: np.sum(x * np.arange(1, len(x)+1)) / (len(x)*(len(x)+1)/2),
            raw=True
        ).values
        wma_full = pd.Series(close).rolling(period).apply(
            lambda x: np.sum(x * np.arange(1, len(x)+1)) / (len(x)*(len(x)+1)/2),
            raw=True
        ).values
        
        # 2 * WMA(price, n/2) - WMA(price, n)
        raw_hma = 2 * wma_half - wma_full
        
        # WMA(raw_hma, sqrt(n))
        hma = pd.Series(raw_hma).rolling(sqrt_period).apply(
            lambda x: np.sum(x * np.arange(1, len(x)+1)) / (len(x)*(len(x)+1)/2),
            raw=True
        ).values
        return hma

    def precompute_indicators(self, df):
        """Pre-compute HMA and Stochastic."""
        p = self.params
        hma_period = p['hma_period']
        stoch_k = p['stoch_k']
        stoch_d = p['stoch_d']
        stoch_smooth = p['stoch_smooth']
        atr_period = p['atr_period']

        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        n = len(df)

        # --- ATR ---
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = np.zeros(n)
        if n > atr_period:
            atr_series = pd.Series(tr).rolling(atr_period).mean()
            atr[atr_period:] = atr_series.values[atr_period-1:]
        else:
            atr = np.full(n, np.mean(tr) if len(tr) > 0 else 0)

        # --- Hull Moving Average ---
        hma = self._hull_moving_average(close, hma_period)

        # --- Stochastic ---
        # Rolling high/low
        high_roll = pd.Series(high).rolling(stoch_k).max().values
        low_roll = pd.Series(low).rolling(stoch_k).min().values
        
        # %K raw
        k_raw = 100 * (close - low_roll) / (high_roll - low_roll + 1e-10)
        
        # %K smoothed (SMA of %K)
        k_smooth = pd.Series(k_raw).rolling(stoch_smooth).mean().values
        
        # %D (SMA of smoothed %K)
        d_smooth = pd.Series(k_smooth).rolling(stoch_d).mean().values

        return {
            'atr': atr,
            'hma': hma,
            'k_raw': k_raw,
            'k_smooth': k_smooth,
            'd_smooth': d_smooth,
            'close': close,
            'low': low,
            'high': high,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        p = self.params
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']

        if idx < max(p['hma_period'], p['stoch_k'], p['stoch_smooth'], p['stoch_d']) + 10:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        low = indicators['low']
        atr = indicators['atr']
        hma = indicators['hma']
        k_smooth = indicators['k_smooth']
        d_smooth = indicators['d_smooth']

        close_price = close[idx]
        low_entry = low[idx]
        atr_val = atr[idx]
        hma_val = hma[idx]
        k_val = k_smooth[idx]
        d_val = d_smooth[idx]

        if idx > 0:
            prev_close = close[idx-1]
            prev_hma = hma[idx-1]
            prev_k = k_smooth[idx-1]
            prev_d = d_smooth[idx-1]
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No previous data'}

        if np.isnan(hma_val) or np.isnan(k_val) or np.isnan(d_val):
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'NaN indicator'}

        # --- Buy Condition ---
        # Stochastic crossed up (K crosses above D) and both below 50
        stoch_buy = (prev_k <= prev_d and k_val > d_val) and (k_val < 50 and d_val < 50)
        # Candle closes above HMA (and previous close was below or at HMA for crossover)
        hma_buy = close_price > hma_val and prev_close <= prev_hma

        if stoch_buy and hma_buy:
            entry = close_price
            sl = low_entry - stop_multiplier * atr_val
            tp = close_price + tp_multiplier * atr_val
            return {
                'action': 'BUY',
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 70,
                'reason': f'Stoch cross up <50 & close above HMA'
            }

        # --- Sell Condition (close long) ---
        # Candle closes below HMA (or previous close was above and now below)
        hma_sell = close_price < hma_val and prev_close >= prev_hma

        if hma_sell:
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': 'Close below HMA'
            }

        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)