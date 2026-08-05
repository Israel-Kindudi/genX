#!/usr/bin/env python
"""
Batch optimization runner with detailed logging and time tracking.
Runs the genetic optimizer for every strategy on every symbol.
Skips if a final result already exists.
Logs every step to a file and console (with emojis, using UTF-8 encoding).
"""

import os
import sys
import json
import glob
import time
import logging
import pandas as pd
from datetime import datetime
from tqdm import tqdm

# ---- Force UTF-8 encoding for console output (Windows compatible) ----
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        # Python < 3.7 fallback: set environment variable
        os.environ['PYTHONIOENCODING'] = 'utf-8'

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import ASSETS, DATA_DIR
from optimization.strategy_optimizer import optimize_strategy, STRATEGY_MAP, find_strategy_key, get_dna_context

# ============================================================================
# Configuration
# ============================================================================
GENERATIONS = 10
POP_SIZE = 20
OUTPUT_DIR = "optimized_strategies"
LOG_DIR = "optimization/logs"
TIMEFRAME = "M5"

# Symbols to optimize (None means all from ASSETS)
SYMBOLS_TO_OPTIMIZE = None  # e.g., ["BreakX 600", "FX Vol 20"]
# Strategies to optimize (None means all from STRATEGY_MAP)
STRATEGIES_TO_OPTIMIZE = None  # e.g., ["Scalping RSI+VWMA (default)"]

# ============================================================================
# Setup logging (UTF-8 for both file and console)
# ============================================================================
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = f"batch_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
log_path = os.path.join(LOG_DIR, log_filename)

# Configure logging with UTF-8 encoding for file, and console uses sys.stdout (already UTF-8)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_path, mode='w', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)   # will use UTF-8 after reconfigure
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# Helper functions
# ============================================================================
def find_csv_file(symbol):
    """Find the CSV file for a given symbol and timeframe."""
    pattern = f"{DATA_DIR}/*{symbol}*{TIMEFRAME}*.csv"
    files = glob.glob(pattern)
    if not files:
        pattern = f"{DATA_DIR}/*{symbol}*.csv"
        files = glob.glob(pattern)
    if files:
        return files[0]
    return None

def load_data_from_csv(csv_path):
    """Load and normalise CSV data, ensuring a 'Date' column exists."""
    logger.debug(f"Loading CSV: {csv_path}")
    df = pd.read_csv(csv_path)
    df.columns = [c.lower() for c in df.columns]
    # Detect date column
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
    # Rename columns to standard OHLC
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
    # Ensure required columns exist
    required = ['Open', 'High', 'Low', 'Close']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Column {col} not found. Available: {df.columns.tolist()}")
    if 'Volume' not in df.columns:
        df['Volume'] = 1
    # CRITICAL: Add 'Date' column (capital D) for the backtester
    if 'Date' not in df.columns:
        if 'date' in df.columns:
            df['Date'] = df['date']
        else:
            df['Date'] = df.index
    logger.debug(f"Loaded {len(df)} rows, columns: {df.columns.tolist()}")
    return df

