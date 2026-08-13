#!/usr/bin/env python
"""
Backtest all optimized strategies using the best parameters from batch optimization.
Saves a comparison summary to CSV and JSON.
Place this script in the /backtest/ folder.
"""

import os
import sys
import json
import glob
import time
import traceback
import pandas as pd
import numpy as np
from datetime import datetime
from tqdm import tqdm

# ---- Add project root to sys.path ----
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ---- Now import project modules ----
from config import DATA_DIR, INITIAL_CAPITAL, RISK_PER_TRADE
from backtester import FastBacktesterEngine
from optimization.strategy_optimizer import (
    find_strategy_key,
    get_dna_context,
    STRATEGY_MAP as OPTIMIZER_STRATEGY_MAP
)
from live_trading.live_engine import DEFAULT_PARAMS

# ============================================================================
# Configuration
# ============================================================================
OPTIMIZED_DIR = os.path.join(project_root, "optimized_strategies")
OUTPUT_DIR = os.path.join(project_root, "backtest_optimized_results")
TIMEFRAME = "M5"
BARS_LIMIT = 10000  # Use last 10k bars for quick test; set to None to use full dataset
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# Helper functions
# ============================================================================
def find_csv_file(symbol):
    pattern = f"{DATA_DIR}/*{symbol}*{TIMEFRAME}*.csv"
    files = glob.glob(pattern)
    if not files:
        pattern = f"{DATA_DIR}/*{symbol}*.csv"
        files = glob.glob(pattern)
    return files[0] if files else None

def load_data(csv_path):
    df = pd.read_csv(csv_path)
    df.columns = [c.lower() for c in df.columns]
    date_col = None
    for col in ['date', 'time', 'datetime']:
        if col in df.columns:
            date_col = col
            break
    if date_col is None:
        df.index = pd.to_datetime(df.index)
        df['date'] = df.index
    else:
        df['date'] = pd.to_datetime(df[date_col])
        df.drop(columns=[col for col in ['date', 'time', 'datetime'] if col != 'date' and col in df.columns], inplace=True)
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
    df = df.rename(columns=col_map)
    required = ['Open', 'High', 'Low', 'Close']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing column {col}")
    if 'Volume' not in df.columns:
        df['Volume'] = 1
    if 'Date' not in df.columns:
        df['Date'] = df['date'] if 'date' in df.columns else df.index
    # Optionally limit rows for quick testing
    if BARS_LIMIT is not None and len(df) > BARS_LIMIT:
        df = df.tail(BARS_LIMIT).reset_index(drop=True)
        print(f"      Using last {BARS_LIMIT} bars (full data has {len(df)} rows).")
    return df

def get_default_params(strategy_name):
    if strategy_name in DEFAULT_PARAMS:
        return DEFAULT_PARAMS[strategy_name]
    for key, params in DEFAULT_PARAMS.items():
        if strategy_name in key or key in strategy_name:
            return params
    return None

def backtest_with_params(strategy_name, symbol, params, df, dna_context=None):
    matched_key = find_strategy_key(strategy_name, OPTIMIZER_STRATEGY_MAP)
    if matched_key is None:
        print(f"      ⚠️ Strategy '{strategy_name}' not found in optimizer map.")
        return None
    strategy_class = OPTIMIZER_STRATEGY_MAP[matched_key][0]
    strategy = strategy_class(**params)
    engine = FastBacktesterEngine(
        df=df,
        strategy=strategy,
        symbol=symbol,
        initial_capital=INITIAL_CAPITAL,
        risk_per_trade=RISK_PER_TRADE,
        timeframe=TIMEFRAME,
        verbose=False,
        dna_context=dna_context
    )
    try:
        report = engine.run(show_progress=False)
        return report
    except Exception as e:
        print(f"      ❌ Backtest exception: {e}")
        traceback.print_exc()
        return None

