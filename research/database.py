import pandas as pd
import numpy as np
import json
import os
import glob
from datetime import datetime
from tqdm import tqdm
import hashlib
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
#  RESEARCH DATABASE – JSONL Based
# ============================================================================
class ResearchDatabase:
    def __init__(self, data_dir="research_data"):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        self.trades_file = os.path.join(data_dir, "trades.jsonl")
        self.insights_file = os.path.join(data_dir, "insights.json")
        
        # Ensure files exist
        if not os.path.exists(self.trades_file):
            with open(self.trades_file, 'w') as f:
                pass

    def store_trade(self, trade_record):
        """Store a single trade record as JSONL."""
        # Generate unique trade ID
        trade_id = hashlib.md5(
            f"{trade_record['symbol']}_{trade_record['entry_time']}_{trade_record['direction']}".encode()
        ).hexdigest()[:16]
        
        trade_record['trade_id'] = trade_id
        trade_record['created_at'] = datetime.now().isoformat()
        
        # Ensure nested dicts are properly structured
        trade_record['dna'] = trade_record.get('dna', {})
        trade_record['parameters'] = trade_record.get('parameters', {})
        trade_record['entry_conditions'] = trade_record.get('entry_conditions', {})
        
        with open(self.trades_file, 'a') as f:
            f.write(json.dumps(trade_record) + '\n')
        
        return trade_id

    def store_batch_trades(self, trades):
        """Store multiple trades efficiently."""
        count = 0
        for trade in trades:
            self.store_trade(trade)
            count += 1
        print(f"💾 Saved {count} trades to {self.trades_file}")
        return count

    def read_all_trades(self):
        """Read all trades into a DataFrame."""
        if not os.path.exists(self.trades_file) or os.path.getsize(self.trades_file) == 0:
            return pd.DataFrame()
        
        trades = []
        with open(self.trades_file, 'r') as f:
            for line in f:
                try:
                    trades.append(json.loads(line.strip()))
                except:
                    continue
        
        if not trades:
            return pd.DataFrame()
        
        df = pd.DataFrame(trades)
        
        # Expand nested JSON columns
        for col in ['dna', 'parameters', 'entry_conditions']:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: x if isinstance(x, dict) else {})
        
        return df

    # ============================================================================
    #  QUERY METHODS
    # ============================================================================

    def query_trades(self, filters=None):
        """
        Query trades with filters.
        
        filters: dict of conditions
        Example: {'symbol': 'BreakX 600', 'result': 'TP'}
        """
        df = self.read_all_trades()
        if df.empty:
            return df
        
        if filters:
            for key, value in filters.items():
                if key in df.columns:
                    df = df[df[key] == value]
                # Check if it's a nested field
                elif '.' in key:
                    parts = key.split('.')
                    if parts[0] in df.columns:
                        df = df[df[parts[0]].apply(lambda x: x.get(parts[1]) == value)]
        
        return df

    def get_trades_by_dna(self, dna_filters):
        """Get trades matching specific DNA conditions."""
        df = self.read_all_trades()
        if df.empty:
            return df
        
        for key, (min_val, max_val) in dna_filters.items():
            df = df[df['dna'].apply(lambda x: min_val <= x.get(key, 0) <= max_val)]
        
        return df

    def get_trades_by_parameters(self, param_filters):
        """Get trades matching specific parameter conditions."""
        df = self.read_all_trades()
        if df.empty:
            return df
        
        for key, (min_val, max_val) in param_filters.items():
            df = df[df['parameters'].apply(lambda x: min_val <= x.get(key, 0) <= max_val)]
        
        return df

    def get_performance_by_dna_bucket(self, dna_key, bins=10):
        """Group trades by DNA bucket and compute performance metrics."""
        df = self.read_all_trades()
        if df.empty:
            return pd.DataFrame()
        
        # Extract DNA values
        df['dna_value'] = df['dna'].apply(lambda x: x.get(dna_key, 0))
        df = df[df['dna_value'].notna()]
        
        if df.empty:
            return pd.DataFrame()
        
        # Create bins
        df['dna_bucket'] = pd.cut(df['dna_value'], bins=bins)
        
        # Aggregate performance
        performance = df.groupby('dna_bucket').agg({
            'pnl': ['count', 'sum', 'mean', 'std'],
            'result': lambda x: (x == 'TP').mean() * 100
        }).round(2)
        
        performance.columns = ['trades', 'total_pnl', 'avg_pnl', 'std_pnl', 'win_rate']
        performance['sharpe'] = performance['avg_pnl'] / (performance['std_pnl'] + 1e-10)
        performance = performance.fillna(0)
        
        return performance

    def get_parameter_performance(self, strategy=None, top_n=10):
        """Get top performing parameter sets for a strategy."""
        df = self.read_all_trades()
        if df.empty:
            return pd.DataFrame()
        
        # Filter by strategy
        if strategy:
            df = df[df['strategy'] == strategy]
        
        if df.empty:
            return pd.DataFrame()
        
        # Group by parameters (convert to JSON string for grouping)
        df['params_str'] = df['parameters'].apply(json.dumps)
        
        performance = df.groupby('params_str').agg({
            'pnl': ['count', 'sum', 'mean'],
            'result': lambda x: (x == 'TP').mean() * 100
        }).round(2)
        
        performance.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
        performance = performance.sort_values('total_pnl', ascending=False).head(top_n)
        
        # Convert params back to dict
        performance['parameters'] = performance.index.map(json.loads)
        performance = performance.reset_index(drop=True)
        
        return performance

    def get_best_parameters_for_dna(self, target_dna, strategy=None, top_n=5):
        """Find optimal parameters for a specific DNA profile."""
        df = self.read_all_trades()
        if df.empty:
            return pd.DataFrame()
        
        # Filter by strategy
        if strategy:
            df = df[df['strategy'] == strategy]
        
        if df.empty:
            return pd.DataFrame()
        
        # Calculate DNA similarity
        def dna_similarity(row):
            row_dna = row.get('dna', {})
            if not row_dna:
                return 0
            # Simple similarity: average of normalized differences
            sim = 0
            count = 0
            for key, target_val in target_dna.items():
                if key in row_dna:
                    diff = abs(row_dna[key] - target_val) / (max(target_val, 0.1) + 1e-10)
                    sim += 1 / (1 + diff)
                    count += 1
            return sim / count if count > 0 else 0
        
        df['dna_similarity'] = df.apply(dna_similarity, axis=1)
        
        # Filter to top 20% similar trades
        threshold = df['dna_similarity'].quantile(0.8)
        df_similar = df[df['dna_similarity'] >= threshold]
        
        if df_similar.empty:
            return pd.DataFrame()
        
        # Find best parameters in similar DNA space
        df_similar['params_str'] = df_similar['parameters'].apply(json.dumps)
        performance = df_similar.groupby('params_str').agg({
            'pnl': ['count', 'sum', 'mean'],
            'result': lambda x: (x == 'TP').mean() * 100
        }).round(2)
        
        performance.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
        performance = performance.sort_values('avg_pnl', ascending=False).head(top_n)
        
        # Convert params back to dict
        performance['parameters'] = performance.index.map(json.loads)
        performance = performance.reset_index(drop=True)
        
        return performance

    def get_insights(self):
        """Generate research insights from the trades database."""
        df = self.read_all_trades()
        if df.empty:
            return {'error': 'No trades in database'}
        
        insights = {}
        
        # 1. Basic stats
        insights['total_trades'] = len(df)
        insights['total_pnl'] = df['pnl'].sum()
        insights['avg_pnl'] = df['pnl'].mean()
        insights['win_rate'] = (df['result'] == 'TP').mean() * 100
        
        # 2. Best DNA profiles
        dna_metrics = {}
        for key in ['entropy', 'hurst', 'volatility', 'jump_rate', 'trend_length']:
            perf = self.get_performance_by_dna_bucket(key)
            if not perf.empty:
                best_bucket = perf['sharpe'].idxmax()
                dna_metrics[key] = {
                    'best_range': str(best_bucket),
                    'win_rate': perf.loc[best_bucket, 'win_rate'],
                    'avg_pnl': perf.loc[best_bucket, 'avg_pnl'],
                    'trades': perf.loc[best_bucket, 'trades']
                }
        insights['best_dna'] = dna_metrics
        
        # 3. Time-based patterns
        if 'entry_time' in df.columns:
            df['hour'] = pd.to_datetime(df['entry_time']).dt.hour
            hourly = df.groupby('hour').agg({
                'pnl': ['count', 'sum', 'mean'],
                'result': lambda x: (x == 'TP').mean() * 100
            })
            hourly.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
            insights['best_hours'] = hourly.sort_values('avg_pnl', ascending=False).head(5).to_dict('index')
        
        # 4. Strategy performance
        if 'strategy' in df.columns:
            strategy_perf = df.groupby('strategy').agg({
                'pnl': ['count', 'sum', 'mean'],
                'result': lambda x: (x == 'TP').mean() * 100
            })
            strategy_perf.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
            insights['strategy_performance'] = strategy_perf.sort_values('avg_pnl', ascending=False).to_dict('index')
        
        # 5. Top parameters
        insights['top_parameters'] = self.get_parameter_performance().to_dict('records')
        
        return insights

    def save_insights(self):
        """Save insights to a JSON file."""
        insights = self.get_insights()
        with open(self.insights_file, 'w') as f:
            json.dump(insights, f, indent=2, default=str)
        print(f"💾 Insights saved to {self.insights_file}")
        return insights


