# Pipeline Overview

This document provides an end-to-end view of the NFL GPP Simulator pipeline, covering data sources, warehouse steps, baselining scripts/outputs, simulation inputs/engine/outputs, and UI integration flow.

## Pipeline Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │    │ Metrics Warehouse│    │  Baseline Build │
│                 │───▶│                  │───▶│                 │
│ • nfl_data_py   │    │ • Team metrics   │    │ • Team priors   │
│ • Schedules     │    │ • Player metrics │    │ • Player priors │
│ • Play-by-play  │    │ • Game metrics   │    │ • Boom thresh.  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             │
│  User Inputs    │    │   Simulator      │             │
│                 │───▶│                  │◀────────────┘
│ • players.csv   │    │ • Monte Carlo    │
│ • Site data     │    │ • Correlations   │
│ • Parameters    │    │ • Environment    │
└─────────────────┘    └──────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   UI/Analysis   │    │     Outputs      │    │   Diagnostics   │
│                 │◀───│                  │───▶│                 │
│ • Streamlit     │    │ • sim_players    │    │ • Accuracy      │
│ • Downloads     │    │ • compare        │    │ • Flags         │
│ • Filters       │    │ • metadata       │    │ • Coverage      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Stage 1: Data Sources

### Primary Data (nfl_data_py)

**Weekly Stats (2023-2024):**
```python
import nfl_data_py as nfl

# Load weekly data for baseline
weekly_data = nfl.import_weekly_data([2023, 2024])
pbp_data = nfl.import_pbp_data([2023, 2024])  # Optional for advanced metrics
schedule = nfl.import_schedules([2023, 2024, 2025])
```

**Data Scope:**
- **Historical baseline**: 2023-2024 regular season only
- **Target projections**: 2025 season/week specified by user
- **No data leakage**: Future actual results excluded from projections

**Raw Data Volume:**
- Weekly stats: ~32 teams × 18 weeks × 2 seasons = 1,152 team-weeks
- Player data: ~1,500-2,000 unique players per season
- Play-by-play: ~170,000 plays per season (optional)

### Schedule Integration

**Game Mapping:**
```python
# Target week schedule
week_schedule = schedule[
    (schedule['season'] == target_season) & 
    (schedule['week'] == target_week)
]

# Generate game_id mappings
game_ids = week_schedule.apply(
    lambda row: f"{row['away_team']}@{row['home_team']}", axis=1
)
```

**Active Teams Filter:**
- Only teams with games in target week included
- Bye weeks automatically excluded
- Used to restrict final player output

## Stage 2: Metrics Warehouse

### Team Metrics Pipeline

**Script:** `src/metrics/team_metrics.py`

**Computation Flow:**
```python
def build_team_metrics(seasons):
    # 1. Aggregate team-level stats by week
    team_weekly = aggregate_team_stats(weekly_data, seasons)
    
    # 2. Calculate pace and volume metrics
    pace_metrics = calculate_pace_metrics(team_weekly)
    
    # 3. Derive passing tendency and efficiency
    passing_metrics = calculate_passing_metrics(pbp_data, seasons)
    
    # 4. EPA and success rates
    efficiency_metrics = calculate_efficiency_metrics(pbp_data, seasons)
    
    # 5. Combine and export
    team_metrics = combine_team_metrics([pace_metrics, passing_metrics, efficiency_metrics])
    return team_metrics
```

**Output:** `data/metrics/team_week.csv`
```
team,week,season,pace,neutral_xpass,proe_neutral,epa_per_play,success_rate,points_per_game
BUF,1,2023,67.2,0.58,0.02,0.15,0.48,31.2
BUF,2,2023,63.8,0.61,-0.01,0.09,0.44,24.6
```

### Player Metrics Pipeline

**Script:** `src/metrics/player_metrics.py`

