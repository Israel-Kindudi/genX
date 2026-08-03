"""
Full DNA Context – Safe access to all 8 chromosomes.
"""
import numpy as np

class FullDNAContext:
    def __init__(self, dna_result):
        self.raw_dna = dna_result
        self.dna = dna_result.get('dna', {})
        self.scores = dna_result.get('scores', {})
        self._extract_all()

    def _extract_all(self):
        # Chromosome I – Distribution
        c1 = self.dna.get('chromosome_i', {})
        self.distribution = {
            'mean_return': c1.get('mean_return', 0),
            'std_return': c1.get('std_return', 1),
            'skewness': c1.get('skewness', 0),
            'excess_kurtosis': c1.get('excess_kurtosis', 0),
            'tail_index': c1.get('tail_index', 5),
            'positive_ratio': c1.get('positive_ratio', 50),
            'var_95': c1.get('var_95', 0),
            'cvar_95': c1.get('cvar_95', 0),
        }

        # Chromosome II – Memory
        c2 = self.dna.get('chromosome_ii', {})
        acf = c2.get('autocorrelation', {})
        self.memory = {
            'hurst': c2.get('hurst_exponent', 0.5),
            'dfa': c2.get('dfa_exponent', 0.5),
            'is_random': c2.get('is_random', True),
            'ljung_box_pvalue': c2.get('ljung_box_pvalue', 0.5),
            'autocorr_1': acf.get('lag_1', 0),
            'autocorr_3': acf.get('lag_3', 0),
            'autocorr_5': acf.get('lag_5', 0),
            'autocorr_10': acf.get('lag_10', 0),
            'autocorr_20': acf.get('lag_20', 0),
        }

        # Chromosome III – Volatility
        c3 = self.dna.get('chromosome_iii', {})
        self.volatility = {
            'realized_vol': c3.get('realized_vol', 0.5),
            'rolling_vol_20': c3.get('rolling_vol_20', 0.5),
            'rolling_vol_100': c3.get('rolling_vol_100', 0.5),
            'ewma_vol': c3.get('ewma_vol', 0.5),
            'atr': c3.get('atr', 0),
            'vol_of_vol': c3.get('vol_of_vol', 0.5),
            'vol_persistence': c3.get('vol_persistence', 0.5),
        }

        # Chromosome IV – Jumps
        c4 = self.dna.get('chromosome_iv', {})
        jstats = c4.get('jump_stats', {})
        self.jumps = {
            'jump_intensity': c4.get('jump_intensity', 0),
            'jump_asymmetry': c4.get('jump_asymmetry', 0),
            'waiting_time_cv': c4.get('waiting_time_cv', 0),
            'has_jumps': bool(jstats),
        }
        for t in ['threshold_3', 'threshold_4', 'threshold_5']:
            if t in jstats:
                s = jstats[t]
                self.jumps[f'{t}_count'] = s.get('total', 0)
                self.jumps[f'{t}_rate'] = s.get('rate', 0)
                pos = s.get('positive', 0)
                neg = s.get('negative', 0)
                total = pos + neg
                self.jumps[f'{t}_asymmetry'] = (pos - neg) / max(1, total)

        # Chromosome V – Temporal
        c5 = self.dna.get('chromosome_v', {})
        sessions = c5.get('session_returns', {})
        self.temporal = {
            'best_hour': c5.get('best_hour', 0),
            'worst_hour': c5.get('worst_hour', 0),
            'best_dow': c5.get('best_dow', 0),
            'worst_dow': c5.get('worst_dow', 0),
            'session_returns': sessions,
            'hourly_returns': c5.get('hourly_returns', {}),
        }
        self.temporal['asian_strength'] = sessions.get('asian', 0)
        self.temporal['european_strength'] = sessions.get('european', 0)
        self.temporal['american_strength'] = sessions.get('american', 0)
        self.temporal['best_session'] = max(sessions, key=sessions.get) if sessions else 'european'

        # Chromosome VI – Information
        c6 = self.dna.get('chromosome_vi', {})
        self.information = {
            'shannon_entropy': c6.get('shannon_entropy', 0.5),
            'max_entropy': c6.get('max_entropy', 1),
            'normalized_entropy': c6.get('normalized_entropy', 0.5),
            'permutation_entropy': c6.get('permutation_entropy', 0.5),
            'sample_entropy': c6.get('sample_entropy', 0.5),
            'lz_complexity': c6.get('lz_complexity', 0.5),
            'predictability': c6.get('predictability', 10),
        }

        # Chromosome VII – Structure
        c7 = self.dna.get('chromosome_vii', {})
        self.structure = {
            'avg_trend_length': c7.get('avg_trend_length', 3),
            'max_trend_length': c7.get('max_trend_length', 10),
            'ou_theta': c7.get('ou_theta', 0),
            'ou_half_life': c7.get('ou_half_life', 100),
            'swing_mean': c7.get('swing_mean', 0),
            'swing_std': c7.get('swing_std', 0),
            'mean_reversion_speed': c7.get('mean_reversion_speed', 0),
        }

        # Chromosome VIII – Synthetic
        c8 = self.dna.get('chromosome_viii', {})
        self.synthetic = {
            'is_synthetic': c8.get('is_synthetic', False),
            'confidence': c8.get('confidence', 0),
            'confidence_level': c8.get('confidence_level', 'Low'),
            'benford_score': c8.get('benford_score', 0),
            'signatures': c8.get('signatures', []),
            'jump_asymmetry': c8.get('jump_asymmetry', 0),
        }

        # Strategy Affinity
        self.strategy_affinity = self.dna.get('strategy_affinity', {})

        # Overall Score
        self.overall_score = self.dna.get('overall_score', 50)

        # Chromosome Scores
        self.chromosome_scores = {
            'distribution': self.scores.get('Distribution', 50),
            'memory': self.scores.get('Memory', 50),
            'volatility': self.scores.get('Volatility', 50),
            'jumps': self.scores.get('Jumps', 50),
            'temporal': self.scores.get('Temporal', 50),
            'information': self.scores.get('Information', 50),
            'structure': self.scores.get('Structure', 50),
            'synthetic': self.scores.get('Synthetic', 50),
        }

    def get_all_metrics(self):
        return {
            **self.distribution,
            **self.memory,
            **self.volatility,
            **self.jumps,
            **self.temporal,
            **self.information,
            **self.structure,
            **self.synthetic,
            'strategy_affinity': self.strategy_affinity,
            'overall_score': self.overall_score,
            'chromosome_scores': self.chromosome_scores,
        }

    def get_summary(self):
        return {
            'hurst': self.memory['hurst'],
            'entropy': self.information['normalized_entropy'],
            'volatility': self.volatility['realized_vol'],
            'predictability': self.information['predictability'],
            'is_synthetic': self.synthetic['is_synthetic'],
            'jump_intensity': self.jumps['jump_intensity'],
            'trend_length': self.structure['avg_trend_length'],
            'mean_reversion_speed': self.structure['mean_reversion_speed'],
            'best_strategy': max(self.strategy_affinity, key=self.strategy_affinity.get) if self.strategy_affinity else 'Unknown',
            'overall_score': self.overall_score,
        }