#!/usr/bin/env python
"""
Analyze optimization results from the batch optimizer.
Reads all *_final.json and *_evaluations.csv files from optimized_strategies/.
Generates summary statistics, rankings, and parameter insights.
"""

import os
import sys
import json
import glob
import pandas as pd
import numpy as np
from datetime import datetime
from collections import defaultdict

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ============================================================================
# Configuration
# ============================================================================
OPT_DIR = "optimized_strategies"
OUTPUT_DIR = "analysis/optimization_analysis"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================================
# Helper functions
# ============================================================================
def parse_strategy_symbol_from_filename(filename):
    """Extract strategy name and symbol from the base filename."""
    basename = os.path.basename(filename).replace('_final.json', '')
    # Assume format: "{strategy_name}_{symbol}"
    # Strategy names may contain underscores, so we split at the last underscore.
    parts = basename.rsplit('_', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        # Fallback: treat whole as strategy, symbol unknown
        return basename, "Unknown"

def load_final_json(filepath):
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        return data
    except:
        return None

def load_evaluation_csv(strategy, symbol):
    """Load the evaluation CSV for a given strategy/symbol."""
    csv_file = os.path.join(OPT_DIR, f"{strategy}_{symbol}_evaluations.csv")
    if os.path.exists(csv_file):
        try:
            return pd.read_csv(csv_file)
        except:
            return None
    return None

# ============================================================================
# Main analysis
# ============================================================================
def main():
    print("🔍 Analyzing Optimization Results")
    print("=" * 60)

    # Find all final JSON files
    final_files = glob.glob(os.path.join(OPT_DIR, "*_final.json"))
    if not final_files:
        print("❌ No final JSON files found.")
        return

    print(f"📋 Found {len(final_files)} optimized strategy/symbol combinations.")

    # Prepare data structures
    records = []
    strategy_stats = defaultdict(lambda: {'count': 0, 'best_fitness': [], 'sharpe': [], 'pnl': [], 'trades': []})
    symbol_stats = defaultdict(lambda: {'count': 0, 'best_fitness': [], 'sharpe': [], 'pnl': [], 'trades': []})

    for filepath in final_files:
        strategy_name, symbol = parse_strategy_symbol_from_filename(filepath)
        data = load_final_json(filepath)
        if data is None:
            print(f"⚠️ Could not load {filepath}")
            continue

        # Extract basic info
        best_fitness = data.get('best_fitness', None)
        best_params = data.get('best_params', {})
        best_report = data.get('best_report', {})
        if best_report is None:
            best_report = {}

        trades = best_report.get('total_trades', 0)
        win_rate = best_report.get('win_rate', 0)
        sharpe = best_report.get('sharpe_ratio', 0)
        pnl = best_report.get('total_pnl', 0)
        max_dd = best_report.get('max_drawdown', 0)
        return_pct = best_report.get('return_pct', 0)

        # Build record
        record = {
            'strategy': strategy_name,
            'symbol': symbol,
            'best_fitness': best_fitness,
            'trades': trades,
            'win_rate': win_rate,
            'sharpe': sharpe,
            'pnl': pnl,
            'max_drawdown': max_dd,
            'return_pct': return_pct,
            'best_params': best_params,
            'file': filepath,
        }
        records.append(record)

        # Update stats
        strategy_stats[strategy_name]['count'] += 1
        strategy_stats[strategy_name]['best_fitness'].append(best_fitness)
        strategy_stats[strategy_name]['sharpe'].append(sharpe)
        strategy_stats[strategy_name]['pnl'].append(pnl)
        strategy_stats[strategy_name]['trades'].append(trades)

        symbol_stats[symbol]['count'] += 1
        symbol_stats[symbol]['best_fitness'].append(best_fitness)
        symbol_stats[symbol]['sharpe'].append(sharpe)
        symbol_stats[symbol]['pnl'].append(pnl)
        symbol_stats[symbol]['trades'].append(trades)

    if not records:
        print("❌ No valid records to analyse.")
        return

    # Convert to DataFrame for easy analysis
    df = pd.DataFrame(records)

    # ---- Summary Statistics ----
    print("\n📊 Summary Statistics per Strategy:")
    for strat, stats in strategy_stats.items():
        count = stats['count']
        avg_fitness = np.mean(stats['best_fitness']) if stats['best_fitness'] else 0
        avg_sharpe = np.mean(stats['sharpe']) if stats['sharpe'] else 0
        avg_pnl = np.mean(stats['pnl']) if stats['pnl'] else 0
        total_trades = sum(stats['trades']) if stats['trades'] else 0
        print(f"  {strat}:")
        print(f"    Count: {count}, Avg Fitness: {avg_fitness:.4f}, Avg Sharpe: {avg_sharpe:.4f}, Avg PnL: ${avg_pnl:.2f}, Total Trades: {total_trades}")

    print("\n📊 Summary Statistics per Symbol:")
    for sym, stats in symbol_stats.items():
        count = stats['count']
        avg_fitness = np.mean(stats['best_fitness']) if stats['best_fitness'] else 0
        avg_sharpe = np.mean(stats['sharpe']) if stats['sharpe'] else 0
        avg_pnl = np.mean(stats['pnl']) if stats['pnl'] else 0
        total_trades = sum(stats['trades']) if stats['trades'] else 0
        print(f"  {sym}:")
        print(f"    Count: {count}, Avg Fitness: {avg_fitness:.4f}, Avg Sharpe: {avg_sharpe:.4f}, Avg PnL: ${avg_pnl:.2f}, Total Trades: {total_trades}")

    # ---- Top Performers ----
    print("\n🏆 Top 10 Best Sharpe Ratio:")
    top_sharpe = df.nlargest(10, 'sharpe')
    print(top_sharpe[['strategy', 'symbol', 'sharpe', 'pnl', 'win_rate', 'trades']].to_string(index=False))

    print("\n🏆 Top 10 Best PnL:")
    top_pnl = df.nlargest(10, 'pnl')
    print(top_pnl[['strategy', 'symbol', 'pnl', 'sharpe', 'win_rate', 'trades']].to_string(index=False))

    print("\n🏆 Top 10 Best Fitness:")
    top_fitness = df.nlargest(10, 'best_fitness')
    print(top_fitness[['strategy', 'symbol', 'best_fitness', 'sharpe', 'pnl']].to_string(index=False))

    # ---- Parameter Analysis (if we have parameters) ----
    # Extract parameters into separate columns
    param_df = df[['strategy', 'symbol', 'best_fitness', 'sharpe', 'pnl']].copy()
    params_list = []
    for idx, row in df.iterrows():
        params = row['best_params']
        for k, v in params.items():
            param_df.loc[idx, f'param_{k}'] = v

    # Compute correlation between parameters and fitness (if enough data)
    param_cols = [c for c in param_df.columns if c.startswith('param_')]
    if len(param_cols) > 0 and len(param_df) > 10:
        print("\n📈 Correlation between parameters and fitness:")
        for col in param_cols:
            corr = param_df[col].corr(param_df['best_fitness'])
            print(f"  {col}: {corr:.4f}")

    # ---- Save to CSV ----
    summary_csv = os.path.join(OUTPUT_DIR, f"optimization_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    df.to_csv(summary_csv, index=False)
    print(f"\n💾 Full summary saved to {summary_csv}")

    # Save top performers separately
    top_sharpe.to_csv(os.path.join(OUTPUT_DIR, "top_sharpe.csv"), index=False)
    top_pnl.to_csv(os.path.join(OUTPUT_DIR, "top_pnl.csv"), index=False)

    # ---- Additional Insights: What strategies are best on which symbols ----
    print("\n💡 Best Strategy per Symbol (by Sharpe):")
    best_per_symbol = df.loc[df.groupby('symbol')['sharpe'].idxmax()]
    print(best_per_symbol[['symbol', 'strategy', 'sharpe', 'pnl']].to_string(index=False))

    print("\n💡 Best Symbol per Strategy (by Sharpe):")
    best_per_strategy = df.loc[df.groupby('strategy')['sharpe'].idxmax()]
    print(best_per_strategy[['strategy', 'symbol', 'sharpe', 'pnl']].to_string(index=False))

    # ---- Save an aggregated summary JSON ----
    summary_json = {
        'total_combinations': len(records),
        'strategies': {s: {'count': strategy_stats[s]['count'],
                           'avg_sharpe': np.mean(strategy_stats[s]['sharpe']) if strategy_stats[s]['sharpe'] else 0,
                           'avg_pnl': np.mean(strategy_stats[s]['pnl']) if strategy_stats[s]['pnl'] else 0,
                           'total_trades': sum(strategy_stats[s]['trades']) if strategy_stats[s]['trades'] else 0}
                       for s in strategy_stats},
        'symbols': {s: {'count': symbol_stats[s]['count'],
                        'avg_sharpe': np.mean(symbol_stats[s]['sharpe']) if symbol_stats[s]['sharpe'] else 0,
                        'avg_pnl': np.mean(symbol_stats[s]['pnl']) if symbol_stats[s]['pnl'] else 0,
                        'total_trades': sum(symbol_stats[s]['trades']) if symbol_stats[s]['trades'] else 0}
                    for s in symbol_stats},
        'top_sharpe': top_sharpe[['strategy', 'symbol', 'sharpe', 'pnl']].to_dict(orient='records'),
        'top_pnl': top_pnl[['strategy', 'symbol', 'pnl', 'sharpe']].to_dict(orient='records')
    }
    with open(os.path.join(OUTPUT_DIR, "optimization_summary.json"), 'w') as f:
        json.dump(summary_json, f, indent=2, default=str)

    print(f"\n✅ Analysis complete. Results saved to {OUTPUT_DIR}/")

# ============================================================================
# Entry point
# ============================================================================
if __name__ == "__main__":
    main()