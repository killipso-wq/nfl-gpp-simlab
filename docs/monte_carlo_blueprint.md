# Monte Carlo Simulation Blueprint

## Overview

This document summarizes the implementation of the NFL Monte Carlo simulation methodology as outlined in the "Realistic NFL Monte Carlo Simulation.pdf" and maps the concepts to the codebase.

## PDF Methodology Summary

### Core Principles

1. **Position-Specific Distributions**: Each position (QB, RB, WR, TE, DST) has distinct usage and efficiency patterns
2. **Correlation Modeling**: Players and teams have dependencies that must be modeled
3. **Game Environment**: Pace, game script, and weather affect all players in a game
4. **Tail Modeling**: Boom and bust outcomes are explicitly modeled beyond normal distributions
5. **Reproducible Sampling**: Fixed seeds ensure consistent results for analysis

### Key Components

#### Game-Level Factors
- **Pace**: Total plays per team, affected by game total and team tendencies
- **Pass Rate**: Affected by game script, weather, and team tendencies  
- **Scoring Environment**: Overall offensive productivity in the game
- **Game Script**: How point spread affects play calling

#### Player-Level Factors
- **Usage Distributions**: Targets, carries, snap share, goal line opportunities
- **Efficiency Distributions**: Yards per target/carry, TD rates, catch rates
- **Role Uncertainty**: Injury probability, usage volatility
- **Position-Specific Boom Thresholds**: Different ceiling expectations by position

#### Correlation Structure
- **Intra-Team Positive**: QB ↔ WR/TE passing game correlations
- **Intra-Team Negative**: RB ↔ passing game (game script effects)
- **Inter-Team Negative**: Opposing teams compete for scoring/pace
- **DST Correlations**: Negative with opposing offense, positive with own offense

## Code Implementation Mapping

### Module Structure

```
src/sim/
├── game_model.py      # Game-level simulation (pace, pass rate, environment)
├── player_model.py    # Player-level simulation (usage, efficiency, scoring)
├── correlation.py     # Correlation modeling and sampling
├── sampler.py         # Monte Carlo sampling engine with seeding
└── pipeline.py        # End-to-end orchestration and output generation
```

### Game Model (`game_model.py`)

**Classes:**
- `GameEnvironment`: Encapsulates game conditions (total, spread, weather, venue)
- `TeamGameState`: Team-specific state (pace, pass rate, adjustments)
- `GameModel`: Simulates game-level factors

**Key Methods:**
- `simulate_game_pace()`: Generates team-specific play counts
- `simulate_pass_rates()`: Generates team-specific pass rates with game script
- `simulate_scoring_environment()`: Overall game productivity

**PDF Alignment:**
- Implements game total and spread effects on pace and pass rate
- Models weather and venue effects on passing
- Provides correlated shocks for teams in the same game

### Player Model (`player_model.py`)

**Classes:**
- `PlayerProjection`: Complete player model with usage and efficiency distributions
- `PlayerUsage`: Target/carry distributions and situational usage
- `PlayerEfficiency`: Yards per opportunity and scoring rates
- `PlayerModel`: Simulation engine for individual players

**Key Methods:**
- `simulate_player_performance()`: Core player simulation
- `_simulate_qb()`, `_simulate_rb()`, `_simulate_receiver()`, `_simulate_dst()`: Position-specific logic
- `_apply_tail_modeling()`: Boom/bust enhancement beyond base distribution

**PDF Alignment:**
- Position-specific volatility and boom thresholds
- DraftKings scoring implementation
- Usage share modeling with role uncertainty
- Tail events for boom/bust outcomes

### Correlation Model (`correlation.py`)

**Classes:**
- `CorrelationModel`: Builds and applies correlation matrices
- `CorrelationPair`: Individual correlation relationships
- `CorrelationType`: Enumeration of correlation types

**Key Methods:**
- `build_correlation_matrix()`: Constructs full correlation matrix
- `sample_correlated_shocks()`: Generates correlated random variables
- `_apply_qb_receiver_correlations()`: QB-WR/TE positive correlations
- `_apply_inter_team_correlations()`: Opposing team negative correlations

**PDF Alignment:**
- QB-receiver positive correlations (0.35 base)
- RB-passing game negative correlations (-0.25 base)
- Inter-team negative correlations (-0.20 base)
- Position competition negative correlations

### Sampling Engine (`sampler.py`)

**Classes:**
- `SamplingConfig`: Configuration for simulation runs
- `SimulationResult`: Individual simulation outcome
- `MonteCarloSampler`: Main sampling engine

**Key Methods:**
- `run_simulation()`: Full simulation workflow
- `_run_single_simulation()`: Individual trial
- `generate_summary_statistics()`: Percentile and metric calculation

**PDF Alignment:**
- Fixed seed reproducibility
- Configurable volatility scaling
- Correlation strength adjustment
- Proper statistical aggregation

