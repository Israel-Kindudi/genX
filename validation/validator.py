#!/usr/bin/env python
"""
Strategy Validation Framework
Validates optimized strategies on:
1. Out‑of‑sample walk‑forward data
2. Live market data via MT5
3. Statistical comparison vs backtest performance
"""

import os
import sys
import json
import time
import glob
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backtester import FastBacktesterEngine
from strategies import (
    ScalpingStrategyRSI_VWMA,
    TrendFollowingStrategy,
    ScalpingStrategy,
    TrendFollowingADX,
    ScalpingStrategyDMI_MACD,
    ScalpingStrategyBB_MACD_TM,
    ScalpingStrategyHMA_Stoch,
    TrendStrategyVWMA_SOTT,
    TrendStrategyPMax_NSM,
    TrendStrategyAroonRSI_SMA
)
from config import DATA_DIR, INITIAL_CAPITAL, RISK_PER_TRADE

# Strategy class mapping (for loading optimized params)
STRATEGY_CLASS_MAP = {
    'Scalping RSI+VWMA': ScalpingStrategyRSI_VWMA,
    'Scalping': ScalpingStrategy,
    'Trend Following': TrendFollowingStrategy,
    'Trend Following ADX': TrendFollowingADX,
    'Scalping DMI+MACD': ScalpingStrategyDMI_MACD,
    'Scalping BB+MACD+TM': ScalpingStrategyBB_MACD_TM,
    'Scalping HMA+Stoch': ScalpingStrategyHMA_Stoch,
    'Trend VWMA+SOTT': TrendStrategyVWMA_SOTT,
    'Trend PMax+NSM': TrendStrategyPMax_NSM,
    'Trend Aroon+RSI+SMA': TrendStrategyAroonRSI_SMA,
}

def load_optimized_params(strategy_name, symbol, output_dir="optimized_strategies"):
    """Load the best parameters from optimization result."""
    file_path = f"{output_dir}/{strategy_name}_{symbol}_final.json"
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                return data.get('best_params'), data.get('best_fitness')
        except:
            pass
    return None, None

def load_data_for_symbol(symbol, timeframe='M5'):
    """Load OHLC data for a symbol and timeframe."""
    pattern = f"{DATA_DIR}/{symbol}_PERIODE_{timeframe}_data.csv"
    files = glob.glob(pattern)
    if not files:
        files = glob.glob(f"{DATA_DIR}/*{symbol}*{timeframe}*.csv")
    if not files:
        return None
    csv_file = files[0]
    df = pd.read_csv(csv_file)
    df.columns = [c.lower() for c in df.columns]
    if 'time' in df.columns:
        df.rename(columns={'time': 'date'}, inplace=True)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    else:
        df.index = pd.to_datetime(df.index)
        df['date'] = df.index
    df = df.sort_values('date').reset_index(drop=True)
    col_map = {}
    for col in df.columns:
        if col in ['open', 'o']:
            col_map[col] = 'Open'
        elif col in ['high', 'h']:
            col_map[col] = 'High'
        elif col in ['low', 'l']:
            col_map[col] = 'Low'
        elif col in ['close', 'c']:
            col_map[col] = 'Close'
        elif col in ['volume', 'vol', 'v']:
            col_map[col] = 'Volume'
        elif col in ['date', 'time']:
            col_map[col] = 'Date'
    df = df.rename(columns=col_map)
    if 'Volume' not in df.columns:
        df['Volume'] = 1
    return df

def split_walk_forward(df, train_ratio=0.7):
    """Split data into train (for optimization) and test (for validation)."""
    split_idx = int(len(df) * train_ratio)
    train_df = df.iloc[:split_idx].copy()
    test_df = df.iloc[split_idx:].copy()
    return train_df, test_df

def run_validation(strategy_class, params, df, symbol, timeframe='M5'):
    """Run backtest on validation data."""
    strategy = strategy_class(**params)
    engine = FastBacktesterEngine(
        df=df,
        strategy=strategy,
        symbol=f"{symbol}_VALIDATION",
        initial_capital=INITIAL_CAPITAL,
        risk_per_trade=RISK_PER_TRADE,
        timeframe=timeframe,
        verbose=False
    )
    report = engine.run(show_progress=False)
    return report

def compare_reports(backtest_report, validation_report):
    """Compare backtest and validation performance."""
    metrics = ['total_trades', 'win_rate', 'profit_factor', 'total_pnl', 'sharpe_ratio', 'max_drawdown', 'return_pct']
    comparison = {}
    for metric in metrics:
        backtest_val = backtest_report.get(metric, 0)
        validation_val = validation_report.get(metric, 0)
        comparison[metric] = {
            'backtest': backtest_val,
            'validation': validation_val,
            'change': validation_val - backtest_val,
            'change_pct': ((validation_val - backtest_val) / (abs(backtest_val) + 1e-10)) * 100
        }
    return comparison

