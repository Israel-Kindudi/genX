"""
Scalping Strategy #9: VWAP Bands + Stochastic RSI

Required Indicators:
- VWAP with band multiplier = 1.5
- 500 SMA
- Stochastic RSI (Stoch RSI)

Entry Conditions:
- Price is above 500 SMA
- Candles touching or below lower VWAP band
- Stoch RSI crosses above 30 from oversold (<30)
- Stop loss under low of entry candle

Exit Conditions:
- Stoch RSI crosses down below 70 from overbought (>70)
- OR price touches top VWAP band
"""

import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class ScalpingStrategyVWAP_StochRSI(BaseStrategy):
    def __init__(self,
                 vwap_band_multiplier=1.5,
                 sma_period=500,
                 stoch_rsi_period=14,
                 stoch_rsi_k=3,
                 stoch_rsi_d=3,
                 atr_period=14,
                 stop_multiplier=1.5,
                 take_profit_multiplier=2.0):
        super().__init__(
            vwap_band_multiplier=vwap_band_multiplier,
            sma_period=sma_period,
            stoch_rsi_period=stoch_rsi_period,
            stoch_rsi_k=stoch_rsi_k,
            stoch_rsi_d=stoch_rsi_d,
            atr_period=atr_period,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier
        )
        self._indicators = None
        self._full_df = None

    def precompute_indicators(self, df):
        """Pre-compute VWAP bands, SMA, and Stochastic RSI."""
        p = self.params
        vwap_mult = p['vwap_band_multiplier']
        sma_period = p['sma_period']
        stoch_rsi_period = p['stoch_rsi_period']
        stoch_rsi_k = p['stoch_rsi_k']
        stoch_rsi_d = p['stoch_rsi_d']
        atr_period = p['atr_period']

        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        volume = df['Volume'].values
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

        # --- 500 SMA ---
        sma_500 = pd.Series(close).rolling(sma_period).mean().values

        # --- VWAP (Volume Weighted Average Price) ---
        # Typical VWAP = cumulative(Typical Price * Volume) / cumulative(Volume)
        typical_price = (high + low + close) / 3.0
        cum_vol = np.cumsum(volume)
        cum_tp_vol = np.cumsum(typical_price * volume)
        vwap = cum_tp_vol / (cum_vol + 1e-10)

        # VWAP bands: VWAP ± (multiplier * standard deviation of deviations)
        # We'll compute rolling std of (typical_price - vwap)
        deviation = typical_price - vwap
        # For simplicity, we can compute std of deviation over the period (or use rolling)
        # Use rolling std of deviation with period = len(df) or a large window
        # For band calculation, use a rolling window of 20 or so, or the whole dataset.
        # We'll use the entire available history for simplicity:
        # But we need it to be a rolling value to avoid look-ahead bias.
        # Use a rolling std of deviation with window = sma_period or 100.
        band_window = min(100, n)
        dev_std = pd.Series(deviation).rolling(band_window).std().values
        vwap_upper = vwap + vwap_mult * dev_std
        vwap_lower = vwap - vwap_mult * dev_std

        # --- Stochastic RSI ---
        # 1. Compute RSI
        delta = pd.Series(close).diff()
        gain = (delta.where(delta > 0, 0)).rolling(stoch_rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(stoch_rsi_period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        rsi_vals = rsi.values

        # 2. Stochastic of RSI
        # Need rolling min/max of RSI over the lookback period (same as stoch_rsi_period)
        rsi_min = pd.Series(rsi_vals).rolling(stoch_rsi_period).min().values
        rsi_max = pd.Series(rsi_vals).rolling(stoch_rsi_period).max().values
        stoch_rsi_raw = 100 * (rsi_vals - rsi_min) / (rsi_max - rsi_min + 1e-10)

        # 3. Smooth %K and %D
        stoch_rsi_k = pd.Series(stoch_rsi_raw).rolling(stoch_rsi_k).mean().values
        stoch_rsi_d = pd.Series(stoch_rsi_k).rolling(stoch_rsi_d).mean().values

        return {
            'atr': atr,
            'sma_500': sma_500,
            'vwap': vwap,
            'vwap_upper': vwap_upper,
            'vwap_lower': vwap_lower,
            'stoch_rsi_k': stoch_rsi_k,
            'stoch_rsi_d': stoch_rsi_d,
            'close': close,
            'low': low,
            'high': high,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        p = self.params
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']

        if idx < max(p['sma_period'], p['stoch_rsi_period'], p['stoch_rsi_k'], p['stoch_rsi_d']) + 10:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        low = indicators['low']
        high = indicators['high']
        atr = indicators['atr']
        sma_500 = indicators['sma_500']
        vwap_lower = indicators['vwap_lower']
        vwap_upper = indicators['vwap_upper']
        stoch_rsi_k = indicators['stoch_rsi_k']
        stoch_rsi_d = indicators['stoch_rsi_d']

        close_price = close[idx]
        low_entry = low[idx]
        high_entry = high[idx]
        atr_val = atr[idx]
        sma_val = sma_500[idx]
        vwap_lower_val = vwap_lower[idx]
        vwap_upper_val = vwap_upper[idx]
        stoch_k_val = stoch_rsi_k[idx]
        stoch_d_val = stoch_rsi_d[idx]

        if idx > 0:
            prev_stoch_k = stoch_rsi_k[idx-1]
            prev_stoch_d = stoch_rsi_d[idx-1]
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No previous data'}

        if np.isnan(sma_val) or np.isnan(vwap_lower_val) or np.isnan(stoch_k_val):
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'NaN indicator'}

        # --- Entry Conditions ---
        # 1. Price above 500 SMA
        price_above_sma = close_price > sma_val

        # 2. Candles touching or below lower VWAP band
        # Check if low touches/breaks below vwap_lower, but we want to be near or below it.
        # We'll use: low <= vwap_lower_val (candle touches or goes below)
        touch_lower_band = low_entry <= vwap_lower_val

        # 3. Stochastic RSI crossing above 30 from oversold
        # Oversold: stoch_k < 30, and we want crossover (prev <= 30 and current > 30)
        stoch_buy = (prev_stoch_k <= 30 and stoch_k_val > 30) or (stoch_k_val > 30 and stoch_d_val > 30 and prev_stoch_k < 30)
        # Simpler: Stoch K crosses above 30
        stoch_cross_above_30 = (prev_stoch_k <= 30 and stoch_k_val > 30)

        if price_above_sma and touch_lower_band and stoch_cross_above_30:
            entry = close_price
            sl = low_entry - stop_multiplier * atr_val
            tp = close_price + tp_multiplier * atr_val
            return {
                'action': 'BUY',
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 70,
                'reason': f'VWAP lower band touch, StochRSI cross >30'
            }

        # --- Exit Conditions ---
        # 1. StochRSI crosses down below 70 from overbought (>70)
        stoch_sell = (prev_stoch_k >= 70 and stoch_k_val < 70) or (stoch_k_val < 70 and stoch_d_val < 70 and prev_stoch_k > 70)
        # 2. Price touches top VWAP band
        touch_upper_band = high_entry >= vwap_upper_val

        if stoch_sell or touch_upper_band:
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': 'StochRSI cross below 70 or VWAP upper band touch'
            }

        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)