# ============================================================================
# Main
# ============================================================================
def main():
    print("🚀 Backtesting Optimized Strategies")
    print(f"   Using BARS_LIMIT = {BARS_LIMIT if BARS_LIMIT else 'FULL'}")
    print("=" * 60)

    opt_files = glob.glob(os.path.join(OPTIMIZED_DIR, "*_final.json"))
    if not opt_files:
        print("❌ No optimized results found.")
        return

    print(f"📋 Found {len(opt_files)} optimized strategy/symbol combinations.")

    results = []
    pbar = tqdm(opt_files, desc="Backtesting", unit="file")

    for idx, opt_file in enumerate(pbar, 1):
        basename = os.path.basename(opt_file).replace('_final.json', '')
        parts = basename.rsplit('_', 1)
        if len(parts) != 2:
            print(f"⚠️ Skipping unparseable: {basename}")
            continue
        strategy_name, symbol = parts[0], parts[1]
        pbar.set_description(f"{idx}/{len(opt_files)} {strategy_name} on {symbol}")

        # Load optimized params
        try:
            with open(opt_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"      ❌ Error loading {opt_file}: {e}")
            continue
        best_params = data.get('best_params')
        if not best_params:
            print(f"      ⚠️ No best_params in {opt_file}")
            continue

        # Load data
        csv_path = find_csv_file(symbol)
        if csv_path is None:
            print(f"      ⚠️ No data for {symbol}, skipping.")
            continue
        print(f"      Loading data from {csv_path}...")
        df = load_data(csv_path)
        print(f"      Data loaded: {len(df)} rows.")

        # DNA context
        dna_context = get_dna_context(symbol, TIMEFRAME)
        if dna_context:
            print(f"      DNA context loaded.")
        else:
            print(f"      ⚠️ No DNA context found.")

        # Optimized backtest
        print(f"      Running optimized backtest...")
        report_opt = backtest_with_params(strategy_name, symbol, best_params, df, dna_context)
        if report_opt is None:
            print(f"      ❌ Optimized backtest failed.")
            continue
        print(f"      ✅ Optimized backtest done. Trades: {report_opt.get('total_trades', 0)}, Sharpe: {report_opt.get('sharpe_ratio', 0):.4f}")

        # Default backtest
        default_params = get_default_params(strategy_name)
        report_def = None
        if default_params:
            print(f"      Running default backtest...")
            report_def = backtest_with_params(strategy_name, symbol, default_params, df, dna_context)
            if report_def:
                print(f"      ✅ Default backtest done. Trades: {report_def.get('total_trades', 0)}, Sharpe: {report_def.get('sharpe_ratio', 0):.4f}")

        record = {
            'strategy': strategy_name,
            'symbol': symbol,
            'optimized_fitness': data.get('best_fitness'),
            'optimized_trades': report_opt.get('total_trades', 0),
            'optimized_win_rate': report_opt.get('win_rate', 0),
            'optimized_sharpe': report_opt.get('sharpe_ratio', 0),
            'optimized_pnl': report_opt.get('total_pnl', 0),
            'optimized_return': report_opt.get('return_pct', 0),
            'optimized_max_dd': report_opt.get('max_drawdown', 0),
        }
        if report_def is not None:
            record['default_trades'] = report_def.get('total_trades', 0)
            record['default_win_rate'] = report_def.get('win_rate', 0)
            record['default_sharpe'] = report_def.get('sharpe_ratio', 0)
            record['default_pnl'] = report_def.get('total_pnl', 0)
            record['default_return'] = report_def.get('return_pct', 0)
            record['default_max_dd'] = report_def.get('max_drawdown', 0)
            record['pnl_improvement'] = record['optimized_pnl'] - record['default_pnl']
            record['sharpe_improvement'] = record['optimized_sharpe'] - record['default_sharpe']

        results.append(record)

    if not results:
        print("❌ No backtest results generated.")
        return

    df_results = pd.DataFrame(results)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    summary_csv = os.path.join(OUTPUT_DIR, f"optimized_backtest_summary_{timestamp}.csv")
    df_results.to_csv(summary_csv, index=False)
    print(f"💾 Summary saved to {summary_csv}")

    # Print summary stats
    print("\n📊 Summary Stats (Optimized vs Default):")
    if 'default_sharpe' in df_results.columns:
        avg_opt_sharpe = df_results['optimized_sharpe'].mean()
        avg_def_sharpe = df_results['default_sharpe'].mean()
        print(f"  Average Optimized Sharpe: {avg_opt_sharpe:.4f}")
        print(f"  Average Default Sharpe:   {avg_def_sharpe:.4f}")
        print(f"  Improvement:              {avg_opt_sharpe - avg_def_sharpe:+.4f}")
    else:
        print(f"  Total Optimized PnL: ${df_results['optimized_pnl'].sum():,.2f}")
        print(f"  Average Win Rate: {df_results['optimized_win_rate'].mean():.2f}%")

    # Also save as JSON
    summary_json = os.path.join(OUTPUT_DIR, f"optimized_backtest_summary_{timestamp}.json")
    df_results.to_json(summary_json, orient='records', indent=2)
    print(f"💾 JSON summary saved to {summary_json}")

    print("\n✅ Done.")

if __name__ == "__main__":
    main()