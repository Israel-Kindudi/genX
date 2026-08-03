"""
Trend Following Strategy using ADX (Average Directional Index)
"""
import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class TrendFollowingADX(BaseStrategy):
    def __init__(self, adx_period=14, ma_fast=10, ma_slow=30, atr_period=14,
                 stop_multiplier=1.5, take_profit_multiplier=2.5):
        super().__init__(
            adx_period=adx_period,
            ma_fast=ma_fast,
            ma_slow=ma_slow,
            atr_period=atr_period,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier
        )
        self._indicators = None
        self._full_df = None

    def precompute_indicators(self, df):
        """Pre-compute all indicators once with proper array alignment."""
        p = self.params
        adx_period = p['adx_period']
        ma_fast = p['ma_fast']
        ma_slow = p['ma_slow']
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
        
        # Pad TR to match length
        tr_padded = np.zeros(n)
        tr_padded[1:] = tr
        
        atr = np.zeros(n)
        if len(tr) >= atr_period:
            atr_series = pd.Series(tr).rolling(atr_period).mean()
            atr[atr_period:] = atr_series.values[atr_period-1:]
        else:
            atr = np.full(n, np.mean(tr) if len(tr) > 0 else 0)

        # --- Directional Movement ---
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)
        for i in range(1, n):
            up = high[i] - high[i-1]
            down = low[i-1] - low[i]
            if up > down and up > 0:
                plus_dm[i] = up
            elif down > up and down > 0:
                minus_dm[i] = down

        # --- Smooth with rolling ---
        tr_smooth = pd.Series(tr_padded).rolling(adx_period).mean().values
        plus_smooth = pd.Series(plus_dm).rolling(adx_period).mean().values
        minus_smooth = pd.Series(minus_dm).rolling(adx_period).mean().values

        # --- ADX ---
        # Handle division by zero
        denom = tr_smooth + 1e-10
        plus_di = 100 * plus_smooth / denom
        minus_di = 100 * minus_smooth / denom
        
        # DX
        di_sum = plus_di + minus_di + 1e-10
        dx = 100 * np.abs(plus_di - minus_di) / di_sum
        
        # ADX is the smoothed DX
        adx = pd.Series(dx).rolling(adx_period).mean().values

        # --- Moving averages ---
        ma_fast_vals = pd.Series(close).rolling(ma_fast).mean().values
        ma_slow_vals = pd.Series(close).rolling(ma_slow).mean().values

        return {
            'atr': atr,
            'adx': adx,
            'ma_fast': ma_fast_vals,
            'ma_slow': ma_slow_vals,
            'close': close,
            'high': high,
            'low': low,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        """Generate signal using pre-computed indicators."""
        p = self.params
        adx_period = p['adx_period']
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']

        if idx < max(adx_period, p['ma_slow']) + 10:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        atr = indicators['atr']
        adx = indicators['adx']
        ma_fast = indicators['ma_fast']
        ma_slow = indicators['ma_slow']

        close_price = close[idx]
        atr_val = atr[idx]
        adx_val = adx[idx]
        ma_f = ma_fast[idx]
        ma_s = ma_slow[idx]

        if idx > 0:
            prev_ma_f = ma_fast[idx-1]
            prev_ma_s = ma_slow[idx-1]
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No previous data'}

        if np.isnan(adx_val) or np.isnan(ma_f) or np.isnan(ma_s):
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'NaN indicator'}

        # Buy Signal: ADX > 25 and fast MA crosses above slow MA
        if adx_val > 25 and ma_f > ma_s and prev_ma_f <= prev_ma_s:
            sl = close_price - stop_multiplier * atr_val
            tp = close_price + tp_multiplier * atr_val
            return {
                'action': 'BUY',
                'entry': close_price,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 75,
                'reason': f'ADX {adx_val:.1f} > 25, MA crossover'
            }

        # Sell (close long): ADX drops below 20 or fast MA crosses below slow MA
        if adx_val < 20 or (ma_f < ma_s and prev_ma_f >= prev_ma_s):
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': 'ADX weak or MA cross down'
            }

        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        """Legacy method for incremental backtesting."""
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)