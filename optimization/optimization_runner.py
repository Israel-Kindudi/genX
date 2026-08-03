#!/usr/bin/env python
"""
Run optimization sequentially for each strategy/symbol based on grouping.
Saves incremental results.
Includes overall progress bar.
"""

import os
import sys
import json
import time
import pandas as pd
import glob
from datetime import datetime
from tqdm import tqdm

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from analysis.strategy_grouping import load_backtest_summary, group_strategies
from optimization.strategy_optimizer import optimize_strategy, get_dna_context, STRATEGY_MAP, find_strategy_key
from config import DATA_DIR

def load_data_for_symbol(symbol, timeframe='M5'):
    """Load OHLC data for a symbol and timeframe."""
    pattern = f"{DATA_DIR}/{symbol}_PERIODE_{timeframe}_data.csv"
    files = glob.glob(pattern)
    if not files:
        # Try with different naming
        files = glob.glob(f"{DATA_DIR}/*{symbol}*{timeframe}*.csv")
    if not files:
        raise FileNotFoundError(f"No data for {symbol} {timeframe}")
    csv_file = files[0]
    df = pd.read_csv(csv_file)
    # Normalize columns (simplified)
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

def main():
    print("="*80)
    print("🚀 STRATEGY OPTIMIZATION RUNNER")
    print("="*80)
    
    # Load backtest summary and group
    df_summary = load_backtest_summary()
    groups, _ = group_strategies(df_summary)
    
    # Collect strategies from excellent and good groups
    strategies_to_optimize = []
    for group_name in ['excellent', 'good']:
        group_df = groups.get(group_name, pd.DataFrame())
        if not group_df.empty:
            for _, row in group_df.iterrows():
                strategies_to_optimize.append(row['Strategy'])
    
    if not strategies_to_optimize:
        print("No strategies to optimize.")
        return
    
    # Remove duplicates
    strategies_to_optimize = list(set(strategies_to_optimize))
    print(f"🧬 Strategies to optimize: {strategies_to_optimize}")
    
    # Define symbols and timeframes to use
    symbols = ["BreakX 600", "BreakX 1200", "BreakX 1800"]
    timeframe = "M5"
    
    # Filter strategies that exist in the map
    valid_strategies = []
    for s in strategies_to_optimize:
        if find_strategy_key(s, STRATEGY_MAP) is not None:
            valid_strategies.append(s)
        else:
            print(f"⚠️ Strategy '{s}' not in STRATEGY_MAP, skipping.")
    
    if not valid_strategies:
        print("No valid strategies to optimize.")
        return
    
    total_jobs = len(valid_strategies) * len(symbols)
    print(f"Total optimization jobs: {total_jobs}")
    
    start_time = time.time()
    job_count = 0
    
    # Overall progress bar
    pbar = tqdm(total=total_jobs, desc="Overall Progress", unit="job")
    for strategy_name in valid_strategies:
        for symbol in symbols:
            job_count += 1
            pbar.set_description(f"Job {job_count}/{total_jobs}: {strategy_name} on {symbol}")
            print(f"\n📊 Job {job_count}/{total_jobs}: {strategy_name} on {symbol}")
            try:
                # Load data
                df = load_data_for_symbol(symbol, timeframe)
                if df is None or len(df) < 200:
                    print(f"   ⚠️ Insufficient data for {symbol}, skipping.")
                    pbar.update(1)
                    continue
                # Load DNA context
                dna_context = get_dna_context(symbol, timeframe)
                # Run optimization
                result = optimize_strategy(
                    strategy_name, 
                    symbol, 
                    df, 
                    dna_context,
                    output_dir="optimized_strategies",
                    generations=8,  # Fast for demo
                    pop_size=15
                )
                if result:
                    print(f"   ✅ Optimization complete for {strategy_name} on {symbol}")
                else:
                    print(f"   ❌ Optimization failed for {strategy_name} on {symbol}")
            except Exception as e:
                print(f"   ❌ Error: {e}")
                import traceback
                traceback.print_exc()
            pbar.update(1)
    
    pbar.close()
    elapsed = time.time() - start_time
    print(f"\n✅ All optimizations completed in {elapsed/60:.1f} minutes.")
    print("📁 Results saved in 'optimized_strategies/'")

if __name__ == "__main__":
    main()