# ============================================================================
#  TRADE COLLECTOR – Integrates with backtester
# ============================================================================
class TradeCollector:
    """Collects trades from backtest and stores them in research database."""
    
    def __init__(self, data_dir="research_data"):
        self.db = ResearchDatabase(data_dir)
        self.backtest_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.trades = []
        
    def add_trade(self, trade):
        """Add a trade to the collection."""
        self.trades.append(trade)
        
    def add_trades_from_backtest(self, backtest_result, symbol, strategy, parameters, dna_snapshot):
        """
        Extract trades from a backtest result and add to collection.
        
        backtest_result: dict from StrategyBacktester._generate_report()
        symbol: string
        strategy: string
        parameters: dict
        dna_snapshot: dict of current DNA metrics
        """
        trades_df = backtest_result.get('trades_df', pd.DataFrame())
        
        if trades_df.empty:
            print("⚠️ No trades in backtest result")
            return
        
        print(f"📊 Processing {len(trades_df)} trades from backtest...")
        
        for _, trade in trades_df.iterrows():
            # Determine result
            reason = trade.get('reason', 'UNKNOWN')
            if reason == 'TP':
                result = 'TP'
            elif reason == 'SL':
                result = 'SL'
            elif reason in ['SCALE_OUT', 'END_OF_DATA']:
                result = 'EXIT'
            else:
                result = reason
            
            # Calculate holding bars
            entry_date = trade.get('entry_date')
            exit_date = trade.get('exit_date')
            holding_bars = 0
            if entry_date and exit_date:
                try:
                    diff = pd.to_datetime(exit_date) - pd.to_datetime(entry_date)
                    holding_bars = diff.seconds // 60 // 5  # Assuming 5-minute bars
                except:
                    pass
            
            trade_record = {
                'symbol': symbol,
                'entry_time': entry_date,
                'exit_time': exit_date,
                'direction': trade.get('type', 'UNKNOWN'),
                'entry_price': trade.get('entry_price', 0),
                'exit_price': trade.get('exit_price', 0),
                'volume': trade.get('volume', 0.01),
                'pnl': trade.get('pnl', 0),
                'pnl_percent': (trade.get('pnl', 0) / max(1, trade.get('entry_price', 1))) * 100,
                'result': result,
                'holding_bars': holding_bars,
                'strategy': strategy,
                'strategy_version': '1.0',
                'dna': dna_snapshot,
                'parameters': parameters,
                'entry_conditions': {
                    'price': trade.get('entry_price', 0),
                    'time': entry_date
                },
                'backtest_id': self.backtest_id
            }
            
            self.add_trade(trade_record)
    
    def save(self):
        """Save all collected trades to database."""
        if self.trades:
            count = self.db.store_batch_trades(self.trades)
            print(f"💾 Saved {count} trades to research database")
            self.trades = []
            return count
        else:
            print("⚠️ No trades to save")
            return 0


