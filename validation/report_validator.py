#!/usr/bin/env python
"""
Validation Report Generator
Generates comprehensive validation reports with visualizations.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def load_validation_results(output_dir="validation_results"):
    """Load validation results from JSON."""
    results_file = f"{output_dir}/validation_results.json"
    if not os.path.exists(results_file):
        return []
    with open(results_file, 'r') as f:
        return json.load(f)

def load_live_results(output_dir="validation_results"):
    """Load live validation results from JSON."""
    results_file = f"{output_dir}/live_validation_results.json"
    if not os.path.exists(results_file):
        return []
    with open(results_file, 'r') as f:
        return json.load(f)

def generate_report(output_dir="validation_results"):
    """Generate a comprehensive validation report."""
    os.makedirs(output_dir, exist_ok=True)
    
    validation_results = load_validation_results(output_dir)
    live_results = load_live_results(output_dir)
    
    print("\n" + "="*80)
    print("📊 VALIDATION REPORT")
    print("="*80)
    
    # 1. Walk-Forward Validation Summary
    if validation_results:
        print("\n1. WALK-FORWARD VALIDATION")
        print("-"*40)
        summary = []
        for res in validation_results:
            v = res.get('validation_report', {})
            comparison = res.get('comparison', {})
            summary.append({
                'Strategy': res.get('strategy', 'Unknown'),
                'Symbol': res.get('symbol', 'Unknown'),
                'Trades': v.get('total_trades', 0),
                'Win Rate %': v.get('win_rate', 0),
                'Sharpe': v.get('sharpe_ratio', 0),
                'PnL': v.get('total_pnl', 0),
                'Max DD %': v.get('max_drawdown', 0),
                'Sharpe Change %': comparison.get('sharpe_ratio', {}).get('change_pct', 0),
                'PnL Change %': comparison.get('total_pnl', {}).get('change_pct', 0),
            })
        df_summary = pd.DataFrame(summary)
        print(df_summary.to_string(index=False))
        df_summary.to_csv(f"{output_dir}/validation_summary_clean.csv", index=False)
    
    # 2. Live Validation Summary
    if live_results:
        print("\n2. LIVE VALIDATION")
        print("-"*40)
        live_summary = []
        for res in live_results:
            r = res.get('report', {})
            live_summary.append({
                'Strategy': res.get('strategy', 'Unknown'),
                'Symbol': res.get('symbol', 'Unknown'),
                'Trades': r.get('total_trades', 0),
                'Win Rate %': r.get('win_rate', 0),
                'Sharpe': r.get('sharpe_ratio', 0),
                'PnL': r.get('total_pnl', 0),
                'Max DD %': r.get('max_drawdown', 0),
            })
        df_live = pd.DataFrame(live_summary)
        print(df_live.to_string(index=False))
        df_live.to_csv(f"{output_dir}/live_validation_summary.csv", index=False)
    
    # 3. Comparison: Backtest vs Validation vs Live
    print("\n3. PERFORMANCE COMPARISON")
    print("-"*40)
    
    # Find strategies that have all three data points
    all_strategies = set()
    if validation_results:
        all_strategies.update([(r['strategy'], r['symbol']) for r in validation_results])
    if live_results:
        all_strategies.update([(r['strategy'], r['symbol']) for r in live_results])
    
    comparison_rows = []
    for strategy, symbol in all_strategies:
        row = {'Strategy': strategy, 'Symbol': symbol}
        
        # Backtest from validation results
        for res in validation_results:
            if res['strategy'] == strategy and res['symbol'] == symbol:
                bt = res.get('backtest_report', {})
                if bt:
                    row['Backtest Sharpe'] = bt.get('sharpe_ratio', np.nan)
                    row['Backtest PnL'] = bt.get('total_pnl', np.nan)
                val = res.get('validation_report', {})
                row['Validation Sharpe'] = val.get('sharpe_ratio', np.nan)
                row['Validation PnL'] = val.get('total_pnl', np.nan)
                break
        
        # Live data
        for res in live_results:
            if res['strategy'] == strategy and res['symbol'] == symbol:
                r = res.get('report', {})
                row['Live Sharpe'] = r.get('sharpe_ratio', np.nan)
                row['Live PnL'] = r.get('total_pnl', np.nan)
                break
        
        comparison_rows.append(row)
    
    if comparison_rows:
        df_comp = pd.DataFrame(comparison_rows)
        print(df_comp.to_string(index=False))
        df_comp.to_csv(f"{output_dir}/performance_comparison.csv", index=False)
    
    # 4. Decision: Ready for Live Trading?
    print("\n4. DEPLOYMENT READINESS")
    print("-"*40)
    
    ready_strategies = []
    for row in comparison_rows:
        strategy = row['Strategy']
        symbol = row['Symbol']
        bt_sharpe = row.get('Backtest Sharpe', np.nan)
        val_sharpe = row.get('Validation Sharpe', np.nan)
        live_sharpe = row.get('Live Sharpe', np.nan)
        
        # Criteria: Sharpe > 0.5 in all three, no significant degradation
        if (bt_sharpe > 0.5 and val_sharpe > 0.5 and live_sharpe > 0.5 and
            val_sharpe > bt_sharpe * 0.7 and live_sharpe > bt_sharpe * 0.7):
            ready_strategies.append({
                'Strategy': strategy,
                'Symbol': symbol,
                'Backtest Sharpe': bt_sharpe,
                'Validation Sharpe': val_sharpe,
                'Live Sharpe': live_sharpe,
                'Status': '✅ Ready'
            })
        else:
            ready_strategies.append({
                'Strategy': strategy,
                'Symbol': symbol,
                'Backtest Sharpe': bt_sharpe,
                'Validation Sharpe': val_sharpe,
                'Live Sharpe': live_sharpe,
                'Status': '❌ Review Needed'
            })
    
    if ready_strategies:
        df_ready = pd.DataFrame(ready_strategies)
        print(df_ready.to_string(index=False))
        df_ready.to_csv(f"{output_dir}/deployment_readiness.csv", index=False)
    
    # 5. Visualizations
    print("\n📊 Generating visualizations...")
    
    if validation_results:
        # Plot Validation vs Backtest Sharpe
        plt.figure(figsize=(12, 6))
        data = []
        for res in validation_results:
            if res.get('backtest_report') and res.get('validation_report'):
                data.append({
                    'Strategy': res['strategy'],
                    'Symbol': res['symbol'],
                    'Backtest': res['backtest_report'].get('sharpe_ratio', 0),
                    'Validation': res['validation_report'].get('sharpe_ratio', 0)
                })
        if data:
            df_plot = pd.DataFrame(data)
            x = np.arange(len(df_plot))
            width = 0.35
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(x - width/2, df_plot['Backtest'], width, label='Backtest', alpha=0.8)
            ax.bar(x + width/2, df_plot['Validation'], width, label='Validation', alpha=0.8)
            ax.set_xlabel('Strategy / Symbol')
            ax.set_ylabel('Sharpe Ratio')
            ax.set_title('Backtest vs Validation Sharpe Ratio')
            ax.set_xticks(x)
            ax.set_xticklabels(df_plot['Strategy'] + '\n' + df_plot['Symbol'], rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/backtest_vs_validation_sharpe.png", dpi=150)
            plt.close()
            print(f"💾 Saved: {output_dir}/backtest_vs_validation_sharpe.png")
    
    if live_results and validation_results:
        # Plot Validation vs Live Sharpe
        plt.figure(figsize=(12, 6))
        data = []
        for res_val in validation_results:
            for res_live in live_results:
                if res_val['strategy'] == res_live['strategy'] and res_val['symbol'] == res_live['symbol']:
                    data.append({
                        'Strategy': res_val['strategy'],
                        'Symbol': res_val['symbol'],
                        'Validation': res_val.get('validation_report', {}).get('sharpe_ratio', 0),
                        'Live': res_live.get('report', {}).get('sharpe_ratio', 0)
                    })
                    break
        if data:
            df_plot = pd.DataFrame(data)
            x = np.arange(len(df_plot))
            width = 0.35
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.bar(x - width/2, df_plot['Validation'], width, label='Validation', alpha=0.8)
            ax.bar(x + width/2, df_plot['Live'], width, label='Live', alpha=0.8)
            ax.set_xlabel('Strategy / Symbol')
            ax.set_ylabel('Sharpe Ratio')
            ax.set_title('Validation vs Live Sharpe Ratio')
            ax.set_xticks(x)
            ax.set_xticklabels(df_plot['Strategy'] + '\n' + df_plot['Symbol'], rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/validation_vs_live_sharpe.png", dpi=150)
            plt.close()
            print(f"💾 Saved: {output_dir}/validation_vs_live_sharpe.png")
    
    # 6. Summary Report
    print("\n📋 SUMMARY REPORT")
    print("-"*40)
    total_strategies = len(ready_strategies)
    ready_count = sum(1 for s in ready_strategies if s['Status'] == '✅ Ready')
    print(f"Total strategies evaluated: {total_strategies}")
    print(f"Ready for deployment: {ready_count}")
    print(f"Needs review: {total_strategies - ready_count}")
    
    # Write HTML report
    html = f"""
    <html>
    <head><title>SYNTHX Validation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #0e1117; color: #e0e0e0; }}
        h1, h2 {{ color: #00ff88; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #1e1e1e; color: #00ccff; }}
        tr:hover {{ background: #1a1a2e; }}
        .ready {{ color: #00ff88; }}
        .review {{ color: #ffaa00; }}
        .fail {{ color: #ff4444; }}
    </style>
    </head>
    <body>
    <h1>🧬 SYNTHX Validation Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Deployment Readiness</h2>
    <table>
        <tr><th>Strategy</th><th>Symbol</th><th>Backtest Sharpe</th><th>Validation Sharpe</th><th>Live Sharpe</th><th>Status</th></tr>
    """
    for row in ready_strategies:
        status_class = 'ready' if 'Ready' in row['Status'] else 'review'
        html += f"""
        <tr>
            <td>{row['Strategy']}</td>
            <td>{row['Symbol']}</td>
            <td>{row['Backtest Sharpe']:.3f}</td>
            <td>{row['Validation Sharpe']:.3f}</td>
            <td>{row['Live Sharpe']:.3f}</td>
            <td class="{status_class}">{row['Status']}</td>
        </tr>
        """
    html += """
    </table>
    <p><span class="ready">✅ Ready</span> = Can deploy to live trading.<br>
    <span class="review">❌ Review Needed</span> = Needs further analysis.</p>
    <hr>
    <p><i>SYNTHX Validation Framework - Powered by Statistical DNA</i></p>
    </body>
    </html>
    """
    
    with open(f"{output_dir}/validation_report.html", 'w') as f:
        f.write(html)
    print(f"💾 HTML report saved: {output_dir}/validation_report.html")

if __name__ == "__main__":
    generate_report()
    print("\n✅ Validation report complete!")