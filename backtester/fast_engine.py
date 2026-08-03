# backtester/fast_engine.py
"""
Fast Backtester Engine - Pre-computes indicators once.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from tqdm import tqdm
from backtester.metrics import PerformanceMetrics

class FastBacktesterEngine:
    """Backtester that pre-computes indicators once for speed."""
    
    # backtester/fast_engine.py (add dna_context support)

class FastBacktesterEngine:
    def __init__(self, df, strategy, symbol="Unknown",
                 initial_capital=10, risk_per_trade=1.0,
                 commission=0.0, timeframe='5m', verbose=True,
                 dna_context=None):  # <-- Add dna_context parameter
        # ... existing code ...
        self.dna_context = dna_context  # <-- Store DNA context for trade DNA
        # ... rest of init ...
        self.df = df.copy()
        self.strategy = strategy
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade / 100.0
        self.commission = commission
        self.timeframe = timeframe
        self.verbose = verbose
        self.trades = []
        self.equity_curve = []
        self.current_position = None
        self.cash = initial_capital
        self.equity = initial_capital
        self.n = len(df)

    def _log(self, msg, level="INFO"):
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}")

    def run(self, show_progress=True):
        self._log("="*60)
        self._log(f"📊 FAST BACKTEST: {self.strategy.get_name()}")
        self._log("="*60)
        self._log(f"Symbol: {self.symbol}")
        self._log(f"Bars: {self.n:,}")
        self._log(f"Capital: ${self.initial_capital:,.2f}")
        self._log(f"Risk: {self.risk_per_trade*100:.1f}%")
        self._log("-"*60)

        # --- Pre-compute indicators ONCE ---
        self._log("⚡ Pre-computing indicators...")
        start_pre = datetime.now()
        
        if hasattr(self.strategy, 'precompute_indicators'):
            indicators = self.strategy.precompute_indicators(self.df)
            self._log(f"✅ Indicators pre-computed ({datetime.now() - start_pre})")
        else:
            indicators = None
            self._log("⚠️ Using standard generate_signal (slower)")

        warmup = 100
        pbar = tqdm(total=self.n - warmup, desc="Processing", unit="bars") if show_progress else None

        for i in range(warmup, self.n):
            bar = self.df.iloc[i]
            date = bar['Date']
            high, low, close = bar['High'], bar['Low'], bar['Close']

            # Generate signal using pre-computed indicators if available
            if indicators is not None and hasattr(self.strategy, 'generate_signal_with_indicators'):
                signal = self.strategy.generate_signal_with_indicators(self.df, indicators, i)
            else:
                signal = self.strategy.generate_signal(self.df.iloc[:i+1])

            # Manage position
            if self.current_position:
                pos = self.current_position
                exit_price = None
                reason = None

                if pos['type'] == 'BUY':
                    if low <= pos['sl']:
                        exit_price = pos['sl']
                        reason = 'SL'
                    elif high >= pos['tp']:
                        exit_price = pos['tp']
                        reason = 'TP'
                else:  # SELL
                    if high >= pos['sl']:
                        exit_price = pos['sl']
                        reason = 'SL'
                    elif low <= pos['tp']:
                        exit_price = pos['tp']
                        reason = 'TP'

                if exit_price is not None:
                    self._close_position(exit_price, date, reason)
                    pbar.update(1) if pbar else None
                    continue

                if signal['action'] in ['CLOSE_LONG', 'CLOSE_SHORT']:
                    self._close_position(close, date, signal.get('reason', 'Signal'))
                    pbar.update(1) if pbar else None
                    continue

            # Open new position
            if signal['action'] in ['BUY', 'SELL'] and self.current_position is None:
                self._open_position(signal, date, bar)
                pbar.update(1) if pbar else None
                continue

            # Update equity
            if self.current_position:
                pos = self.current_position
                if pos['type'] == 'BUY':
                    self.equity = self.cash + pos['volume'] * (close - pos['entry'])
                else:
                    self.equity = self.cash + pos['volume'] * (pos['entry'] - close)
                self.equity_curve.append({'date': date, 'equity': self.equity})

            pbar.update(1) if pbar else None

        if pbar:
            pbar.close()

        if self.current_position:
            last_bar = self.df.iloc[-1]
            self._close_position(last_bar['Close'], last_bar['Date'], 'END_OF_DATA')

        self._log("✅ Backtest complete")
        return PerformanceMetrics.calculate(self)

    def _open_position(self, signal, date, bar):
        action = signal['action']
        entry = signal['entry']
        sl = signal['stop_loss']
        tp = signal['take_profit']

        risk_amount = self.cash * self.risk_per_trade
        if sl is None or entry is None:
            volume = 0.01
        else:
            risk_per_unit = abs(entry - sl)
            if risk_per_unit == 0:
                volume = 0.01
            else:
                volume = risk_amount / risk_per_unit
                # Cap volume to reasonable max (e.g., 100 lots)
                max_lots = 100.0
                volume = min(volume, max_lots)
                volume = max(0.01, volume)
                # Round to lot step (assume 0.01)
                volume = round(volume / 0.01) * 0.01
                volume = round(volume, 2)

        pos_type = 'BUY' if action == 'BUY' else 'SELL'
        self.current_position = {
            'type': pos_type,
            'entry': entry,
            'sl': sl,
            'tp': tp,
            'volume': volume,
            'entry_date': date,
            'entry_bar': bar
        }

        self.trades.append({
            'entry_date': date,
            'exit_date': None,
            'type': pos_type,
            'entry_price': entry,
            'exit_price': None,
            'volume': volume,
            'pnl': 0,
            'reason': 'OPEN',
            'confidence': signal.get('confidence', 50),
            'signal_reason': signal.get('reason', '')
        })

    def _close_position(self, exit_price, date, reason, partial_volume=None):
        if self.current_position is None:
            return

        pos = self.current_position
        volume = partial_volume if partial_volume else pos['volume']

        if pos['type'] == 'BUY':
            pnl = (exit_price - pos['entry']) * volume
        else:
            pnl = (pos['entry'] - exit_price) * volume

        pnl -= self.commission * volume
        self.cash += pnl

        # Find the open trade and close it
        for trade in self.trades:
            if trade['exit_date'] is None and trade['entry_date'] == pos['entry_date'] and trade['type'] == pos['type']:
                trade['exit_date'] = date
                trade['exit_price'] = exit_price
                trade['pnl'] = pnl
                trade['reason'] = reason
                break
        else:
            # If no matching trade found, append a new one (shouldn't happen)
            self.trades.append({
                'entry_date': pos['entry_date'],
                'exit_date': date,
                'type': pos['type'],
                'entry_price': pos['entry'],
                'exit_price': exit_price,
                'volume': volume,
                'pnl': pnl,
                'reason': reason,
                'confidence': 0,
                'signal_reason': ''
            })

        if partial_volume and partial_volume < pos['volume']:
            pos['volume'] -= partial_volume
            if pos['type'] == 'BUY':
                self.equity = self.cash + pos['volume'] * (exit_price - pos['entry'])
            else:
                self.equity = self.cash + pos['volume'] * (pos['entry'] - exit_price)
            self.equity_curve.append({'date': date, 'equity': self.equity})
        else:
            self.current_position = None
            self.equity = self.cash
            self.equity_curve.append({'date': date, 'equity': self.equity})