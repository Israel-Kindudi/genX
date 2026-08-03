"""
Base Strategy – abstract class for all strategies.
"""
from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    def __init__(self, **kwargs):
        self.name = self.__class__.__name__
        self.params = kwargs

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame) -> dict:
        """Legacy method for incremental backtesting."""
        pass

    def precompute_indicators(self, df: pd.DataFrame) -> dict:
        """
        Pre-compute all indicators once using vectorized operations.
        Returns a dict of numpy arrays.
        """
        return {}

    def generate_signal_with_indicators(self, df: pd.DataFrame, indicators: dict, idx: int) -> dict:
        """
        Generate signal using pre-computed indicators.
        """
        return {'action': 'HOLD', 'confidence': 0, 'reason': 'Not implemented'}

    def get_params(self) -> dict:
        return self.params

    def get_name(self) -> str:
        return self.name