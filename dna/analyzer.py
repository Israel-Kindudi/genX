"""
DNA Analyzer – Full 8‑Chromosome Profile with progress bars and time tracking.
"""

import sys
import os
import json
import glob
import time
import pandas as pd
import numpy as np
from datetime import datetime
from scipy import stats
from scipy.stats import entropy, kurtosis, skew, jarque_bera, chi2
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from config import DATA_DIR, DNA_RESULTS_DIR

# ============================================================================
#  DNA ANALYZER CLASS
# ============================================================================

class DNAAnalyzer:
    def __init__(self, df, symbol, timeframe, verbose=True):
        self.df = df.copy()
        self.symbol = symbol
        self.timeframe = timeframe
        self.verbose = verbose
        self.n = len(df)
        self.dna = {}
        self.scores = {}
        self.start_time = time.time()

    def _log(self, msg, level="INFO"):
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}")

    def analyze(self):
        self._log(f"🧬 Analyzing {self.symbol} ({self.timeframe}) – {self.n:,} bars")
        self._chromosome_i_distribution()
        self._chromosome_ii_memory()
        self._chromosome_iii_volatility()
        self._chromosome_iv_jumps()
        self._chromosome_v_temporal()
        self._chromosome_vi_information()
        self._chromosome_vii_structure()
        self._chromosome_viii_synthetic()
        self._compute_strategy_affinity()
        self._compute_overall_score()
        elapsed = time.time() - self.start_time
        self._log(f"✅ Analysis completed in {elapsed:.1f}s")
        return self.dna, self.scores

    # ---------- Chromosome I: Distribution ----------
    def _chromosome_i_distribution(self):
        self._log("   Chromosome I – Distribution")
        close = self.df['Close'].values
        returns = np.diff(np.log(close))
        returns = returns[returns != 0]
        if len(returns) < 10:
            returns = np.diff(np.log(close))

        mean = np.mean(returns)
        std = np.std(returns)
        skew_val = skew(returns)
        kurt_val = kurtosis(returns, fisher=True)
        var_95 = np.percentile(returns, 5)
        cvar_95 = returns[returns <= var_95].mean() if len(returns[returns <= var_95]) > 0 else var_95
        sorted_abs = np.sort(np.abs(returns))[::-1]
        tail_index = np.nan
        if len(sorted_abs) > 100:
            tail_index = 1 / np.mean(np.log(sorted_abs[:100] / sorted_abs[100]))

        self.dna['chromosome_i'] = {
            'mean_return': float(mean * 10000),
            'median_return': float(np.median(returns) * 10000),
            'std_return': float(std * 10000),
            'coef_variation': float(std / abs(mean)) if abs(mean) > 0 else 0,
            'skewness': float(skew_val),
            'excess_kurtosis': float(kurt_val),
            'tail_index': float(tail_index) if not np.isnan(tail_index) else None,
            'var_95': float(var_95 * 10000),
            'cvar_95': float(cvar_95 * 10000),
            'min_return': float(np.min(returns) * 10000),
            'max_return': float(np.max(returns) * 10000),
            'positive_ratio': float((returns > 0).mean() * 100),
            'negative_ratio': float((returns < 0).mean() * 100),
        }
        try:
            _, jb_p = jarque_bera(returns)
            self.scores['Distribution'] = (1 - min(1, jb_p * 20)) * 100
        except:
            self.scores['Distribution'] = 50

    # ---------- Chromosome II: Memory ----------
    def _chromosome_ii_memory(self):
        self._log("   Chromosome II – Memory")
        returns = np.diff(np.log(self.df['Close'].values))
        acf = {}
        for lag in [1, 3, 5, 10, 20]:
            if len(returns) > lag:
                corr = np.corrcoef(returns[:-lag], returns[lag:])[0, 1]
                acf[f'lag_{lag}'] = float(corr) if not np.isnan(corr) else 0
        hurst = self._hurst_exponent(returns)
        dfa = 0.5 + (hurst - 0.5) * 0.8
        lb_pvalue = self._ljung_box_test(returns)
        is_random = lb_pvalue > 0.05 if lb_pvalue else True

        self.dna['chromosome_ii'] = {
            'autocorrelation': acf,
            'hurst_exponent': float(hurst),
            'dfa_exponent': float(dfa),
            'ljung_box_pvalue': float(lb_pvalue) if lb_pvalue else 0.5,
            'is_random': bool(is_random),
        }
        mem_score = 0
        if hurst < 0.45:
            mem_score += 40
        elif hurst > 0.55:
            mem_score += 40
        else:
            mem_score += 20
        if abs(acf.get('lag_1', 0)) > 0.1:
            mem_score += 30
        elif abs(acf.get('lag_1', 0)) > 0.05:
            mem_score += 15
        self.scores['Memory'] = min(100, mem_score + 30 if not is_random else 0)

    # ---------- Chromosome III: Volatility ----------
    def _chromosome_iii_volatility(self):
        self._log("   Chromosome III – Volatility")
        returns = np.diff(np.log(self.df['Close'].values))
        vol = np.std(returns) * np.sqrt(252) * 100
        rv20 = pd.Series(returns).rolling(20).std().iloc[-1] * np.sqrt(252) * 100 if len(returns) >= 20 else 0
        rv100 = pd.Series(returns).rolling(100).std().iloc[-1] * np.sqrt(252) * 100 if len(returns) >= 100 else 0
        ewma = self._ewma_volatility(returns) * 100
        high, low, close = self.df['High'].values, self.df['Low'].values, self.df['Close'].values
        atr = self._atr(high, low, close)
        vol_series = pd.Series(returns).rolling(20).std() * np.sqrt(252) * 100
        vol_of_vol = vol_series.std() if len(vol_series) > 0 else 0
        vol_persistence = vol_series.autocorr() if len(vol_series) > 1 else 0

        self.dna['chromosome_iii'] = {
            'realized_vol': float(vol),
            'rolling_vol_20': float(rv20),
            'rolling_vol_100': float(rv100),
            'ewma_vol': float(ewma),
            'atr': float(atr),
            'vol_of_vol': float(vol_of_vol),
            'vol_persistence': float(vol_persistence) if not np.isnan(vol_persistence) else 0,
        }
        vol_score = 0
        if vol_persistence > 0.5:
            vol_score += 50
        elif vol_persistence > 0.3:
            vol_score += 30
        if vol_of_vol < 1:
            vol_score += 30
        elif vol_of_vol < 5:
            vol_score += 15
        self.scores['Volatility'] = min(100, vol_score + 20)

    # ---------- Chromosome IV: Jumps ----------
    def _chromosome_iv_jumps(self):
        self._log("   Chromosome IV – Jumps")
        returns = np.diff(np.log(self.df['Close'].values))
        std = np.std(returns)
        jump_stats = {}
        for thresh in [3, 4, 5]:
            mask = returns > thresh * std
            neg_mask = returns < -thresh * std
            pos = mask.sum()
            neg = neg_mask.sum()
            if pos + neg > 0:
                jump_stats[f'threshold_{thresh}'] = {
                    'positive': int(pos),
                    'negative': int(neg),
                    'total': int(pos + neg),
                    'rate': float((pos + neg) / len(returns) * 100),
                    'pos_rate': float(pos / len(returns) * 100),
                    'neg_rate': float(neg / len(returns) * 100),
                    'mean_pos': float(np.mean(returns[mask]) * 10000) if pos > 0 else 0,
                    'mean_neg': float(np.mean(returns[neg_mask]) * 10000) if neg > 0 else 0,
                    'max_pos': float(np.max(returns[mask]) * 10000) if pos > 0 else 0,
                    'max_neg': float(np.min(returns[neg_mask]) * 10000) if neg > 0 else 0,
                }
        mask4 = returns > 4 * std
        jump_intensity = mask4.sum() / len(returns) if len(returns) > 0 else 0
        indices = np.where(mask4)[0]
        if len(indices) > 2:
            waits = np.diff(indices)
            cv = np.std(waits) / np.mean(waits) if np.mean(waits) > 0 else 0
        else:
            cv = 0
        asymmetry = (jump_stats.get('threshold_4', {}).get('positive', 0) - jump_stats.get('threshold_4', {}).get('negative', 0)) / max(1, jump_stats.get('threshold_4', {}).get('total', 1))

        self.dna['chromosome_iv'] = {
            'jump_stats': jump_stats,
            'jump_intensity': float(jump_intensity),
            'waiting_time_cv': float(cv),
            'jump_asymmetry': float(asymmetry),
        }
        jump_score = 0
        if jump_intensity > 0:
            jump_score += 30
            if cv < 1.2:
                jump_score += 40
            if abs(asymmetry) > 0.5:
                jump_score += 20
        self.scores['Jumps'] = min(100, jump_score + 10)

    # ---------- Chromosome V: Temporal ----------
    def _chromosome_v_temporal(self):
        self._log("   Chromosome V – Temporal")
        df = self.df.copy()
        df['hour'] = df['Date'].dt.hour
        df['dayofweek'] = df['Date'].dt.dayofweek
        df['month'] = df['Date'].dt.month
        returns = np.diff(np.log(df['Close'].values))
        returns = np.append([0], returns)
        df['returns'] = returns

        hourly = df.groupby('hour')['returns'].mean()
        dow = df.groupby('dayofweek')['returns'].mean()
        month = df.groupby('month')['returns'].mean()
        sessions = {
            'asian': df[(df['hour'] >= 0) & (df['hour'] < 8)]['returns'].mean(),
            'european': df[(df['hour'] >= 8) & (df['hour'] < 14)]['returns'].mean(),
            'american': df[(df['hour'] >= 14) & (df['hour'] < 22)]['returns'].mean(),
        }
        best_hour = int(hourly.idxmax()) if len(hourly) > 0 else 0
        worst_hour = int(hourly.idxmin()) if len(hourly) > 0 else 0
        best_dow = int(dow.idxmax()) if len(dow) > 0 else 0
        worst_dow = int(dow.idxmin()) if len(dow) > 0 else 0

        self.dna['chromosome_v'] = {
            'hourly_returns': {int(k): float(v) for k, v in hourly.items()},
            'dow_returns': {int(k): float(v) for k, v in dow.items()},
            'month_returns': {int(k): float(v) for k, v in month.items()},
            'session_returns': {k: float(v) for k, v in sessions.items()},
            'best_hour': best_hour,
            'worst_hour': worst_hour,
            'best_dow': best_dow,
            'worst_dow': worst_dow,
        }
        temporal_score = 0
        if len(hourly) > 0 and hourly.max() - hourly.min() > 1e-5:
            temporal_score += 40
        if len(dow) > 0 and abs(dow.max() - dow.min()) > 1e-5:
            temporal_score += 30
        self.scores['Temporal'] = min(100, temporal_score + 30)

    # ---------- Chromosome VI: Information ----------
    def _chromosome_vi_information(self):
        self._log("   Chromosome VI – Information")
        returns = np.diff(np.log(self.df['Close'].values))
        returns = returns[returns != 0]
        if len(returns) < 50:
            returns = np.diff(np.log(self.df['Close'].values))

        if len(returns) > 8000:
            idx = np.linspace(0, len(returns)-1, 8000, dtype=int)
            returns = returns[idx]

        hist, _ = np.histogram(returns, bins=20)
        hist = hist / hist.sum()
        shannon = entropy(hist, base=2)
        max_ent = np.log2(20)
        norm_ent = shannon / max_ent

        perm_ent = self._permutation_entropy(returns)
        sample_ent = self._sample_entropy(returns, m=2, r=0.2) if len(returns) < 2000 else None
        lz = self._lempel_ziv_complexity(returns)

        self.dna['chromosome_vi'] = {
            'shannon_entropy': float(shannon),
            'max_entropy': float(max_ent),
            'normalized_entropy': float(norm_ent),
            'permutation_entropy': float(perm_ent) if perm_ent else None,
            'sample_entropy': float(sample_ent) if sample_ent else None,
            'lz_complexity': float(lz) if lz else None,
            'predictability': float((1 - norm_ent) * 100),
        }
        info_score = (1 - norm_ent) * 100
        if lz and lz < 0.5:
            info_score += 15
        self.scores['Information'] = min(100, info_score + 10)

    # ---------- Chromosome VII: Structure ----------
    def _chromosome_vii_structure(self):
        self._log("   Chromosome VII – Structure")
        close = self.df['Close'].values
        returns = np.diff(np.log(close))
        direction = np.sign(returns)
        runs = []
        cur = 1
        for i in range(1, len(direction)):
            if direction[i] == direction[i-1] and direction[i] != 0:
                cur += 1
            else:
                if cur > 1:
                    runs.append(cur)
                cur = 1
        avg_trend = np.mean(runs) if runs else 0
        max_trend = np.max(runs) if runs else 0
        theta, half_life = self._ou_parameters(close)
        swings = np.abs(np.diff(close))
        swing_mean = np.mean(swings)
        swing_std = np.std(swings)

        self.dna['chromosome_vii'] = {
            'avg_trend_length': float(avg_trend),
            'max_trend_length': int(max_trend),
            'ou_theta': float(theta) if theta else None,
            'ou_half_life': float(half_life) if half_life else None,
            'swing_mean': float(swing_mean),
            'swing_std': float(swing_std),
            'mean_reversion_speed': float(abs(theta)) if theta else 0,
        }
        struct_score = 0
        if half_life and 5 < half_life < 50:
            struct_score += 50
        elif half_life and half_life > 100:
            struct_score += 30
        else:
            struct_score += 20
        if avg_trend > 3:
            struct_score += 20
        self.scores['Structure'] = min(100, struct_score + 30)

    # ---------- Chromosome VIII: Synthetic ----------
    def _chromosome_viii_synthetic(self):
        self._log("   Chromosome VIII – Synthetic")
        signatures = []
        confidence = 0

        # Tick volume analysis
        if 'Volume' in self.df.columns:
            vol = self.df['Volume'].values
            if len(vol) > 0:
                try:
                    mode_series = pd.Series(vol).mode()
                    if len(mode_series) > 0:
                        most_common = mode_series.iloc[0]
                        pct = (vol == most_common).sum() / len(vol) * 100
                        if pct > 50:
                            signatures.append(f"Constant tick volume ({pct:.1f}% at {most_common})")
                            confidence += 15
                except:
                    pass

        # Jump asymmetry
        returns = np.diff(np.log(self.df['Close'].values))
        threshold = 4 * np.std(returns)
        pos = (returns > threshold).sum()
        neg = (returns < -threshold).sum()
        asym = abs(pos - neg) / max(1, pos + neg)
        if pos > 0 and neg == 0:
            signatures.append("100% positive jumps")
            confidence += 20
        elif neg > 0 and pos == 0:
            signatures.append("100% negative jumps")
            confidence += 20
        elif asym > 0.7:
            signatures.append(f"Strong jump asymmetry ({pos} vs {neg})")
            confidence += 15

        # Poisson-like waiting
        cv = self.dna['chromosome_iv'].get('waiting_time_cv', 0)
        if 0.7 < cv < 1.3:
            signatures.append(f"Poisson-like jump process (CV={cv:.2f})")
            confidence += 15

        # Zero gaps
        gaps = self.df['Open'].values[1:] - self.df['Close'].values[:-1]
        zero_gaps = (gaps == 0).mean() * 100
        if zero_gaps > 50:
            signatures.append(f"Zero gaps: {zero_gaps:.1f}%")
            confidence += 10

        # Benford test (fixed)
        benford = self._benford_test(returns)
        if benford is not None and benford < 0.05:
            signatures.append("Benford's law violation")
            confidence += 15

        self.dna['chromosome_viii'] = {
            'signatures': signatures,
            'confidence': min(100, confidence),
            'is_synthetic': confidence > 50,
            'confidence_level': 'High' if confidence > 70 else 'Medium' if confidence > 50 else 'Low',
            'benford_score': float(benford) if benford is not None else None,
            'jump_asymmetry': float(asym),
        }
        self.scores['Synthetic'] = confidence

    # ---------- Strategy Affinity ----------
    def _compute_strategy_affinity(self):
        hurst = self.dna['chromosome_ii']['hurst_exponent']
        entropy = self.dna['chromosome_vi']['normalized_entropy']
        vol = self.dna['chromosome_iii']['realized_vol']
        pred = self.dna['chromosome_vi']['predictability']
        trend_len = self.dna['chromosome_vii']['avg_trend_length']
        jump_int = self.dna['chromosome_iv']['jump_intensity']
        skewness = self.dna['chromosome_i']['skewness']
        vol_persist = self.dna['chromosome_iii']['vol_persistence']

        scores = {}
        # Mean Reversion
        mr_score = 0
        if hurst < 0.45:
            mr_score += 30
        if entropy < 0.6:
            mr_score += 25
        if vol < 1.0:
            mr_score += 20
        if pred > 30:
            mr_score += 15
        scores['Mean Reversion'] = min(100, mr_score + 10)

        # Trend Following
        tf_score = 0
        if hurst > 0.55:
            tf_score += 35
        if trend_len > 4:
            tf_score += 30
        if pred > 25:
            tf_score += 20
        scores['Trend Following'] = min(100, tf_score + 15)

        # Scalping
        scalp_score = 0
        if vol < 1.0:
            scalp_score += 35
        if jump_int < 0.005:
            scalp_score += 30
        if abs(skewness) < 0.2:
            scalp_score += 20
        scores['Scalping'] = min(100, scalp_score + 15)

        # Market Making
        mm_score = 0
        if vol < 1.0:
            mm_score += 30
        if vol_persist > 0.8:
            mm_score += 30
        if abs(skewness) < 0.2:
            mm_score += 20
        scores['Market Making'] = min(100, mm_score + 20)

        # Momentum
        mom_score = 0
        if self.dna['chromosome_ii']['autocorrelation'].get('lag_1', 0) > 0.05:
            mom_score += 35
        if skewness > 0.1:
            mom_score += 30
        if hurst > 0.5:
            mom_score += 20
        scores['Momentum'] = min(100, mom_score + 15)

        # Breakout
        break_score = 0
        if jump_int > 0.01:
            break_score += 40
        if self.dna['chromosome_i']['excess_kurtosis'] > 1:
            break_score += 30
        scores['Breakout'] = min(100, break_score + 30)

        self.dna['strategy_affinity'] = scores

    def _compute_overall_score(self):
        overall = np.mean([
            self.scores.get('Distribution', 0),
            self.scores.get('Memory', 0),
            self.scores.get('Volatility', 0),
            self.scores.get('Jumps', 0),
            self.scores.get('Temporal', 0),
            self.scores.get('Information', 0),
            self.scores.get('Structure', 0),
            self.scores.get('Synthetic', 0),
        ])
        self.dna['overall_score'] = overall

    # ---------- Static helpers ----------
    @staticmethod
    def _hurst_exponent(ts):
        N = len(ts)
        if N < 50:
            return 0.5
        max_lag = min(N//2, 100)
        lags = range(10, max_lag, 5)
        tau = []
        for lag in lags:
            if lag == 0:
                continue
            chunks = [ts[i:i+lag] for i in range(0, N-lag+1, lag)]
            if len(chunks) < 2:
                break
            mean_std = np.mean([np.std(chunk) for chunk in chunks if len(chunk)==lag])
            mean_range = np.mean([np.max(chunk)-np.min(chunk) for chunk in chunks if len(chunk)==lag])
            if mean_std > 0:
                tau.append(mean_range / mean_std)
        if len(tau) < 2:
            return 0.5
        coeffs = np.polyfit(np.log(lags[:len(tau)]), np.log(tau), 1)
        return coeffs[0]

    @staticmethod
    def _ewma_volatility(returns, lam=0.94):
        if len(returns) == 0:
            return 0
        vol = np.var(returns)
        for ret in returns[1:]:
            vol = lam * vol + (1 - lam) * ret**2
        return np.sqrt(vol)

    @staticmethod
    def _atr(high, low, close, period=14):
        if len(high) < period:
            return 0
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        return np.mean(tr[-period:])

    @staticmethod
    def _ou_parameters(price):
        if len(price) < 50:
            return None, None
        y = price[:-1]
        dy = price[1:] - price[:-1]
        X = np.column_stack([np.ones(len(y)), y])
        try:
            beta = np.linalg.lstsq(X, dy, rcond=None)[0]
            theta = -beta[1]
            if theta <= 0:
                return None, None
            half_life = np.log(2) / theta
            return theta, half_life
        except:
            return None, None

    @staticmethod
    def _permutation_entropy(ts, m=3, delay=1):
        from itertools import permutations
        if len(ts) < m * delay + 1:
            return None
        patterns = {}
        for i in range(len(ts) - m * delay):
            indices = np.argsort([ts[i + j * delay] for j in range(m)])
            key = tuple(indices)
            patterns[key] = patterns.get(key, 0) + 1
        total = sum(patterns.values())
        probs = [count / total for count in patterns.values()]
        return -sum(p * np.log(p) for p in probs if p > 0) / np.log(6)

    @staticmethod
    def _sample_entropy(ts, m=2, r=0.2):
        if len(ts) < m + 10:
            return None
        N = len(ts)
        r = r * np.std(ts)
        def _maxdist(xi, xj):
            return np.max(np.abs(xi - xj))
        def _phi(m):
            count = 0
            for i in range(N - m):
                template = ts[i:i+m]
                for j in range(N - m):
                    if i != j and _maxdist(template, ts[j:j+m]) <= r:
                        count += 1
            return count / ((N - m) * (N - m - 1))
        phi_m = _phi(m)
        phi_m1 = _phi(m + 1)
        if phi_m > 0 and phi_m1 > 0:
            return -np.log(phi_m1 / phi_m)
        return None

    @staticmethod
    def _lempel_ziv_complexity(ts):
        if len(ts) < 10:
            return None
        binary = (np.sign(ts) + 1) // 2
        binary_str = ''.join(map(str, binary.astype(int)))
        n = len(binary_str)
        substrings = set()
        complexity = 0
        i = 0
        while i < n:
            j = i + 1
            found = False
            while j <= n:
                if binary_str[i:j] not in substrings:
                    substrings.add(binary_str[i:j])
                    complexity += 1
                    found = True
                    break
                j += 1
            if not found:
                complexity += 1
            i = j
        return complexity / n

    @staticmethod
    def _benford_test(ts):
        """Benford's law test with proper length handling."""
        if len(ts) < 50:
            return None
        abs_returns = np.abs(ts)
        abs_returns = abs_returns[abs_returns > 0]
        if len(abs_returns) < 50:
            return None

        # Get first digits (ignore sign and decimal)
        first_digits = []
        for x in abs_returns * 10000:  # scale to get meaningful digits
            # Convert to string, get first digit
            s = str(int(x))
            if s and s[0].isdigit():
                first_digits.append(int(s[0]))

        if len(first_digits) < 50:
            return None

        observed = np.bincount(first_digits, minlength=10)[1:]  # digits 1-9
        expected = np.log10(1 + 1 / np.arange(1, 10))
        expected = expected / expected.sum() * len(first_digits)

        # Ensure same length
        min_len = min(len(observed), len(expected))
        observed = observed[:min_len]
        expected = expected[:min_len]

        if np.sum(expected) == 0:
            return None

        chi2 = np.sum((observed - expected)**2 / (expected + 1e-10))
        # Approximate p-value (we just return the chi-squared value)
        return chi2 / len(observed)  # normalized as a score

    @staticmethod
    def _ljung_box_test(ts, lags=20):
        """Ljung-Box test for autocorrelation."""
        if len(ts) < lags + 1:
            return 0.5
        n = len(ts)
        acf = np.zeros(lags)
        for lag in range(1, lags + 1):
            if lag < len(ts):
                corr = np.corrcoef(ts[:-lag], ts[lag:])[0, 1]
                acf[lag-1] = float(corr) if not np.isnan(corr) else 0
            else:
                acf[lag-1] = 0
        q_stat = n * (n + 2) * np.sum(acf**2 / (n - np.arange(1, lags + 1)))
        # p-value from chi-square
        try:
            from scipy.stats import chi2
            p_value = 1 - chi2.cdf(q_stat, lags)
        except:
            p_value = 0.5
        return p_value

    # ---------- Save results ----------
    def save(self, output_dir=None):
        if output_dir is None:
            output_dir = DNA_RESULTS_DIR
        os.makedirs(output_dir, exist_ok=True)
        filename = f"{output_dir}/{self.symbol}_{self.timeframe}_DNA.json"
        data = {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'bars': self.n,
            'dna': self.dna,
            'scores': self.scores,
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        self._log(f"💾 Saved DNA to {filename}")
        return filename


# ============================================================================
#  MAIN SCRIPT – Process all files with progress bar
# ============================================================================

def load_data(csv_path):
    df = pd.read_csv(csv_path)
    df.columns = [col.lower() for col in df.columns]
    if 'time' in df.columns:
        df.rename(columns={'time': 'date'}, inplace=True)
    elif 'datetime' in df.columns:
        df.rename(columns={'datetime': 'date'}, inplace=True)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    else:
        df.index = pd.to_datetime(df.index)
        df['date'] = df.index
    df = df.sort_values('date').reset_index(drop=True)
    col_map = {}
    for col in df.columns:
        if col.lower() in ['open', 'o']:
            col_map[col] = 'Open'
        elif col.lower() in ['high', 'h']:
            col_map[col] = 'High'
        elif col.lower() in ['low', 'l']:
            col_map[col] = 'Low'
        elif col.lower() in ['close', 'c']:
            col_map[col] = 'Close'
        elif col.lower() in ['volume', 'vol', 'v']:
            col_map[col] = 'Volume'
        elif col.lower() in ['date', 'time', 'datetime']:
            col_map[col] = 'Date'
    df = df.rename(columns=col_map)
    if 'Volume' not in df.columns:
        df['Volume'] = 1
    return df

def get_timeframe_from_filename(filename):
    if '_M1_' in filename or '_M1.' in filename:
        return 'M1'
    elif '_M5_' in filename or '_M5.' in filename:
        return 'M5'
    elif '_M15_' in filename or '_M15.' in filename:
        return 'M15'
    elif '_M30_' in filename or '_M30.' in filename:
        return 'M30'
    elif '_H1_' in filename or '_H1.' in filename:
        return 'H1'
    elif '_H4_' in filename or '_H4.' in filename:
        return 'H4'
    else:
        return 'M1'

def main():
    print("\n" + "="*80)
    print("🧬 DNA ANALYZER – Full 8‑Chromosome Profile")
    print("="*80)
    print(f"Data Directory: {DATA_DIR}")
    print(f"Output Directory: {DNA_RESULTS_DIR}")
    print("="*80)

    csv_files = glob.glob(f"{DATA_DIR}/*.csv")
    if not csv_files:
        print(f"No CSV files found in {DATA_DIR}")
        return

    print(f"Found {len(csv_files)} data files.")
    total_start = time.time()

    pbar = tqdm(csv_files, desc="Processing symbols", unit="file")
    for csv_path in pbar:
        basename = os.path.basename(csv_path)
        symbol = basename.replace('_PERIODE_M1_data.csv', '').replace('.csv', '')
        timeframe = get_timeframe_from_filename(basename)
        pbar.set_description(f"Processing {symbol} ({timeframe})")

        df = load_data(csv_path)
        if df is None or len(df) < 50:
            print(f"⚠️ Insufficient data for {symbol}, skipping")
            continue

        analyzer = DNAAnalyzer(df, symbol, timeframe, verbose=False)
        analyzer.analyze()
        analyzer.save()

    total_elapsed = time.time() - total_start
    print(f"\n✅ DNA Analysis Complete in {total_elapsed:.1f}s")
    print(f"📁 Results saved to: {DNA_RESULTS_DIR}")

if __name__ == "__main__":
    main()