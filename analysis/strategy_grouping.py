#!/usr/bin/env python
"""
Group strategies by performance metrics from backtest summary.
"""

import pandas as pd
import numpy as np
import os
import glob

def load_backtest_summary(csv_path=None):
    """Load the backtest summary CSV."""
    if csv_path is None:
        files = glob.glob("backtest_full_summary.csv")
        if not files:
            files = glob.glob("backtest_comparison.csv")
        if not files:
            raise FileNotFoundError("No backtest summary CSV found.")
        csv_path = files[0]
    df = pd.read_csv(csv_path)
    # Standardize columns
    df.columns = df.columns.str.strip()
    return df

def group_strategies(df, metrics=['Sharpe', 'Win Rate %', 'Profit Factor']):
    """
    Group strategies by performance.
    Returns a dict with groups: 'excellent', 'good', 'average', 'poor'
    """
    # Aggregate per strategy (mean across symbols/timeframes)
    if 'Strategy' not in df.columns:
        raise KeyError("Column 'Strategy' not found.")
    
    grouped = df.groupby('Strategy').agg({
        'Sharpe': 'mean',
        'Win Rate %': 'mean',
        'Profit Factor': 'mean',
        'Total PnL': 'sum',
        'Trades': 'sum'
    }).reset_index()
    
    # Define thresholds
    def categorize(row):
        sharpe = row['Sharpe']
        win_rate = row['Win Rate %']
        pf = row['Profit Factor']
        if sharpe > 1.0 and win_rate > 50 and pf > 1.5:
            return 'excellent'
        elif sharpe > 0.5 and win_rate > 45 and pf > 1.2:
            return 'good'
        elif sharpe > 0.0 and win_rate > 40 and pf > 0.8:
            return 'average'
        else:
            return 'poor'
    
    grouped['group'] = grouped.apply(categorize, axis=1)
    
    # Separate into dict
    groups = {
        'excellent': grouped[grouped['group'] == 'excellent'],
        'good': grouped[grouped['group'] == 'good'],
        'average': grouped[grouped['group'] == 'average'],
        'poor': grouped[grouped['group'] == 'poor']
    }
    
    return groups, grouped

def save_grouping_report(groups, output_dir="analysis_results"):
    os.makedirs(output_dir, exist_ok=True)
    for group_name, df in groups.items():
        if not df.empty:
            df.to_csv(f"{output_dir}/strategies_{group_name}.csv", index=False)
    print(f"💾 Grouping reports saved to {output_dir}/")

if __name__ == "__main__":
    df = load_backtest_summary()
    groups, all_grouped = group_strategies(df)
    save_grouping_report(groups)
    print("Strategy grouping complete.")