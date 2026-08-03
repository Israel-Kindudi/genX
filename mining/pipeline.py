# mining/pipeline.py

import pandas as pd
from research.database import ResearchDatabase
from mining.feature_engineering import TradeFeatureEngineer
from mining.regime_detector import RegimeDetector
from mining.predictive_modeling import WinPredictor
from mining.strategy_regime_analysis import StrategyRegimeAnalyzer

class DataMiningPipeline:
    def __init__(self, trades_df=None):
        if trades_df is None:
            db = ResearchDatabase()
            self.trades = db.read_all_trades()
        else:
            self.trades = trades_df

        self.engineered = None
        self.regime_df = None
        self.model_results = None
        self.regime_performance = None

    def run(self):
        print("🧬 Starting Data Mining Pipeline...")

        # 1. Feature Engineering
        print("  🔧 Feature Engineering...")
        engineer = TradeFeatureEngineer(self.trades)
        self.engineered = engineer.add_features()

        # 2. Regime Detection
        print("  🔍 Regime Detection...")
        detector = RegimeDetector(self.engineered, n_regimes=4)
        self.regime_df = detector.fit()
        regime_stats = detector.describe_regimes()
        print("     Regime statistics:")
        print(regime_stats)

        # 3. Predictive Modeling
        print("  🤖 Win Prediction Model...")
        predictor = WinPredictor(self.regime_df)
        self.model_results = predictor.train()
        print(f"     Accuracy: {self.model_results['accuracy']:.2f}")
        print("     Top 5 features:")
        print(self.model_results['feature_importance'].head(5))

        # 4. Strategy by Regime
        print("  📊 Strategy per Regime...")
        analyzer = StrategyRegimeAnalyzer(self.regime_df)
        self.regime_performance = analyzer.performance_by_regime()
        best_per_regime = analyzer.best_strategy_per_regime()
        print("     Best strategy per regime:")
        for regime, strategy in best_per_regime.items():
            print(f"       Regime {regime}: {strategy}")

        print("✅ Data Mining Complete!")

        return {
            'regime_df': self.regime_df,
            'regime_stats': regime_stats,
            'model_results': self.model_results,
            'regime_performance': self.regime_performance,
            'best_per_regime': best_per_regime
        }

    def save_results(self, output_dir="mining_results"):
        import os, json
        os.makedirs(output_dir, exist_ok=True)

        # Save feature importance
        if self.model_results:
            self.model_results['feature_importance'].to_csv(f"{output_dir}/feature_importance.csv", index=False)

        # Save regime stats
        if self.regime_performance is not None:
            self.regime_performance.to_csv(f"{output_dir}/regime_performance.csv")

        # Save best strategy per regime
        if hasattr(self, 'best_per_regime'):
            with open(f"{output_dir}/best_per_regime.json", 'w') as f:
                json.dump(self.best_per_regime, f, indent=2)

        print(f"💾 Results saved to {output_dir}/")