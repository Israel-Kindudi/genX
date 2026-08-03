"""
Genetic Algorithm Optimization using the new modular backtester.
Includes full DNA guidance, progress bars, and detailed logging.
"""

import random
import numpy as np
import pandas as pd
from datetime import datetime
import json
import os
import glob
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Import strategies and backtester
from strategies import ScalpingStrategyRSI_VWMA, TrendFollowingStrategy, ScalpingStrategy
from backtester import BacktesterEngine
from dna.context import FullDNAContext

class FullDNAGeneticOptimizer:
    def __init__(self,
                 df,
                 symbol,
                 dna_result,
                 population_size=30,
                 generations=15,
                 mutation_rate=0.15,
                 crossover_rate=0.7,
                 elitism=0.1,
                 timeframe='5m',
                 initial_capital=10000,
                 risk_per_trade=1.0,
                 verbose=True):

        self.df = df
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital
        self.risk_per_trade = risk_per_trade
        self.verbose = verbose

        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism = elitism

        # Full DNA context
        self.dna_context = FullDNAContext(dna_result)
        self.dna_summary = self.dna_context.get_summary()

        # Best tracking
        self.best_solution = None
        self.best_fitness = -999
        self.best_report = None
        self.fitness_history = []
        self.population_history = []

    def _log(self, message, level="INFO"):
        if self.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{level}] {message}")

    def _print_dna_context(self):
        self._log("=" * 70)
        self._log("🧬 FULL DNA CONTEXT")
        self._log("=" * 70)
        dna = self.dna_context
        self._log(f"  Hurst: {dna.memory['hurst']:.4f}")
        self._log(f"  Entropy: {dna.information['normalized_entropy']:.4f}")
        self._log(f"  Volatility: {dna.volatility['realized_vol']:.2f}%")
        self._log(f"  Predictability: {dna.information['predictability']:.1f}%")
        self._log(f"  Trend Length: {dna.structure['avg_trend_length']:.2f}")
        self._log(f"  Jump Intensity: {dna.jumps['jump_intensity']:.6f}")
        self._log(f"  Is Synthetic: {dna.synthetic['is_synthetic']}")
        self._log(f"  Overall Score: {dna.overall_score:.1f}%")
        self._log("  Strategy Affinity:")
        for s, sc in sorted(dna.strategy_affinity.items(), key=lambda x: x[1], reverse=True):
            self._log(f"    {s}: {sc:.1f}%")
        self._log("=" * 70)

    def _get_strategy_parameter_bounds(self, strategy_name):
        if strategy_name == 'Trend Following':
            return {
                'lookback_bars': (10, 100),
                'entry_threshold': (1.0, 4.0),
                'stop_multiplier': (1.0, 4.0),
                'take_profit_multiplier': (1.5, 5.0),
                'max_trend_bars': (5, 30),
                'min_trend_bars': (2, 6),
            }
        elif strategy_name == 'Scalping_RSI_VWMA':
            return {
                'rsi_period': (5, 14),
                'vwma_period': (10, 30),
                'sma_200': (150, 250),
                'sma_12': (5, 20),
                'atr_period': (10, 20),
            }
        else:  # Scalping / Mean Reversion / Market Making
            return {
                'lookback_bars': (5, 50),
                'entry_threshold': (0.2, 2.5),
                'stop_multiplier': (0.3, 2.5),
                'take_profit_multiplier': (0.5, 3.0),
                'max_hold_bars': (2, 15),
                'min_profit_bp': (0.1, 1.5),
            }

    def _create_individual(self, strategy_name):
        bounds = self._get_strategy_parameter_bounds(strategy_name)
        params = {}
        for key, (mn, mx) in bounds.items():
            if isinstance(mn, int) and isinstance(mx, int):
                params[key] = random.randint(mn, mx)
            else:
                params[key] = round(random.uniform(mn, mx), 2)
        return {'strategy': strategy_name, 'params': params}

    def _create_strategy(self, individual):
        strategy_name = individual['strategy']
        params = individual['params'].copy()

        if strategy_name == 'Trend Following':
            accepted = ['lookback_bars', 'entry_threshold', 'stop_multiplier',
                        'take_profit_multiplier', 'max_trend_bars', 'min_trend_bars', 'atr_period']
            int_keys = ['lookback_bars', 'max_trend_bars', 'min_trend_bars', 'atr_period']
            cls = TrendFollowingStrategy
        elif strategy_name == 'Scalping_RSI_VWMA':
            accepted = ['rsi_period', 'vwma_period', 'sma_200', 'sma_12', 'atr_period']
            int_keys = ['rsi_period', 'vwma_period', 'sma_200', 'sma_12', 'atr_period']
            cls = ScalpingStrategyRSI_VWMA
        else:
            accepted = ['lookback_bars', 'entry_threshold', 'stop_multiplier',
                        'take_profit_multiplier', 'max_hold_bars', 'min_profit_bp', 'atr_period']
            int_keys = ['lookback_bars', 'max_hold_bars', 'atr_period']
            cls = ScalpingStrategy

        filtered = {k: v for k, v in params.items() if k in accepted}
        for key in int_keys:
            if key in filtered:
                filtered[key] = int(round(filtered[key]))
        return cls(**filtered)

    def _evaluate_fitness(self, individual):
        try:
            strategy = self._create_strategy(individual)
            engine = BacktesterEngine(
                self.df,
                strategy,
                symbol=self.symbol,
                initial_capital=self.initial_capital,
                risk_per_trade=self.risk_per_trade,
                timeframe=self.timeframe,
                verbose=False
            )
            report = engine.run(show_progress=False)
            if report['total_trades'] < 5:
                return -999, report

            sharpe = report['sharpe_ratio']
            pf = report['profit_factor']
            wr = report['win_rate'] / 100.0
            dd = max(0, report['max_drawdown'] / 20.0)
            dna_bonus = self._calculate_full_dna_bonus(individual, report)
            fitness = (0.30 * sharpe + 0.25 * pf + 0.20 * wr * 100 +
                       0.10 * (report['total_trades'] / 100.0) + dna_bonus - dd * 0.5)
            fitness = max(0, fitness)
            return fitness, report
        except Exception as e:
            self._log(f"Error evaluating individual: {e}", "ERROR")
            return -999, None

    def _calculate_full_dna_bonus(self, individual, report):
        bonus = 0.0
        strategy = individual['strategy']
        dna = self.dna_context

        # Chromosome I – Distribution
        if abs(dna.distribution['skewness']) < 0.1:
            bonus += 0.08
        if dna.distribution['excess_kurtosis'] < 1:
            bonus += 0.05

        # Chromosome II – Memory
        hurst = dna.memory['hurst']
        if strategy in ['Mean Reversion', 'Scalping', 'Scalping_RSI_VWMA']:
            if hurst < 0.45:
                bonus += 0.15
        elif strategy == 'Trend Following':
            if hurst > 0.55:
                bonus += 0.15

        # Chromosome III – Volatility
        if dna.volatility['realized_vol'] < 1.0:
            bonus += 0.05
        if dna.volatility['vol_persistence'] > 0.9:
            bonus += 0.08

        # Chromosome IV – Jumps
        if dna.jumps['jump_intensity'] < 0.005:
            bonus += 0.10

        # Chromosome VI – Information
        entropy = dna.information['normalized_entropy']
        if entropy < 0.6:
            bonus += 0.15
        elif entropy < 0.7:
            bonus += 0.08

        pred = dna.information['predictability']
        if pred > 30:
            bonus += 0.12
        elif pred > 20:
            bonus += 0.06

        # Chromosome VII – Structure
        if strategy in ['Mean Reversion', 'Scalping', 'Scalping_RSI_VWMA']:
            if dna.structure['mean_reversion_speed'] > 0.01:
                bonus += 0.10
        elif strategy == 'Trend Following':
            if dna.structure['avg_trend_length'] > 4:
                bonus += 0.10

        # Chromosome VIII – Synthetic
        if dna.synthetic['is_synthetic'] and dna.synthetic['confidence'] > 50:
            bonus += 0.12
            if strategy in ['Scalping', 'Scalping_RSI_VWMA']:
                bonus += 0.08

        # Strategy affinity bonus
        aff = dna.strategy_affinity.get(strategy, 50)
        bonus += (aff / 100.0) * 0.15

        # Chromosome scores average
        avg_score = sum(dna.chromosome_scores.values()) / len(dna.chromosome_scores)
        if avg_score > 70:
            bonus += 0.05

        return bonus

    def _crossover(self, p1, p2):
        if random.random() > self.crossover_rate:
            return p1.copy(), p2.copy()
        params1 = p1['params'].copy()
        params2 = p2['params'].copy()
        common = set(params1.keys()) & set(params2.keys())
        for k in common:
            if random.random() < 0.5:
                params1[k], params2[k] = params2[k], params1[k]
        if random.random() < 0.1:
            p1['strategy'], p2['strategy'] = p2['strategy'], p1['strategy']
        return {'strategy': p1['strategy'], 'params': params1}, {'strategy': p2['strategy'], 'params': params2}

    def _mutate(self, individual):
        strategy = individual['strategy']
        bounds = self._get_strategy_parameter_bounds(strategy)
        params = individual['params']
        rate = self.mutation_rate
        if self.dna_context.information['normalized_entropy'] > 0.8:
            rate *= 1.3
        if self.dna_context.synthetic['is_synthetic']:
            rate *= 0.8

        for key, (mn, mx) in bounds.items():
            if key in params and random.random() < rate:
                if isinstance(mn, int) and isinstance(mx, int):
                    step = max(1, int((mx - mn) * 0.1))
                    delta = random.randint(-step, step)
                    params[key] = max(mn, min(mx, params[key] + delta))
                else:
                    span = mx - mn
                    delta = random.uniform(-span * 0.1, span * 0.1)
                    params[key] = round(max(mn, min(mx, params[key] + delta)), 2)
        return individual

    def _select_parents(self, population, fitness):
        tourn = random.sample(list(zip(population, fitness)), 3)
        return max(tourn, key=lambda x: x[1])[0]

    def _get_strategy_options(self):
        # Combine DNA affinity with the new strategy
        aff = self.dna_context.strategy_affinity
        strategies = list(aff.keys()) if aff else ['Scalping', 'Trend Following', 'Market Making']
        if 'Scalping_RSI_VWMA' not in strategies:
            strategies.append('Scalping_RSI_VWMA')
        if aff:
            scores = np.array([aff.get(s, 50) for s in strategies])
            scores = scores / scores.sum()
        else:
            scores = np.ones(len(strategies)) / len(strategies)
        return strategies, scores

    def _create_initial_population(self):
        strategies, weights = self._get_strategy_options()
        pop = []
        for _ in range(self.population_size):
            s = np.random.choice(strategies, p=weights)
            pop.append(self._create_individual(s))
        return pop

    def optimize(self):
        start_time = datetime.now()
        self._log("=" * 70)
        self._log("🧬 FULL DNA-GUIDED GENETIC OPTIMIZATION")
        self._log("=" * 70)
        self._log(f"Symbol: {self.symbol}")
        self._log(f"Timeframe: {self.timeframe}")
        self._print_dna_context()
        self._log(f"Population: {self.population_size}")
        self._log(f"Generations: {self.generations}")
        self._log(f"Mutation Rate: {self.mutation_rate*100:.1f}%")
        self._log(f"Crossover Rate: {self.crossover_rate*100:.1f}%")
        self._log("=" * 70)

        # Initial population
        self._log("Creating initial population...")
        pop = self._create_initial_population()

        self._log("Evaluating initial population...")
        fitness = []
        reports = []
        for ind in tqdm(pop, desc="Initial eval", unit="ind", leave=True):
            f, r = self._evaluate_fitness(ind)
            fitness.append(f)
            reports.append(r)

        best_idx = np.argmax(fitness)
        self.best_fitness = fitness[best_idx]
        self.best_solution = pop[best_idx].copy()
        self.best_report = reports[best_idx]
        self.fitness_history.append(self.best_fitness)
        self.population_history.append(pop.copy())

        self._log(f"Initial Best Fitness: {self.best_fitness:.4f}")
        self._log(f"  Strategy: {self.best_solution['strategy']}")
        if self.best_report:
            self._log(f"  Trades: {self.best_report['total_trades']}, Sharpe: {self.best_report['sharpe_ratio']:.2f}")

        # Evolution loop with progress bar
        gen_iter = tqdm(range(self.generations), desc="Evolution", unit="gen", leave=True)
        for gen in gen_iter:
            new_pop = []
            # Elitism
            elite_count = int(self.elitism * self.population_size)
            sorted_idx = np.argsort(fitness)
            for idx in sorted_idx[-elite_count:]:
                new_pop.append(pop[idx].copy())

            while len(new_pop) < self.population_size:
                p1 = self._select_parents(pop, fitness)
                p2 = self._select_parents(pop, fitness)
                c1, c2 = self._crossover(p1, p2)
                c1 = self._mutate(c1)
                c2 = self._mutate(c2)
                new_pop.append(c1)
                if len(new_pop) < self.population_size:
                    new_pop.append(c2)

            pop = new_pop
            new_fitness = []
            new_reports = []
            for ind in pop:
                f, r = self._evaluate_fitness(ind)
                new_fitness.append(f)
                new_reports.append(r)

            fitness = new_fitness
            reports = new_reports

            best_idx = np.argmax(fitness)
            if fitness[best_idx] > self.best_fitness:
                self.best_fitness = fitness[best_idx]
                self.best_solution = pop[best_idx].copy()
                self.best_report = reports[best_idx]
            self.fitness_history.append(self.best_fitness)
            self.population_history.append(pop.copy())

            # Update progress bar with best info
            gen_iter.set_postfix({
                'BestFit': f"{self.best_fitness:.4f}",
                'Strategy': self.best_solution['strategy'],
                'Sharpe': f"{self.best_report['sharpe_ratio']:.2f}" if self.best_report else "N/A"
            })

            if gen % 5 == 0 or gen == self.generations - 1:
                self._log(f"Gen {gen}/{self.generations}: Best Fitness: {self.best_fitness:.4f}, "
                         f"Strategy: {self.best_solution['strategy']}")

        elapsed = datetime.now() - start_time
        self._log("=" * 70)
        self._log("✅ OPTIMIZATION COMPLETE")
        self._log(f"Time: {elapsed.total_seconds():.1f}s")
        self._log(f"Best Fitness: {self.best_fitness:.4f}")
        self._log(f"Best Strategy: {self.best_solution['strategy']}")
        self._log(f"Best Parameters: {json.dumps(self.best_solution['params'], indent=2)}")
        if self.best_report:
            self._log(f"Performance:")
            self._log(f"  Trades: {self.best_report['total_trades']}")
            self._log(f"  Win Rate: {self.best_report['win_rate']:.1f}%")
            self._log(f"  Profit Factor: {self.best_report['profit_factor']:.2f}")
            self._log(f"  Sharpe Ratio: {self.best_report['sharpe_ratio']:.2f}")
            self._log(f"  Total PnL: ${self.best_report['total_pnl']:.2f}")
        self._log("=" * 70)

        return {
            'best_solution': self.best_solution,
            'best_fitness': self.best_fitness,
            'best_report': self.best_report,
            'fitness_history': self.fitness_history,
            'dna_context': self.dna_context.get_all_metrics(),
            'dna_summary': self.dna_context.get_summary(),
            'params': {
                'population_size': self.population_size,
                'generations': self.generations,
                'mutation_rate': self.mutation_rate,
                'crossover_rate': self.crossover_rate,
            }
        }

    def save_results(self, output_dir="genetic_optimization"):
        os.makedirs(output_dir, exist_ok=True)
        result = {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'best_solution': self.best_solution,
            'best_fitness': self.best_fitness,
            'best_report': self.best_report,
            'fitness_history': self.fitness_history,
            'dna_context': self.dna_context.get_all_metrics(),
            'dna_summary': self.dna_context.get_summary(),
            'dna_chromosome_scores': self.dna_context.chromosome_scores,
            'strategy_affinity': self.dna_context.strategy_affinity,
            'overall_dna_score': self.dna_context.overall_score,
            'params': {
                'population_size': self.population_size,
                'generations': self.generations,
                'mutation_rate': self.mutation_rate,
                'crossover_rate': self.crossover_rate,
            }
        }
        filename = f"{output_dir}/{self.symbol}_{self.timeframe}_full_dna_genetic_opt.json"
        with open(filename, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        self._log(f"💾 Results saved to {filename}")
        return filename


# ============================================================================
#  Multi‑symbol optimizer using the new structure
# ============================================================================
class MultiSymbolOptimizer:
    def __init__(self, data_dict, dna_results, timeframe='5m', verbose=True):
        self.data_dict = data_dict
        self.dna_results = dna_results
        self.timeframe = timeframe
        self.verbose = verbose
        self.results = {}

    def _log(self, msg, level="INFO"):
        if self.verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}")

    def get_dna_for_symbol(self, symbol):
        return self.dna_results.get(f"{symbol}_{self.timeframe}", None)

    def run(self, population_size=20, generations=10):
        self._log("=" * 70)
        self._log("🧬 MULTI‑SYMBOL DNA‑GUIDED GENETIC OPTIMIZATION")
        self._log("=" * 70)
        for symbol, df in self.data_dict.items():
            dna = self.get_dna_for_symbol(symbol)
            if not dna:
                self._log(f"⚠️ No DNA for {symbol} at {self.timeframe}, skipping")
                continue
            self._log(f"\n📊 Optimizing: {symbol}")
            opt = FullDNAGeneticOptimizer(
                df=df,
                symbol=symbol,
                dna_result=dna,
                population_size=population_size,
                generations=generations,
                timeframe=self.timeframe,
                verbose=self.verbose
            )
            result = opt.optimize()
            opt.save_results()
            self.results[symbol] = result

        self._print_summary()
        return self.results

    def _print_summary(self):
        self._log("\n" + "=" * 70)
        self._log("📊 OPTIMIZATION SUMMARY")
        self._log("=" * 70)
        for symbol, res in self.results.items():
            rep = res.get('best_report', {})
            dna_sum = res.get('dna_summary', {})
            self._log(f"\n{symbol}:")
            self._log(f"  DNA Score: {dna_sum.get('overall_score', 0):.1f}%")
            self._log(f"  Strategy: {res['best_solution']['strategy']}")
            self._log(f"  Trades: {rep.get('total_trades', 0)}")
            self._log(f"  Win Rate: {rep.get('win_rate', 0):.1f}%")
            self._log(f"  Sharpe: {rep.get('sharpe_ratio', 0):.2f}")
            self._log(f"  PnL: ${rep.get('total_pnl', 0):.2f}")
            self._log(f"  Fitness: {res['best_fitness']:.4f}")
        self._log("=" * 70)


