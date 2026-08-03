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
ASSETS = ['BreakX 600', 'BreakX 1200', 'BreakX 1800', 'FX Vol 20']
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