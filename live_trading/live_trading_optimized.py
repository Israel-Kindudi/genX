#!/usr/bin/env python
"""
Live Trading Engine – Full MT5 integration with:
- Session persistence (unique folder per run)
- Periodic position sync with history-based PnL recovery
- JSONL streaming for equity and trade events
- DNA logging (per-symbol instantiation)
- Robust closing via enhanced connector
- Multi-terminal support (optional terminal_path)
- Optimized parameter loading (use_optimized=True)
- Breakeven trigger based on TP distance, with profit lock
"""

import os
import sys
import time
import json
import glob
import pandas as pd
import numpy as np
from datetime import datetime
import MetaTrader5 as mt5
import warnings
from typing import Optional

warnings.filterwarnings('ignore')

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
    TrendStrategyAroonRSI_SMA,
)
from config import INITIAL_CAPITAL, RISK_PER_TRADE
from mt5_connection_multi_terminal_v1 import MT5Connection, GENX_TO_MT5_MAP
from dna.analyzer import DNAAnalyzer

# ============================================================================
# STRATEGY CLASS MAPPING
# ============================================================================
STRATEGY_CLASS_MAP = {
    'Scalping RSI+VWMA (default)': ScalpingStrategyRSI_VWMA,
    'Scalping RSI+VWMA (tuned)': ScalpingStrategyRSI_VWMA,
    'Scalping (default)': ScalpingStrategy,
    'Scalping DMI+MACD (default)': ScalpingStrategyDMI_MACD,
    'Scalping DMI+MACD (tuned)': ScalpingStrategyDMI_MACD,
    'Scalping BB+MACD+TM (default)': ScalpingStrategyBB_MACD_TM,
    'Scalping BB+MACD+TM (tuned)': ScalpingStrategyBB_MACD_TM,
    'Scalping HMA+Stoch (default)': ScalpingStrategyHMA_Stoch,
    'Scalping HMA+Stoch (tuned)': ScalpingStrategyHMA_Stoch,
    'Scalping VWAP+StochRSI (default)': ScalpingStrategy,
    'Scalping VWAP+StochRSI (tuned)': ScalpingStrategy,
    'Trend Following (default)': TrendFollowingStrategy,
    'Trend Following ADX (default)': TrendFollowingADX,
    'Trend VWMA+SOTT (default)': TrendStrategyVWMA_SOTT,
    'Trend VWMA+SOTT (tuned)': TrendStrategyVWMA_SOTT,
    'Trend PMax+NSM (default)': TrendStrategyPMax_NSM,
    'Trend PMax+NSM (tuned)': TrendStrategyPMax_NSM,
    'Trend Aroon+RSI+SMA (default)': TrendStrategyAroonRSI_SMA,
    'Trend Aroon+RSI+SMA (tuned)': TrendStrategyAroonRSI_SMA,
}