**Position-Specific Processing:**
```python
def build_player_metrics(seasons):
    # QB metrics
    qb_metrics = calculate_qb_metrics(weekly_data, pbp_data, seasons)
    
    # RB metrics  
    rb_metrics = calculate_rb_metrics(weekly_data, pbp_data, seasons)
    
    # WR/TE metrics
    receiving_metrics = calculate_receiving_metrics(weekly_data, pbp_data, seasons)
    
    # Combine all positions
    player_metrics = combine_player_metrics([qb_metrics, rb_metrics, receiving_metrics])
    return player_metrics
```

**Output:** `data/metrics/player_week.csv`
```
player_id,player_name,position,team,week,season,targets,receptions,yards,tds,wopr,racr
BUF_WR_STEFANDIGGS,Stefon Diggs,WR,BUF,1,2023,12,8,125,1,0.31,0.89
BUF_WR_STEFANDIGGS,Stefon Diggs,WR,BUF,2,2023,10,7,102,0,0.28,0.92
```

### Game-Level Aggregation

**Script:** `src/metrics/game_metrics.py`

**Correlation Modeling:**
```python
def build_game_metrics(team_metrics, player_metrics):
    # Aggregate to game level for correlation analysis
    game_metrics = aggregate_by_game(team_metrics, player_metrics)
    
    # Calculate QB-receiver correlations
    qb_receiver_corr = calculate_qb_receiver_correlations(game_metrics)
    
    # Team-level correlations (pace, scoring)
    team_correlations = calculate_team_correlations(game_metrics)
    
    return game_metrics, correlations
```

**Output:** `data/metrics/game_week.csv`
```
game_id,week,season,total_plays,total_points,pace_combined,pass_rate_combined
BUF@MIA,1,2023,142,51,66.8,0.61
KC@DET,1,2023,134,42,64.2,0.58
```

## Stage 3: Baseline Building

### Team Priors Generation

**Script:** `scripts/build_baseline.py`

**Command:**
```bash
python scripts/build_baseline.py --start 2023 --end 2024 --out data
```

**Processing Steps:**
```python
def build_team_priors(team_metrics):
    # 1. Calculate position averages across 2023-2024
    team_averages = team_metrics.groupby('team').agg({
        'pace': ['mean', 'std'],
        'neutral_xpass': 'mean',
        'proe_neutral': 'mean',
        'epa_per_play': 'mean',
        'success_rate': 'mean'
    })
    
    # 2. Apply Empirical-Bayes shrinkage toward league mean
    shrunk_priors = apply_empirical_bayes_shrinkage(team_averages)
    
    # 3. Format for simulator consumption
    team_priors = format_team_priors(shrunk_priors)
    return team_priors
```

**Output:** `data/baseline/team_priors.csv`
```
team,pace_mean,pace_std,neutral_xpass,proe_neutral,epa_per_play_off,epa_per_play_def,success_rate_off,success_rate_def
BUF,65.2,4.1,0.58,0.03,0.12,-0.05,0.46,0.42
KC,63.8,3.9,0.61,-0.01,0.15,-0.08,0.48,0.40
```

### Player Priors Generation

**Processing by Position:**
```python
def build_player_priors(player_metrics):
    # QB priors
    qb_priors = build_qb_priors(player_metrics[player_metrics.position == 'QB'])
    
    # RB priors
    rb_priors = build_rb_priors(player_metrics[player_metrics.position == 'RB'])
    
    # WR priors  
    wr_priors = build_wr_priors(player_metrics[player_metrics.position == 'WR'])
    
    # TE priors
    te_priors = build_te_priors(player_metrics[player_metrics.position == 'TE'])
    
    # Combine all positions
    player_priors = pd.concat([qb_priors, rb_priors, wr_priors, te_priors])
    return player_priors
```

**Output:** `data/baseline/player_priors.csv`
```
player_id,position,usage_alpha,usage_beta,efficiency_mean,efficiency_std,td_rate_alpha,td_rate_beta,sample_size
BUF_QB_JOSHALLAN,QB,28.5,6.2,7.8,1.2,0.052,0.948,34
KC_RB_ISAIAHPACHECO,RB,12.8,42.1,4.6,0.8,0.068,0.932,29
```

### Boom Thresholds Generation

**Script:** `scripts/build_boom_thresholds.py`

**Command:**
```bash
python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90
```

