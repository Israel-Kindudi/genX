"""
Generic Backtester Engine – uses any BaseStrategy.
"""
import pandas as pd
import numpy as np
from datetime import datetime
from tqdm import tqdm
from backtester.metrics import PerformanceMetrics

class BacktesterEngine:
    def __init__(self, df, strategy, symbol="Unknown",
                 initial_capital=10000, risk_per_trade=1.0,
                 commission=0.0, timeframe='5m', verbose=True):
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
        self._log(f"📊 BACKTEST: {self.strategy.get_name()}")
        self._log("="*60)
        self._log(f"Symbol: {self.symbol}")
        self._log(f"Bars: {self.n:,}")
        self._log(f"Capital: ${self.initial_capital:,.2f}")
        self._log(f"Risk: {self.risk_per_trade*100:.1f}%")
        self._log("-"*60)

        warmup = 100
        pbar = tqdm(total=self.n - warmup, desc="Processing", unit="bars") if show_progress else None

        for i in range(warmup, self.n):
            bar = self.df.iloc[i]
            date = bar['Date']
            high, low, close = bar['High'], bar['Low'], bar['Close']

            signal = self.strategy.generate_signal(self.df.iloc[:i+1])

            # Manage position
            if self.current_position:
                pos = self.current_position
                exit_price = None
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
                self.equity = self.cash + pos['volume'] * (close - pos['entry']) if pos['type'] == 'BUY' else self.cash + pos['volume'] * (pos['entry'] - close)
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
            volume = risk_amount / risk_per_unit if risk_per_unit > 0 else 0.01
            volume = round(max(0.01, volume), 2)

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
        pnl = (exit_price - pos['entry']) * volume if pos['type'] == 'BUY' else (pos['entry'] - exit_price) * volume
        self.cash += pnl - self.commission * volume

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
            # Update equity with remaining position
            if pos['type'] == 'BUY':
                self.equity = self.cash + pos['volume'] * (exit_price - pos['entry'])
            else:
                self.equity = self.cash + pos['volume'] * (pos['entry'] - exit_price)
            self.equity_curve.append({'date': date, 'equity': self.equity})
        else:
            self.current_position = None
            self.equity = self.cash
            self.equity_curve.append({'date': date, 'equity': self.equity})