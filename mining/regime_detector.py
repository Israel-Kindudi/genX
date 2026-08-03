# mining/regime_detector.py

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import pandas as pd
import numpy as np

class RegimeDetector:
    def __init__(self, df, n_regimes=4):
        self.df = df
        self.n_regimes = n_regimes
        self.scaler = StandardScaler()
        self.model = None

    def fit(self):
        # Select DNA features for clustering
        dna_features = ['hurst', 'entropy', 'volatility', 'predictability', 'trend_length']
        available = [f for f in dna_features if f in self.df.columns]
        X = self.df[available].fillna(0)
        X_scaled = self.scaler.fit_transform(X)

        self.model = KMeans(n_clusters=self.n_regimes, random_state=42)
        labels = self.model.fit_predict(X_scaled)

        self.df['regime'] = labels
        return self.df

    def describe_regimes(self):
        """Describe each regime."""
        regime_stats = self.df.groupby('regime').agg({
            'pnl': ['mean', 'std', 'count'],
            'win_rate': 'mean',
            'hurst': 'mean',
            'entropy': 'mean',
            'volatility': 'mean',
        }).round(2)
        return regime_stats

    def plot_regimes(self):
        # Plot cluster centroids
        import matplotlib.pyplot as plt
        import seaborn as sns

        centroids = pd.DataFrame(self.model.cluster_centers_, columns=['hurst', 'entropy', 'volatility', 'predictability', 'trend_length'])
        centroids.plot(kind='bar')
        plt.title('Regime Centroids (DNA profile)')
        plt.tight_layout()
        return plt