**Processing:**
```python
def build_boom_thresholds(player_metrics, quantile=0.90):
    # Calculate position-level boom thresholds from historical data
    boom_thresholds = player_metrics.groupby('position')['dk_points'].quantile(quantile)
    
    # Format as JSON for simulator
    thresholds_dict = {
        'quantile': quantile,
        'thresholds': boom_thresholds.to_dict(),
        'baseline_period': '2023-2024',
        'created_at': datetime.now().isoformat()
    }
    return thresholds_dict
```

**Output:** `data/baseline/boom_thresholds.json`
```json
{
  "quantile": 0.90,
  "thresholds": {
    "QB": 28.5,
    "RB": 22.1,
    "WR": 24.7,
    "TE": 18.9,
    "DST": 16.2
  },
  "baseline_period": "2023-2024",
  "created_at": "2025-01-15T10:30:00"
}
```

## Stage 4: Simulation Engine

### Input Processing

**User Inputs:**
```python
# Primary input: players.csv from site or adapter
players_df = pd.read_csv(players_file)

# Validate and normalize
players_df = normalize_player_data(players_df)
players_df['player_id'] = generate_player_ids(players_df)

# Column mapping and validation
column_mapping = detect_column_mapping(players_df)
missing_columns = validate_required_columns(players_df, column_mapping)
```

**Prior Integration:**
```python
# Load baseline priors
team_priors = pd.read_csv('data/baseline/team_priors.csv')
player_priors = pd.read_csv('data/baseline/player_priors.csv')
boom_thresholds = json.load(open('data/baseline/boom_thresholds.json'))

# Join with user inputs
enhanced_players = join_with_priors(players_df, player_priors, team_priors)
```

### Monte Carlo Engine

**Core Simulation Loop:**
```python
def run_monte_carlo_simulation(players_df, priors, n_sims=10000, seed=12345):
    np.random.seed(seed)
    
    # Initialize output arrays
    sim_results = np.zeros((n_sims, len(players_df)))
    
    for sim_idx in range(n_sims):
        # 1. Sample team-level environment factors
        team_factors = sample_team_environment(team_priors, game_totals, spreads)
        
        # 2. Sample player usage within team context
        usage_samples = sample_player_usage(player_priors, team_factors)
        
        # 3. Sample efficiency and touchdowns
        efficiency_samples = sample_player_efficiency(player_priors, usage_samples)
        
        # 4. Convert to DK points with bonuses
        dk_points = convert_to_dk_scoring(usage_samples, efficiency_samples)
        
        # 5. Store results
        sim_results[sim_idx] = dk_points
    
    return sim_results
```

**Environment Sampling:**
```python
def sample_team_environment(team_priors, game_info):
    # Base team pace and pass rate
    base_pace = np.random.normal(team_priors['pace_mean'], team_priors['pace_std'])
    base_pass_rate = team_priors['neutral_xpass'] + team_priors['proe_neutral']
    
    # Game total and spread adjustments
    total_factor = game_info['total'] / 44.0  # Normalize to average
    pace_adjusted = base_pace * total_factor
    
    # Spread adjustments for game script
    spread_factor = 1.0 + (game_info['spread'] * 0.01)  # Slight adjustment
    pass_rate_adjusted = base_pass_rate * spread_factor
    
    return {
        'pace': pace_adjusted,
        'pass_rate': pass_rate_adjusted,
        'total_factor': total_factor
    }
```

### Output Generation

**Quantile Calculation:**
```python
def calculate_simulation_outputs(sim_results):
    # Core quantiles
    sim_mean = np.mean(sim_results, axis=0)
    floor_p10 = np.percentile(sim_results, 10, axis=0)
    p75 = np.percentile(sim_results, 75, axis=0)
    ceiling_p90 = np.percentile(sim_results, 90, axis=0)
    p95 = np.percentile(sim_results, 95, axis=0)
    
    # Standard deviation
    sim_std = np.std(sim_results, axis=0, ddof=1)
    
    return {
        'sim_mean': sim_mean,
        'floor_p10': floor_p10,
        'p75': p75,
        'ceiling_p90': ceiling_p90,
        'p95': p95,
        'sim_std': sim_std
    }
```

