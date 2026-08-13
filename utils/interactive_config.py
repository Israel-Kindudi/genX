#!/usr/bin/env python
"""
Interactive configuration for live trading.
Reads strategy grouping CSV and prompts the user to select strategies and symbols.
Now supports breakeven trigger, profit lock, and other parameters.
"""

import sys
import os
import json
import pandas as pd
from typing import List, Optional

# Ensure project root is in sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ------------------------------------------------------------------------
# Default config file location
# ------------------------------------------------------------------------
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "live_config_interactive.json")

def load_strategy_groups(csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load the strategy grouping CSV.
    Expects columns: Strategy, Group (or score/rating).
    If not found, returns an empty DataFrame.
    """
    if csv_path is None:
        possible_paths = [
            "analysis/strategy_groups.csv",
            "strategy_groups.csv",
            "../analysis/strategy_groups.csv"
        ]
        for p in possible_paths:
            if os.path.exists(p):
                csv_path = p
                break
    if csv_path and os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        group_col = None
        for col in ['group', 'category', 'rating', 'performance']:
            if col in df.columns:
                group_col = col
                break
        if group_col is None:
            df['group'] = 'Unknown'
            group_col = 'group'
        strategy_col = None
        for col in ['strategy', 'Strategy', 'name', 'Name']:
            if col in df.columns:
                strategy_col = col
                break
        if strategy_col is None:
            strategy_col = df.columns[0]
        df.rename(columns={strategy_col: 'strategy', group_col: 'group'}, inplace=True)
        return df[['strategy', 'group']]
    return pd.DataFrame()

def interactive_select_strategies(available_strategies: List[str],
                                  grouping_csv: Optional[str] = None) -> List[str]:
    """
    Interactively select which strategies to enable.
    Uses strategy groups to suggest defaults.
    """
    print("\n" + "=" * 60)
    print("📊 Strategy Selection")
    print("=" * 60)

    df_groups = load_strategy_groups(grouping_csv)
    if not df_groups.empty:
        print("Found strategy groups:")
        groups = df_groups['group'].unique()
        for g in groups:
            count = len(df_groups[df_groups['group'] == g])
            print(f"  - {g}: {count} strategies")
        print()
        enabled_groups = []
        for g in groups:
            default = 'y' if g.lower() in ['good', 'average', 'medium'] else 'n'
            prompt = f"Enable {g} strategies? (y/n) [default={default}]: "
            resp = input(prompt).strip().lower()
            if resp == '':
                resp = default
            if resp in ['y', 'yes']:
                enabled_groups.append(g)
        enabled_from_groups = df_groups[df_groups['group'].isin(enabled_groups)]['strategy'].tolist()
        print(f"\n✅ Enabled {len(enabled_from_groups)} strategies from groups: {enabled_groups}")
        if input("Review individual strategies? (y/n) [default=n]: ").strip().lower() in ['y', 'yes']:
            enabled_from_groups = _review_strategies(enabled_from_groups, available_strategies)
        return enabled_from_groups
    else:
        print("No strategy grouping file found. Please select strategies individually.")
        enabled = []
        for s in available_strategies:
            resp = input(f"Enable '{s}'? (y/n) [default=y]: ").strip().lower()
            if resp == '' or resp in ['y', 'yes']:
                enabled.append(s)
        return enabled

def _review_strategies(current_enabled: List[str], all_strategies: List[str]) -> List[str]:
    print("\n📋 Current enabled strategies:")
    for i, s in enumerate(current_enabled, 1):
        print(f"  {i}. {s}")
    while True:
        resp = input("\nEnter number to toggle, 'done' to finish: ").strip().lower()
        if resp == 'done':
            break
        try:
            idx = int(resp) - 1
            if 0 <= idx < len(current_enabled):
                s = current_enabled[idx]
                current_enabled.pop(idx)
                print(f"❌ Removed '{s}'")
            else:
                print("Invalid number.")
        except ValueError:
            resp2 = input("Add strategy name (or 'done'): ").strip()
            if resp2.lower() == 'done':
                break
            if resp2 in all_strategies and resp2 not in current_enabled:
                current_enabled.append(resp2)
                print(f"✅ Added '{resp2}'")
            else:
                print("Strategy not found or already enabled.")
    return current_enabled

def interactive_select_symbols(all_symbols: List[str]) -> List[str]:
    print("\n" + "=" * 60)
    print("💹 Symbol Selection")
    print("=" * 60)
    prompt = (f"Enter symbols to enable (comma-separated), or 'all' for all, 'none' for none. "
              f"\nAvailable: {', '.join(all_symbols)}\n> ")
    resp = input(prompt).strip()
    if resp.lower() == 'all':
        return all_symbols
    if resp.lower() == 'none':
        return []
    chosen = [s.strip() for s in resp.split(',') if s.strip()]
    valid = [s for s in chosen if s in all_symbols]
    invalid = [s for s in chosen if s not in all_symbols]
    if invalid:
        print(f"⚠️ Invalid symbol(s): {invalid}")
    if not valid:
        print("No valid symbols selected. Enabling all as fallback.")
        return all_symbols
    return valid

def save_config(config: dict, path: str = DEFAULT_CONFIG_PATH):
    """
    Save the selected configuration to a JSON file.
    Includes profit_lock_fraction if present.
    """
    # Ensure all keys are present
    config.setdefault('profit_lock_fraction', 0.5)
    with open(path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Configuration saved to {path}")

def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """
    Load a saved configuration.
    """
    if os.path.exists(path):
        with open(path, 'r') as f:
            config = json.load(f)
        # Ensure backward compatibility
        if 'profit_lock_fraction' not in config:
            config['profit_lock_fraction'] = 0.5
        return config
    return {}

# ============================================================================
# MAIN – Run interactive config standalone
# ============================================================================
if __name__ == "__main__":
    # Define all symbols (from config or hardcoded)
    ALL_SYMBOLS = ["BreakX 600", "BreakX 1200", "BreakX 1800", "PainX 600", "GainX 800",
                   "FX Vol 20", "FX Vol 40", "FX Vol 60", "FX Vol 80", "FX Vol 99"]

    # Load strategies from backtest if possible
    try:
        from live_trading.live_engine import load_strategies_from_backtest
        available_strategies = load_strategies_from_backtest()
        print(f"✅ Loaded {len(available_strategies)} strategies from backtest.")
    except Exception as e:
        print(f"⚠️ Could not load strategies from backtest: {e}")
        # fallback
        available_strategies = ["Scalping DMI+MACD (default)", "Scalping DMI+MACD (tuned)", "Scalping HMA+Stoch (tuned)"]
        print("Using fallback strategy list.")

    print("Starting interactive configuration...")
    print("If you want to skip this and use a config file, press Ctrl+C now.")

    try:
        selected_symbols = interactive_select_symbols(ALL_SYMBOLS)
        selected_strategies = interactive_select_strategies(available_strategies)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
        sys.exit(0)

    # Build config
    config = {
        'symbols': selected_symbols,
        'strategies': selected_strategies,
        'demo': True,
        'cycles': 100,
        'interval': 60,
        'risk': 1.0,
        'terminal': None,
        'max_positions': 7,
        'max_per_strategy': 3,
        'use_optimized': False,
        'breakeven_trigger': 0.0,
        'profit_lock_fraction': 0.5,
    }

    # Ask user for additional settings
    print("\nAdditional settings:")
    demo_input = input("Run in demo mode? (y/n) [default=y]: ").strip().lower()
    if demo_input == 'n':
        config['demo'] = False

    cycles_input = input("Number of cycles [default=100]: ").strip()
    if cycles_input.isdigit():
        config['cycles'] = int(cycles_input)

    interval_input = input("Interval between cycles (seconds) [default=60]: ").strip()
    if interval_input.isdigit():
        config['interval'] = int(interval_input)

    risk_input = input("Risk per trade (% of equity) [default=1.0]: ").strip()
    if risk_input:
        try:
            config['risk'] = float(risk_input)
        except:
            pass

    breakeven_input = input("Breakeven trigger (fraction of initial stop, 0=off) [default=0.0]: ").strip()
    if breakeven_input:
        try:
            config['breakeven_trigger'] = float(breakeven_input)
        except:
            pass

    profit_lock_input = input("Profit lock fraction (fraction of current profit to lock) [default=0.5]: ").strip()
    if profit_lock_input:
        try:
            config['profit_lock_fraction'] = float(profit_lock_input)
        except:
            pass

    use_opt_input = input("Use optimized parameters? (y/n) [default=n]: ").strip().lower()
    if use_opt_input == 'y':
        config['use_optimized'] = True

    # Save
    save_config(config, DEFAULT_CONFIG_PATH)
    print(f"\n✅ Configuration saved to {DEFAULT_CONFIG_PATH}")
    print("You can now run the live engine with: python feature/run_live.py")