# ============================================================================
#  DNA SNAPSHOT COLLECTOR
# ============================================================================
class DNASnapshot:
    """Capture DNA snapshot at a point in time."""
    
    @staticmethod
    def from_dna_analyzer(dna_result):
        """Extract DNA snapshot from DNA Analyzer result."""
        if not dna_result:
            return {}
        
        # Try to extract from nested structure
        if 'dna' in dna_result:
            dna_result = dna_result['dna']
        
        return {
            'entropy': dna_result.get('chromosome_vi', {}).get('normalized_entropy', 0.5),
            'hurst': dna_result.get('chromosome_ii', {}).get('hurst_exponent', 0.5),
            'volatility': dna_result.get('chromosome_iii', {}).get('realized_vol', 0.5),
            'jump_rate': dna_result.get('chromosome_iv', {}).get('jump_intensity', 0),
            'trend_length': dna_result.get('chromosome_vii', {}).get('avg_trend_length', 0),
            'vol_persistence': dna_result.get('chromosome_iii', {}).get('vol_persistence', 0),
            'skewness': dna_result.get('chromosome_i', {}).get('skewness', 0),
            'kurtosis': dna_result.get('chromosome_i', {}).get('excess_kurtosis', 0),
            'predictability': dna_result.get('chromosome_vi', {}).get('predictability', 0),
            'is_synthetic': dna_result.get('chromosome_viii', {}).get('is_synthetic', False)
        }
    
    @staticmethod
    def from_dict(dna_dict):
        """Create DNA snapshot from a dictionary."""
        return {
            'entropy': dna_dict.get('entropy', 0.5),
            'hurst': dna_dict.get('hurst', 0.5),
            'volatility': dna_dict.get('volatility', 0.5),
            'jump_rate': dna_dict.get('jump_rate', 0),
            'trend_length': dna_dict.get('trend_length', 0),
            'vol_persistence': dna_dict.get('vol_persistence', 0),
            'skewness': dna_dict.get('skewness', 0),
            'kurtosis': dna_dict.get('kurtosis', 0),
            'predictability': dna_dict.get('predictability', 0),
            'is_synthetic': dna_dict.get('is_synthetic', False)
        }


