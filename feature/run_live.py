#!/usr/bin/env python
"""
CLI launcher for the GenX live trading engine.
Allows selecting symbols and strategies via command-line arguments or config file.
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from live_trading.live_engine import LiveTradingEngine, ALL_SYMBOLS
from live_trading.live_engine import load_strategies_from_backtest


def parse_args():
    parser = argparse.ArgumentParser(
        description="GenX Live Trading Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (demo mode, all symbols, strategies from backtest)
  python run_live.py

  # Trade only BreakX 600 and FX Vol 20, with specific strategies
  python run_live.py -s "BreakX 600,FX Vol 20" -t "Scalping DMI+MACD (default),Trend Following ADX (default)"

  # Run real mode with 2% risk per trade, 50 cycles, 5-min interval
  python run_live.py --real --risk 2.0 --cycles 50 --interval 300

  # Load configuration from file
  python run_live.py --config live_config.json
        """
    )

    # Symbol selection
    parser.add_argument(
        "-s", "--symbols",
        type=str,
        help="Comma-separated list of symbols to trade (e.g., 'BreakX 600,FX Vol 20'). Default: all."
    )

    # Strategy selection
    parser.add_argument(
        "-t", "--strategies",
        type=str,
        help="Comma-separated list of strategy names (exact names from backtest summary). Default: load from backtest."
    )

    # Mode
    parser.add_argument(
        "--demo",
        action="store_true",
        default=True,
        help="Run in demo mode (no real orders). This is the default."
    )
    parser.add_argument(
        "--real",
        action="store_false",
        dest="demo",
        help="Run in real mode (actual order execution). Use with caution!"
    )

    # Parameters
    parser.add_argument(
        "--cycles",
        type=int,
        default=100,
        help="Number of trading cycles to run (default: 100)."
    )
    parser.add_argument(
        "--bars",
        type=int,
        default=200,
        help="Number of historical bars to fetch per cycle (default: 200)."
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

    # Configuration file
    parser.add_argument(
        "-c", "--config",
        type=str,
        help="Load configuration from a JSON file (overrides command-line arguments except --config)."
    )

    # Utility
    parser.add_argument(
        "--list-symbols",
        action="store_true",
        help="List all available symbols and exit."
    )
    parser.add_argument(
        "--list-strategies",
        action="store_true",
        help="List strategies from backtest summary and exit."
    )

    return parser.parse_args()


def load_config_file(path):
    """Load configuration from JSON file."""
    with open(path, 'r') as f:
        config = json.load(f)
    return config


def main():
    args = parse_args()

    # Handle utility flags
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
    if args.config:
        config = load_config_file(args.config)
        # Override args with config values
        for key, value in config.items():
            if key == "symbols":
                args.symbols = ",".join(value) if isinstance(value, list) else value
            elif key == "strategies":
                args.strategies = ",".join(value) if isinstance(value, list) else value
            elif key == "demo":
                args.demo = value
            elif key == "cycles":
                args.cycles = value
            elif key == "bars":
                args.bars = value
            elif key == "interval":
                args.interval = value
            elif key == "risk":
                args.risk = value

    # Parse symbol list
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
        # Validate symbols
        valid_symbols = set(ALL_SYMBOLS)
        invalid = [s for s in symbols if s not in valid_symbols]
        if invalid:
            print(f"❌ Invalid symbol(s): {invalid}")
            print(f"Available: {', '.join(ALL_SYMBOLS)}")
            return
    else:
        symbols = None  # will use all symbols

    # Parse strategy list
    if args.strategies:
        strategies = [s.strip() for s in args.strategies.split(",")]
        # We'll let the engine validate them (or we can pre-check)
    else:
        strategies = None  # load from backtest

    # Instantiate engine
    engine = LiveTradingEngine(
        symbols=symbols,
        strategy_list=strategies,
        demo_mode=args.demo,
        verbose=True,
        risk_per_trade=args.risk
    )

    # Run
    engine.run(cycles=args.cycles, bars=args.bars, interval=args.interval)


if __name__ == "__main__":
    main()