# backtester/metrics.py
import pandas as pd
import numpy as np
import json
from datetime import datetime

class PerformanceMetrics:
    @staticmethod
    def calculate(backtester):
        trades_df = pd.DataFrame(backtester.trades)
        
        # Ensure exit_date column
        if 'exit_date' not in trades_df.columns:
            trades_df['exit_date'] = None
        
        closed = trades_df[trades_df['exit_date'].notna()]

        # Default return for no trades
        default_report = {
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'total_pnl': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'win_loss_ratio': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'return_pct': 0,
            'trades_df': trades_df,
            'trade_dna': [],
            'equity_df': pd.DataFrame(backtester.equity_curve)
        }

        if len(closed) == 0:
            return default_report

        total = len(closed)
        wins = closed[closed['pnl'] > 0]
        losses = closed[closed['pnl'] < 0]
        win_rate = len(wins) / total if total > 0 else 0
        total_pnl = closed['pnl'].sum()
        gross_profit = wins['pnl'].sum() if not wins.empty else 0
        gross_loss = abs(losses['pnl'].sum()) if not losses.empty else 0
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else np.inf
        avg_win = wins['pnl'].mean() if not wins.empty else 0
        avg_loss = losses['pnl'].mean() if not losses.empty else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

        equity_df = pd.DataFrame(backtester.equity_curve)
        if len(equity_df) > 0:
            equity_df['drawdown'] = equity_df['equity'] / equity_df['equity'].cummax() - 1
            max_drawdown = equity_df['drawdown'].min()
            equity_df['returns'] = equity_df['equity'].pct_change()
            sharpe = (equity_df['returns'].mean() / (equity_df['returns'].std() + 1e-10)) * np.sqrt(252)
        else:
            max_drawdown = 0
            sharpe = 0

        return_pct = (backtester.cash - backtester.initial_capital) / backtester.initial_capital * 100

        # Build trade DNA
        trade_dna = []
        for _, trade in closed.iterrows():
            holding_bars = 0
            if trade['entry_date'] and trade['exit_date']:
                try:
                    diff = pd.to_datetime(trade['exit_date']) - pd.to_datetime(trade['entry_date'])
                    holding_bars = diff.total_seconds() / 60
                except:
                    pass
            dna_entry = {
                'entry_date': trade['entry_date'],
                'exit_date': trade['exit_date'],
                'direction': trade['type'],
                'entry_price': trade['entry_price'],
                'exit_price': trade['exit_price'],
                'volume': trade['volume'],
                'pnl': trade['pnl'],
                'reason': trade['reason'],
                'holding_bars': holding_bars,
                'confidence': trade.get('confidence', 50),
                'signal_reason': trade.get('signal_reason', ''),
                'trade_duration_minutes': holding_bars,
                'entry_exit_spread': abs(trade['exit_price'] - trade['entry_price']),
                'pnl_per_unit': trade['pnl'] / trade['volume'] if trade['volume'] > 0 else 0,
                'is_winner': trade['pnl'] > 0,
                'profit_pct': (trade['pnl'] / (trade['entry_price'] * trade['volume'])) * 100 if trade['volume'] > 0 and trade['entry_price'] > 0 else 0,
            }
            if hasattr(backtester, 'dna_context') and backtester.dna_context:
                dna_entry['dna_context'] = backtester.dna_context
            trade_dna.append(dna_entry)

        return {
            'total_trades': total,
            'win_rate': win_rate * 100,
            'profit_factor': profit_factor,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'win_loss_ratio': win_loss_ratio,
            'max_drawdown': max_drawdown * 100,
            'sharpe_ratio': sharpe,
            'return_pct': return_pct,
            'trades_df': closed,
            'trade_dna': trade_dna,
            'equity_df': equity_df
        }

    @staticmethod
    def save_report(report, strategy_name, symbol, timeframe='M5', output_dir="backtest_reports"):
        """Save all report files safely with timeframe in filename."""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{strategy_name}_{symbol}_{timeframe}_{timestamp}"
        
        # --- 1. Trade Log (CSV) ---
        trade_file = None
        if len(report.get('trades_df', pd.DataFrame())) > 0:
            trades = report['trades_df'].copy()
            columns = ['entry_date', 'exit_date', 'type', 'entry_price', 'exit_price', 
                       'volume', 'pnl', 'reason']
            existing_cols = [c for c in columns if c in trades.columns]
            trades = trades[existing_cols]
            trades = trades.rename(columns={
                'type': 'Direction',
                'entry_price': 'Entry Price',
                'exit_price': 'Exit Price',
                'volume': 'Volume',
                'pnl': 'PnL',
                'reason': 'Reason'
            })
            trade_file = f"{output_dir}/{base_filename}_trades.csv"
            trades.to_csv(trade_file, index=False)
            print(f"  💾 Trade log saved: {trade_file}")
        
        # --- 2. Trade DNA (JSON) ---
        dna_file = None
        if len(report.get('trade_dna', [])) > 0:
            dna_file = f"{output_dir}/{base_filename}_trade_dna.json"
            with open(dna_file, 'w') as f:
                json.dump(report['trade_dna'], f, indent=2, default=str)
            print(f"  💾 Trade DNA saved: {dna_file}")
        
        # --- 3. Summary (CSV) ---
        summary = {
            'strategy': strategy_name,
            'symbol': symbol,
            'timeframe': timeframe,
            'total_trades': report.get('total_trades', 0),
            'win_rate': report.get('win_rate', 0),
            'profit_factor': report.get('profit_factor', 0),
            'total_pnl': report.get('total_pnl', 0),
            'avg_win': report.get('avg_win', 0),
            'avg_loss': report.get('avg_loss', 0),
            'win_loss_ratio': report.get('win_loss_ratio', 0),
            'max_drawdown': report.get('max_drawdown', 0),
            'sharpe_ratio': report.get('sharpe_ratio', 0),
            'return_pct': report.get('return_pct', 0),
            'timestamp': timestamp
        }
        summary_df = pd.DataFrame([summary])
        summary_file = f"{output_dir}/{base_filename}_summary.csv"
        summary_df.to_csv(summary_file, index=False)
        print(f"  💾 Summary saved: {summary_file}")
        
        # --- 4. Equity Curve (CSV) ---
        eq_file = None
        if len(report.get('equity_df', pd.DataFrame())) > 0:
            eq_file = f"{output_dir}/{base_filename}_equity.csv"
            report['equity_df'].to_csv(eq_file, index=False)
            print(f"  💾 Equity curve saved: {eq_file}")
        
        return {
            'trade_file': trade_file,
            'dna_file': dna_file,
            'summary_file': summary_file,
            'eq_file': eq_file
        }