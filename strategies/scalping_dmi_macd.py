"""
Scalping Strategy #2: DMI Stochastic + MACD
"""
import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class ScalpingStrategyDMI_MACD(BaseStrategy):
    def __init__(self,
                 dmi_period=14,
                 stoch_k=14,
                 stoch_d=3,
                 macd_fast=12,
                 macd_slow=26,
                 macd_signal=9,
                 atr_period=14,
                 stop_multiplier=1.5,
                 take_profit_multiplier=2.0):
        super().__init__(
            dmi_period=dmi_period,
            stoch_k=stoch_k,
            stoch_d=stoch_d,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            atr_period=atr_period,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier
        )
        self._indicators = None
        self._full_df = None

    def precompute_indicators(self, df):
        """Pre-compute all indicators once with proper array alignment."""
        p = self.params
        dmi_period = p['dmi_period']
        stoch_k = p['stoch_k']
        stoch_d = p['stoch_d']
        macd_fast = p['macd_fast']
        macd_slow = p['macd_slow']
        macd_signal = p['macd_signal']
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
        tr_padded = np.concatenate([[0], tr])  # length n
        atr = np.zeros(n)
        if n > atr_period:
            atr_series = pd.Series(tr).rolling(atr_period).mean()
            atr[atr_period:] = atr_series.values[atr_period-1:]
        else:
            atr = np.full(n, np.mean(tr) if len(tr) > 0 else 0)

        # --- DMI ---
        plus_dm = np.zeros(n)
        minus_dm = np.zeros(n)
        for i in range(1, n):
            up = high[i] - high[i-1]
            down = low[i-1] - low[i]
            if up > down and up > 0:
                plus_dm[i] = up
            elif down > up and down > 0:
                minus_dm[i] = down

        # Smooth with rolling (min_periods=1 to avoid NaN)
        tr_smooth = pd.Series(tr_padded).rolling(dmi_period, min_periods=1).mean().values
        plus_smooth = pd.Series(plus_dm).rolling(dmi_period, min_periods=1).mean().values
        minus_smooth = pd.Series(minus_dm).rolling(dmi_period, min_periods=1).mean().values

        plus_di = 100 * plus_smooth / (tr_smooth + 1e-10)
        minus_di = 100 * minus_smooth / (tr_smooth + 1e-10)
        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        adx = pd.Series(dx).rolling(dmi_period, min_periods=1).mean().values

        # --- DMI Stochastic ---
        adx_stoch = np.zeros(n)
        for i in range(stoch_k, n):
            window = adx[i-stoch_k:i]
            if len(window) > 0 and np.max(window) > np.min(window):
                adx_stoch[i] = (adx[i] - np.min(window)) / (np.max(window) - np.min(window)) * 100

        stoch_d_vals = pd.Series(adx_stoch).rolling(stoch_d, min_periods=1).mean().values

        # --- MACD ---
        ema_fast = pd.Series(close).ewm(span=macd_fast, adjust=False).mean().values
        ema_slow = pd.Series(close).ewm(span=macd_slow, adjust=False).mean().values
        macd_line = ema_fast - ema_slow
        signal_line = pd.Series(macd_line).ewm(span=macd_signal, adjust=False).mean().values
        macd_hist = macd_line - signal_line

        return {
            'atr': atr,
            'adx_stoch': adx_stoch,
            'stoch_d': stoch_d_vals,
            'macd_hist': macd_hist,
            'close': close,
            'low': low,
            'high': high,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        p = self.params
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']

        if idx < max(p['dmi_period'], p['macd_slow']) + 10:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        low = indicators['low']
        atr = indicators['atr']
        adx_stoch = indicators['adx_stoch']
        stoch_d = indicators['stoch_d']
        macd_hist = indicators['macd_hist']

        close_price = close[idx]
        low_entry = low[idx]
        atr_val = atr[idx]
        macd_hist_val = macd_hist[idx]
        adx_stoch_val = adx_stoch[idx]
        stoch_d_val = stoch_d[idx]

        if idx > 0:
            prev_macd_hist = macd_hist[idx-1]
            prev_adx_stoch = adx_stoch[idx-1]
            prev_stoch_d = stoch_d[idx-1]
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No previous data'}

        if np.isnan(macd_hist_val) or np.isnan(adx_stoch_val) or np.isnan(stoch_d_val):
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'NaN indicator'}

        # Buy Signal
        macd_green = (macd_hist_val > 0 and prev_macd_hist <= 0) or (macd_hist_val > 0 and macd_hist_val > prev_macd_hist)
        dmi_stoch_buy = (adx_stoch_val < 30 and adx_stoch_val > prev_adx_stoch) or (stoch_d_val < 30 and stoch_d_val > prev_stoch_d)

        if macd_green and dmi_stoch_buy:
            entry = close_price
            sl = low_entry - stop_multiplier * atr_val
            tp = close_price + tp_multiplier * atr_val
            return {
                'action': 'BUY',
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 70,
                'reason': f'MACD green & DMI Stoch buy'
            }

        # Sell Signal (Close Long)
        macd_red = (macd_hist_val < 0 and prev_macd_hist >= 0) or (macd_hist_val < 0 and macd_hist_val < prev_macd_hist)
        if macd_red:
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': f'MACD red'
            }

        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)