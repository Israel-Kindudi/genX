#!/usr/bin/env python
"""
CLI launcher for the GenX live trading engine.
Allows interactive selection, config file, and full parameter customisation.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Dict, Any

# ------------------------------------------------------------
# Ensure project root is in sys.path
# ------------------------------------------------------------
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from live_trading.live_multi_terminal import LiveTradingEngine, ALL_SYMBOLS
from live_trading.live_multi_terminal import load_strategies_from_backtest

# Try to import interactive helpers
try:
    from utils.interactive_config import (
        interactive_select_strategies,
        interactive_select_symbols,
        save_config,
        load_config,
        DEFAULT_CONFIG_PATH
    )
except ImportError:
    def interactive_select_strategies(strategies, grouping_csv=None):
        return strategies
    def interactive_select_symbols(symbols):
        return symbols
    def save_config(config, path=None):
        print("Config saved (interactive_config not available)")
    def load_config(path=None):
        return {}
    DEFAULT_CONFIG_PATH = "live_config_interactive.json"


# ============================================================================
#  COMMAND LINE ARGUMENT PARSING
# ============================================================================
def parse_args():
    parser = argparse.ArgumentParser(
        description="GenX Live Trading Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (demo mode, all symbols, strategies from backtest)
  python run_live.py

  # Interactive setup (prompts for strategies and symbols)
  python run_live.py

  # Trade only specific symbols and strategies
  python run_live.py -s "BreakX 600,FX Vol 20" -t "Scalping DMI+MACD (default),Trend Following ADX (default)"

  # Run real mode with custom risk, cycles, and terminal
  python run_live.py --real --risk 2.0 --cycles 50 --interval 300 --terminal "C:\\Program Files\\MetaTrader 5\\terminal64.exe"

  # Load full configuration from JSON (supports all engine parameters)
  python run_live.py --config full_config.json
        """
    )

    # Symbol selection
    parser.add_argument(
        "-s", "--symbols",
        type=str,
        help="Comma-separated list of symbols to trade."
    )

    # Strategy selection
    parser.add_argument(
        "-t", "--strategies",
        type=str,
        help="Comma-separated list of strategy names."
    )

    # Mode
    parser.add_argument(
        "--demo",
        action="store_true",
        default=True,
        help="Run in demo mode (default)."
    )
    parser.add_argument(
        "--real",
        action="store_false",
        dest="demo",
        help="Run in real mode."
    )

    # Core parameters
    parser.add_argument(
        "--cycles",
        type=int,
        default=100,
        help="Number of trading cycles (default: 100)."
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=200,
        help="Number of historical bars per cycle (default: 200)."
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Sleep interval between cycles in seconds (default: 60)."
    )
    parser.add_argument(
        "--risk",
        type=float,
        default=1.0,
        help="Risk per trade as percentage of equity (default: 1.0)."
    )

    # Terminal path
    parser.add_argument(
        "--terminal",
        type=str,
        help="Path to the MT5 terminal executable."
    )

    # Additional engine parameters (can be overridden via config)
    parser.add_argument(
        "--max-positions",
        type=int,
        default=7,
        help="Maximum total open positions (default: 7)."
    )
    parser.add_argument(
        "--max-per-strategy",
        type=int,
        default=3,
        help="Maximum positions per strategy (default: 3)."
    )
    parser.add_argument(
        "--use-optimized",
        action="store_true",
        help="Use optimized parameters from optimization_results."
    )

    # Configuration file
    parser.add_argument(
        "-c", "--config",
        type=str,
        help="Load configuration from a JSON file (overrides CLI arguments)."
    )

    # Utility
    parser.add_argument(
        "--list-symbols",
        action="store_true",
        help="List available symbols and exit."
    )
    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="List strategies from backtest and exit."
    )

    return parser.parse_args()