# ============================================================================
#  RESEARCH ANALYZER – Ask questions about the database
# ============================================================================
class ResearchAnalyzer:
    def __init__(self, data_dir="research_data"):
        self.db = ResearchDatabase(data_dir)
    
    def print_summary(self):
        """Print a summary of the research database."""
        df = self.db.read_all_trades()
        if df.empty:
            print("No trades in database")
            return
        
        print("="*80)
        print("📊 RESEARCH DATABASE SUMMARY")
        print("="*80)
        print(f"Total Trades: {len(df):,}")
        print(f"Total PnL: ${df['pnl'].sum():.2f}")
        print(f"Average PnL: ${df['pnl'].mean():.2f}")
        print(f"Win Rate: {(df['result'] == 'TP').mean()*100:.1f}%")
        print(f"Profit Factor: {df[df['pnl']>0]['pnl'].sum() / abs(df[df['pnl']<0]['pnl'].sum()) if df[df['pnl']<0]['pnl'].sum() != 0 else 0:.2f}")
        print("-"*80)
        
        if 'strategy' in df.columns:
            print("Strategy Performance:")
            for strategy, group in df.groupby('strategy'):
                win_rate = (group['result'] == 'TP').mean() * 100
                print(f"  {strategy}: {len(group)} trades, ${group['pnl'].sum():.2f}, {win_rate:.1f}%")
        print("="*80)
    
    def question_1_best_dna_for_sharpe(self):
        """Which DNA profile produces the highest Sharpe?"""
        insights = {}
        for key in ['entropy', 'hurst', 'volatility', 'jump_rate', 'trend_length']:
            perf = self.db.get_performance_by_dna_bucket(key)
            if not perf.empty and 'sharpe' in perf.columns:
                best_bucket = perf['sharpe'].idxmax()
                insights[key] = {
                    'best_range': str(best_bucket),
                    'sharpe': float(perf.loc[best_bucket, 'sharpe']),
                    'win_rate': float(perf.loc[best_bucket, 'win_rate']),
                    'trades': int(perf.loc[best_bucket, 'trades'])
                }
        return insights
    
    def question_2_best_parameters_for_entropy(self, entropy_low=0.5, entropy_high=0.7):
        """Which parameter set performs best when entropy is in a specific range?"""
        return self.db.get_trades_by_dna({
            'entropy': (entropy_low, entropy_high)
        })
    
    def question_3_optimal_tp_with_vol_persistence(self):
        """Does optimal TP multiplier change with volatility persistence?"""
        df = self.db.read_all_trades()
        if df.empty:
            return pd.DataFrame()
        
        # Extract TP multiplier and vol persistence
        df['tp_mult'] = df['parameters'].apply(lambda x: x.get('take_profit_multiplier', 0))
        df['vol_persistence'] = df['dna'].apply(lambda x: x.get('vol_persistence', 0))
        
        # Create buckets
        df['vol_persistence_bucket'] = pd.cut(df['vol_persistence'], bins=5)
        
        result = df.groupby(['tp_mult', 'vol_persistence_bucket']).agg({
            'pnl': ['count', 'mean'],
            'result': lambda x: (x == 'TP').mean() * 100
        }).round(2)
        
        return result
    
    def question_4_loss_patterns_by_time(self):
        """Are losses concentrated during specific hours?"""
        df = self.db.read_all_trades()
        if df.empty or 'entry_time' not in df.columns:
            return pd.DataFrame()
        
        df['hour'] = pd.to_datetime(df['entry_time']).dt.hour
        
        result = df.groupby('hour').agg({
            'pnl': ['count', 'sum', 'mean'],
            'result': lambda x: (x == 'TP').mean() * 100
        }).round(2)
        
        result.columns = ['trades', 'total_pnl', 'avg_pnl', 'win_rate']
        result = result.sort_values('avg_pnl', ascending=False)
        
        return result
    
    def question_5_loss_patterns_by_dna_state(self):
        """Are losses concentrated after specific market states?"""
        df = self.db.read_all_trades()
        if df.empty:
            return pd.DataFrame()
        
        # Extract DNA features
        df['entropy'] = df['dna'].apply(lambda x: x.get('entropy', 0.5))
        df['hurst'] = df['dna'].apply(lambda x: x.get('hurst', 0.5))
        
        # Create buckets
        df['entropy_bucket'] = pd.cut(df['entropy'], bins=5)
        df['hurst_bucket'] = pd.cut(df['hurst'], bins=5)
        
        result = df.groupby(['entropy_bucket', 'hurst_bucket']).agg({
            'pnl': ['count', 'mean'],
            'result': lambda x: (x == 'TP').mean() * 100
        }).round(2)
        
        return result
    
    def generate_research_report(self):
        """Generate a comprehensive research report."""
        df = self.db.read_all_trades()
        if df.empty:
            return {'error': 'No trades in database'}
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_trades': len(df),
            'total_pnl': float(df['pnl'].sum()),
            'avg_pnl': float(df['pnl'].mean()),
            'win_rate': float((df['result'] == 'TP').mean() * 100),
        }
        
        # Best DNA
        report['best_dna_for_sharpe'] = self.question_1_best_dna_for_sharpe()
        
        # Loss patterns
        report['loss_patterns_by_time'] = self.question_4_loss_patterns_by_time().to_dict('index') if not self.question_4_loss_patterns_by_time().empty else {}
        
        # Strategy performance
        if 'strategy' in df.columns:
            report['strategy_performance'] = df.groupby('strategy').agg({
                'pnl': ['count', 'sum', 'mean'],
                'result': lambda x: (x == 'TP').mean() * 100
            }).round(2).to_dict()
        
        # Top parameters
        report['top_parameters'] = self.db.get_parameter_performance().to_dict('records')
        
        return report
    
    def export_to_csv(self, output_file="research_data/trades_export.csv"):
        """Export all trades to CSV."""
        df = self.db.read_all_trades()
        if df.empty:
            print("No trades to export")
            return
        
        # Flatten nested columns
        for col in ['dna', 'parameters', 'entry_conditions']:
            if col in df.columns:
                for key in df[col].iloc[0].keys() if not df[col].empty and isinstance(df[col].iloc[0], dict) else []:
                    df[f'{col}_{key}'] = df[col].apply(lambda x: x.get(key) if isinstance(x, dict) else None)
        
        # Drop nested columns
        cols_to_drop = ['dna', 'parameters', 'entry_conditions']
        df = df.drop(columns=[c for c in cols_to_drop if c in df.columns])
        
        df.to_csv(output_file, index=False)
        print(f"💾 Exported {len(df)} trades to {output_file}")
        return output_file


