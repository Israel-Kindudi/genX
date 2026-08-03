#!/usr/bin/env python
"""
Backtest Runner – Compare multiple strategies on all symbols/timeframes.
Generates comprehensive reports including trade DNA for optimization.
"""
import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import glob
import time
import json
from tqdm import tqdm



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
    ScalpingStrategyVWAP_StochRSI,
    TrendStrategyVWMA_SOTT,
    TrendStrategyPMax_NSM,
    TrendStrategyAroonRSI_SMA
)
from backtester import FastBacktesterEngine
from backtester.metrics import PerformanceMetrics
from config import DATA_DIR, INITIAL_CAPITAL, RISK_PER_TRADE

# ============================================================================
#  DATA LOADING
# ============================================================================

def load_data_from_path(csv_path):
    """Load OHLCV data from a given CSV path."""
    print(f"📂 Loading: {csv_path}")
    df = pd.read_csv(csv_path)
    df.columns = [col.lower() for col in df.columns]
    
    if 'time' in df.columns:
        df.rename(columns={'time': 'date'}, inplace=True)
    elif 'datetime' in df.columns:
        df.rename(columns={'datetime': 'date'}, inplace=True)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    else:
        df.index = pd.to_datetime(df.index)
        df['date'] = df.index
    
    df = df.sort_values('date').reset_index(drop=True)
    
    col_map = {}
    for col in df.columns:
        if col.lower() in ['open', 'o']:
            col_map[col] = 'Open'
        elif col.lower() in ['high', 'h']:
            col_map[col] = 'High'
        elif col.lower() in ['low', 'l']:
            col_map[col] = 'Low'
        elif col.lower() in ['close', 'c']:
            col_map[col] = 'Close'
        elif col.lower() in ['volume', 'vol', 'v']:
            col_map[col] = 'Volume'
        elif col.lower() in ['date', 'time', 'datetime']:
            col_map[col] = 'Date'
    
    df = df.rename(columns=col_map)
    
    required = ['Date', 'Open', 'High', 'Low', 'Close']
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"⚠️ Missing columns: {missing}")
        return None
    
    if 'Volume' not in df.columns:
        df['Volume'] = 1
    
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close'])
    return df

def load_dna_context(symbol, timeframe='5m'):
    """Load DNA context for a symbol."""
    dna_file = f"dna_results/{symbol}_{timeframe}_DNA.json"
    if os.path.exists(dna_file):
        try:
            with open(dna_file, 'r') as f:
                return json.load(f)
        except:
            pass
    return None

# ============================================================================
#  BACKTEST RUNNER
# ============================================================================

def run_backtest(df, strategy, strategy_name, symbol, timeframe, verbose=False, dna_context=None):
    print(f"  ▶️ Running {strategy_name}...")
    start_time = time.time()
    
    try:
        engine = FastBacktesterEngine(
            df=df,
            strategy=strategy,
            symbol=symbol,
            initial_capital=INITIAL_CAPITAL,
            risk_per_trade=RISK_PER_TRADE,
            timeframe=timeframe,
            verbose=verbose,
            dna_context=dna_context
        )
        report = engine.run(show_progress=True)
        elapsed = time.time() - start_time
        
        saved_files = PerformanceMetrics.save_report(
            report, 
            strategy_name, 
            symbol, 
            timeframe=timeframe,
            output_dir="backtest_reports"
        )
        
        print(f"  ✅ {strategy_name}: {report['total_trades']} trades, "
              f"Sharpe: {report['sharpe_ratio']:.2f}, "
              f"PnL: ${report['total_pnl']:.2f} "
              f"({elapsed:.1f}s)")
        return report, saved_files
        
    except Exception as e:
        print(f"  ❌ {strategy_name} failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            'total_trades': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'total_pnl': 0,
            'return_pct': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'trades_df': pd.DataFrame(),
            'trade_dna': [],
            'equity_df': pd.DataFrame()
        }, None

# ============================================================================
#  MAIN
# ============================================================================