# ============================================================================
# Main batch runner
# ============================================================================
def main():
    logger.info("🚀 Starting Batch Optimization")
    logger.info(f"   Generations: {GENERATIONS}, Population: {POP_SIZE}")
    logger.info(f"   Output directory: {OUTPUT_DIR}")
    logger.info(f"   Log file: {log_path}")
    logger.info("=" * 60)

    # Get strategies and symbols lists
    if STRATEGIES_TO_OPTIMIZE is None:
        strategies = list(STRATEGY_MAP.keys())
    else:
        strategies = STRATEGIES_TO_OPTIMIZE

    if SYMBOLS_TO_OPTIMIZE is None:
        symbols = ASSETS
    else:
        symbols = SYMBOLS_TO_OPTIMIZE

    logger.info(f"📋 Strategies: {len(strategies)}")
    logger.info(f"📋 Symbols: {len(symbols)}")
    total_combinations = len(strategies) * len(symbols)
    logger.info(f"Total combinations: {total_combinations}")
    logger.info("=" * 60)

    # Summary data
    summary = []

    # Overall progress bar
    total_start = time.time()
    pbar = tqdm(total=total_combinations, desc="Overall Progress", position=0)

    # Loop over strategies
    for strategy_idx, strategy_name in enumerate(strategies, 1):
        logger.info(f"\n📌 Strategy [{strategy_idx}/{len(strategies)}]: {strategy_name}")
        strategy_results = []

        for symbol_idx, symbol in enumerate(symbols, 1):
            logger.info(f"   Symbol [{symbol_idx}/{len(symbols)}]: {symbol}")
            combo_start = time.time()

            # Check if already optimized
            final_file = f"{OUTPUT_DIR}/{strategy_name}_{symbol}_final.json"
            if os.path.exists(final_file):
                logger.info(f"      ⏭️  Skipping: result already exists.")
                strategy_results.append({'symbol': symbol, 'status': 'skipped'})
                pbar.update(1)
                continue

            # Find CSV file
            csv_path = find_csv_file(symbol)
            if csv_path is None:
                logger.warning(f"      ❌ No CSV found for {symbol} (timeframe {TIMEFRAME})")
                strategy_results.append({'symbol': symbol, 'status': 'no_data'})
                pbar.update(1)
                continue

            # Load data
            try:
                df = load_data_from_csv(csv_path)
                logger.info(f"      Data loaded: {len(df)} rows")
            except Exception as e:
                logger.error(f"      ❌ Error loading data: {e}")
                strategy_results.append({'symbol': symbol, 'status': 'load_error', 'error': str(e)})
                pbar.update(1)
                continue

            # Get DNA context
            dna_context = get_dna_context(symbol, TIMEFRAME)
            if dna_context:
                logger.info(f"      🧬 DNA context loaded.")
            else:
                logger.warning(f"      ⚠️ No DNA context found; continuing without it.")

            # Run optimization
            try:
                logger.info(f"      🔄 Starting optimization...")
                result = optimize_strategy(
                    strategy_name,
                    symbol,
                    df,
                    dna_context,
                    output_dir=OUTPUT_DIR,
                    generations=GENERATIONS,
                    pop_size=POP_SIZE
                )
                combo_elapsed = time.time() - combo_start
                if result is not None:
                    logger.info(f"      ✅ Optimization complete in {combo_elapsed:.1f}s. Best fitness: {result.get('best_fitness'):.4f}")
                    strategy_results.append({
                        'symbol': symbol,
                        'status': 'success',
                        'best_fitness': result.get('best_fitness'),
                        'elapsed': combo_elapsed
                    })
                else:
                    logger.warning(f"      ⚠️ Optimization returned None.")
                    strategy_results.append({'symbol': symbol, 'status': 'failed'})
            except Exception as e:
                logger.error(f"      ❌ Optimization error: {e}", exc_info=True)
                strategy_results.append({'symbol': symbol, 'status': 'error', 'error': str(e)})

            pbar.update(1)

        # Save strategy summary
        summary.append({
            'strategy': strategy_name,
            'results': strategy_results
        })

    pbar.close()
    total_elapsed = time.time() - total_start

    # Print final summary
    logger.info("\n" + "=" * 60)
    logger.info(f"✅ Batch optimization completed in {total_elapsed:.1f}s")
    logger.info("Summary:")
    for s in summary:
        successes = len([r for r in s['results'] if r.get('status') == 'success'])
        total = len(s['results'])
        logger.info(f"  {s['strategy']}: {successes}/{total} optimized")

    # Save summary to JSON
    summary_file = f"{OUTPUT_DIR}/batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    logger.info(f"💾 Summary saved to {summary_file}")
    logger.info(f"📄 Full log saved to {log_path}")

# ============================================================================
# Entry point
# ============================================================================
if __name__ == "__main__":
    main()