# ============================================================================
#  MAIN
# ============================================================================
if __name__ == "__main__":
    print("="*80)
    print("🧬 SYNTHX RESEARCH DATABASE (JSONL)")
    print("="*80)
    
    # Initialize database
    db = ResearchDatabase()
    print(f"✅ Database initialized at: {db.trades_file}")
    
    # ===== Example: Load existing trades from CSV =====
    trade_files = glob.glob("backtest_trades_*.csv")
    
    if trade_files:
        print(f"\n📂 Found {len(trade_files)} trade files:")
        for f in trade_files:
            print(f"  📄 {os.path.basename(f)}")
        
        # Load and store trades
        collector = TradeCollector()
        total_loaded = 0
        
        for trade_file in trade_files:
            try:
                df = pd.read_csv(trade_file)
                
                # Extract strategy and symbol from filename
                filename = os.path.basename(trade_file)
                parts = filename.replace("backtest_trades_", "").replace(".csv", "").split("_")
                strategy = parts[0] if len(parts) > 0 else "Unknown"
                symbol = "_".join(parts[1:]) if len(parts) > 1 else "Unknown"
                
                print(f"\n📊 Loading: {filename}")
                print(f"   Strategy: {strategy}")
                print(f"   Symbol: {symbol}")
                print(f"   Trades: {len(df)}")
                
                # For each trade, create a record with placeholder DNA
                for _, trade in df.iterrows():
                    trade_record = {
                        'symbol': symbol,
                        'entry_time': trade.get('entry_date'),
                        'exit_time': trade.get('exit_date'),
                        'direction': trade.get('type'),
                        'entry_price': trade.get('entry_price', 0),
                        'exit_price': trade.get('exit_price', 0),
                        'volume': trade.get('volume', 0.01),
                        'pnl': trade.get('pnl', 0),
                        'pnl_percent': 0,
                        'result': trade.get('reason', 'UNKNOWN'),
                        'holding_bars': 0,
                        'strategy': strategy,
                        'strategy_version': '1.0',
                        'dna': {
                            'entropy': 0.6,
                            'hurst': 0.3,
                            'volatility': 0.4,
                            'jump_rate': 0.001,
                            'trend_length': 4.0
                        },
                        'parameters': {
                            'lookback': 20,
                            'stop_multiplier': 1.5,
                            'take_profit_multiplier': 2.0
                        },
                        'entry_conditions': {
                            'price': trade.get('entry_price', 0),
                            'time': trade.get('entry_date')
                        },
                        'backtest_id': 'legacy'
                    }
                    collector.add_trade(trade_record)
                    total_loaded += 1
                
                collector.save()
                
            except Exception as e:
                print(f"❌ Error loading {trade_file}: {e}")
        
        print(f"\n✅ Total trades loaded: {total_loaded}")
    
    # ===== Research Analysis =====
    print("\n" + "="*80)
    print("📊 RESEARCH ANALYSIS")
    print("="*80)
    
    analyzer = ResearchAnalyzer()
    analyzer.print_summary()
    
    # Question 1: Best DNA for Sharpe
    print("\n1️⃣ Best DNA for Sharpe Ratio:")
    best_dna = analyzer.question_1_best_dna_for_sharpe()
    for key, value in best_dna.items():
        print(f"   {key}: {value}")
    
    # Question 4: Loss patterns by time
    print("\n4️⃣ Loss Patterns by Time (Top 3):")
    loss_patterns = analyzer.question_4_loss_patterns_by_time()
    if not loss_patterns.empty:
        print(loss_patterns.head(3).to_string())
    
    # Generate and save insights
    print("\n" + "="*80)
    print("📊 GENERATING INSIGHTS")
    print("="*80)
    
    insights = db.save_insights()
    print(f"✅ Insights saved to: {db.insights_file}")
    
    # Export to CSV
    analyzer.export_to_csv()
    
    print("\n✅ Research Database Ready!")
    print(f"   Trades file: {db.trades_file}")
    print(f"   Insights file: {db.insights_file}")