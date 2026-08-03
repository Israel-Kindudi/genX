"""
Trend Strategy #2: PMax + NSM (Normalized Smoothed MACD)

Buy Conditions:
- PMax indicator is green (uptrend) and shows a buy signal
- Candles closing above bottom PMax line
- NSM (Normalized Smoothed MACD) is below -0.70 and MACD line crosses above signal line

Sell Conditions:
- PMax shows a sell signal
- OR candle closes below bottom PMax line
"""

import numpy as np
import pandas as pd
from strategies.base import BaseStrategy

class TrendStrategyPMax_NSM(BaseStrategy):
    def __init__(self,
                 atr_length=8,
                 atr_multiplier=3.6,
                 ma_type='VAR',  # VAR, SMA, EMA
                 ma_length=10,
                 macd_fast=12,
                 macd_slow=26,
                 macd_signal=9,
                 atr_period=14,
                 stop_multiplier=1.5,
                 take_profit_multiplier=2.5):
        super().__init__(
            atr_length=atr_length,
            atr_multiplier=atr_multiplier,
            ma_type=ma_type,
            ma_length=ma_length,
            macd_fast=macd_fast,
            macd_slow=macd_slow,
            macd_signal=macd_signal,
            atr_period=atr_period,
            stop_multiplier=stop_multiplier,
            take_profit_multiplier=take_profit_multiplier
        )
        self._indicators = None
        self._full_df = None

    def _calculate_ma(self, close, length, ma_type='VAR'):
        """Calculate moving average based on type."""
        if ma_type == 'SMA':
            return pd.Series(close).rolling(length).mean().values
        elif ma_type == 'EMA':
            return pd.Series(close).ewm(span=length, adjust=False).mean().values
        elif ma_type == 'VAR':
            # VAR = Variable Moving Average (or just use EMA with smoothing)
            # Simplified: use EMA
            return pd.Series(close).ewm(span=length, adjust=False).mean().values
        else:
            return pd.Series(close).rolling(length).mean().values

    def _pmax(self, df, atr_length=8, atr_multiplier=3.6, ma_type='VAR', ma_length=10):
        """
        PMax (Parabolic/SAR + Moving Average) indicator.
        Based on KivancOzbilgic's PMax Explorer.
        """
        close = df['Close'].values
        high = df['High'].values
        low = df['Low'].values

        n = len(close)
        pmax = np.zeros(n)
        trend = np.zeros(n)  # 1 = up, -1 = down
        sar = np.zeros(n)
        buy_signal = np.zeros(n, dtype=bool)
        sell_signal = np.zeros(n, dtype=bool)
        bottom_pmax = np.zeros(n)
        top_pmax = np.zeros(n)

        # Calculate ATR
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        atr = np.zeros(n)
        if n > atr_length:
            atr_series = pd.Series(tr).rolling(atr_length).mean()
            atr[atr_length:] = atr_series.values[atr_length-1:]
        else:
            atr = np.full(n, np.mean(tr) if len(tr) > 0 else 0)

        # Calculate MA (VAR or other)
        ma = self._calculate_ma(close, ma_length, ma_type)

        # Initialize Parabolic SAR
        step = 0.02
        max_step = 0.2
        sar = np.zeros(n)
        ep = np.zeros(n)  # Extreme point
        trend = np.zeros(n)
        trend[0] = 1  # Start with uptrend

        # Initial SAR
        if n > 0:
            # First bar: SAR = close[0] - atr[0] * atr_multiplier (approximately)
            sar[0] = close[0] - atr_multiplier * atr[0]

        for i in range(1, n):
            # Update SAR based on previous trend
            if trend[i-1] == 1:  # Uptrend
                sar[i] = sar[i-1] + step * (ep[i-1] - sar[i-1])
                # Ensure SAR is below price
                if sar[i] > low[i]:
                    sar[i] = min(low[i], ep[i-1])
                # Check reversal to downtrend
                if low[i] <= sar[i]:
                    trend[i] = -1
                    sar[i] = ep[i-1]
                    sell_signal[i] = True
                    ep[i] = low[i]
                else:
                    trend[i] = 1
                    # Update extreme point
                    if high[i] > ep[i-1]:
                        ep[i] = high[i]
                        step = min(max_step, step + 0.02)
                    else:
                        ep[i] = ep[i-1]
            else:  # Downtrend
                sar[i] = sar[i-1] - step * (sar[i-1] - ep[i-1])
                # Ensure SAR is above price
                if sar[i] < high[i]:
                    sar[i] = max(high[i], ep[i-1])
                # Check reversal to uptrend
                if high[i] >= sar[i]:
                    trend[i] = 1
                    sar[i] = ep[i-1]
                    buy_signal[i] = True
                    ep[i] = high[i]
                else:
                    trend[i] = -1
                    if low[i] < ep[i-1]:
                        ep[i] = low[i]
                        step = min(max_step, step + 0.02)
                    else:
                        ep[i] = ep[i-1]

            # Set ep[i] if not set
            if ep[i] == 0:
                ep[i] = ep[i-1]

        # PMax is the MA line colored by trend
        # If trend is up, PMax = ma (green), if down, PMax = ma (red)
        # Top PMax is when trend is up, bottom PMax is when trend is down
        pmax = ma.copy()
        for i in range(n):
            if trend[i] == 1:
                bottom_pmax[i] = ma[i]  # bottom line for uptrend
                top_pmax[i] = ma[i] + atr_multiplier * atr[i]
            else:
                top_pmax[i] = ma[i]  # top line for downtrend
                bottom_pmax[i] = ma[i] - atr_multiplier * atr[i]

        # Color = green if trend up, red if down
        is_green = trend == 1

        return {
            'pmax': pmax,
            'trend': trend,
            'is_green': is_green,
            'buy_signal': buy_signal,
            'sell_signal': sell_signal,
            'bottom_pmax': bottom_pmax,
            'top_pmax': top_pmax,
            'atr': atr,
            'sar': sar,
        }

    def _nsm(self, df, fast=12, slow=26, signal=9):
        """Normalized Smoothed MACD."""
        close = df['Close'].values

        # MACD
        ema_fast = pd.Series(close).ewm(span=fast, adjust=False).mean().values
        ema_slow = pd.Series(close).ewm(span=slow, adjust=False).mean().values
        macd_line = ema_fast - ema_slow
        signal_line = pd.Series(macd_line).ewm(span=signal, adjust=False).mean().values
        macd_hist = macd_line - signal_line

        # Normalize MACD (Z-score or min-max)
        # Use rolling z-score for normalization
        mean = pd.Series(macd_line).rolling(slow).mean().values
        std = pd.Series(macd_line).rolling(slow).std().values
        nsm = np.zeros(len(close))
        for i in range(slow, len(close)):
            if std[i] > 0:
                nsm[i] = (macd_line[i] - mean[i]) / std[i]

        return {
            'macd_line': macd_line,
            'signal_line': signal_line,
            'macd_hist': macd_hist,
            'nsm': nsm,
        }

    def precompute_indicators(self, df):
        """Pre-compute PMax and NSM."""
        p = self.params
        atr_length = p['atr_length']
        atr_multiplier = p['atr_multiplier']
        ma_type = p['ma_type']
        ma_length = p['ma_length']
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
        atr = np.zeros(n)
        if n > atr_period:
            atr_series = pd.Series(tr).rolling(atr_period).mean()
            atr[atr_period:] = atr_series.values[atr_period-1:]
        else:
            atr = np.full(n, np.mean(tr) if len(tr) > 0 else 0)

        # --- PMax ---
        pmax_data = self._pmax(df, atr_length, atr_multiplier, ma_type, ma_length)

        # --- NSM ---
        nsm_data = self._nsm(df, macd_fast, macd_slow, macd_signal)

        return {
            'atr': atr,
            'pmax': pmax_data['pmax'],
            'trend': pmax_data['trend'],
            'is_green': pmax_data['is_green'],
            'buy_signal': pmax_data['buy_signal'],
            'sell_signal': pmax_data['sell_signal'],
            'bottom_pmax': pmax_data['bottom_pmax'],
            'top_pmax': pmax_data['top_pmax'],
            'macd_line': nsm_data['macd_line'],
            'signal_line': nsm_data['signal_line'],
            'macd_hist': nsm_data['macd_hist'],
            'nsm': nsm_data['nsm'],
            'close': close,
            'low': low,
            'high': high,
        }

    def generate_signal_with_indicators(self, df, indicators, idx):
        p = self.params
        stop_multiplier = p['stop_multiplier']
        tp_multiplier = p['take_profit_multiplier']

        warmup = max(p['atr_length'], p['ma_length'], p['macd_slow'], p['macd_fast']) + 20
        if idx < warmup:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'Warmup'}

        close = indicators['close']
        low = indicators['low']
        atr = indicators['atr']
        is_green = indicators['is_green']
        buy_signal = indicators['buy_signal']
        sell_signal = indicators['sell_signal']
        bottom_pmax = indicators['bottom_pmax']
        macd_line = indicators['macd_line']
        signal_line = indicators['signal_line']
        nsm = indicators['nsm']

        close_price = close[idx]
        low_entry = low[idx]
        atr_val = atr[idx]
        nsm_val = nsm[idx]
        macd_val = macd_line[idx]
        signal_val = signal_line[idx]
        bottom_val = bottom_pmax[idx]

        if idx > 0:
            prev_macd = macd_line[idx-1]
            prev_signal = signal_line[idx-1]
            prev_nsm = nsm[idx-1]
            prev_close = close[idx-1]
            prev_bottom = bottom_pmax[idx-1]
        else:
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'No previous data'}

        if np.isnan(nsm_val) or np.isnan(macd_val) or np.isnan(signal_val):
            return {'action': 'HOLD', 'confidence': 0, 'reason': 'NaN indicator'}

        # --- Buy Condition ---
        # 1. PMax is green (uptrend) and shows buy signal
        pmax_buy = is_green[idx] and buy_signal[idx]

        # 2. Candles closing above bottom PMax line
        price_above_bottom = close_price > bottom_val

        # 3. NSM below -0.70 and MACD line crosses above signal line
        nsm_condition = nsm_val < -0.70 and prev_nsm <= -0.70
        macd_cross = prev_macd <= prev_signal and macd_val > signal_val

        if pmax_buy and price_above_bottom and nsm_condition and macd_cross:
            entry = close_price
            sl = low_entry - stop_multiplier * atr_val
            tp = close_price + tp_multiplier * atr_val

            return {
                'action': 'BUY',
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'confidence': 75,
                'reason': f'PMax green & NSM cross up (NSM: {nsm_val:.2f})'
            }

        # --- Sell Condition ---
        # 1. PMax shows sell signal
        pmax_sell = sell_signal[idx]

        # 2. Candle closes below bottom PMax line
        price_below_bottom = close_price < bottom_val and prev_close >= prev_bottom

        if pmax_sell or price_below_bottom:
            return {
                'action': 'CLOSE_LONG',
                'confidence': 60,
                'reason': f'PMax sell or close below bottom PMax'
            }

        return {'action': 'HOLD', 'confidence': 0, 'reason': 'No signal'}

    def generate_signal(self, df):
        if self._indicators is None or len(df) != len(self._full_df):
            self._full_df = df.copy()
            self._indicators = self.precompute_indicators(df)
        idx = len(df) - 1
        return self.generate_signal_with_indicators(df, self._indicators, idx)