# ============================================================================
# DEFAULT PARAMETERS
# ============================================================================
DEFAULT_PARAMS = {
    'Scalping RSI+VWMA (default)': {
        'rsi_period': 9, 'vwma_period': 20, 'sma_200': 200, 'sma_12': 12, 'atr_period': 14
    },
    'Scalping RSI+VWMA (tuned)': {
        'rsi_period': 7, 'vwma_period': 15, 'sma_200': 180, 'sma_12': 10, 'atr_period': 14
    },
    'Scalping (default)': {
        'lookback_bars': 10, 'entry_threshold': 0.5, 'stop_multiplier': 0.8,
        'take_profit_multiplier': 1.0, 'max_hold_bars': 5, 'min_profit_bp': 0.5, 'atr_period': 14
    },
    'Scalping DMI+MACD (default)': {
        'dmi_period': 14, 'stoch_k': 14, 'stoch_d': 3,
        'macd_fast': 12, 'macd_slow': 26, 'macd_signal': 9,
        'atr_period': 14, 'stop_multiplier': 1.5, 'take_profit_multiplier': 2.0
    },
    'Scalping DMI+MACD (tuned)': {
        'dmi_period': 10, 'stoch_k': 10, 'stoch_d': 2,
        'macd_fast': 8, 'macd_slow': 21, 'macd_signal': 7,
        'atr_period': 14, 'stop_multiplier': 1.2, 'take_profit_multiplier': 1.8
    },
    'Scalping BB+MACD+TM (default)': {
        'macd_fast': 12, 'macd_slow': 26, 'macd_signal': 9,
        'bb_period': 20, 'bb_std': 2.0, 'tm_period': 20,
        'atr_period': 14, 'stop_multiplier': 1.5, 'take_profit_multiplier': 2.0
    },
    'Scalping BB+MACD+TM (tuned)': {
        'macd_fast': 10, 'macd_slow': 21, 'macd_signal': 7,
        'bb_period': 15, 'bb_std': 1.8, 'tm_period': 15,
        'atr_period': 14, 'stop_multiplier': 1.2, 'take_profit_multiplier': 1.8
    },
    'Scalping HMA+Stoch (default)': {
        'hma_period': 30, 'stoch_k': 14, 'stoch_d': 3, 'stoch_smooth': 6,
        'atr_period': 14, 'stop_multiplier': 1.5, 'take_profit_multiplier': 2.0
    },
    'Scalping HMA+Stoch (tuned)': {
        'hma_period': 20, 'stoch_k': 10, 'stoch_d': 3, 'stoch_smooth': 5,
        'atr_period': 14, 'stop_multiplier': 1.2, 'take_profit_multiplier': 1.8
    },
    'Scalping VWAP+StochRSI (default)': {
        'lookback_bars': 10, 'entry_threshold': 0.5, 'stop_multiplier': 0.8,
        'take_profit_multiplier': 1.0, 'max_hold_bars': 5, 'min_profit_bp': 0.5, 'atr_period': 14
    },
    'Scalping VWAP+StochRSI (tuned)': {
        'lookback_bars': 8, 'entry_threshold': 0.4, 'stop_multiplier': 0.7,
        'take_profit_multiplier': 1.2, 'max_hold_bars': 4, 'min_profit_bp': 0.6, 'atr_period': 14
    },
    'Trend Following (default)': {
        'lookback_bars': 20, 'entry_threshold': 1.5, 'stop_multiplier': 1.5,
        'take_profit_multiplier': 2.0, 'max_trend_bars': 10, 'min_trend_bars': 3, 'atr_period': 14
    },
    'Trend Following ADX (default)': {
        'adx_period': 14, 'ma_fast': 10, 'ma_slow': 30,
        'atr_period': 14, 'stop_multiplier': 1.5, 'take_profit_multiplier': 2.5
    },
    'Trend VWMA+SOTT (default)': {
        'vwma_fast': 8, 'vwma_slow': 30,
        'sott_k': 100, 'sott_k_smooth': 10,
        'sott_ott_period': 2, 'sott_ott_percent': 0.5,
        'atr_period': 14, 'stop_multiplier': 1.5, 'take_profit_multiplier': 2.5
    },
    'Trend VWMA+SOTT (tuned)': {
        'vwma_fast': 6, 'vwma_slow': 25,
        'sott_k': 80, 'sott_k_smooth': 8,
        'sott_ott_period': 2, 'sott_ott_percent': 0.3,
        'atr_period': 14, 'stop_multiplier': 1.2, 'take_profit_multiplier': 2.0
    },
    'Trend PMax+NSM (default)': {
        'atr_length': 8, 'atr_multiplier': 3.6, 'ma_length': 10,
        'macd_fast': 12, 'macd_slow': 26, 'macd_signal': 9,
        'atr_period': 14, 'stop_multiplier': 1.5, 'take_profit_multiplier': 2.5
    },
    'Trend PMax+NSM (tuned)': {
        'atr_length': 6, 'atr_multiplier': 3.0, 'ma_length': 8,
        'macd_fast': 10, 'macd_slow': 21, 'macd_signal': 7,
        'atr_period': 14, 'stop_multiplier': 1.2, 'take_profit_multiplier': 2.0
    },
    'Trend Aroon+RSI+SMA (default)': {
        'aroon_period': 14, 'rsi_period': 14, 'sma_period': 10,
        'atr_period': 14, 'stop_multiplier': 1.5, 'take_profit_multiplier': 2.5
    },
    'Trend Aroon+RSI+SMA (tuned)': {
        'aroon_period': 10, 'rsi_period': 10, 'sma_period': 8,
        'atr_period': 14, 'stop_multiplier': 1.2, 'take_profit_multiplier': 2.0
    },
}

# ============================================================================
# SYMBOLS
# ============================================================================
ALL_SYMBOLS = ["BreakX 600", "BreakX 1200", "BreakX 1800", "PainX 600", "GainX 800",
               "FX Vol 20", "FX Vol 40", "FX Vol 60", "FX Vol 80", "FX Vol 99","PainX 800",
               "GainX 400","FlipX 1","PainX 400"]

SYMBOL_VARIANTS = {
    "FX Vol 20": ["FX Vol 20", "Fx Vol 20"],
    "FX Vol 40": ["FX Vol 40", "Fx Vol 40"],
    "FX Vol 60": ["FX Vol 60", "Fx Vol 60"],
    "FX Vol 80": ["FX Vol 80", "Fx Vol 80"],
    "FX Vol 99": ["FX Vol 99", "Fx Vol 99"],
}

# ============================================================================
# LOAD STRATEGIES FROM BACKTEST
# ============================================================================
def load_strategies_from_backtest():
    csv_files = glob.glob("backtest_full_summary.csv")
    if not csv_files:
        csv_files = glob.glob("backtest_comparison.csv")
    if not csv_files:
        print("⚠️ No backtest summary found. Using default strategies.")
        return ['Scalping DMI+MACD (default)', 'Scalping DMI+MACD (tuned)', 'Scalping HMA+Stoch (tuned)']
    
    df = pd.read_csv(csv_files[0])
    df.columns = df.columns.str.strip()
    
    if 'Total PnL' in df.columns and 'Trades' in df.columns:
        df['Total PnL'] = pd.to_numeric(df['Total PnL'], errors='coerce')
        df['Trades'] = pd.to_numeric(df['Trades'], errors='coerce')
        
        grouped = df.groupby('Strategy').agg({
            'Total PnL': 'sum',
            'Trades': 'sum'
        }).reset_index()
        
        valid = grouped[(grouped['Total PnL'] > 0) & (grouped['Trades'] > 5)]
        strategies = valid['Strategy'].tolist()
        if strategies:
            print(f"✅ Loaded {len(strategies)} strategies from backtest summary")
            return strategies
    
    return ['Scalping DMI+MACD (default)', 'Scalping DMI+MACD (tuned)', 'Scalping HMA+Stoch (tuned)']