# ============================================================================
#  CONFIG FILE LOADING
# ============================================================================
def load_config_file(path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


# ============================================================================
#  ENGINE INSTANTIATION HELPER
# ============================================================================
def create_engine_kwargs(args, config_override: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Build the keyword arguments for LiveTradingEngine, merging:
    - CLI arguments (args)
    - Config file overrides (if any)
    - Interactive selections (if any)
    """
    kwargs = {}

    # Map CLI args to engine parameters
    # Symbols & strategies are handled separately (as lists or None)
    if args.symbols:
        kwargs['symbols'] = [s.strip() for s in args.symbols.split(",")]
    else:
        kwargs['symbols'] = None

    if args.strategies:
        kwargs['strategy_list'] = [s.strip() for s in args.strategies.split(",")]
    else:
        kwargs['strategy_list'] = None

    kwargs['demo_mode'] = args.demo
    kwargs['verbose'] = True
    kwargs['risk_per_trade'] = args.risk
    kwargs['terminal_path'] = args.terminal or os.getenv("MT5_TERMINAL")
    kwargs['max_total_positions'] = args.max_positions
    kwargs['max_positions_per_strategy'] = args.max_per_strategy
    kwargs['use_optimized'] = args.use_optimized

    # Apply config file overrides (these take precedence over CLI)
    if config_override:
        for key, value in config_override.items():
            # Skip keys that are handled separately or are not engine parameters
            if key in ['symbols', 'strategies', 'demo', 'cycles', 'bars', 'interval', 'risk', 'terminal', 'max_positions', 'max_per_strategy', 'use_optimized']:
                continue
            # Map known engine parameters
            if key in ['max_total_positions', 'max_positions_per_strategy', 'use_optimized', 'risk_per_trade', 'demo_mode', 'verbose']:
                kwargs[key] = value
            elif key == 'terminal_path':
                kwargs['terminal_path'] = value
            elif key == 'symbols' and isinstance(value, list):
                kwargs['symbols'] = value
            elif key == 'strategies' and isinstance(value, list):
                kwargs['strategy_list'] = value

    return kwargs


# ============================================================================
#  MAIN
# ============================================================================
def main():
    args = parse_args()

    # Utility flags
    if args.list_symbols:
        print("Available symbols:")
        for sym in ALL_SYMBOLS:
            print(f"  - {sym}")
        return

    if args.list_strategies:
        strategies = load_strategies_from_backtest()
        print("Strategies loaded from backtest summary:")
        for s in strategies:
            print(f"  - {s}")
        return

    # Load config file if provided
    config_overrides = {}
    if args.config:
        config_overrides = load_config_file(args.config)
        # Override CLI args with config values (except those that are explicitly set)
        for key, value in config_overrides.items():
            if key == 'symbols' and isinstance(value, list):
                args.symbols = ",".join(value)
            elif key == 'strategies' and isinstance(value, list):
                args.strategies = ",".join(value)
            elif key == 'demo':
                args.demo = value
            elif key == 'cycles':
                args.cycles = value
            elif key == 'bars':
                args.bars = value
            elif key == 'interval':
                args.interval = value
            elif key == 'risk':
                args.risk = value
            elif key == 'terminal':
                args.terminal = value
            elif key == 'max_positions':
                args.max_positions = value
            elif key == 'max_per_strategy':
                args.max_per_strategy = value
            elif key == 'use_optimized':
                args.use_optimized = value

    # Interactive mode if no config, symbols, or strategies are provided
    if not args.config and not args.symbols and not args.strategies:
        print("No configuration provided. Entering interactive setup...")
        saved = load_config(DEFAULT_CONFIG_PATH)
        if saved:
            print("\n✅ Found previous configuration:")
            print(f"  Strategies: {saved.get('strategies', [])}")
            print(f"  Symbols: {saved.get('symbols', [])}")
            use_saved = input("Use this configuration? (y/n) [default=y]: ").strip().lower()
            if use_saved != 'n':
                if 'symbols' in saved and saved['symbols']:
                    args.symbols = ",".join(saved['symbols'])
                if 'strategies' in saved and saved['strategies']:
                    args.strategies = ",".join(saved['strategies'])
                if 'demo' in saved:
                    args.demo = saved['demo']
                if 'cycles' in saved:
                    args.cycles = saved['cycles']
                if 'interval' in saved:
                    args.interval = saved['interval']
                if 'risk' in saved:
                    args.risk = saved['risk']
                if 'terminal' in saved:
                    args.terminal = saved['terminal']
                if 'max_positions' in saved:
                    args.max_positions = saved['max_positions']
                if 'max_per_strategy' in saved:
                    args.max_per_strategy = saved['max_per_strategy']
                if 'use_optimized' in saved:
                    args.use_optimized = saved['use_optimized']

        # If still no symbols, ask
        if not args.symbols:
            symbols = interactive_select_symbols(ALL_SYMBOLS)
            args.symbols = ",".join(symbols)

        # If still no strategies, ask
        if not args.strategies:
            strategies = load_strategies_from_backtest()
            grouping_csv = os.getenv("STRATEGY_GROUPING_CSV", "analysis/strategy_groups.csv")
            if not os.path.exists(grouping_csv):
                for p in ["strategy_groups.csv", "../analysis/strategy_groups.csv"]:
                    if os.path.exists(p):
                        grouping_csv = p
                        break
            selected = interactive_select_strategies(strategies, grouping_csv)
            args.strategies = ",".join(selected)

        # Save for next time
        config_to_save = {
            'symbols': [s.strip() for s in args.symbols.split(',')] if args.symbols else [],
            'strategies': [s.strip() for s in args.strategies.split(',')] if args.strategies else [],
            'demo': args.demo,
            'cycles': args.cycles,
            'interval': args.interval,
            'risk': args.risk,
            'terminal': getattr(args, 'terminal', None),
            'max_positions': args.max_positions,
            'max_per_strategy': args.max_per_strategy,
            'use_optimized': args.use_optimized
        }
        save_config(config_to_save, DEFAULT_CONFIG_PATH)

    # Validate symbols
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
        invalid = [s for s in symbols if s not in ALL_SYMBOLS]
        if invalid:
            print(f"❌ Invalid symbol(s): {invalid}")
            print(f"Available: {', '.join(ALL_SYMBOLS)}")
            return
    else:
        symbols = None

    # Build engine kwargs
    engine_kwargs = create_engine_kwargs(args, config_overrides)

    # If symbols/strategies are None, they will be resolved inside the engine
    # But we already have them from args; we can pass explicitly
    if symbols is not None:
        engine_kwargs['symbols'] = symbols
    if args.strategies:
        engine_kwargs['strategy_list'] = [s.strip() for s in args.strategies.split(",")]

    # Show summary
    print("\n📋 Configuration Summary:")
    print(f"   Symbols: {engine_kwargs.get('symbols', 'ALL')}")
    print(f"   Strategies: {engine_kwargs.get('strategy_list', 'from backtest')}")
    print(f"   Demo mode: {engine_kwargs.get('demo_mode')}")
    print(f"   Risk: {engine_kwargs.get('risk_per_trade')}% per trade")
    print(f"   Max total positions: {engine_kwargs.get('max_total_positions', 7)}")
    print(f"   Max per strategy: {engine_kwargs.get('max_positions_per_strategy', 3)}")
    print(f"   Use optimized: {engine_kwargs.get('use_optimized', False)}")
    print(f"   Terminal: {engine_kwargs.get('terminal_path', 'default')}")
    print("=" * 60)

    confirm = input("Start trading with this configuration? (y/n) [default=y]: ").strip().lower()
    if confirm not in ['', 'y', 'yes']:
        print("Aborted by user.")
        return

    # Instantiate and run
    engine = LiveTradingEngine(**engine_kwargs)
    engine.run(cycles=args.cycles, bars=args.bars, interval=args.interval)


if __name__ == "__main__":
    main()