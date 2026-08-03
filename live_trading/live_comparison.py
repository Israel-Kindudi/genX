#!/usr/bin/env python
"""
Live Comparison Analysis
Analyzes and visualizes comparison results between default and optimized strategies.
"""

import os
import sys
import json
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def load_comparison_results(output_dir="live_results"):
    """Load all comparison results from directory."""
    results = []
    for file in glob.glob(f"{output_dir}/*_comparison.json"):
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                results.append(data)
        except:
            continue
    return results

def generate_report(output_dir="live_results"):
    """Generate a report comparing default vs optimized strategies."""
    results = load_comparison_results(output_dir)
    if not results:
        print("No comparison results found.")
        return
    
    print("\n" + "="*80)
    print("📊 LIVE COMPARISON REPORT: Default vs Optimized")
    print("="*80)
    
    # Build summary table
    rows = []
    for res in results:
        comp = res.get('comparison', {})
        default_rep = res.get('default_report', {})
        opt_rep = res.get('optimized_report', {})
        rows.append({
            'Strategy': res.get('strategy', 'Unknown'),
            'Symbol': res.get('symbol', 'Unknown'),
            'Default Trades': default_rep.get('total_trades', 0),
            'Opt Trades': opt_rep.get('total_trades', 0),
            'Default Sharpe': default_rep.get('sharpe_ratio', 0),
            'Opt Sharpe': opt_rep.get('sharpe_ratio', 0),
            'Sharpe Improv %': comp.get('sharpe_ratio', {}).get('improvement_pct', 0),
            'Default PnL': default_rep.get('total_pnl', 0),
            'Opt PnL': opt_rep.get('total_pnl', 0),
            'PnL Improv %': comp.get('total_pnl', {}).get('improvement_pct', 0),
            'Default Win Rate %': default_rep.get('win_rate', 0),
            'Opt Win Rate %': opt_rep.get('win_rate', 0),
        })
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    df.to_csv(f"{output_dir}/comparison_report.csv", index=False)
    
    # Identify best improvers
    best_sharpe = df.nlargest(3, 'Sharpe Improv %')[['Strategy', 'Symbol', 'Sharpe Improv %', 'Opt Sharpe']]
    best_pnl = df.nlargest(3, 'PnL Improv %')[['Strategy', 'Symbol', 'PnL Improv %', 'Opt PnL']]
    
    print("\n🏆 Top 3 Sharpe Improvers:")
    print(best_sharpe.to_string(index=False))
    
    print("\n🏆 Top 3 PnL Improvers:")
    print(best_pnl.to_string(index=False))
    
    # Plot comparison
    plt.figure(figsize=(14, 8))
    
    # Sharpe comparison
    plt.subplot(2, 2, 1)
    x = np.arange(len(df))
    width = 0.35
    plt.bar(x - width/2, df['Default Sharpe'], width, label='Default', alpha=0.8)
    plt.bar(x + width/2, df['Opt Sharpe'], width, label='Optimized', alpha=0.8)
    plt.xlabel('Strategy / Symbol')
    plt.ylabel('Sharpe Ratio')
    plt.title('Default vs Optimized Sharpe Ratio')
    plt.xticks(x, df['Strategy'] + '\n' + df['Symbol'], rotation=45, ha='right')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # PnL comparison
    plt.subplot(2, 2, 2)
    plt.bar(x - width/2, df['Default PnL'], width, label='Default', alpha=0.8)
    plt.bar(x + width/2, df['Opt PnL'], width, label='Optimized', alpha=0.8)
    plt.xlabel('Strategy / Symbol')
    plt.ylabel('Total PnL ($)')
    plt.title('Default vs Optimized PnL')
    plt.xticks(x, df['Strategy'] + '\n' + df['Symbol'], rotation=45, ha='right')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Win Rate comparison
    plt.subplot(2, 2, 3)
    plt.bar(x - width/2, df['Default Win Rate %'], width, label='Default', alpha=0.8)
    plt.bar(x + width/2, df['Opt Win Rate %'], width, label='Optimized', alpha=0.8)
    plt.xlabel('Strategy / Symbol')
    plt.ylabel('Win Rate (%)')
    plt.title('Default vs Optimized Win Rate')
    plt.xticks(x, df['Strategy'] + '\n' + df['Symbol'], rotation=45, ha='right')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # Trade count comparison
    plt.subplot(2, 2, 4)
    plt.bar(x - width/2, df['Default Trades'], width, label='Default', alpha=0.8)
    plt.bar(x + width/2, df['Opt Trades'], width, label='Optimized', alpha=0.8)
    plt.xlabel('Strategy / Symbol')
    plt.ylabel('Number of Trades')
    plt.title('Default vs Optimized Trade Count')
    plt.xticks(x, df['Strategy'] + '\n' + df['Symbol'], rotation=45, ha='right')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/comparison_charts.png", dpi=150)
    print(f"\n📊 Charts saved to {output_dir}/comparison_charts.png")
    plt.close()
    
    # Generate HTML report
    html = f"""
    <html>
    <head><title>SYNTHX Live Comparison Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #0e1117; color: #e0e0e0; }}
        h1, h2 {{ color: #00ff88; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #333; }}
        th {{ background: #1e1e1e; color: #00ccff; }}
        .positive {{ color: #00ff88; }}
        .negative {{ color: #ff4444; }}
        .neutral {{ color: #ffaa00; }}
    </style>
    </head>
    <body>
    <h1>🧬 SYNTHX Live Comparison Report</h1>
    <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <h2>Summary Table</h2>
    {df.to_html(index=False, classes='table')}
    
    <h2>Top Improvers</h2>
    <h3>Sharpe Ratio Improvers</h3>
    {best_sharpe.to_html(index=False)}
    
    <h3>PnL Improvers</h3>
    {best_pnl.to_html(index=False)}
    
    <img src="comparison_charts.png" alt="Comparison Charts" style="max-width:100%;">
    
    <hr>
    <p><i>SYNTHX Live Comparison - Powered by Statistical DNA</i></p>
    </body>
    </html>
    """
    
    with open(f"{output_dir}/comparison_report.html", 'w') as f:
        f.write(html)
    print(f"💾 HTML report saved to {output_dir}/comparison_report.html")
    
    return df

if __name__ == "__main__":
    generate_report()