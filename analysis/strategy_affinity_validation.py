#!/usr/bin/env python
"""
Strategy Affinity Validation
Compares DNA-based strategy affinity scores with actual backtest performance.
"""

import os
import sys
import json
import glob
import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import DNA_RESULTS_DIR

class StrategyAffinityValidator:
    def __init__(self, backtest_summary_csv=None):
        if backtest_summary_csv is None:
            csv_files = glob.glob("backtest_full_summary.csv")
            if not csv_files:
                csv_files = glob.glob("backtest_comparison.csv")
            if not csv_files:
                raise FileNotFoundError("No backtest summary CSV found.")
            backtest_summary_csv = csv_files[0]
        self.summary_csv = backtest_summary_csv
        self.summary_df = None
        self.dna_profiles = None
        self.dna_affinity = {}
        self.merged = pd.DataFrame()
        self.results = {}

    def _standardize_columns(self, df):
        mapping = {}
        for col in df.columns:
            col_clean = col.strip()
            if 'symbol' in col_clean.lower():
                mapping[col] = 'Symbol'
            elif 'timeframe' in col_clean.lower():
                mapping[col] = 'Timeframe'
            elif 'strategy' in col_clean.lower():
                mapping[col] = 'Strategy'
            elif 'trade' in col_clean.lower():
                mapping[col] = 'Trades'
            elif 'win rate' in col_clean.lower():
                mapping[col] = 'Win Rate %'
            elif 'profit factor' in col_clean.lower():
                mapping[col] = 'Profit Factor'
            elif 'pnl' in col_clean.lower():
                mapping[col] = 'Total PnL'
            elif 'return' in col_clean.lower():
                mapping[col] = 'Return %'
            elif 'sharpe' in col_clean.lower():
                mapping[col] = 'Sharpe'
            elif 'max dd' in col_clean.lower() or 'drawdown' in col_clean.lower():
                mapping[col] = 'Max DD %'
        return df.rename(columns=mapping)

    def load_data(self):
        print(f"📂 Loading backtest summary from: {self.summary_csv}")
        self.summary_df = pd.read_csv(self.summary_csv)
        self.summary_df.columns = self.summary_df.columns.str.strip()
        self.summary_df = self._standardize_columns(self.summary_df)

        # Standardize symbol naming
        if 'Symbol' in self.summary_df.columns:
            self.summary_df['Symbol'] = self.summary_df['Symbol'].str.replace('_PERIOD_data', '')

        print(f"📊 Backtest summary columns: {list(self.summary_df.columns)}")
        print(f"📊 First 5 rows:\n{self.summary_df.head()}")
        print(f"   Total rows: {len(self.summary_df)}")

        # Load DNA profiles
        print(f"🧬 Loading DNA profiles from: {DNA_RESULTS_DIR}")
        dna_files = glob.glob(f"{DNA_RESULTS_DIR}/*_DNA.json")
        print(f"   Found {len(dna_files)} DNA files.")

        if len(dna_files) == 0:
            print("   ⚠️ No DNA files found. Check DNA_RESULTS_DIR in config.py")
            return

        self.dna_profiles = {}
        for file in dna_files:
            try:
                with open(file, 'r') as f:
                    data = json.load(f)
                # Extract symbol and timeframe from filename
                basename = os.path.basename(file)
                name = basename.replace('_DNA.json', '')
                # Pattern: symbol_PERIOD_M1_data_M1
                parts = name.split('_PERIOD_')
                if len(parts) == 2:
                    symbol = parts[0]
                    rest = parts[1]
                    # rest: M1_data_M1 -> extract M1
                    tf_part = rest.split('_data_')[0] if '_data_' in rest else 'M1'
                    timeframe = tf_part
                else:
                    # Fallback: use data fields
                    symbol = data.get('symbol', name)
                    timeframe = data.get('timeframe', 'M1')
                key = f"{symbol}_{timeframe}"
                self.dna_profiles[key] = data
                print(f"   Loaded DNA for key: {key}")
            except Exception as e:
                print(f"⚠️ Error loading {file}: {e}")

        print(f"✅ Loaded {len(self.dna_profiles)} DNA profiles.")
        if self.dna_profiles:
            print(f"   Sample keys: {list(self.dna_profiles.keys())[:10]}")

        # Extract affinity scores
        self.dna_affinity = {}
        for key, data in self.dna_profiles.items():
            dna = data.get('dna', {})
            affinity = dna.get('strategy_affinity', {})
            chrom_ii = dna.get('chromosome_ii', {})
            chrom_vi = dna.get('chromosome_vi', {})
            chrom_iii = dna.get('chromosome_iii', {})
            chrom_iv = dna.get('chromosome_iv', {})
            chrom_vii = dna.get('chromosome_vii', {})
            chrom_viii = dna.get('chromosome_viii', {})
            scores = data.get('scores', {})
            self.dna_affinity[key] = {
                'affinity': affinity,
                'hurst': chrom_ii.get('hurst_exponent', np.nan),
                'entropy': chrom_vi.get('normalized_entropy', np.nan),
                'volatility': chrom_iii.get('realized_vol', np.nan),
                'predictability': chrom_vi.get('predictability', np.nan),
                'trend_length': chrom_vii.get('avg_trend_length', np.nan),
                'jump_intensity': chrom_iv.get('jump_intensity', np.nan),
                'is_synthetic': chrom_viii.get('is_synthetic', False),
                'overall_score': dna.get('overall_score', np.nan),
                'score_distribution': scores.get('Distribution', np.nan),
                'score_memory': scores.get('Memory', np.nan),
                'score_volatility': scores.get('Volatility', np.nan),
                'score_jumps': scores.get('Jumps', np.nan),
                'score_temporal': scores.get('Temporal', np.nan),
                'score_information': scores.get('Information', np.nan),
                'score_structure': scores.get('Structure', np.nan),
                'score_synthetic': scores.get('Synthetic', np.nan),
            }

    def merge_data(self):
        print("🔗 Merging data...")
        if self.summary_df is None or self.summary_df.empty:
            print("   No backtest data to merge.")
            return

        if not self.dna_affinity:
            print("   No DNA affinity data to merge.")
            return

        merged_rows = []
        print(f"   Backtest rows: {len(self.summary_df)}")
        print(f"   DNA affinity entries: {len(self.dna_affinity)}")
        print(f"   Backtest first symbol/timeframe: {self.summary_df.iloc[0]['Symbol']}_{self.summary_df.iloc[0]['Timeframe']}")
        print(f"   DNA keys sample: {list(self.dna_affinity.keys())[:5]}")

        for idx, row in self.summary_df.iterrows():
            symbol = row.get('Symbol', 'Unknown')
            timeframe = row.get('Timeframe', 'M1')
            strategy = row.get('Strategy', 'Unknown')
            key = f"{symbol}_{timeframe}"

            dna = self.dna_affinity.get(key, {})
            if not dna:
                if idx < 5:
                    print(f"   ⚠️ No DNA for key: {key}")
                continue

            affinity = dna.get('affinity', {})
            aff_score = None
            # Exact match
            for dna_strat, score in affinity.items():
                if dna_strat == strategy:
                    aff_score = score
                    break
            if aff_score is None:
                # Partial match
                for dna_strat, score in affinity.items():
                    if dna_strat in strategy or strategy in dna_strat:
                        aff_score = score
                        break
            if aff_score is None:
                # Match by first word
                strategy_base = strategy.split('(')[0].strip()
                for dna_strat, score in affinity.items():
                    if dna_strat.startswith(strategy_base) or strategy_base.startswith(dna_strat):
                        aff_score = score
                        break
            if aff_score is None:
                continue

            merged_rows.append({
                'Symbol': symbol,
                'Timeframe': timeframe,
                'Strategy': strategy,
                'Trades': row.get('Trades', 0),
                'Win Rate %': row.get('Win Rate %', 0),
                'Profit Factor': row.get('Profit Factor', 0),
                'Total PnL': row.get('Total PnL', 0),
                'Return %': row.get('Return %', 0),
                'Sharpe': row.get('Sharpe', 0),
                'Max DD %': row.get('Max DD %', 0),
                'Affinity': aff_score,
                'hurst': dna.get('hurst', np.nan),
                'entropy': dna.get('entropy', np.nan),
                'volatility': dna.get('volatility', np.nan),
                'predictability': dna.get('predictability', np.nan),
                'trend_length': dna.get('trend_length', np.nan),
                'jump_intensity': dna.get('jump_intensity', np.nan),
                'is_synthetic': dna.get('is_synthetic', False),
                'overall_dna_score': dna.get('overall_score', np.nan),
                'score_distribution': dna.get('score_distribution', np.nan),
                'score_memory': dna.get('score_memory', np.nan),
                'score_volatility': dna.get('score_volatility', np.nan),
                'score_jumps': dna.get('score_jumps', np.nan),
                'score_temporal': dna.get('score_temporal', np.nan),
                'score_information': dna.get('score_information', np.nan),
                'score_structure': dna.get('score_structure', np.nan),
                'score_synthetic': dna.get('score_synthetic', np.nan),
            })

        self.merged = pd.DataFrame(merged_rows)
        print(f"✅ Merged {len(self.merged)} rows.")
        if not self.merged.empty:
            print(f"   Columns: {list(self.merged.columns)}")
            print(f"   First 5 rows:\n{self.merged.head()}")

    def compute_correlations(self):
        print("📊 Computing correlations...")
        if self.merged.empty:
            print("⚠️ No merged data to compute correlations.")
            return

        perf_metrics = ['Win Rate %', 'Profit Factor', 'Total PnL', 'Return %', 'Sharpe']
        df_filtered = self.merged[self.merged['Trades'] >= 5].copy()

        if df_filtered.empty:
            print("⚠️ No rows with >=5 trades.")
            return

        self.correlations = {}
        for metric in perf_metrics:
            if metric not in df_filtered.columns:
                continue
            if 'Affinity' not in df_filtered.columns:
                print("⚠️ 'Affinity' column missing.")
                return
            corr_pearson, p_pearson = pearsonr(df_filtered['Affinity'], df_filtered[metric])
            corr_spearman, p_spearman = spearmanr(df_filtered['Affinity'], df_filtered[metric])
            self.correlations[metric] = {
                'pearson': corr_pearson,
                'pearson_p': p_pearson,
                'spearman': corr_spearman,
                'spearman_p': p_spearman,
            }

        print("✅ Correlations computed.")

        # DNA metrics vs performance
        dna_metrics = ['hurst', 'entropy', 'volatility', 'predictability', 'trend_length',
                       'jump_intensity', 'overall_dna_score']
        dna_correlations = {}
        for metric in perf_metrics:
            if metric not in df_filtered.columns:
                continue
            for dna_metric in dna_metrics:
                if dna_metric in df_filtered.columns:
                    corr, p = pearsonr(df_filtered[dna_metric].fillna(0), df_filtered[metric])
                    dna_correlations[(dna_metric, metric)] = corr
        self.dna_correlations = dna_correlations

    def plot_correlations(self, output_dir="analysis_results"):
        os.makedirs(output_dir, exist_ok=True)
        if not hasattr(self, 'correlations') or not self.correlations:
            print("⚠️ No correlations to plot.")
            return

        # Bar chart
        metrics = list(self.correlations.keys())
        corr_values = [self.correlations[m]['pearson'] for m in metrics]
        if not corr_values:
            return
        df_corr = pd.DataFrame({'Metric': metrics, 'Correlation': corr_values})
        plt.figure(figsize=(10, 6))
        bars = plt.bar(df_corr['Metric'], df_corr['Correlation'], color='steelblue')
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        plt.ylabel('Pearson Correlation with Affinity')
        plt.title('Strategy Affinity vs. Performance Metrics')
        plt.xticks(rotation=45)
        for bar, val in zip(bars, df_corr['Correlation']):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
                     f'{val:.3f}', ha='center', va='bottom', fontsize=9)
        plt.tight_layout()
        plt.savefig(f"{output_dir}/affinity_performance_correlation.png", dpi=150)
        plt.close()
        print(f"💾 Saved: {output_dir}/affinity_performance_correlation.png")

        # Scatter Affinity vs Sharpe
        df_plot = self.merged[self.merged['Trades'] >= 5]
        if not df_plot.empty and 'Sharpe' in df_plot.columns and 'Affinity' in df_plot.columns:
            plt.figure(figsize=(10, 8))
            scatter = plt.scatter(df_plot['Affinity'], df_plot['Sharpe'],
                                 c=df_plot['Trades'], cmap='viridis', alpha=0.6, s=50)
            plt.colorbar(scatter, label='Number of Trades')
            plt.xlabel('DNA Affinity Score')
            plt.ylabel('Sharpe Ratio')
            plt.title('Affinity vs. Sharpe Ratio')
            z = np.polyfit(df_plot['Affinity'].dropna(), df_plot['Sharpe'].dropna(), 1)
            p = np.poly1d(z)
            x_line = np.linspace(df_plot['Affinity'].min(), df_plot['Affinity'].max(), 100)
            r = self.correlations.get('Sharpe', {}).get('pearson', 0)
            plt.plot(x_line, p(x_line), "r--", alpha=0.7, label=f'Trend (r={r:.3f})')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/affinity_vs_sharpe.png", dpi=150)
            plt.close()
            print(f"💾 Saved: {output_dir}/affinity_vs_sharpe.png")

        # DNA metrics heatmap
        if hasattr(self, 'dna_correlations') and self.dna_correlations:
            dna_metrics = ['hurst', 'entropy', 'volatility', 'predictability',
                           'trend_length', 'jump_intensity', 'overall_dna_score']
            perf_metrics = ['Sharpe', 'Win Rate %', 'Profit Factor', 'Return %']
            matrix = np.zeros((len(dna_metrics), len(perf_metrics)))
            for i, dm in enumerate(dna_metrics):
                for j, pm in enumerate(perf_metrics):
                    matrix[i, j] = self.dna_correlations.get((dm, pm), np.nan)
            fig, ax = plt.subplots(figsize=(8, 6))
            im = ax.imshow(matrix, cmap='RdBu_r', vmin=-1, vmax=1)
            ax.set_xticks(np.arange(len(perf_metrics)))
            ax.set_yticks(np.arange(len(dna_metrics)))
            ax.set_xticklabels(perf_metrics, rotation=45, ha='right')
            ax.set_yticklabels(dna_metrics)
            for i in range(len(dna_metrics)):
                for j in range(len(perf_metrics)):
                    val = matrix[i, j]
                    if not np.isnan(val):
                        ax.text(j, i, f'{val:.2f}', ha='center', va='center',
                               color='white' if abs(val) > 0.5 else 'black')
            plt.colorbar(im, ax=ax, label='Correlation')
            plt.title('DNA Metrics vs. Performance')
            plt.tight_layout()
            plt.savefig(f"{output_dir}/dna_metrics_vs_performance_heatmap.png", dpi=150)
            plt.close()
            print(f"💾 Saved: {output_dir}/dna_metrics_vs_performance_heatmap.png")

    def generate_report(self, output_dir="analysis_results"):
        os.makedirs(output_dir, exist_ok=True)
        with open(f"{output_dir}/affinity_validation_report.txt", 'w') as f:
            f.write("="*80 + "\n")
            f.write("STRATEGY AFFINITY VS PERFORMANCE VALIDATION REPORT\n")
            f.write("="*80 + "\n\n")

            # Data overview
            total_backtest = len(self.summary_df) if self.summary_df is not None else 0
            merged_rows = len(self.merged)
            f.write("1. DATA OVERVIEW\n")
            f.write("-"*40 + "\n")
            f.write(f"Total backtest rows: {total_backtest}\n")
            f.write(f"Merged rows (with affinity): {merged_rows}\n")
            if not self.merged.empty:
                f.write(f"Rows with >=5 trades: {len(self.merged[self.merged['Trades'] >= 5])}\n")
            f.write("\n")

            # Correlations
            f.write("2. CORRELATIONS BETWEEN AFFINITY AND PERFORMANCE\n")
            f.write("-"*40 + "\n")
            if hasattr(self, 'correlations') and self.correlations:
                for metric, corr_dict in self.correlations.items():
                    f.write(f"{metric}:\n")
                    f.write(f"  Pearson r: {corr_dict['pearson']:.4f} (p={corr_dict['pearson_p']:.4f})\n")
                    f.write(f"  Spearman r: {corr_dict['spearman']:.4f} (p={corr_dict['spearman_p']:.4f})\n")
            else:
                f.write("No correlations computed.\n")
            f.write("\n")

            # Interpretation
            f.write("3. INTERPRETATION\n")
            f.write("-"*40 + "\n")
            if hasattr(self, 'correlations') and self.correlations:
                for metric, corr_dict in self.correlations.items():
                    r = corr_dict['pearson']
                    if r > 0.5:
                        strength = "Strong positive"
                    elif r > 0.3:
                        strength = "Moderate positive"
                    elif r > 0.1:
                        strength = "Weak positive"
                    elif r > -0.1:
                        strength = "Negligible"
                    elif r > -0.3:
                        strength = "Weak negative"
                    elif r > -0.5:
                        strength = "Moderate negative"
                    else:
                        strength = "Strong negative"
                    f.write(f"  {metric}: {strength} correlation (r={r:.3f})\n")
            else:
                f.write("No correlations to interpret.\n")
            f.write("\n")

            # Top DNA metrics
            f.write("4. TOP DNA METRICS CORRELATED WITH SHARPE\n")
            f.write("-"*40 + "\n")
            if hasattr(self, 'dna_correlations') and self.dna_correlations:
                sharpe_corrs = {k: v for k, v in self.dna_correlations.items() if k[1] == 'Sharpe'}
                sorted_corrs = sorted(sharpe_corrs.items(), key=lambda x: abs(x[1]), reverse=True)
                for (dna_metric, perf_metric), corr in sorted_corrs:
                    f.write(f"  {dna_metric:20} vs {perf_metric:12}: {corr:.4f}\n")
            else:
                f.write("No DNA correlations available.\n")
            f.write("\n")

            # Conclusion
            f.write("5. CONCLUSION\n")
            f.write("-"*40 + "\n")
            if hasattr(self, 'correlations') and self.correlations:
                avg_corr = np.mean([self.correlations[m]['pearson'] for m in self.correlations])
                f.write(f"Average correlation: {avg_corr:.3f}\n")
                if avg_corr > 0.2:
                    f.write("DNA affinity shows a positive relationship with strategy performance.\n")
                    f.write("This suggests the DNA analysis is useful for guiding strategy selection.\n")
                else:
                    f.write("The correlation is weak. DNA affinity alone may not be sufficient to predict performance.\n")
                    f.write("Consider incorporating other factors (e.g., market regime, parameter tuning).\n")
            else:
                f.write("Insufficient data to draw conclusions.\n")

        print(f"💾 Report saved: {output_dir}/affinity_validation_report.txt")

    def run_all(self, output_dir="analysis_results"):
        self.load_data()
        self.merge_data()
        self.compute_correlations()
        self.plot_correlations(output_dir)
        self.generate_report(output_dir)

        print("\n" + "="*80)
        print("📊 SUMMARY OF AFFINITY VALIDATION")
        print("="*80)
        print(f"Total merged rows: {len(self.merged)}")
        if hasattr(self, 'correlations') and self.correlations:
            for metric, corr_dict in self.correlations.items():
                print(f"{metric:15} : Pearson r = {corr_dict['pearson']:.4f}  (p={corr_dict['pearson_p']:.4f})")
        else:
            print("No correlations computed.")

if __name__ == "__main__":
    validator = StrategyAffinityValidator()
    validator.run_all()
    print("\n✅ Analysis complete. Check the 'analysis_results' folder.")