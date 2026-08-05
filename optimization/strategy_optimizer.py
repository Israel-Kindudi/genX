#!/usr/bin/env python
"""
Optimize a single strategy using the genetic algorithm, with DNA context.
Saves results incrementally. Includes progress bars, time tracking, and detailed evaluation table.
"""

import sys
import os
import json
import time
import random
import numpy as np
import pandas as pd
from datetime import datetime
from tqdm import tqdm

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from strategies import (
    ScalpingStrategyRSI_VWMA,
    TrendFollowingStrategy,
    ScalpingStrategy,
    TrendFollowingADX,
    ScalpingStrategyDMI_MACD,
    ScalpingStrategyBB_MACD_TM,
    ScalpingStrategyHMA_Stoch,
    TrendStrategyVWMA_SOTT,
    TrendStrategyPMax_NSM,
    TrendStrategyAroonRSI_SMA
)
from backtester import FastBacktesterEngine
from dna.context import FullDNAContext
from config import DATA_DIR, INITIAL_CAPITAL, RISK_PER_TRADE

# Full mapping of strategy names (as they appear in backtest summary) to (class, parameter bounds)
STRATEGY_MAP = {
    # --- Scalping strategies ---
    'Scalping RSI+VWMA (default)': (ScalpingStrategyRSI_VWMA, {
        'rsi_period': (5, 14),
        'vwma_period': (10, 30),
        'sma_200': (150, 250),
        'sma_12': (5, 20),
        'atr_period': (10, 20)
    }),
    'Scalping RSI+VWMA (tuned)': (ScalpingStrategyRSI_VWMA, {
        'rsi_period': (5, 14),
        'vwma_period': (10, 30),
        'sma_200': (150, 250),
        'sma_12': (5, 20),
        'atr_period': (10, 20)
    }),
    'Scalping (default)': (ScalpingStrategy, {
        'lookback_bars': (5, 50),
        'entry_threshold': (0.2, 2.5),
        'stop_multiplier': (0.3, 2.5),
        'take_profit_multiplier': (0.5, 3.0),
        'max_hold_bars': (2, 15),
        'min_profit_bp': (0.1, 1.5),
        'atr_period': (10, 20)
    }),
    'Scalping DMI+MACD (default)': (ScalpingStrategyDMI_MACD, {
        'dmi_period': (7, 21),
        'stoch_k': (7, 21),
        'stoch_d': (2, 5),
        'macd_fast': (8, 16),
        'macd_slow': (21, 34),
        'macd_signal': (5, 13),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Scalping DMI+MACD (tuned)': (ScalpingStrategyDMI_MACD, {
        'dmi_period': (7, 21),
        'stoch_k': (7, 21),
        'stoch_d': (2, 5),
        'macd_fast': (8, 16),
        'macd_slow': (21, 34),
        'macd_signal': (5, 13),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Scalping BB+MACD+TM (default)': (ScalpingStrategyBB_MACD_TM, {
        'macd_fast': (8, 16),
        'macd_slow': (21, 34),
        'macd_signal': (5, 13),
        'bb_period': (10, 25),
        'bb_std': (1.5, 2.5),
        'tm_period': (10, 25),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Scalping BB+MACD+TM (tuned)': (ScalpingStrategyBB_MACD_TM, {
        'macd_fast': (8, 16),
        'macd_slow': (21, 34),
        'macd_signal': (5, 13),
        'bb_period': (10, 25),
        'bb_std': (1.5, 2.5),
        'tm_period': (10, 25),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Scalping HMA+Stoch (default)': (ScalpingStrategyHMA_Stoch, {
        'hma_period': (15, 35),
        'stoch_k': (10, 18),
        'stoch_d': (2, 5),
        'stoch_smooth': (4, 8),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Scalping HMA+Stoch (tuned)': (ScalpingStrategyHMA_Stoch, {
        'hma_period': (15, 35),
        'stoch_k': (10, 18),
        'stoch_d': (2, 5),
        'stoch_smooth': (4, 8),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),

    # --- Trend strategies ---
    'Trend Following (default)': (TrendFollowingStrategy, {
        'lookback_bars': (10, 100),
        'entry_threshold': (1.0, 4.0),
        'stop_multiplier': (1.0, 4.0),
        'take_profit_multiplier': (1.5, 5.0),
        'max_trend_bars': (5, 30),
        'min_trend_bars': (2, 6),
        'atr_period': (10, 20)
    }),
    'Trend Following ADX (default)': (TrendFollowingADX, {
        'adx_period': (10, 20),
        'ma_fast': (8, 15),
        'ma_slow': (20, 40),
        'atr_period': (10, 20),
        'stop_multiplier': (1.0, 3.0),
        'take_profit_multiplier': (1.5, 4.0)
    }),
    'Trend VWMA+SOTT (default)': (TrendStrategyVWMA_SOTT, {
        'vwma_fast': (5, 10),
        'vwma_slow': (20, 40),
        'sott_k': (80, 120),
        'sott_k_smooth': (6, 12),
        'sott_ott_period': (1, 3),
        'sott_ott_percent': (0.2, 0.8),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Trend VWMA+SOTT (tuned)': (TrendStrategyVWMA_SOTT, {
        'vwma_fast': (5, 10),
        'vwma_slow': (20, 40),
        'sott_k': (80, 120),
        'sott_k_smooth': (6, 12),
        'sott_ott_period': (1, 3),
        'sott_ott_percent': (0.2, 0.8),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Trend PMax+NSM (default)': (TrendStrategyPMax_NSM, {
        'atr_length': (6, 10),
        'atr_multiplier': (2.5, 4.5),
        'ma_length': (8, 12),
        'macd_fast': (8, 14),
        'macd_slow': (20, 28),
        'macd_signal': (5, 9),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Trend PMax+NSM (tuned)': (TrendStrategyPMax_NSM, {
        'atr_length': (6, 10),
        'atr_multiplier': (2.5, 4.5),
        'ma_length': (8, 12),
        'macd_fast': (8, 14),
        'macd_slow': (20, 28),
        'macd_signal': (5, 9),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Trend Aroon+RSI+SMA (default)': (TrendStrategyAroonRSI_SMA, {
        'aroon_period': (10, 18),
        'rsi_period': (10, 18),
        'sma_period': (6, 14),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
    'Trend Aroon+RSI+SMA (tuned)': (TrendStrategyAroonRSI_SMA, {
        'aroon_period': (10, 18),
        'rsi_period': (10, 18),
        'sma_period': (6, 14),
        'atr_period': (10, 20),
        'stop_multiplier': (0.8, 2.0),
        'take_profit_multiplier': (1.5, 3.5)
    }),
}

# Helper function for fuzzy matching
def find_strategy_key(strategy_name, strategy_map):
    """Find the closest matching key in the strategy map."""
    if strategy_name in strategy_map:
        return strategy_name
    cleaned = strategy_name.strip()
    for key in strategy_map.keys():
        if cleaned == key:
            return key
        if cleaned.lower() == key.lower():
            return key
    for key in strategy_map.keys():
        if cleaned in key or key in cleaned:
            return key
    import re
    base_name = re.sub(r'\s*\(.*?\)', '', strategy_name).strip()
    for key in strategy_map.keys():
        key_base = re.sub(r'\s*\(.*?\)', '', key).strip()
        if base_name == key_base:
            return key
    return None

import glob
import json
import os

def get_dna_context(symbol, timeframe='M5'):
    """
    Load DNA context for a symbol and timeframe.
    Handles flexible filename patterns:
    - {symbol}_{timeframe}_DNA.json
    - {symbol}_PERIOD_{timeframe}_data_{timeframe}_DNA.json
    - {symbol}_*_{timeframe}_DNA.json
    """
    dna_folder = "dna_results"

    # 1. Try exact match first (fastest)
    exact_file = f"{dna_folder}/{symbol}_{timeframe}_DNA.json"
    if os.path.exists(exact_file):
        try:
            with open(exact_file, 'r') as f:
                return json.load(f)
        except:
            pass

    # 2. Try glob with symbol and timeframe in filename
    pattern = f"{dna_folder}/*{symbol}*{timeframe}*_DNA.json"
    files = glob.glob(pattern)
    if files:
        try:
            with open(files[0], 'r') as f:
                return json.load(f)
        except:
            pass

    # 3. Try glob with symbol only, then check content for timeframe
    pattern2 = f"{dna_folder}/*{symbol}*_DNA.json"
    files2 = glob.glob(pattern2)
    for file in files2:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                # Check if the data's timeframe matches
                if data.get('timeframe') == timeframe:
                    return data
        except:
            continue

    # 4. Try glob with symbol and any timeframe (return first match)
    pattern3 = f"{dna_folder}/*{symbol}*.json"
    files3 = glob.glob(pattern3)
    if files3:
        try:
            with open(files3[0], 'r') as f:
                return json.load(f)
        except:
            pass

    # 5. Not found
    return None

def evaluate_parameters(strategy_class, params, df, symbol, dna_context):
    """Evaluate a parameter set on the given data."""
    strategy = strategy_class(**params)
    engine = FastBacktesterEngine(
        df=df,
        strategy=strategy,
        symbol=symbol,
        initial_capital=INITIAL_CAPITAL,
        risk_per_trade=RISK_PER_TRADE,
        timeframe='M5',
        verbose=False,
        dna_context=dna_context
    )
    report = engine.run(show_progress=False)
    return report.get('sharpe_ratio', 0), report

def optimize_strategy(strategy_name, symbol, df, dna_context, output_dir="optimized_strategies", generations=10, pop_size=20):
    """
    Run genetic optimization for a specific strategy on a specific symbol.
    Saves results incrementally. Includes progress bar and evaluation table.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    matched_key = find_strategy_key(strategy_name, STRATEGY_MAP)
    if matched_key is None:
        print(f"⚠️ Strategy {strategy_name} not found in map.")
        return None
    
    strategy_class, bounds = STRATEGY_MAP[matched_key]
    
    print(f"\n🧬 Optimizing {strategy_name} (matched to '{matched_key}') on {symbol}")
    print(f"   Generations: {generations}, Population: {pop_size}")
    print(f"   Total evaluations: {generations * pop_size}")
    print("-" * 60)
    
    start_time = time.time()
    all_evals = []  # store evaluation records for table
    
    # Initial population
    population = []
    for _ in range(pop_size):
        params = {}
        for key, (mn, mx) in bounds.items():
            if isinstance(mn, int) and isinstance(mx, int):
                params[key] = random.randint(mn, mx)
            else:
                params[key] = round(random.uniform(mn, mx), 2)
        population.append(params)
    
    fitness_history = []
    best_params = None
    best_fitness = -999
    best_report = None
    
    # Outer progress bar for generations
    gen_pbar = tqdm(range(generations), desc="Generations", unit="gen", position=0)
    
    for gen in gen_pbar:
        fitness_scores = []
        reports = []
        eval_records = []
        
        # Inner progress bar for individuals
        ind_pbar = tqdm(range(pop_size), desc=f"  Gen {gen+1} eval", unit="ind", leave=False, position=1)
        
        for idx in ind_pbar:
            params = population[idx]
            fitness, report = evaluate_parameters(strategy_class, params, df, symbol, dna_context)
            fitness_scores.append(fitness)
            reports.append(report)
            
            # Record for table
            record = {
                'gen': gen+1,
                'ind': idx+1,
                'fitness': round(fitness, 4),
                'trades': report.get('total_trades', 0),
                'win_rate': round(report.get('win_rate', 0), 2),
                'sharpe': round(report.get('sharpe_ratio', 0), 4),
                'pnl': round(report.get('total_pnl', 0), 2),
            }
            # Add parameter values
            for key, val in params.items():
                record[f'p_{key}'] = val
            eval_records.append(record)
            all_evals.append(record)
            
            # Update inner progress bar description
            params_str = ', '.join([f"{k}={v}" for k, v in list(params.items())[:3]])
            ind_pbar.set_postfix({'fitness': f"{fitness:.4f}", 'params': params_str})
        
        # Update best
        best_idx = np.argmax(fitness_scores)
        if fitness_scores[best_idx] > best_fitness:
            best_fitness = fitness_scores[best_idx]
            best_params = population[best_idx].copy()
            best_report = reports[best_idx]
        
        fitness_history.append(best_fitness)
        
        # Save progress incrementally
        progress = {
            'strategy': strategy_name,
            'matched_key': matched_key,
            'symbol': symbol,
            'generation': gen,
            'best_fitness': best_fitness,
            'best_params': best_params,
            'fitness_history': fitness_history,
            'best_report': best_report,
            'timestamp': datetime.now().isoformat()
        }
        with open(f"{output_dir}/{strategy_name}_{symbol}_progress.json", 'w') as f:
            json.dump(progress, f, indent=2, default=str)
        
        # Update outer progress bar
        gen_pbar.set_postfix({'best': f"{best_fitness:.4f}", 'trades': best_report.get('total_trades', 0) if best_report else 0})
        
        # --- Display evaluation table for this generation ---
        if gen == 0 or gen == generations-1 or gen % 2 == 0:
            df_evals = pd.DataFrame(eval_records)
            # Show key columns
            display_cols = ['ind', 'fitness', 'trades', 'win_rate', 'sharpe', 'pnl']
            # Add first 3 parameter columns
            param_cols = [c for c in df_evals.columns if c.startswith('p_')][:3]
            display_cols.extend(param_cols)
            df_display = df_evals[display_cols].sort_values('fitness', ascending=False)
            print(f"\n📊 Generation {gen+1} Evaluation Results (top 5):")
            print(df_display.head(5).to_string(index=False))
            print("-" * 60)
        
        # Selection, crossover, mutation
        fitness_scores = np.array(fitness_scores)
        min_fit = np.min(fitness_scores)
        if min_fit < 0:
            fitness_scores = fitness_scores - min_fit + 1e-6
        probs = fitness_scores / np.sum(fitness_scores)
        
        new_population = []
        # Elitism: keep top 2
        sorted_idx = np.argsort(fitness_scores)[::-1]
        new_population.append(population[sorted_idx[0]].copy())
        new_population.append(population[sorted_idx[1]].copy())
        
        while len(new_population) < pop_size:
            parents = np.random.choice(len(population), size=2, p=probs, replace=False)
            p1 = population[parents[0]]
            p2 = population[parents[1]]
            child = {}
            for key in bounds.keys():
                if random.random() < 0.5:
                    child[key] = p1[key]
                else:
                    child[key] = p2[key]
            mut_rate = 0.1
            if random.random() < mut_rate:
                key = random.choice(list(bounds.keys()))
                mn, mx = bounds[key]
                if isinstance(mn, int) and isinstance(mx, int):
                    child[key] = random.randint(mn, mx)
                else:
                    child[key] = round(random.uniform(mn, mx), 2)
            new_population.append(child)
        population = new_population
        
        # Clean up inner pbar (already closed by tqdm)
    
    elapsed = time.time() - start_time
    print(f"\n✅ Optimization complete in {elapsed:.1f}s. Best fitness: {best_fitness:.4f}")
    print(f"   Best parameters: {best_params}")
    
    # Save final result
    final_result = {
        'strategy': strategy_name,
        'matched_key': matched_key,
        'symbol': symbol,
        'best_fitness': best_fitness,
        'best_params': best_params,
        'best_report': best_report,
        'fitness_history': fitness_history,
        'all_evaluations': all_evals,
        'elapsed_seconds': elapsed,
        'timestamp': datetime.now().isoformat()
    }
    with open(f"{output_dir}/{strategy_name}_{symbol}_final.json", 'w') as f:
        json.dump(final_result, f, indent=2, default=str)
    
    # Also save evaluation table to CSV for later analysis
    if all_evals:
        df_all = pd.DataFrame(all_evals)
        df_all.to_csv(f"{output_dir}/{strategy_name}_{symbol}_evaluations.csv", index=False)
        print(f"💾 Evaluation table saved to {output_dir}/{strategy_name}_{symbol}_evaluations.csv")
    
    return final_result

if __name__ == "__main__":
    # Example usage: test optimization on a single strategy
    import glob
    symbol = "BreakX 600"
    timeframe = "M5"
    csv_file = f"{DATA_DIR}/{symbol}_PERIODE_M5_data.csv"
    if not os.path.exists(csv_file):
        csv_files = glob.glob(f"{DATA_DIR}/*.csv")
        for f in csv_files:
            if symbol in f and 'M5' in f:
                csv_file = f
                break
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
    
    dna_context = get_dna_context(symbol, timeframe)
    result = optimize_strategy("Scalping RSI+VWMA (default)", symbol, df, dna_context, generations=5, pop_size=10)
    print(result)