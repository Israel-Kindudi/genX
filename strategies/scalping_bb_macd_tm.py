"""
Scalping Strategy #3: Bollinger Band MACD + Trend Magic (TM)

Buy Conditions:
- BB+MACD indicator is green (MACD > upper Bollinger band)
- TM indicator is blue (close > TM line) and candle closes above it
- Entry at market, stop loss under low of entry candle

Sell Conditions:
- BB+MACD indicator turns blue (MACD < lower Bollinger band)
- OR candle closes below TM indicator
"""

import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class ScalpingStrategyBB_MACD_TM(BaseStrategy):
    def __init__(self,
                 macd_fast=12,
                 macd_slow=26,
                 macd_signal=9,
                 bb_period=20,
                 bb_std=2.0,
                 tm_period=20,          # EMA period for Trend Magic
                 atr_period=14,
                 stop_multiplier=1.5,
                 take_profit_multiplier=2.0):
        super().__init__(
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            bb_period=bb_period,
            bb_std=bb_std,
            tm_period=tm_period,
            atr_period=atr_period,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier
        )
        self._indicators = None
        self._full_df = None

    def precompute_indicators(self, df):
        """Pre-compute MACD, Bollinger Bands on MACD, Trend Magic (EMA)."""
        p = self.params
        macd_fast = p['macd_fast']
        macd_slow = p['macd_slow']
        macd_signal = p['macd_signal']
        bb_period = p['bb_period']
        bb_std = p['bb_std']
        tm_period = p['tm_period']
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
        tr_padded = np.concatenate([[0], tr])
        atr = np.zeros(n)
        if n > atr_period:
            atr_series = pd.Series(tr).rolling(atr_period).mean()
            atr[atr_period:] = atr_series.values[atr_period-1:]
        else:
            atr = np.full(n, np.mean(tr) if len(tr) > 0 else 0)

        # --- MACD ---
        ema_fast = pd.Series(close).ewm(span=macd_fast, adjust=False).mean().values
        ema_slow = pd.Series(close).ewm(span=macd_slow, adjust=False).mean().values
        macd_line = ema_fast - ema_slow
        signal_line = pd.Series(macd_line).ewm(span=macd_signal, adjust=False).mean().values
        macd_hist = macd_line - signal_line

        # --- Bollinger Bands on MACD line ---
        # Rolling mean and std of MACD line
        macd_sma = pd.Series(macd_line).rolling(bb_period).mean().values
        macd_std = pd.Series(macd_line).rolling(bb_period).std().values
        upper_band = macd_sma + bb_std * macd_std
        lower_band = macd_sma - bb_std * macd_std

        # --- Trend Magic (TM) = EMA of close ---
        tm_line = pd.Series(close).ewm(span=tm_period, adjust=False).mean().values

        return {
            'atr': atr,
            'macd_line': macd_line,
            'signal_line': signal_line,
            'macd_hist': macd_hist,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'tm_line': tm_line,
            'close': close,
            'low': low,
            'high': high,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        p = self.params
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']

        if idx < max(p['macd_slow'], p['bb_period'], p['tm_period']) + 10:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        low = indicators['low']
        atr = indicators['atr']
        macd_line = indicators['macd_line']
        upper_band = indicators['upper_band']
        lower_band = indicators['lower_band']
        tm_line = indicators['tm_line']

        close_price = close[idx]
        low_entry = low[idx]
        atr_val = atr[idx]
        macd_val = macd_line[idx]
        upper_val = upper_band[idx]
        lower_val = lower_band[idx]
        tm_val = tm_line[idx]

        # Previous values for crossover detection
        if idx > 0:
            prev_close = close[idx-1]
            prev_tm = tm_line[idx-1]
            prev_macd = macd_line[idx-1]
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No previous data'}

        # --- BB+MACD green: MACD > upper band (bullish) ---
        macd_green = macd_val > upper_val

        # --- BB+MACD blue: MACD < lower band (bearish) ---
        macd_blue = macd_val < lower_val

        # --- TM blue: close > TM line (uptrend) ---
        tm_blue = close_price > tm_val

        # --- Buy Condition ---
        # MACD green AND TM blue AND candle closes above TM (crossover)
        macd_green_buy = macd_green and (prev_macd <= upper_val or macd_val > prev_macd)  # optionally strengthening
        # For simplicity: MACD green and TM blue and price above TM
        buy = macd_green and tm_blue and close_price > tm_val and prev_close <= prev_tm  # crossover candle close above TM

        # --- Sell Condition ---
        # MACD turns blue OR candle closes below TM
        macd_turns_blue = macd_blue and (prev_macd >= lower_val or macd_val < prev_macd)
        sell = macd_turns_blue or (close_price < tm_val and prev_close >= prev_tm)  # cross below

        if buy:
            entry = close_price
            sl = low_entry - stop_multiplier * atr_val
            tp = close_price + tp_multiplier * atr_val
            return {
                'action': 'BUY',
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 70,
                'reason': f'BB+MACD green & TM blue (MACD: {macd_val:.3f}, TM: {tm_val:.2f})'
            }
        elif sell:
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': f'BB+MACD blue or close below TM'
            }
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)