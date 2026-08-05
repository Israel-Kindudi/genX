#!/usr/bin/env python
"""
Interactive configuration for live trading.
Reads strategy grouping CSV and prompts the user to select strategies and symbols.
"""

import os
import json
import pandas as pd
from typing import List, Optional

# ------------------------------------------------------------------------
# Default config file location (user's home directory or project root)
# ------------------------------------------------------------------------
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "live_config_interactive.json")


def load_strategy_groups(csv_path: Optional[str] = None) -> pd.DataFrame:
    """
    Load the strategy grouping CSV.
    Expects columns: Strategy, Group (or score/rating).
    If not found, returns an empty DataFrame.
    """
    if csv_path is None:
        # Try common locations
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
        # Ensure we have a column that identifies groups
        # Look for 'group', 'category', 'rating', 'performance'
        group_col = None
        for col in ['group', 'category', 'rating', 'performance']:
            if col in df.columns:
                group_col = col
                break
        if group_col is None:
            # Fallback: treat all as 'Unknown'
            df['group'] = 'Unknown'
            group_col = 'group'
        # Also need a strategy name column
        strategy_col = None
        for col in ['strategy', 'Strategy', 'name', 'Name']:
            if col in df.columns:
                strategy_col = col
                break
        if strategy_col is None:
            # If no strategy column, assume first column is strategy
            strategy_col = df.columns[0]
        # Normalize column names
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

    # Load grouping if available
    df_groups = load_strategy_groups(grouping_csv)
    if not df_groups.empty:
        print("Found strategy groups:")
        # Show groups
        groups = df_groups['group'].unique()
        for g in groups:
            count = len(df_groups[df_groups['group'] == g])
            print(f"  - {g}: {count} strategies")
        print()
        # Ask user which groups to enable
        enabled_groups = []
        for g in groups:
            # Suggest default: enable 'Good' and 'Average', disable 'Poor'
            default = 'y' if g.lower() in ['good', 'average', 'medium'] else 'n'
            prompt = f"Enable {g} strategies? (y/n) [default={default}]: "
            resp = input(prompt).strip().lower()
            if resp == '':
                resp = default
            if resp in ['y', 'yes']:
                enabled_groups.append(g)
        # Collect strategies from enabled groups
        enabled_from_groups = df_groups[df_groups['group'].isin(enabled_groups)]['strategy'].tolist()
        print(f"\n✅ Enabled {len(enabled_from_groups)} strategies from groups: {enabled_groups}")
        # Ask to review individual strategies
        if input("Review individual strategies? (y/n) [default=n]: ").strip().lower() in ['y', 'yes']:
            enabled_from_groups = _review_strategies(enabled_from_groups, available_strategies)
        return enabled_from_groups

    else:
        # No grouping file: list all strategies and ask individually
        print("No strategy grouping file found. Please select strategies individually.")
        enabled = []
        for s in available_strategies:
            resp = input(f"Enable '{s}'? (y/n) [default=y]: ").strip().lower()
            if resp == '' or resp in ['y', 'yes']:
                enabled.append(s)
        return enabled


def _review_strategies(current_enabled: List[str], all_strategies: List[str]) -> List[str]:
    """
    Allow the user to toggle individual strategies.
    """
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
            # Allow adding a strategy by name
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
    """
    Interactively select which symbols to enable.
    Allows comma-separated list, 'all', 'none', or individual selection.
    """
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

    # Comma-separated
    chosen = [s.strip() for s in resp.split(',') if s.strip()]
    # Validate
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
    """
    with open(path, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"✅ Configuration saved to {path}")


def load_config(path: str = DEFAULT_CONFIG_PATH) -> dict:
    """
    Load a saved configuration.
    """
    if os.path.exists(path):
        with open(path, 'r') as f:
            return json.load(f)
    return {}