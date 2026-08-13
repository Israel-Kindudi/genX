"""
Global configuration for SYNTHX.
"""
import os

# Paths
DATA_DIR = "data"
DNA_RESULTS_DIR = "dna_results"
RESEARCH_DATA_DIR = "research_data"
OPTIMIZATION_DIR = "optimization_results"
GENETIC_OPT_DIR = "genetic_optimization"
DASHBOARD_DIR = "dashboard"

# Assets & timeframes
ASSETS = ['BreakX 600', 'BreakX 1200', 'GainX 600',
          'BreakX 1800', 'FX Vol 20','GainX 999',
          'FX Vol 40','FX Vol 99','GainX 400',
          'FX Vol 60', 'FiboX','PainX 600',
          'FlipX 1','FlipX 2', 'FlipX 3', 'FlipX 4',
          'PlusX 1', 'TrendX 600', 'TrendX 1200',]
TIMEFRAMES = ['1m', '5m', '15m', '30m', '1h', '4h']

# Trading parameters
INITIAL_CAPITAL = 10
RISK_PER_TRADE = 1.0  # percent
COMMISSION = 0.0

# Genetic Algorithm defaults
POPULATION_SIZE = 20
GENERATIONS = 10
MUTATION_RATE = 0.15
CROSSOVER_RATE = 0.7
ELITISM = 0.1

# Ensure directories exist
for d in [DATA_DIR, DNA_RESULTS_DIR, RESEARCH_DATA_DIR, OPTIMIZATION_DIR, GENETIC_OPT_DIR]:
    os.makedirs(d, exist_ok=True)