"""
Scalping Strategy #1: RSI + VWMA (Optimized - Pre-computed Indicators)
"""
import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class ScalpingStrategyRSI_VWMA(BaseStrategy):
    def __init__(self, rsi_period=9, vwma_period=20, sma_200=200, sma_12=12, atr_period=14):
        super().__init__(rsi_period=rsi_period, vwma_period=vwma_period,
                         sma_200=sma_200, sma_12=sma_12, atr_period=atr_period)
        self._indicators = None
        self._full_df = None

    def precompute_indicators(self, df):
        """Pre-compute all indicators once using vectorized operations."""
        p = self.params
        rsi_period = p['rsi_period']
        vwma_period = p['vwma_period']
        sma_200 = p['sma_200']
        sma_12 = p['sma_12']
        atr_period = p['atr_period']

        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values
        volume = df['Volume'].values if 'Volume' in df.columns else np.ones(len(df))

        # --- ATR (vectorized) ---
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

        # --- SMA 200 ---
        sma_200_arr = pd.Series(close).rolling(sma_200).mean().values

        # --- SMA 12 ---
        sma_12_arr = pd.Series(close).rolling(sma_12).mean().values

        # --- RSI (vectorized) ---
        delta = pd.Series(close).diff()
        gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
        rs = gain / loss
        rsi_vals = 100 - (100 / (1 + rs))
        rsi_vals = rsi_vals.values

        # --- VWMA of RSI (vectorized with numpy) ---
        vwma_rsi = np.full(len(df), np.nan)
        if len(df) >= vwma_period:
            vol_weights = volume[:len(df)]
            rsi_weighted = rsi_vals * vol_weights
            vol_sum = np.convolve(vol_weights, np.ones(vwma_period), mode='same')
            rsi_sum = np.convolve(rsi_weighted, np.ones(vwma_period), mode='same')
            for i in range(vwma_period-1, len(df)):
                if vol_sum[i] > 0:
                    vwma_rsi[i] = rsi_sum[i] / vol_sum[i]

        return {
            'atr': atr,
            'sma_200': sma_200_arr,
            'sma_12': sma_12_arr,
            'rsi': rsi_vals,
            'vwma_rsi': vwma_rsi,
            'close': close,
            'low': low,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        """Generate signal using pre-computed indicators."""
        p = self.params
        warmup = max(p['sma_200'], p['rsi_period'], p['vwma_period'], p['sma_12']) + 10

        if idx < warmup:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        # Ensure idx is within bounds
        if idx >= len(indicators['close']):
            idx = len(indicators['close']) - 1

        close = indicators['close']
        atr = indicators['atr']
        sma_200 = indicators['sma_200']
        sma_12 = indicators['sma_12']
        rsi = indicators['rsi']
        vwma_rsi = indicators['vwma_rsi']

        close_price = close[idx]
        atr_val = atr[idx]
        sma200_val = sma_200[idx]
        sma12_val = sma_12[idx]
        rsi_val = rsi[idx]
        vwma_val = vwma_rsi[idx]

        if idx > 0:
            prev_rsi = rsi[idx-1]
            prev_vwma = vwma_rsi[idx-1]
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No previous data'}

        if np.isnan(sma200_val) or np.isnan(rsi_val) or np.isnan(vwma_val) or np.isnan(sma12_val):
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'NaN indicator'}

        buy = (close_price > sma200_val and
               prev_rsi <= prev_vwma and rsi_val > vwma_val and
               close_price > sma12_val)

        sell = (close_price < sma12_val or
                (prev_rsi >= prev_vwma and rsi_val < vwma_val))

        if buy:
            sl = close_price - 1.0 * atr_val
            tp = close_price + 1.5 * atr_val
            return {
                'action': 'BUY',
                'entry': close_price,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 70,
                'reason': 'RSI cross above VWMA'
            }
        elif sell:
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': 'Sell condition'
            }
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        """
        Legacy method for incremental backtesting.
        Pre-computes indicators once on the full dataframe.
        """
        # If this is a new dataframe or we haven't computed indicators yet
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        
        # Get the current index (last bar)
        idx = len(df) - 1
        
        return self.generate_signal_with_indicators(df, self._indicators, idx)