# ============================================================================
# LIVE TRADING ENGINE
# ============================================================================
class LiveTradingEngine:
    def __init__(self, symbols=None, max_total_positions=7, max_positions_per_strategy=3,
                 strategy_list=None, use_optimized=False, demo_mode=True, verbose=True,
                 risk_per_trade=1.0, terminal_path: Optional[str] = None,
                 breakeven_trigger: float = 0.0, profit_lock_fraction: float = 0.5):
        self.symbols = symbols or ALL_SYMBOLS
        self.max_total_positions = max_total_positions
        self.max_positions_per_strategy = max_positions_per_strategy
        self.use_optimized = use_optimized
        self.demo_mode = demo_mode
        self.verbose = verbose
        self.risk_per_trade = risk_per_trade / 100.0
        self.breakeven_trigger = breakeven_trigger
        self.profit_lock_fraction = profit_lock_fraction
        self.strategy_list = strategy_list or load_strategies_from_backtest()
        self.position_count = 0
        self.strategy_positions = {s: 0 for s in self.strategy_list}
        self.performance = {s: {'trades': 0, 'pnl': 0, 'wins': 0, 'losses': 0} for s in self.strategy_list}
        self.cycle_count = 0
        self.open_positions = {}

        # Session management
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = f"live_results/session_{self.session_id}"
        os.makedirs(self.session_dir, exist_ok=True)
        self.trade_log = []

        # Sync settings
        self.sync_interval = 10
        self.cycle_counter = 0

        # MT5 connector
        self.conn = MT5Connection(terminal_path=terminal_path)
        self.symbol_dna_cache = {}

    def _log(self, msg, level="INFO"):
        if self.verbose:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{level}] {msg}")

    # ========================================================================
    # JSONL STREAMING
    # ========================================================================
    def _log_event(self, event_type, data):
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data
        }
        events_file = os.path.join(self.session_dir, "events.jsonl")
        with open(events_file, 'a') as f:
            f.write(json.dumps(event, default=str) + "\n")

    def _log_equity(self):
        if not self.is_mt5_ready():
            return
        balance = self.conn.get_account_balance()
        equity = self.conn.get_account_equity()
        self._log_event("equity", {
            "balance": balance,
            "equity": equity,
            "open_positions": self.position_count,
            "cycle": self.cycle_count
        })

    # ========================================================================
    # CONNECTION
    # ========================================================================
    def connect_mt5(self):
        self._log("Connecting via MT5Connection...")
        success = self.conn.connect()
        if success:
            self._log("✅ MT5 connected successfully via connector.")
        else:
            self._log("❌ MT5 connection failed.", "ERROR")
        return success

    def disconnect_mt5(self):
        self.conn.disconnect()
        self._log("MT5 disconnected")

    def is_mt5_ready(self):
        return self.conn.is_connected()

    # ========================================================================
    # HISTORY RETRIEVAL FOR EXTERNAL CLOSES
    # ========================================================================
    def _get_closed_trade_details(self, ticket):
        try:
            deals = mt5.history_deals_get(position=ticket)
            if deals is not None and len(deals) > 0:
                deal = deals[-1]
                return {
                    'exit_price': deal.price,
                    'pnl': deal.profit,
                    'close_time': deal.time,
                }
            orders = mt5.history_orders_get(ticket=ticket)
            if orders is not None and len(orders) > 0:
                order = orders[-1]
                return {
                    'exit_price': order.price,
                    'pnl': order.profit,
                    'close_time': order.time_done,
                }
            return None
        except Exception as e:
            self._log(f"Error fetching history for ticket {ticket}: {e}", "ERROR")
            return None

    # ========================================================================
    # POSITION SYNCHRONISATION
    # ========================================================================
    def _sync_open_positions(self):
        if not self.is_mt5_ready():
            self._log("MT5 not ready, cannot sync positions.", "WARNING")
            return

        self._log("Syncing open positions with MT5...")
        mt5_positions = self.conn.get_positions()
        mt5_tickets = set()
        mt5_pos_dict = {}
        for pos in mt5_positions:
            mt5_tickets.add(pos['ticket'])
            mt5_pos_dict[pos['ticket']] = pos

        to_remove = []
        for key, local_pos in self.open_positions.items():
            ticket = local_pos.get('ticket')
            if ticket is not None and ticket not in mt5_tickets:
                self._log(f"Position {ticket} ({local_pos['strategy']} on {local_pos['symbol']}) no longer in MT5.")
                history = self._get_closed_trade_details(ticket)
                if history is not None:
                    pnl = history.get('pnl', 0)
                    if pnl != 0:
                        self.performance[local_pos['strategy']]['trades'] += 1
                        self.performance[local_pos['strategy']]['pnl'] += pnl
                        if pnl > 0:
                            self.performance[local_pos['strategy']]['wins'] += 1
                        else:
                            self.performance[local_pos['strategy']]['losses'] += 1
                        self._log(f"📊 Recorded PnL from closed trade {ticket}: ${pnl:.2f}")
                    for trade in self.trade_log:
                        if trade.get('ticket') == ticket and trade.get('status') == 'open':
                            trade['status'] = 'closed'
                            trade['exit_price'] = history.get('exit_price')
                            trade['exit_time'] = datetime.fromtimestamp(history.get('close_time', time.time())).isoformat()
                            trade['pnl'] = pnl
                            trade['close_reason'] = 'external (SL/TP or manual)'
                            break
                else:
                    for trade in self.trade_log:
                        if trade.get('ticket') == ticket and trade.get('status') == 'open':
                            trade['status'] = 'stale'
                            trade['close_reason'] = 'no history found'
                            break
                to_remove.append(key)

        for key in to_remove:
            self._remove_local_position(key, reason="stale")

        for ticket, pos in mt5_pos_dict.items():
            exists = any(local.get('ticket') == ticket for local in self.open_positions.values())
            if exists:
                continue
            genx_sym = pos.get('symbol') or pos.get('mt5_symbol', 'Unknown')
            comment = pos.get('comment', '')
            strategy_name = None
            if comment.startswith("SYNTHX_"):
                raw = comment[7:]
                for s in self.strategy_list:
                    clean_s = s.replace(' ', '_').replace('(', '').replace(')', '').replace('+', '').replace('-', '')
                    if clean_s in raw or raw in clean_s:
                        strategy_name = s
                        break
            if not strategy_name:
                strategy_name = self.strategy_list[0] if self.strategy_list else "Unknown"
                self._log(f"Could not determine strategy for position {ticket}, assigning to {strategy_name}")

            key = (strategy_name, genx_sym)
            if key in self.open_positions:
                self.open_positions[key]['ticket'] = ticket
            else:
                self.open_positions[key] = {
                    'strategy': strategy_name,
                    'symbol': genx_sym,
                    'entry_price': pos['price_open'],
                    'sl': pos['sl'],
                    'tp': pos['tp'],
                    'lot': pos['volume'],
                    'entry_time': datetime.fromtimestamp(pos.get('time', time.time())),
                    'action': 'BUY' if pos['type'] == mt5.ORDER_TYPE_BUY else 'SELL',
                    'status': 'open',
                    'ticket': ticket
                }
                self.position_count += 1
                self.strategy_positions[strategy_name] = self.strategy_positions.get(strategy_name, 0) + 1
                self._log(f"Added missing position {ticket} ({strategy_name} on {genx_sym}) from MT5 sync.")

        self._log(f"Sync complete. Local positions: {self.position_count}")

    def _remove_local_position(self, key, reason="stale"):
        if key not in self.open_positions:
            return
        pos = self.open_positions[key]
        ticket = pos.get('ticket')
        if ticket is not None:
            for trade in self.trade_log:
                if trade.get('ticket') == ticket and trade.get('status') == 'open':
                    trade['status'] = 'closed' if reason == 'closed' else 'stale'
                    trade['exit_time'] = datetime.now().isoformat()
                    trade['exit_price'] = None
                    trade['pnl'] = None
                    trade['close_reason'] = reason
                    break
        self.position_count = max(0, self.position_count - 1)
        self.strategy_positions[pos['strategy']] = max(0, self.strategy_positions.get(pos['strategy'], 0) - 1)
        self._log(f"🧹 Removed {reason} position {pos['strategy']} on {pos['symbol']} from local tracking.")
        del self.open_positions[key]

    # ========================================================================
    # SYMBOL RESOLUTION
    # ========================================================================
    def _resolve_mt5_symbol(self, genx_name):
        mt5_sym = self.conn.resolve_genx_symbol(genx_name)
        if mt5_sym:
            return mt5_sym
        variants = SYMBOL_VARIANTS.get(genx_name, [genx_name])
        for v in variants:
            info = mt5.symbol_info(v)
            if info is not None:
                return v
        return None

    # ========================================================================
    # DATA FETCHING & DNA COMPUTATION
    # ========================================================================
    def get_live_ohlc(self, symbol, bars=200):
        if not self.is_mt5_ready():
            return None
        mt5_sym = self._resolve_mt5_symbol(symbol)
        if not mt5_sym:
            return None
        df = self.conn.get_historical_data(mt5_sym, mt5.TIMEFRAME_M5, bars)
        if df.empty:
            return None
        df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close'
        }, inplace=True)
        if 'Date' in df.columns:
            df.set_index('Date', inplace=True)
        return df[['Open', 'High', 'Low', 'Close']]

    def _compute_dna_profile(self, symbol, df):
        if df is None or len(df) < 50:
            return None
        try:
            analyzer = DNAAnalyzer(df, symbol, mt5.TIMEFRAME_M5)
            if hasattr(analyzer, 'context'):
                profile = analyzer.context
            elif hasattr(analyzer, 'profile'):
                profile = analyzer.profile
            elif hasattr(analyzer, 'get_profile'):
                profile = analyzer.get_profile()
            else:
                profile = None
            return profile
        except Exception as e:
            self._log(f"Error computing DNA for {symbol}: {e}", "ERROR")
            return None

    # ========================================================================
    # OPTIMIZED PARAMETER LOADING
    # ========================================================================
    def _load_optimized_params(self, strategy_name, symbol):
        opt_dir = "optimized_strategies"
        all_files = glob.glob(os.path.join(opt_dir, "*_final.json"))
        
        def sanitize(name):
            return name.replace(' ', '_').replace('(', '').replace(')', '').replace('+', '')
        
        target_sanitized = sanitize(strategy_name)
        for f in all_files:
            basename = os.path.basename(f).replace('_final.json', '')
            parts = basename.rsplit('_', 1)
            if len(parts) != 2:
                continue
            file_strategy, file_symbol = parts[0], parts[1]
            if sanitize(file_strategy) == target_sanitized and file_symbol == symbol:
                try:
                    with open(f, 'r') as fh:
                        data = json.load(fh)
                        return data.get('best_params')
                except:
                    return None
        return None

    # ========================================================================
    # STRATEGY PARAMETERS
    # ========================================================================
    def get_strategy_params(self, strategy_name, symbol):
        if self.use_optimized:
            params = self._load_optimized_params(strategy_name, symbol)
            if params:
                self._log(f"🔧 Using OPTIMIZED parameters for {strategy_name} on {symbol}")
                return params, "optimized"
            else:
                self._log(f"⚠️ No optimized params found for {strategy_name} on {symbol}, falling back to default.")
        if strategy_name in DEFAULT_PARAMS:
            return DEFAULT_PARAMS[strategy_name], "default"
        for key, params in DEFAULT_PARAMS.items():
            if key in strategy_name or strategy_name in key:
                return params, "default"
        base_name = strategy_name.split('(')[0].strip()
        for key, params in DEFAULT_PARAMS.items():
            if key.startswith(base_name) or base_name.startswith(key):
                return params, "default"
        return None, None

    def get_strategy_class(self, strategy_name):
        if strategy_name in STRATEGY_CLASS_MAP:
            return STRATEGY_CLASS_MAP[strategy_name]
        for key, cls in STRATEGY_CLASS_MAP.items():
            if key in strategy_name or strategy_name in key:
                return cls
        base_name = strategy_name.split('(')[0].strip()
        for key, cls in STRATEGY_CLASS_MAP.items():
            if key.startswith(base_name) or base_name.startswith(key):
                return cls
        return None

    # ========================================================================
    # ORDER SENDING & POSITION MANAGEMENT
    # ========================================================================
    def _calculate_lot(self, symbol, entry_price, stop_loss):
        if entry_price is None or stop_loss is None:
            return 0.01
        if not self.is_mt5_ready():
            return 0.01
        used_symbol = self._resolve_mt5_symbol(symbol)
        if not used_symbol:
            return 0.01
        symbol_info = mt5.symbol_info(used_symbol)
        if symbol_info is None:
            return 0.01
        tick_value = symbol_info.trade_tick_value
        tick_size = symbol_info.trade_tick_size
        if tick_size == 0:
            return 0.01
        account = mt5.account_info()
        if account is None:
            return 0.01
        risk_amount = account.equity * self.risk_per_trade
        sl_distance = abs(entry_price - stop_loss)
        ticks = sl_distance / tick_size
        if ticks == 0:
            return 0.01
        lot = risk_amount / (ticks * tick_value)
        lot_step = symbol_info.volume_step
        lot = round(lot / lot_step) * lot_step
        lot = max(symbol_info.volume_min, min(symbol_info.volume_max, lot))
        return round(lot, 2)

    def _send_mt5_order(self, symbol, action, lot, sl, tp, comment):
        if not self.is_mt5_ready():
            return False, "MT5 not ready", None
        if self.demo_mode:
            self._log(f"  [DEMO] {action} {lot} lots on {symbol} (SL: {sl}, TP: {tp})")
            return True, "Demo order accepted", None

        used_symbol = self._resolve_mt5_symbol(symbol)
        if not used_symbol:
            return False, f"Symbol {symbol} not found", None

        if action.upper() == "BUY":
            order_type = mt5.ORDER_TYPE_BUY
        elif action.upper() == "SELL":
            order_type = mt5.ORDER_TYPE_SELL
        else:
            return False, f"Invalid action: {action}", None

        result = self.conn.place_market_order(
            symbol=used_symbol,
            order_type=order_type,
            volume=lot,
            sl=sl,
            tp=tp,
            comment="GenX",
            filling_mode=mt5.ORDER_FILLING_FOK
        )

        if result.get('success'):
            return True, f"Order placed: {result.get('order_id')} (price: {result.get('price')})", result.get('order_id')
        else:
            return False, f"Order failed: {result.get('error', 'Unknown error')}", None

    def _update_stop_loss(self, ticket, new_sl):
        if self.demo_mode:
            self._log(f"[DEMO] Update SL for {ticket} to {new_sl}")
            return True
        if not self.is_mt5_ready():
            return False
        try:
            pos = mt5.positions_get(ticket=ticket)
            if not pos or len(pos) == 0:
                return False
            pos = pos[0]
            symbol = pos.symbol
            current_tp = pos.tp if pos.tp else 0
        except:
            return False

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": current_tp,
            "magic": 123456,
        }
        try:
            result = mt5.order_send(request)
            if result is None:
                return False
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                self._log(f"✅ Stop loss updated to {new_sl} for ticket {ticket}")
                return True
            else:
                self._log(f"Failed to update SL for {ticket}: {result.comment} (code {result.retcode})", "ERROR")
                return False
        except Exception as e:
            self._log(f"Exception updating SL: {e}", "ERROR")
            return False

    def open_position(self, strategy_name, symbol, signal, dna_profile=None):
        key = (strategy_name, symbol)
        if key in self.open_positions:
            return None
        if self.position_count >= self.max_total_positions:
            self._log(f"Total position limit reached ({self.position_count}/{self.max_total_positions})")
            return None
        if self.strategy_positions.get(strategy_name, 0) >= self.max_positions_per_strategy:
            self._log(f"{strategy_name} limit reached ({self.strategy_positions[strategy_name]}/{self.max_positions_per_strategy})")
            return None

        entry = signal['entry']
        sl = signal['stop_loss']
        tp = signal['take_profit']
        lot = self._calculate_lot(symbol, entry, sl)
        if lot <= 0:
            self._log(f"Invalid lot size: {lot}", "ERROR")
            return None

        success, msg, order_id = self._send_mt5_order(symbol, signal['action'], lot, sl, tp, "GenX")
        if not success:
            self._log(f"Order failed: {msg}", "ERROR")
            return None

        pos = {
            'strategy': strategy_name,
            'symbol': symbol,
            'entry_price': entry,
            'sl': sl,
            'initial_sl': sl,
            'tp': tp,
            'lot': lot,
            'entry_time': datetime.now(),
            'action': signal['action'],
            'status': 'open',
            'ticket': order_id
        }
        self.open_positions[key] = pos
        self.position_count += 1
        self.strategy_positions[strategy_name] = self.strategy_positions.get(strategy_name, 0) + 1
        self._log(f"🟢 OPEN {strategy_name} on {symbol} @ {entry:.2f} (Ticket: {order_id}, Total: {self.position_count})")

        trade_entry = {
            'ticket': order_id,
            'strategy': strategy_name,
            'symbol': symbol,
            'action': signal['action'],
            'entry_price': entry,
            'lot': lot,
            'sl': sl,
            'tp': tp,
            'entry_time': datetime.now().isoformat(),
            'exit_price': None,
            'exit_time': None,
            'pnl': None,
            'status': 'open',
        }
        if dna_profile is not None:
            trade_entry['dna'] = dna_profile
        self.trade_log.append(trade_entry)

        self._log_event("trade_open", {
            "ticket": order_id,
            "strategy": strategy_name,
            "symbol": symbol,
            "action": signal['action'],
            "entry_price": entry,
            "lot": lot,
            "sl": sl,
            "tp": tp
        })
        self._log_equity()
        return pos

    def close_position(self, key, exit_price=None):
        if key not in self.open_positions:
            return
        pos = self.open_positions[key]
        if pos['status'] != 'open':
            return

        if not self.demo_mode and pos.get('ticket'):
            try:
                mt5_check = mt5.positions_get(ticket=pos['ticket'])
            except Exception as e:
                self._log(f"Error checking position {pos['ticket']}: {e}", "ERROR")
                return
            if mt5_check is None or len(mt5_check) == 0:
                self._log(f"Position {pos['ticket']} no longer exists in MT5. Removing locally.")
                self._remove_local_position(key, reason="stale")
                return

        close_success = False
        if not self.demo_mode and pos.get('ticket'):
            try:
                close_result = self.conn.close_position(pos['ticket'], comment="GenX_Close")
            except Exception as e:
                self._log(f"Exception in close_position: {e}", "ERROR")
                return

            if close_result.get('success'):
                self._log(f"✅ MT5 position {pos['ticket']} closed.")
                close_success = True
            else:
                error_msg = close_result.get('error', '').lower()
                if "not found" in error_msg or "already closed" in error_msg:
                    self._log(f"Position {pos['ticket']} already closed; removing locally.")
                    self._remove_local_position(key, reason="stale")
                    return
                else:
                    self._log(f"⚠️ Failed to close MT5 position {pos['ticket']}: {close_result.get('error')}", "ERROR")
                    return
        else:
            close_success = True

        if exit_price is None:
            df = self.get_live_ohlc(pos['symbol'], 1)
            if df is not None:
                exit_price = df['Close'].iloc[-1]
            else:
                exit_price = pos['entry_price']

        if pos['action'] == 'BUY':
            pnl = (exit_price - pos['entry_price']) * pos['lot']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['lot']

        pos['exit_price'] = exit_price
        pos['exit_time'] = datetime.now()
        pos['pnl'] = pnl
        pos['status'] = 'closed'

        self.position_count = max(0, self.position_count - 1)
        self.strategy_positions[pos['strategy']] = max(0, self.strategy_positions.get(pos['strategy'], 0) - 1)
        self.performance[pos['strategy']]['trades'] += 1
        self.performance[pos['strategy']]['pnl'] += pnl
        if pnl > 0:
            self.performance[pos['strategy']]['wins'] += 1
        else:
            self.performance[pos['strategy']]['losses'] += 1

        self._log(f"🔴 CLOSE {pos['strategy']} on {pos['symbol']} PnL: ${pnl:.2f}")

        for trade in self.trade_log:
            if trade.get('ticket') == pos.get('ticket') and trade.get('status') == 'open':
                trade['exit_price'] = exit_price
                trade['exit_time'] = datetime.now().isoformat()
                trade['pnl'] = pnl
                trade['status'] = 'closed'
                trade['close_reason'] = 'signal'
                break

        self._log_event("trade_close", {
            "ticket": pos['ticket'],
            "strategy": pos['strategy'],
            "symbol": pos['symbol'],
            "exit_price": exit_price,
            "pnl": pnl,
            "reason": "signal"
        })
        self._log_equity()

        del self.open_positions[key]

    # ========================================================================
    # SESSION SAVING
    # ========================================================================
    def _save_session(self):
        trade_file = os.path.join(self.session_dir, "trades.json")
        with open(trade_file, 'w') as f:
            json.dump(self.trade_log, f, indent=2, default=str)
        self._log(f"Trade log saved to {trade_file}")

        perf_file = os.path.join(self.session_dir, "performance.json")
        with open(perf_file, 'w') as f:
            json.dump(self.performance, f, indent=2)
        self._log(f"Performance saved to {perf_file}")

        if self.open_positions:
            pos_snapshot = {}
            for key, pos in self.open_positions.items():
                pos_snapshot[f"{key[0]}_{key[1]}"] = pos
            pos_file = os.path.join(self.session_dir, "open_positions.json")
            with open(pos_file, 'w') as f:
                json.dump(pos_snapshot, f, indent=2, default=str)
            self._log(f"Open positions snapshot saved to {pos_file}")

    # ========================================================================
    # MAIN LOOP (with TP-based breakeven)
    # ========================================================================
    def run_cycle(self, bars=200):
        self.cycle_count += 1
        self.cycle_counter += 1

        if self.cycle_counter % self.sync_interval == 0:
            self._sync_open_positions()
            self._log_equity()

        self._log(f"🔄 Cycle {self.cycle_count}")

        if not self.is_mt5_ready():
            self._log("MT5 not ready, attempting reconnect...")
            if not self.connect_mt5():
                self._log("Failed to reconnect", "ERROR")
                return

        self.symbol_dna_cache = {}

        for symbol in self.symbols:
            df = self.get_live_ohlc(symbol, bars)
            if df is None:
                continue
            dna_profile = self._compute_dna_profile(symbol, df)
            if dna_profile is not None:
                self.symbol_dna_cache[symbol] = dna_profile
            else:
                self.symbol_dna_cache[symbol] = None

            for strategy_name in self.strategy_list:
                key = (strategy_name, symbol)
                existing = self.open_positions.get(key)

                params, param_type = self.get_strategy_params(strategy_name, symbol)
                if params is None:
                    continue

                strategy_class = self.get_strategy_class(strategy_name)
                if strategy_class is None:
                    continue

                try:
                    strategy = strategy_class(**params)
                    signal = strategy.generate_signal(df)

                    if existing and signal.get('action') in ['CLOSE_LONG', 'CLOSE_SHORT']:
                        self.close_position(key)
                        continue

                    if signal.get('action') in ['BUY', 'SELL'] and existing is None:
                        if self.position_count >= self.max_total_positions:
                            continue
                        if self.strategy_positions.get(strategy_name, 0) >= self.max_positions_per_strategy:
                            continue
                        self.open_position(strategy_name, symbol, signal, dna_profile=self.symbol_dna_cache.get(symbol))
                except Exception as e:
                    self._log(f"Error in strategy {strategy_name}: {e}", "ERROR")
                    continue

        # ---- Breakeven with Profit Lock (TP-based) ----
        if self.breakeven_trigger > 0 and self.profit_lock_fraction > 0:
            for key, pos in list(self.open_positions.items()):
                if pos.get('status') != 'open':
                    continue
                ticket = pos.get('ticket')
                if not ticket:
                    continue
                symbol = pos['symbol']
                mt5_sym = self._resolve_mt5_symbol(symbol)
                if not mt5_sym:
                    continue
                tick = mt5.symbol_info_tick(mt5_sym)
                if not tick:
                    continue
                current_price = tick.bid if pos['action'] == 'SELL' else tick.ask
                entry = pos['entry_price']
                tp = pos['tp']
                tp_distance = abs(tp - entry)
                if tp_distance == 0:
                    continue

                if pos['action'] == 'BUY':
                    profit = current_price - entry
                    if profit >= tp_distance * self.breakeven_trigger:
                        locked_profit = profit * self.profit_lock_fraction
                        new_sl = entry + locked_profit
                        # Ensure new SL is above current SL and below current price
                        tick_size = mt5.symbol_info(mt5_sym).trade_tick_size
                        new_sl = min(new_sl, current_price - tick_size)
                        if new_sl > pos['sl']:
                            if self._update_stop_loss(ticket, new_sl):
                                pos['sl'] = new_sl
                else:  # SELL
                    profit = entry - current_price
                    if profit >= tp_distance * self.breakeven_trigger:
                        locked_profit = profit * self.profit_lock_fraction
                        new_sl = entry - locked_profit
                        tick_size = mt5.symbol_info(mt5_sym).trade_tick_size
                        new_sl = max(new_sl, current_price + tick_size)
                        if new_sl < pos['sl']:
                            if self._update_stop_loss(ticket, new_sl):
                                pos['sl'] = new_sl

        self._log_equity()

    def print_status(self):
        print("\n" + "="*70)
        print(f"📊 STATUS: Cycle {self.cycle_count} | Positions: {self.position_count}/{self.max_total_positions}")
        print("   Strategy Positions:")
        for strat, count in self.strategy_positions.items():
            if count > 0:
                print(f"      {strat}: {count}")
        print("   Open Positions:")
        for key, pos in self.open_positions.items():
            if pos['status'] == 'open':
                print(f"      {pos['strategy']} on {pos['symbol']} @ {pos['entry_price']:.2f} (Ticket: {pos.get('ticket', 'N/A')})")
        print("="*70)

    def print_final_summary(self):
        print("\n" + "="*70)
        print("📊 FINAL PERFORMANCE SUMMARY")
        print("="*70)
        total_trades = 0
        total_pnl = 0
        total_wins = 0
        total_losses = 0
        for strat, perf in self.performance.items():
            if perf['trades'] > 0:
                win_rate = (perf['wins'] / perf['trades']) * 100 if perf['trades'] > 0 else 0
                print(f"   {strat}: {perf['trades']} trades, PnL: ${perf['pnl']:.2f}, Win Rate: {win_rate:.1f}%")
                total_trades += perf['trades']
                total_pnl += perf['pnl']
                total_wins += perf['wins']
                total_losses += perf['losses']
        if total_trades > 0:
            win_rate = (total_wins / total_trades) * 100
            print(f"   TOTAL: {total_trades} trades, PnL: ${total_pnl:.2f}, Win Rate: {win_rate:.1f}%")
        print("="*70)

    # ========================================================================
    # RUN METHOD (MUST EXIST)
    # ========================================================================
    def run(self, cycles=10, bars=200, interval=10):
        if not self.connect_mt5():
            return

        self._sync_open_positions()

        self._log(f"🚀 Starting live trading engine (Session: {self.session_id})")
        self._log(f"   Strategies: {len(self.strategy_list)} strategies")
        self._log(f"   Symbols: {self.symbols}")
        self._log(f"   Max total positions: {self.max_total_positions}, Max per strategy: {self.max_positions_per_strategy}")
        self._log(f"   Using optimized params: {self.use_optimized}")
        self._log(f"   Risk per trade: {self.risk_per_trade*100:.1f}%")
        self._log(f"   Demo mode: {self.demo_mode}")
        self._log(f"   Breakeven trigger: {self.breakeven_trigger*100:.1f}% (of TP distance)")
        self._log(f"   Profit lock fraction: {self.profit_lock_fraction*100:.1f}%")

        if not self.demo_mode:
            self._log("⚠️  REAL ORDERS ARE ENABLED! Proceed with caution.", "WARNING")
            confirm = input("Type 'CONFIRM' to continue with real orders: ")
            if confirm != "CONFIRM":
                self._log("Aborted by user.")
                return

        try:
            for cycle in range(cycles):
                self.run_cycle(bars)
                self.print_status()
                time.sleep(interval)
        except KeyboardInterrupt:
            self._log("Interrupted by user")
        finally:
            self._log("Closing all remaining positions...")
            for key in list(self.open_positions.keys()):
                self.close_position(key)
            self.disconnect_mt5()
            self.print_final_summary()
            self._save_session()

# ============================================================================
# EXPOSE FOR CLI
# ============================================================================
__all__ = [
    'LiveTradingEngine',
    'ALL_SYMBOLS',
    'load_strategies_from_backtest',
]

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    engine = LiveTradingEngine(
        symbols=None,
        max_total_positions=7,
        max_positions_per_strategy=3,
        strategy_list=None,
        use_optimized=False,
        demo_mode=False,
        verbose=True,
        risk_per_trade=1.0
    )
    engine.run(cycles=100, bars=200, interval=60)