**Boom and Value Metrics:**
```python
def calculate_boom_and_value_metrics(sim_results, players_df, boom_thresholds):
    # Boom probability calculation
    boom_probs = []
    for i, player in players_df.iterrows():
        pos_boom = boom_thresholds['thresholds'][player['POS']]
        site_boost = max(1.20 * player.get('FPTS', 0), player.get('FPTS', 0) + 5)
        boom_cut = max(pos_boom, site_boost)
        boom_prob = np.mean(sim_results[:, i] >= boom_cut)
        boom_probs.append(boom_prob)
    
    # Value calculations
    value_per_1k = sim_mean / (players_df['SAL'] / 1000)
    ceil_per_1k = ceiling_p90 / (players_df['SAL'] / 1000)
    
    return boom_probs, value_per_1k, ceil_per_1k
```

## Stage 5: Output Processing

### Primary Artifacts Generation

**sim_players.csv:**
```python
def generate_sim_players_output(players_df, sim_outputs, boom_metrics):
    sim_players = pd.DataFrame({
        'player_id': players_df['player_id'],
        'PLAYER': players_df['PLAYER'],
        'POS': players_df['POS'],
        'TEAM': players_df['TEAM'],
        'OPP': players_df['OPP'],
        'sim_mean': sim_outputs['sim_mean'],
        'floor_p10': sim_outputs['floor_p10'],
        'p75': sim_outputs['p75'],
        'ceiling_p90': sim_outputs['ceiling_p90'],
        'p95': sim_outputs['p95'],
        'boom_prob': boom_metrics['boom_prob'],
        'rookie_fallback': players_df.get('rookie_fallback', False),
        'SAL': players_df.get('SAL', None)
    })
    return sim_players
```

**compare.csv:**
```python
def generate_compare_output(sim_players, players_df, value_metrics, boom_scores):
    compare = sim_players.copy()
    compare['site_fpts'] = players_df.get('FPTS', None)
    compare['delta_mean'] = compare['sim_mean'] - compare['site_fpts']
    compare['pct_delta'] = compare['delta_mean'] / np.abs(compare['site_fpts'])
    compare['beat_site_prob'] = value_metrics['beat_site_prob']
    compare['value_per_1k'] = value_metrics['value_per_1k']
    compare['ceil_per_1k'] = value_metrics['ceil_per_1k']
    compare['site_val'] = players_df.get('VAL', None)
    compare['RST%'] = players_df.get('RST%', None)
    compare['boom_score'] = boom_scores['boom_score']
    compare['dart_flag'] = boom_scores['dart_flag']
    return compare
```

### Diagnostics Generation

**Accuracy Metrics:**
```python
def generate_diagnostics(compare_df):
    # Exclude rookie fallback players
    non_rookies = compare_df[~compare_df['rookie_fallback']]
    
    diagnostics = {}
    for position in ['QB', 'RB', 'WR', 'TE', 'DST']:
        pos_data = non_rookies[non_rookies['POS'] == position]
        if len(pos_data) > 0:
            diagnostics[position] = {
                'count': len(pos_data),
                'mae': np.mean(np.abs(pos_data['delta_mean'])),
                'rmse': np.sqrt(np.mean(pos_data['delta_mean']**2)),
                'correlation': pos_data[['sim_mean', 'site_fpts']].corr().iloc[0,1],
                'coverage_p10_p90': coverage_calculation(pos_data)
            }
    
    return pd.DataFrame(diagnostics).T
```

**Flags Generation:**
```python
def generate_flags(compare_df, thresholds):
    flags = []
    
    # Large absolute deltas
    large_deltas = compare_df[np.abs(compare_df['delta_mean']) > thresholds['delta_threshold']]
    for _, player in large_deltas.iterrows():
        flags.append({
            'player_id': player['player_id'],
            'flag_type': 'large_delta',
            'flag_value': player['delta_mean'],
            'severity': 'warning'
        })
    
    # Extreme boom scores
    extreme_boom = compare_df[
        (compare_df['boom_score'] < 5) | (compare_df['boom_score'] > 95)
    ]
    for _, player in extreme_boom.iterrows():
        flags.append({
            'player_id': player['player_id'],
            'flag_type': 'extreme_boom_score',
            'flag_value': player['boom_score'],
            'severity': 'info'
        })
    
    return pd.DataFrame(flags)
```