### Pipeline Orchestration (`pipeline.py`)

**Classes:**
- `PipelineConfig`: End-to-end configuration
- `PipelineMetadata`: Run metadata and tracking
- `SimulationPipeline`: Complete workflow orchestration

**Key Methods:**
- `run_full_pipeline()`: Complete simulation workflow
- `_add_derived_metrics()`: Boom probability, value calculations
- `_generate_comparison_analysis()`: Site projection comparison
- `_generate_diagnostics()`: Model accuracy metrics

**PDF Alignment:**
- Generates all required output formats
- Includes boom/value/beat-site metrics
- Provides diagnostic accuracy measures
- Saves reproducible metadata

## Output Schema

### Primary Outputs

#### `sim_players.csv`
- **Player identification**: `player_id`, `name`, `team`, `position`, `salary`
- **Simulation statistics**: `sim_mean`, `sim_std`, `sim_min`, `sim_max`
- **Percentiles**: `p10`, `p25`, `p50`, `p75`, `p90`, `p95`
- **Boom metrics**: `boom_prob`, `boom_score`, `dart_flag`
- **Value metrics**: `value_per_1k`, `ceil_per_1k`
- **Comparison**: `beat_site_prob`, `vs_site_delta`

#### `compare.csv`
- Side-by-side comparison of simulation vs site projections
- Includes all metrics from `sim_players.csv`
- Coverage analysis (`coverage_p10_p90`)

#### `diagnostics_summary.csv`
- Model accuracy by position and overall
- MAE, RMSE, correlation vs site projections
- Coverage percentages
- Sample size information

#### `flags.csv`
- Outlier identification (large deltas, high volatility)
- Data quality issues (missing salary, unknown positions)
- Manual review recommendations

### Metadata

#### `metadata.json`
- Run identification and timestamp
- Configuration parameters used
- Data summary (player/game counts)
- Git commit for reproducibility
- Methodology reference

## Validation and Testing

### Unit Tests (`tests/test_sampler.py`)

1. **Deterministic Seeding**: Same seed produces identical results
2. **Distribution Shapes**: Proper percentile ordering and statistical properties
3. **Correlation Application**: QB-WR correlations vs independent sampling
4. **Zero Floor**: Fantasy points never negative
5. **Volatility Effects**: Multiplier affects result spread appropriately

### Integration Testing

1. **End-to-End Pipeline**: Full workflow produces expected outputs
2. **Data Format Compliance**: Outputs match expected schema
3. **Performance**: Simulation completes within reasonable time
4. **Error Handling**: Graceful handling of data issues

## Usage Examples

### Basic Simulation

```python
from src.sim.pipeline import SimulationPipeline, create_default_pipeline_config

# Configure simulation
config = create_default_pipeline_config()
config.n_simulations = 10000
config.seed = 42

# Run simulation
pipeline = SimulationPipeline(config)
output_dir, metadata = pipeline.run_full_pipeline(players_df, season=2024, week=1)
```

### Custom Configuration

```python
# Adjust volatility and correlations
config.volatility_multiplier = 1.2  # 20% more volatile
config.correlation_strength = 0.8   # Weaker correlations
config.include_correlations = True

# Custom boom thresholds
config.boom_thresholds = {
    'QB': 30.0,  # Higher QB boom threshold
    'RB': 18.0,
    'WR': 16.0,
    'TE': 12.0,
    'DST': 10.0
}
```

### Analysis Workflow

1. **Upload Data**: Load player CSV with required columns
2. **Configure Simulation**: Set parameters via Streamlit UI
3. **Run Simulation**: Execute Monte Carlo trials
4. **Review Results**: Analyze percentiles, boom rates, value metrics
5. **Check Diagnostics**: Validate model accuracy vs site projections
6. **Flag Review**: Address outliers and data quality issues
7. **Export Results**: Download CSV files for further analysis

## Future Enhancements

### Planned Improvements
- **Historical Calibration**: Use 2023-2024 data for parameter estimation
- **Advanced Correlations**: Copula-based dependency modeling
- **Weather Integration**: Detailed weather impact modeling
- **Injury Modeling**: Dynamic injury probability updates
- **Performance Optimization**: Vectorized sampling for 100k+ simulations

### Research Areas
- **Backtesting Framework**: CRPS/Brier score validation
- **Reliability Curves**: Calibration assessment
- **Alternative Distributions**: Skewed-normal, mixture models
- **Dynamic Adjustments**: In-season parameter updates

## References

- **Primary Methodology**: `docs/research/monte_carlo_football.pdf`
- **Implementation Code**: `src/sim/` modules
- **Test Suite**: `tests/test_sampler.py`
- **Application Interface**: `app.py` (Streamlit)

This blueprint serves as the bridge between the theoretical methodology and the practical implementation, ensuring alignment with the PDF specifications while providing clear guidance for development and usage.