def main():
    print("\n" + "="*80)
    print("🧬 SYNTHX BACKTEST RUNNER (All Symbols)")
    print("="*80)
    print(f"Data Directory: {DATA_DIR}")
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}")
    print(f"Risk per Trade: {RISK_PER_TRADE:.1f}%")
    print("="*80)
    
    csv_files = glob.glob(f"{DATA_DIR}/*.csv")
    if not csv_files:
        print("❌ No CSV files found in data/ folder.")
        return
    
    print(f"\n📊 Found {len(csv_files)} data files:")
    for f in csv_files:
        print(f"  - {os.path.basename(f)}")
    
    # Define strategies (once)
    strategy_defs = [
        ('Scalping RSI+VWMA (default)', ScalpingStrategyRSI_VWMA()),
        ('Scalping RSI+VWMA (tuned)', ScalpingStrategyRSI_VWMA(rsi_period=7, vwma_period=15, sma_200=180, sma_12=10)),
        ('Trend Following (default)', TrendFollowingStrategy()),
        ('Trend Following ADX (default)', TrendFollowingADX()),
        ('Scalping (default)', ScalpingStrategy()),
        ('Scalping DMI+MACD (default)', ScalpingStrategyDMI_MACD()),
        ('Scalping DMI+MACD (tuned)', ScalpingStrategyDMI_MACD(dmi_period=10, stoch_k=10, stoch_d=2, macd_fast=8, macd_slow=21, macd_signal=7, stop_multiplier=1.2, take_profit_multiplier=1.8)),
        ('Scalping BB+MACD+TM (default)', ScalpingStrategyBB_MACD_TM()),
        ('Scalping BB+MACD+TM (tuned)', ScalpingStrategyBB_MACD_TM(
    macd_fast=10,
    macd_slow=21,
    macd_signal=7,
    bb_period=15,
    bb_std=1.8,
    tm_period=15,
    stop_multiplier=1.2,
    take_profit_multiplier=1.8
)),
    ('Scalping HMA+Stoch (default)', ScalpingStrategyHMA_Stoch()),
    ('Scalping HMA+Stoch (tuned)', ScalpingStrategyHMA_Stoch(
    hma_period=20,
    stoch_k=10,
    stoch_d=3,
    stoch_smooth=5,
    stop_multiplier=1.2,
    take_profit_multiplier=1.8
    )),
    # Inside strategy_defs list:
    ('Scalping VWAP+StochRSI (default)', ScalpingStrategyVWAP_StochRSI()),
    ('Scalping VWAP+StochRSI (tuned)', ScalpingStrategyVWAP_StochRSI(
    vwap_band_multiplier=1.2,
    sma_period=400,
    stoch_rsi_period=10,
    stoch_rsi_k=2,
    stoch_rsi_d=2,
    stop_multiplier=1.2,
    take_profit_multiplier=1.8
)),
    ('Trend VWMA+SOTT (default)', TrendStrategyVWMA_SOTT()),
    ('Trend VWMA+SOTT (tuned)', TrendStrategyVWMA_SOTT(
    vwma_fast=6,
    vwma_slow=25,
    sott_k=80,
    sott_k_smooth=8,
    sott_ott_period=2,
    sott_ott_percent=0.3,
    stop_multiplier=1.2,
    take_profit_multiplier=2.0
)),
    ('Trend PMax+NSM (default)', TrendStrategyPMax_NSM()),
    ('Trend PMax+NSM (tuned)', TrendStrategyPMax_NSM(
    atr_length=6,
    atr_multiplier=3.0,
    ma_length=8,
    macd_fast=10,
    macd_slow=21,
    macd_signal=7,
    stop_multiplier=1.2,
    take_profit_multiplier=2.0
)),
    ('Trend Aroon+RSI+SMA (default)', TrendStrategyAroonRSI_SMA()),
    ('Trend Aroon+RSI+SMA (tuned)', TrendStrategyAroonRSI_SMA(
    aroon_period=10,
    rsi_period=10,
    sma_period=8,
    stop_multiplier=1.2,
    take_profit_multiplier=2.0
)),
    ]
    
    all_results = []
    
    for csv_path in csv_files:
        # Extract symbol and timeframe from filename
        basename = os.path.basename(csv_path).replace('.csv', '')
        # Try to split: e.g., "BreakX 600_PERIODE_M5_data" -> symbol="BreakX 600", timeframe="M5"
        parts = basename.split('_')
        # Find the part that contains 'PERIODE' or starts with 'M' (timeframe)
        timeframe = None
        symbol_parts = []
        for part in parts:
            if 'PERIODE' in part:
                # extract M1, M5, etc.
                tf_part = part.replace('PERIODE_', '')
                if tf_part in ['M1', 'M5', 'M15', 'M30', 'H1', 'H4']:
                    timeframe = tf_part
                else:
                    # fallback: assume it's the timeframe
                    timeframe = tf_part
            elif part in ['M1', 'M5', 'M15', 'M30', 'H1', 'H4']:
                timeframe = part
            else:
                symbol_parts.append(part)
        symbol = '_'.join(symbol_parts) if symbol_parts else basename
        
        if timeframe is None:
            # default to M5
            timeframe = 'M5'
        
        print(f"\n📊 Processing: {symbol} ({timeframe})")
        df = load_data_from_path(csv_path)
        if df is None:
            continue
        print(f"   Loaded {len(df):,} bars")
        
        # Load DNA context if available
        dna_context = load_dna_context(symbol, timeframe)
        if dna_context:
            print(f"   Loaded DNA context")
        
        # Run each strategy
        for strategy_name, strategy in strategy_defs:
            report, saved = run_backtest(
                df, strategy, strategy_name, symbol, timeframe,
                verbose=False, dna_context=dna_context
            )
            all_results.append({
                'Symbol': symbol,
                'Timeframe': timeframe,
                'Strategy': strategy_name,
                'Trades': report['total_trades'],
                'Win Rate %': report['win_rate'],
                'Profit Factor': report['profit_factor'],
                'Total PnL': report['total_pnl'],
                'Return %': report['return_pct'],
                'Sharpe': report['sharpe_ratio'],
                'Max DD %': report['max_drawdown'],
            })
    
    # --- Summary across all ---
    print("\n" + "="*100)
    print("📊 FULL BACKTEST SUMMARY (All Symbols/Timeframes)")
    print("="*100)
    summary_df = pd.DataFrame(all_results)
    display_cols = ['Symbol', 'Timeframe', 'Strategy', 'Trades', 'Win Rate %', 'Profit Factor',
                    'Total PnL', 'Return %', 'Sharpe', 'Max DD %']
    print(summary_df[display_cols].to_string(index=False))
    
    summary_df.to_csv("backtest_full_summary.csv", index=False)
    print("\n💾 Full summary saved to backtest_full_summary.csv")
    
    # Find best overall by Sharpe
    valid = summary_df[summary_df['Trades'] >= 5]
    if not valid.empty:
        best_idx = valid['Sharpe'].idxmax()
        best = valid.loc[best_idx]
        print(f"\n🏆 Best overall by Sharpe: {best['Strategy']} on {best['Symbol']} ({best['Timeframe']})")
        print(f"   Sharpe: {best['Sharpe']:.2f}, Trades: {best['Trades']}, PnL: ${best['Total PnL']:.2f}")

if __name__ == "__main__":
    main()