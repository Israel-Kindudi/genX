"""
Trend Strategy #3: Aroon Trend Trading Strategy

Buy Conditions:
- RSI crosses above 50
- Price is above 10 SMA
- Aroon Up line crosses above Aroon Down line

Sell Conditions:
- Price closes below 10 SMA
- OR Aroon Up crosses below 80
"""

import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class TrendStrategyAroonRSI_SMA(BaseStrategy):
    def __init__(self,
                 aroon_period=14,
                 rsi_period=14,
                 sma_period=10,
                 atr_period=14,
                 stop_multiplier=1.5,
                 take_profit_multiplier=2.5):
        super().__init__(
            aroon_period=aroon_period,
            rsi_period=rsi_period,
            sma_period=sma_period,
            atr_period=atr_period,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier
        )
        self._indicators = None
        self._full_df = None

    def precompute_indicators(self, df):
        """Pre-compute Aroon, RSI, SMA, ATR."""
        p = self.params
        aroon_period = p['aroon_period']
        rsi_period = p['rsi_period']
        sma_period = p['sma_period']
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

        # --- Aroon ---
        # Aroon Up = ((period - bars since highest high) / period) * 100
        # Aroon Down = ((period - bars since lowest low) / period) * 100
        aroon_up = np.zeros(n)
        aroon_down = np.zeros(n)

        for i in range(aroon_period, n):
            # Bars since highest high
            window_high = high[i-aroon_period:i+1]
            highest_idx = np.argmax(window_high)
            bars_since_high = aroon_period - highest_idx
            aroon_up[i] = ((aroon_period - bars_since_high) / aroon_period) * 100

            # Bars since lowest low
            window_low = low[i-aroon_period:i+1]
            lowest_idx = np.argmin(window_low)
            bars_since_low = aroon_period - lowest_idx
            aroon_down[i] = ((aroon_period - bars_since_low) / aroon_period) * 100

        # --- RSI ---
        delta = pd.Series(close).diff()
        gain = (delta.where(delta > 0, 0)).rolling(rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(rsi_period).mean()
        rs = gain / loss
        rsi_vals = 100 - (100 / (1 + rs))
        rsi_vals = rsi_vals.values

        # --- SMA ---
        sma_vals = pd.Series(close).rolling(sma_period).mean().values

        return {
            'atr': atr,
            'aroon_up': aroon_up,
            'aroon_down': aroon_down,
            'rsi': rsi_vals,
            'sma': sma_vals,
            'close': close,
            'low': low,
            'high': high,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        p = self.params
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']

        if idx < max(p['aroon_period'], p['rsi_period'], p['sma_period']) + 10:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        low = indicators['low']
        atr = indicators['atr']
        aroon_up = indicators['aroon_up']
        aroon_down = indicators['aroon_down']
        rsi = indicators['rsi']
        sma = indicators['sma']

        close_price = close[idx]
        low_entry = low[idx]
        atr_val = atr[idx]
        rsi_val = rsi[idx]
        sma_val = sma[idx]
        aroon_up_val = aroon_up[idx]
        aroon_down_val = aroon_down[idx]

        if idx > 0:
            prev_rsi = rsi[idx-1]
            prev_aroon_up = aroon_up[idx-1]
            prev_aroon_down = aroon_down[idx-1]
            prev_close = close[idx-1]
            prev_sma = sma[idx-1]
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No previous data'}

        if np.isnan(rsi_val) or np.isnan(aroon_up_val) or np.isnan(aroon_down_val) or np.isnan(sma_val):
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'NaN indicator'}

        # --- Buy Condition ---
        # 1. RSI crosses above 50
        rsi_cross_up = prev_rsi <= 50 and rsi_val > 50

        # 2. Price above 10 SMA (and previous close below or at SMA for crossover)
        price_above_sma = close_price > sma_val

        # 3. Aroon Up crosses above Aroon Down
        aroon_cross_up = prev_aroon_up <= prev_aroon_down and aroon_up_val > aroon_down_val

        if rsi_cross_up and price_above_sma and aroon_cross_up:
            entry = close_price
            sl = low_entry - stop_multiplier * atr_val
            tp = close_price + tp_multiplier * atr_val

            return {
                'action': 'BUY',
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 75,
                'reason': f'RSI cross up & Aroon cross up (RSI: {rsi_val:.1f})'
            }

        # --- Sell Condition ---
        # 1. Price closes below 10 SMA (crossover)
        price_below_sma = close_price < sma_val and prev_close >= prev_sma

        # 2. Aroon Up crosses below 80 (weakening trend)
        aroon_weak = aroon_up_val < 80 and prev_aroon_up >= 80

        if price_below_sma or aroon_weak:
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': f'Close below SMA or Aroon Up < 80'
            }

        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)