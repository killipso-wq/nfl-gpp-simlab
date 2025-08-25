# NFL GPP SimLab - Quick Start Guide

Welcome to NFL GPP SimLab! This guide will get you up and running with Monte Carlo simulations for NFL GPP optimization in just a few minutes.

## Installation

Install NFL GPP SimLab with basic functionality:

```bash
pip install nfl-gpp-simlab
```

For CLI with YAML configuration support:

```bash
pip install nfl-gpp-simlab[cli]
```

For development:

```bash
pip install nfl-gpp-simlab[dev]
```

## Quick Start

### 1. Generate a Configuration File

```bash
nfl-gpp-sim --generate-config my_config.toml
```

This creates a sample configuration file with default settings:

```toml
# NFL GPP SimLab Configuration File
n_trials = 10000        # Number of Monte Carlo trials
base_seed = 42          # Random seed for reproducibility  
n_jobs = 1              # Number of parallel jobs
quantiles = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95]  # Statistical quantiles
```

### 2. Prepare Your Player Data

Create a CSV file with your player data. Required columns:
- `PLAYER`: Player name
- `POS`: Position 
- `TEAM`: Team abbreviation

Optional columns:
- `FPTS`: Site fantasy points projection
- `SAL` or `SALARY`: Player salary
- `RST%` or `OWN`: Rostered percentage/ownership
- `VAL`: Site value metric
- `OPP`: Opponent team
- `O/U`: Over/under total
- `SPRD`: Point spread

Example `players.csv`:

```csv
PLAYER,POS,TEAM,FPTS,SAL,RST%
Josh Allen,QB,BUF,25.5,8500,12.3
Saquon Barkley,RB,NYG,18.2,7000,8.7
Stefon Diggs,WR,BUF,16.8,6500,11.2
Travis Kelce,TE,KC,14.5,7500,15.8
```

### 3. Run Your First Simulation

Using configuration file:

```bash
nfl-gpp-sim --config my_config.toml --input players.csv --output results/
```

Using command line parameters:

```bash
nfl-gpp-sim --input players.csv --output results/ --n-trials 50000 --seed 123
```

### 4. Analyze Results

The simulation generates several output files in your results directory:

- **`sim_players.csv`**: Core simulation results with projections
- **`compare.csv`**: Comparison between your sims and site projections  
- **`diagnostics_summary.csv`**: Accuracy metrics and statistics
- **`flags.csv`**: Flagged outliers and data issues
- **`metadata.json`**: Simulation configuration and runtime info

## Configuration Options

### Core Parameters

| Parameter | Description | Default | Example |
|-----------|-------------|---------|---------|
| `n_trials` | Number of Monte Carlo trials | 10000 | 50000 |
| `base_seed` | Random seed for reproducibility | 42 | 123 |
| `n_jobs` | Parallel processing jobs | 1 | 4 |
| `quantiles` | Statistical quantiles to compute | [0.1, 0.25, 0.5, 0.75, 0.9, 0.95] | [0.1, 0.5, 0.9] |

### Environment Variables

- `NFL_GPP_SIMLAB_N_JOBS`: Set default number of parallel jobs

```bash
export NFL_GPP_SIMLAB_N_JOBS=4
nfl-gpp-sim --input players.csv --output results/
```

## Understanding Output Files

### sim_players.csv
Your Monte Carlo projections with key statistics:
- `sim_mean`: Average projected points
- `floor_p10`: 10th percentile (floor)
- `ceiling_p90`: 90th percentile (ceiling)
- `boom_prob`: Probability of boom performance

### compare.csv  
Side-by-side comparison with site projections:
- `delta_mean`: Difference between your projection and site
- `beat_site_prob`: Probability of outperforming site projection
- `value_per_1k`: Value per $1k salary
- `dart_flag`: High-upside, low-ownership flag

### diagnostics_summary.csv
Accuracy metrics for model validation:
- `mae`: Mean absolute error vs site projections
- `rmse`: Root mean squared error  
- `correlation`: Correlation with site projections
- `coverage_p10_p90`: % of site projections within your confidence intervals

## Configuration File Formats

### TOML (Recommended)

```toml
n_trials = 25000
base_seed = 999
n_jobs = 4
quantiles = [0.1, 0.5, 0.9]

[advanced]
enable_boom_analysis = true
```

### YAML (Optional)

```yaml
n_trials: 25000
base_seed: 999
n_jobs: 4
quantiles: [0.1, 0.5, 0.9]

advanced:
  enable_boom_analysis: true
```

## CLI Help

Get full CLI documentation:

```bash
nfl-gpp-sim --help
```

View version:

```bash
nfl-gpp-sim --version
```

## Next Steps

- Explore the [full README](../README.md) for complete feature documentation
- Check out [Monte Carlo methodology](research/monte_carlo_methodology.md) for simulation details
- Review [GPP strategy blueprint](gpp_strategy_blueprint.md) for optimization strategies

## Troubleshooting

### Common Issues

**YAML configuration not working:**
```bash
pip install nfl-gpp-simlab[cli]  # Install YAML support
```

**Memory issues with large simulations:**
- Reduce `n_trials` (start with 10,000)
- Increase `n_jobs` for better parallelization
- Process smaller player sets

**Inconsistent results:**
- Ensure you're using the same `base_seed`
- Check that input data hasn't changed

For additional help, see the [full documentation](../README.md) or open an issue on GitHub.