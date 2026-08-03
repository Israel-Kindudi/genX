# mining/feature_engineering.py

import pandas as pd
import numpy as np

class TradeFeatureEngineer:
    def __init__(self, trades_df):
        self.trades = trades_df.copy()
        self.engineered = None

    def add_features(self):
        """Add engineered features to trade data."""
        df = self.trades

        # --- From trade DNA ---
        if 'dna' in df.columns:
            dna = pd.json_normalize(df['dna'])
            df = pd.concat([df, dna], axis=1)

        # --- Time features ---
        df['hour'] = pd.to_datetime(df['entry_time']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['entry_time']).dt.dayofweek
        df['month'] = pd.to_datetime(df['entry_time']).dt.month

        # --- Performance features ---
        df['pnl_abs'] = df['pnl'].abs()
        df['pnl_pct'] = df['pnl'] / df['entry_price'] * 100
        df['is_winner'] = df['pnl'] > 0

        # --- Holding period ---
        df['holding_bars'] = (pd.to_datetime(df['exit_time']) - pd.to_datetime(df['entry_time'])).dt.total_seconds() / 60

        # --- Strategy parameters (flatten) ---
        if 'parameters' in df.columns:
            params = pd.json_normalize(df['parameters'])
            df = pd.concat([df, params], axis=1)

        # --- Rolling averages (per symbol) ---
        df['avg_pnl_10'] = df.groupby('symbol')['pnl'].transform(lambda x: x.rolling(10, min_periods=1).mean())
        df['win_rate_20'] = df.groupby('symbol')['is_winner'].transform(lambda x: x.rolling(20, min_periods=1).mean())

        self.engineered = df
        return df