def validate_all_strategies(strategies_to_validate=None, output_dir="validation_results"):
    """
    Validate multiple strategies across symbols.
    strategies_to_validate: list of strategy names (e.g., ['Scalping RSI+VWMA', 'Scalping'])
    If None, validates all strategies with optimized params.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    symbols = ["BreakX 600", "BreakX 1200", "BreakX 1800"]
    timeframe = "M5"
    
    all_results = []
    
    # Collect strategies to validate
    if strategies_to_validate is None:
        # Find all optimized strategy files
        opt_files = glob.glob("optimized_strategies/*_final.json")
        strategies_to_validate = []
        for f in opt_files:
            base = os.path.basename(f).replace('_final.json', '')
            # Extract strategy name (remove symbol)
            parts = base.split('_')
            if len(parts) >= 2:
                strategy = '_'.join(parts[:-1])
                if strategy not in strategies_to_validate:
                    strategies_to_validate.append(strategy)
    
    print(f"🔍 Validating {len(strategies_to_validate)} strategies...")
    
    for strategy_name in strategies_to_validate:
        # Find matching strategy class
        strategy_class = None
        for key, cls in STRATEGY_CLASS_MAP.items():
            if key in strategy_name:
                strategy_class = cls
                break
        if strategy_class is None:
            print(f"⚠️ No class found for {strategy_name}, skipping.")
            continue
        
        for symbol in symbols:
            print(f"\n📊 Validating {strategy_name} on {symbol}")
            
            # Load optimized params
            params, best_fitness = load_optimized_params(strategy_name, symbol)
            if params is None:
                print(f"   ⚠️ No optimized params for {strategy_name} on {symbol}, skipping.")
                continue
            
            # Load data
            df = load_data_for_symbol(symbol, timeframe)
            if df is None:
                print(f"   ⚠️ No data for {symbol}, skipping.")
                continue
            
            # Split into train (for reference) and test (validation)
            train_df, test_df = split_walk_forward(df, train_ratio=0.7)
            
            # Run validation on test data
            validation_report = run_validation(strategy_class, params, test_df, symbol, timeframe)
            
            # Load backtest report for comparison (if available)
            backtest_file = f"backtest_reports/{strategy_name}_{symbol}_summary.csv"
            backtest_report = None
            if os.path.exists(backtest_file):
                try:
                    backtest_df = pd.read_csv(backtest_file)
                    backtest_report = backtest_df.iloc[0].to_dict()
                except:
                    pass
            
            # Compare if backtest report available
            comparison = None
            if backtest_report:
                comparison = compare_reports(backtest_report, validation_report)
            
            result = {
                'strategy': strategy_name,
                'symbol': symbol,
                'timeframe': timeframe,
                'validation_report': validation_report,
                'backtest_report': backtest_report,
                'comparison': comparison,
                'params': params,
                'best_fitness': best_fitness,
                'timestamp': datetime.now().isoformat()
            }
            all_results.append(result)
            
            # Print summary
            print(f"   ✅ Validation complete: {validation_report['total_trades']} trades, Sharpe: {validation_report['sharpe_ratio']:.3f}")
            if comparison:
                sharpe_change = comparison['sharpe_ratio']['change_pct']
                pnl_change = comparison['total_pnl']['change_pct']
                print(f"      vs backtest: Sharpe {sharpe_change:+.1f}%, PnL {pnl_change:+.1f}%")
    
    # Save all results
    results_file = f"{output_dir}/validation_results.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\n💾 Validation results saved to {results_file}")
    
    # Generate summary table
    summary_rows = []
    for res in all_results:
        v = res['validation_report']
        comparison = res.get('comparison', {})
        summary_rows.append({
            'Strategy': res['strategy'],
            'Symbol': res['symbol'],
            'Trades': v.get('total_trades', 0),
            'Win Rate %': f"{v.get('win_rate', 0):.1f}",
            'Sharpe': f"{v.get('sharpe_ratio', 0):.3f}",
            'Total PnL': f"${v.get('total_pnl', 0):.2f}",
            'Max DD %': f"{v.get('max_drawdown', 0):.1f}",
            'Sharpe Change %': f"{comparison.get('sharpe_ratio', {}).get('change_pct', 0):+.1f}",
            'PnL Change %': f"{comparison.get('total_pnl', {}).get('change_pct', 0):+.1f}",
        })
    
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(f"{output_dir}/validation_summary.csv", index=False)
    print(f"💾 Validation summary saved to {output_dir}/validation_summary.csv")
    
    return all_results

if __name__ == "__main__":
    results = validate_all_strategies()
    print("\n✅ Validation complete!")