# ============================================================================
#  Main execution
# ============================================================================
if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧬 FULL DNA‑GUIDED GENETIC OPTIMIZATION (Modular Structure)")
    print("=" * 80)
    print("Including Scalping Strategy #1: RSI + VWMA")
    print("=" * 80)

    # Load DNA results
    dna_files = glob.glob("dna_results/*_DNA.json")
    dna_results = {}
    for file in dna_files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                symbol = data.get('symbol', os.path.basename(file).replace('_DNA.json', ''))
                timeframe = data.get('timeframe', 'unknown')
                dna_results[f"{symbol}_{timeframe}"] = data
        except Exception as e:
            print(f"⚠️ Error loading {file}: {e}")

    print(f"✅ Loaded {len(dna_results)} DNA profiles")

    # Load data
    csv_files = glob.glob("data/*.csv")
    data_dict = {}
    for csv_file in csv_files:
        symbol = os.path.basename(csv_file).replace("_PERIODE_M1_data.csv", "")
        try:
            df = pd.read_csv(csv_file)
            df.columns = [col.lower() for col in df.columns]
            if 'time' in df.columns:
                df.rename(columns={'time': 'date'}, inplace=True)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            else:
                df.index = pd.to_datetime(df.index)
                df['date'] = df.index
            df = df.sort_values('date').reset_index(drop=True)
            column_map = {'open': 'Open', 'high': 'High', 'low': 'Low', 'close': 'Close', 'date': 'Date', 'volume': 'Volume'}
            df = df.rename(columns=column_map)
            if all(c in df.columns for c in ['Date', 'Open', 'High', 'Low', 'Close']):
                print(f"✅ Loaded {symbol}: {len(df):,} bars")
                data_dict[symbol] = df
        except Exception as e:
            print(f"⚠️ Error loading {csv_file}: {e}")

    if not data_dict:
        print("No data files loaded.")
        exit()

    # Run optimization
    optimizer = MultiSymbolOptimizer(
        data_dict=data_dict,
        dna_results=dna_results,
        timeframe='5m',
        verbose=True
    )
    results = optimizer.run(population_size=15, generations=8)

    print("\n✅ Full DNA Genetic Optimization Complete!")
    print("📁 Check genetic_optimization/ for full results")