## Stage 6: UI Integration

### Streamlit Pipeline

**File Upload and Processing:**
```python
# In app.py or streamlit_app.py
uploaded_file = st.file_uploader("Upload players.csv", type=['csv'])
if uploaded_file:
    players_df = pd.read_csv(uploaded_file)
    
    # Column mapping detection
    column_mapping = detect_columns(players_df)
    st.subheader("Column Mapping")
    display_mapping_table(column_mapping)
    
    # Validation warnings
    warnings = validate_input_data(players_df)
    if warnings:
        st.warning(f"Data issues detected: {warnings}")
```

**Simulation Execution:**
```python
# Simulation parameters
n_sims = st.number_input("Number of simulations", min_value=100, max_value=100000, value=10000)
seed = st.number_input("Random seed", value=12345)

if st.button("Run Simulation"):
    # Cache simulation results
    @st.cache_data
    def run_cached_simulation(file_bytes, n_sims, seed):
        return run_full_simulation(players_df, n_sims, seed)
    
    # Execute with caching
    sim_results = run_cached_simulation(uploaded_file.getvalue(), n_sims, seed)
    
    # Display results
    display_simulation_results(sim_results)
```

**Download Integration:**
```python
# Individual CSV downloads
st.download_button(
    label="Download sim_players.csv",
    data=sim_players.to_csv(index=False),
    file_name="sim_players.csv",
    mime="text/csv"
)

# ZIP bundle
zip_buffer = create_simulation_bundle(sim_players, compare, diagnostics, flags, metadata)
st.download_button(
    label="Download All (ZIP)",
    data=zip_buffer.getvalue(),
    file_name="simulator_outputs.zip",
    mime="application/zip"
)
```

## Performance and Scaling

### Computational Complexity

**Time Complexity:**
- Team metrics: O(T × P) where T = teams, P = players per team
- Player metrics: O(P × G) where P = players, G = games in baseline
- Simulation: O(S × P) where S = simulations, P = players in week
- Overall: O(S × P) dominated by simulation step

**Memory Usage:**
- Baseline data: ~100MB for 2-season warehouse
- Simulation arrays: ~50MB for 150 players × 10k sims
- UI caching: ~20MB for cached results
- Peak usage: ~200MB for full pipeline

### Optimization Opportunities

**Current Bottlenecks:**
1. Monte Carlo loops (can be vectorized further)
2. Quantile calculations (use approximate methods for speed)
3. File I/O (use efficient formats like Parquet)

**Future Enhancements:**
1. Numba JIT compilation for simulation loops
2. Parallel processing for position groups
3. GPU acceleration for large simulation counts
4. Incremental baseline updates instead of full rebuilds

## Error Handling and Recovery

### Pipeline Resilience

**Stage-Level Checkpoints:**
```python
# Save intermediate results for recovery
def save_checkpoint(stage_name, data, output_dir):
    checkpoint_file = f"{output_dir}/checkpoints/{stage_name}.pkl"
    with open(checkpoint_file, 'wb') as f:
        pickle.dump(data, f)

def load_checkpoint(stage_name, output_dir):
    checkpoint_file = f"{output_dir}/checkpoints/{stage_name}.pkl"
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file, 'rb') as f:
            return pickle.load(f)
    return None
```

**Graceful Degradation:**
- Missing salary data: Skip value calculations, show warnings
- No site FPTS: Skip comparison metrics, focus on projections only
- Insufficient historical data: Use position baselines with flags
- Network issues: Use cached nfl_data_py data if available

This pipeline overview provides the complete data flow from raw NFL data through simulation to user-facing outputs, ensuring reliable and scalable processing of fantasy football projections.