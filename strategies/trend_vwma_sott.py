"""
Trend Strategy #1: VWMA Crossover + SOTT (Smoothed Optimal Trend Tracker)

Buy Conditions:
- SOTT crosses up under 50 (oversold) and produces buy signal
- Candles closing above 30 VWMA
- 8 VWMA crosses above 30 VWMA
- Stop loss under last swing low

Exit/Sell Conditions:
- Candle closes below 30 VWMA
- OR SOTT crosses down (sell signal)
"""

import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class TrendStrategyVWMA_SOTT(BaseStrategy):
    def __init__(self,
                 vwma_fast=8,
                 vwma_slow=30,
                 sott_k=100,          # %K Length for SOTT
                 sott_k_smooth=10,    # %K Smoothing for SOTT
                 sott_ott_period=2,   # OTT Period
                 sott_ott_percent=0.5, # OTT Percent
                 atr_period=14,
                 stop_multiplier=1.5,
                 take_profit_multiplier=2.5):
        super().__init__(
            vwma_fast=vwma_fast,
            vwma_slow=vwma_slow,
            sott_k=sott_k,
            sott_k_smooth=sott_k_smooth,
            sott_ott_period=sott_ott_period,
            sott_ott_percent=sott_ott_percent,
            atr_period=atr_period,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier
        )
        self._indicators = None
        self._full_df = None

    def _vwma(self, close, volume, period):
        """Volume Weighted Moving Average."""
        vwma = np.full(len(close), np.nan)
        for i in range(period, len(close)):
            price_sum = np.sum(close[i-period:i] * volume[i-period:i])
            vol_sum = np.sum(volume[i-period:i])
            if vol_sum > 0:
                vwma[i] = price_sum / vol_sum
        return vwma

    def _sott(self, close, k=100, k_smooth=10, ott_period=2, ott_percent=0.5):
        """
        Smoothed Optimal Trend Tracker (SOTT).
        Based on KivancOzbilgic's OTT indicator.
        """
        n = len(close)
        sott = np.full(n, np.nan)
        buy_signal = np.zeros(n, dtype=bool)
        sell_signal = np.zeros(n, dtype=bool)

        # Step 1: Calculate %K (Stochastic-like)
        # Rolling high/low for %K
        high_roll = pd.Series(close).rolling(k).max().values
        low_roll = pd.Series(close).rolling(k).min().values
        k_raw = 100 * (close - low_roll) / (high_roll - low_roll + 1e-10)

        # Step 2: Smooth %K
        k_smooth_arr = pd.Series(k_raw).rolling(k_smooth).mean().values

        # Step 3: OTT (Optimal Trend Tracker)
        # Calculate the "trend" value
        # Using EMA-like smoothing
        for i in range(k + k_smooth + ott_period, n):
            # Trend calculation: smoothed stochastic crossing
            # Determine if price is in uptrend or downtrend
            prev_sott = sott[i-1] if i > 0 else 0

            # Simple OTT logic based on smoothed stochastic
            # If k_smooth is above 50 and rising, uptrend
            if k_smooth_arr[i] > 50:
                # Potential buy signal
                if k_smooth_arr[i] > k_smooth_arr[i-1] and k_smooth_arr[i-1] <= 50:
                    buy_signal[i] = True
                    sott[i] = 1  # uptrend
                else:
                    sott[i] = 1 if prev_sott >= 0 else -1
            else:
                # Potential sell signal
                if k_smooth_arr[i] < k_smooth_arr[i-1] and k_smooth_arr[i-1] >= 50:
                    sell_signal[i] = True
                    sott[i] = -1  # downtrend
                else:
                    sott[i] = -1 if prev_sott <= 0 else 1

            # Apply OTT smoothing (optional)
            # We'll use the OTT percent to filter noise
            if ott_percent > 0:
                # Simple filter: don't flip too quickly
                if i > 1:
                    diff = sott[i] - sott[i-1]
                    if abs(diff) > 0 and abs(diff) * 100 > ott_percent:
                        # significant change, keep it
                        pass
                    else:
                        sott[i] = sott[i-1]  # smooth

        # After OTT, refine buy/sell signals
        for i in range(k + k_smooth + ott_period, n):
            if sott[i] == 1 and sott[i-1] <= 0:
                buy_signal[i] = True
            elif sott[i] == -1 and sott[i-1] >= 0:
                sell_signal[i] = True

        return {
            'sott': sott,
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'k_smooth': k_smooth_arr,
            'k_raw': k_raw,
        }

    def precompute_indicators(self, df):
        """Pre-compute VWMA and SOTT."""
        p = self.params
        vwma_fast = p['vwma_fast']
        vwma_slow = p['vwma_slow']
        sott_k = p['sott_k']
        sott_k_smooth = p['sott_k_smooth']
        sott_ott_period = p['sott_ott_period']
        sott_ott_percent = p['sott_ott_percent']
        atr_period = p['atr_period']

        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        volume = df['Volume'].values if 'Volume' in df.columns else np.ones(len(df))
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

        # --- VWMA ---
        vwma_fast_arr = self._vwma(close, volume, vwma_fast)
        vwma_slow_arr = self._vwma(close, volume, vwma_slow)

        # --- SOTT ---
        sott_data = self._sott(close, sott_k, sott_k_smooth, sott_ott_period, sott_ott_percent)

        return {
            'atr': atr,
            'vwma_fast': vwma_fast_arr,
            'vwma_slow': vwma_slow_arr,
            'sott': sott_data['sott'],
            'buy_signal': sott_data['buy_signal'],
            'sell_signal': sott_data['sell_signal'],
            'k_smooth': sott_data['k_smooth'],
            'close': close,
            'high': high,
            'low': low,
        }

    def _find_swing_low(self, df, idx, lookback=20):
        """Find the last swing low within lookback period."""
        low = df['Low'].values
        if idx < lookback:
            return low[idx]  # fallback
        # Find the lowest point in recent bars
        window = low[max(0, idx-lookback):idx+1]
        if len(window) > 0:
            return np.min(window)
        return low[idx]

    def generate_signal_with_indicators(self, df, indicators, idx):
        p = self.params
        vwma_slow = p['vwma_slow']
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']

        if idx < max(vwma_slow, p['sott_k']) + 20:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        low = indicators['low']
        atr = indicators['atr']
        vwma_fast_arr = indicators['vwma_fast']
        vwma_slow_arr = indicators['vwma_slow']
        sott = indicators['sott']
        buy_signal = indicators['buy_signal']
        sell_signal = indicators['sell_signal']
        k_smooth = indicators['k_smooth']

        close_price = close[idx]
        low_entry = low[idx]
        atr_val = atr[idx]
        vwma_slow_val = vwma_slow_arr[idx]
        vwma_fast_val = vwma_fast_arr[idx]
        sott_val = sott[idx]
        k_val = k_smooth[idx]

        if idx > 0:
            prev_k = k_smooth[idx-1]
            prev_close = close[idx-1]
            prev_vwma_slow = vwma_slow_arr[idx-1]
            prev_vwma_fast = vwma_fast_arr[idx-1]
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No previous data'}

        if np.isnan(vwma_slow_val) or np.isnan(vwma_fast_val) or np.isnan(sott_val):
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'NaN indicator'}

        # --- Buy Condition ---
        # 1. SOTT crosses up under 50 (buy signal) or SOTT > 0 and increasing
        sott_buy = buy_signal[idx] or (sott_val > 0 and sott_val > sott[idx-1] if idx > 0 else False)
        sott_under_50 = k_val < 50 and k_val > prev_k  # crossing up from under 50

        # 2. Candles closing above 30 VWMA
        price_above_vwma_slow = close_price > vwma_slow_val

        # 3. 8 VWMA crosses above 30 VWMA
        vwma_cross = prev_vwma_fast <= prev_vwma_slow and vwma_fast_val > vwma_slow_val

        if (sott_buy or sott_under_50) and price_above_vwma_slow and vwma_cross:
            # Find swing low for stop loss
            swing_low = self._find_swing_low(df, idx, lookback=20)
            entry = close_price
            sl = swing_low - 0.5 * atr_val  # slightly below swing low
            tp = close_price + tp_multiplier * atr_val

            return {
                'action': 'BUY',
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 75,
                'reason': f'SOTT cross up & VWMA cross (K: {k_val:.1f})'
            }

        # --- Exit/Sell Condition ---
        # 1. Candle closes below 30 VWMA
        close_below_vwma = close_price < vwma_slow_val and prev_close >= prev_vwma_slow

        # 2. SOTT crosses down (sell signal)
        sott_sell = sell_signal[idx] or (sott_val < 0 and sott_val < sott[idx-1] if idx > 0 else False)

        if close_below_vwma or sott_sell:
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': f'SOTT sell or close below VWMA'
            }

        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)