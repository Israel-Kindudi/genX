#!/usr/bin/env python
"""
Aggregate all backtest summary CSV files into one comprehensive CSV.
Scans current directory and backtest_reports/ for *_summary.csv files.
"""
import os
import glob
import pandas as pd

def main():
    summary_files = []
    # Look in root
    summary_files.extend(glob.glob("*_summary.csv"))
    # Look in backtest_reports
    summary_files.extend(glob.glob("backtest_reports/*_summary.csv"))
    # Look in any other likely folders
    summary_files.extend(glob.glob("**/*_summary.csv", recursive=True))
    
    # Remove duplicates
    summary_files = list(set(summary_files))
    print(f"Found {len(summary_files)} summary files.")
    
    all_dfs = []
    for f in summary_files:
        try:
            df = pd.read_csv(f)
            # Check if it has the expected columns
            required = ['Symbol', 'Strategy', 'Trades']
            if all(c in df.columns for c in required):
                # Add source file for tracking
                df['source_file'] = os.path.basename(f)
                all_dfs.append(df)
                print(f"  Loaded: {f} ({len(df)} rows)")
            else:
                print(f"  Skipping: {f} (missing columns)")
        except Exception as e:
            print(f"  Error reading {f}: {e}")
    
    if not all_dfs:
        print("No valid summary files found.")
        return
    
    combined = pd.concat(all_dfs, ignore_index=True)
    # Drop duplicates based on Symbol, Strategy, Timeframe, Trades (keep first)
    combined = combined.drop_duplicates(subset=['Symbol', 'Strategy', 'Timeframe', 'Trades'], keep='first')
    
    # Sort by Symbol, Strategy
    combined = combined.sort_values(['Symbol', 'Strategy']).reset_index(drop=True)
    
    # Save
    combined.to_csv("backtest_full_summary_combined.csv", index=False)
    print(f"\n✅ Combined summary saved to backtest_full_summary_combined.csv")
    print(f"   Total rows: {len(combined)}")
    print(f"   Unique symbols: {combined['Symbol'].nunique()}")
    print(f"   Unique strategies: {combined['Strategy'].nunique()}")
    
    # Show which symbols are included
    print("\n📋 Symbols in combined summary:")
    for sym in sorted(combined['Symbol'].unique()):
        print(f"  - {sym}")

if __name__ == "__main__":
    main()