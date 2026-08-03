# mining/strategy_regime_analysis.py

class StrategyRegimeAnalyzer:
    def __init__(self, df):
        self.df = df

    def performance_by_regime(self):
        # Ensure 'regime' column exists
        if 'regime' not in self.df.columns:
            raise ValueError("Run RegimeDetector first")

        result = self.df.groupby(['regime', 'strategy']).agg({
            'pnl': ['count', 'sum', 'mean'],
            'win_rate': 'mean',
            'return_pct': 'mean'
        }).round(2)
        return result

    def best_strategy_per_regime(self):
        perf = self.performance_by_regime()
        # Find strategy with highest average PnL per regime
        best = perf.groupby('regime')['pnl']['mean'].idxmax()
        return best