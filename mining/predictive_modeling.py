# mining/predictive_modeling.py

from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pandas as pd
import numpy as np

class WinPredictor:
    def __init__(self, df):
        self.df = df
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.feature_importance = None

    def prepare_data(self):
        # Select features (exclude target and non‑numeric)
        exclude = ['is_winner', 'pnl', 'entry_time', 'exit_time', 'symbol', 'strategy']
        feature_cols = [c for c in self.df.columns if c not in exclude and pd.api.types.is_numeric_dtype(self.df[c])]
        X = self.df[feature_cols].fillna(0)
        y = self.df['is_winner'].astype(int)
        return X, y, feature_cols

    def train(self, test_size=0.3):
        X, y, self.feature_names = self.prepare_data()
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

        self.model.fit(X_train, y_train)
        self.feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

        y_pred = self.model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred)

        return {
            'accuracy': acc,
            'report': report,
            'feature_importance': self.feature_importance,
            'model': self.model
        }

    def plot_importance(self, top_n=15):
        import matplotlib.pyplot as plt
        top = self.feature_importance.head(top_n)
        plt.figure(figsize=(10,6))
        plt.barh(top['feature'], top['importance'])
        plt.xlabel('Importance')
        plt.title('Top Features for Win Prediction')
        plt.gca().invert_yaxis()
        plt.tight_layout()
        return plt