# Compare Projections - Analysis Workflow

This document explains how to analyze the key output files from the NFL GPP Simulator: sim_players.csv, compare.csv, diagnostics_summary.csv, and flags.csv. It provides interpretations, workflows, and best practices for reviewing simulation results.

## Overview

The simulator produces four primary analysis files, each serving a specific purpose in the projection review workflow:

1. **sim_players.csv** - Core Monte Carlo projections and quantiles
2. **compare.csv** - Comparison with site projections and value metrics 
3. **diagnostics_summary.csv** - Accuracy and coverage statistics
4. **flags.csv** - Notable outliers and data quality issues

This document provides a systematic approach to reviewing these outputs for lineup construction, strategy development, and model validation.

## sim_players.csv Analysis

### Core Projection Fields

**Key Metrics to Review:**
```
sim_mean          # Primary projection (expected value)
floor_p10         # Downside protection (10th percentile)
ceiling_p90       # Upside potential (90th percentile)
p75               # Solid performance threshold
p95               # Spike week potential
boom_prob         # Probability of boom performance
```

### Analysis Workflow

**1. Position-Level Overview:**
```python
# Group by position to understand ranges
position_summary = sim_players.groupby('POS').agg({
    'sim_mean': ['count', 'mean', 'std', 'min', 'max'],
    'ceiling_p90': ['mean', 'max'],
    'boom_prob': ['mean', 'max']
})
```

**2. Team-Level Analysis:**
```python
# Identify high-projected team stacks
team_summary = sim_players.groupby('TEAM').agg({
    'sim_mean': 'sum',  # Total team projection
    'ceiling_p90': 'sum',  # Team ceiling
    'boom_prob': 'mean'  # Average boom probability
}).sort_values('sim_mean', ascending=False)
```

**3. Game-Level Totals:**
```python
# Extract game totals for correlation analysis
sim_players['game_id'] = sim_players['OPP'] + '@' + sim_players['TEAM']
game_totals = sim_players.groupby('game_id')['sim_mean'].sum()
```

### Key Interpretation Points

**Projection Ranges by Position:**
- **QB**: sim_mean 18-32, ceiling_p90 25-40
- **RB**: sim_mean 8-22, ceiling_p90 15-35  
- **WR**: sim_mean 6-24, ceiling_p90 12-38
- **TE**: sim_mean 4-18, ceiling_p90 8-28
- **DST**: sim_mean 2-15, ceiling_p90 6-22

**Quality Indicators:**
- **Tight ranges**: More predictable players (floor > 8 for skill positions)
- **Wide ranges**: High volatility (ceiling_p90 / floor_p10 > 3.0)
- **High boom_prob**: Upside plays (boom_prob > 0.25)

## compare.csv Analysis

### Value and Efficiency Metrics

**Primary Analysis Fields:**
```
delta_mean        # sim_mean - site_fpts (projection difference)
pct_delta         # Percentage difference vs site
beat_site_prob    # P(sim_result >= site_fpts)
value_per_1k      # Points per $1k salary
ceil_per_1k       # Ceiling per $1k salary
boom_score        # Composite boom metric (1-100)
dart_flag         # Low-owned, high-boom plays
```

### Analysis Workflow

**1. Value Identification:**
```python
# Top value plays by position
value_plays = compare.groupby('POS').apply(
    lambda x: x.nlargest(5, 'value_per_1k')[['PLAYER', 'value_per_1k', 'sim_mean', 'SAL']]
)

# Ceiling value for tournaments
ceiling_value = compare.groupby('POS').apply(
    lambda x: x.nlargest(5, 'ceil_per_1k')[['PLAYER', 'ceil_per_1k', 'ceiling_p90', 'SAL']]
)
```

**2. Projection Disagreement Analysis:**
```python
# Largest positive deltas (sim higher than site)
positive_deltas = compare[compare['delta_mean'] > 0].nlargest(10, 'delta_mean')

# Largest negative deltas (sim lower than site)  
negative_deltas = compare[compare['delta_mean'] < 0].nsmallest(10, 'delta_mean')

# High confidence disagreements
high_confidence = compare[
    (np.abs(compare['pct_delta']) > 0.15) &  # 15%+ difference
    (compare['beat_site_prob'] > 0.7)  # High confidence
]
```

**3. Boom and Dart Analysis:**
```python
# Tournament upside plays
tournament_plays = compare[
    (compare['boom_score'] >= 70) &
    (compare['RST%'] <= 15)  # Lower ownership
].sort_values('boom_score', ascending=False)

# Pure dart plays (low-owned, high-boom)
dart_plays = compare[compare['dart_flag'] == True]

# Ownership vs boom score correlation
ownership_boom = compare.plot.scatter(x='RST%', y='boom_score', alpha=0.6)
```

### Value Thresholds by Position

**Cash Game Value (value_per_1k):**
- **QB**: 2.8+ excellent, 2.4+ good, 2.0+ playable
- **RB**: 3.2+ excellent, 2.8+ good, 2.4+ playable
- **WR**: 3.0+ excellent, 2.6+ good, 2.2+ playable
- **TE**: 2.6+ excellent, 2.2+ good, 1.8+ playable
- **DST**: 3.5+ excellent, 3.0+ good, 2.5+ playable

**Tournament Boom Thresholds:**
- **boom_score 85+**: Elite upside, consider regardless of ownership
- **boom_score 70-84**: Strong upside, prefer under 20% ownership
- **boom_score 50-69**: Moderate upside, need under 10% ownership
- **boom_score <50**: Cash game focus unless extreme value

## diagnostics_summary.csv Analysis

### Model Accuracy Assessment

**Key Accuracy Metrics:**
```
mae               # Mean Absolute Error vs site projections
rmse              # Root Mean Square Error vs site projections  
correlation       # Pearson correlation with site projections
coverage_p10_p90  # % of site projections within [p10, p90] interval
```

### Analysis Workflow

**1. Overall Model Performance:**
```python
# Load diagnostics
diagnostics = pd.read_csv('diagnostics_summary.csv', index_col='position')

# Overall accuracy summary
overall_stats = {
    'Total Players': diagnostics['count'].sum(),
    'Weighted MAE': np.average(diagnostics['mae'], weights=diagnostics['count']),
    'Weighted Correlation': np.average(diagnostics['correlation'], weights=diagnostics['count']),
    'Average Coverage': diagnostics['coverage_p10_p90'].mean()
}
```

**2. Position-Level Performance:**
```python
# Position accuracy comparison
accuracy_comparison = diagnostics[['mae', 'rmse', 'correlation', 'coverage_p10_p90']].round(3)
print(accuracy_comparison)

# Best/worst performing positions
best_position = diagnostics.loc[diagnostics['correlation'].idxmax()]
worst_position = diagnostics.loc[diagnostics['correlation'].idxmin()]
```

**3. Coverage Analysis:**
```python
# Coverage quality assessment
good_coverage = diagnostics[diagnostics['coverage_p10_p90'].between(0.75, 0.85)]
poor_coverage = diagnostics[diagnostics['coverage_p10_p90'] < 0.70]

# Identify calibration issues
over_confident = diagnostics[diagnostics['coverage_p10_p90'] < 0.75]  # Too narrow
under_confident = diagnostics[diagnostics['coverage_p10_p90'] > 0.85]  # Too wide
```

### Performance Interpretation

**Accuracy Benchmarks:**
- **MAE < 3.0**: Excellent accuracy for skill positions
- **MAE 3.0-5.0**: Good accuracy, usable for most purposes
- **MAE > 5.0**: Poor accuracy, investigate data issues

**Correlation Targets:**
- **r > 0.70**: Strong agreement with site projections
- **r 0.50-0.70**: Moderate agreement, some systematic differences
- **r < 0.50**: Weak agreement, significant methodological differences

**Coverage Calibration:**
- **80% ± 5%**: Well-calibrated intervals
- **< 75%**: Over-confident (intervals too narrow)
- **> 85%**: Under-confident (intervals too wide)

## flags.csv Analysis

### Data Quality Review

**Flag Types:**
```
large_delta       # Projection differences exceeding thresholds
extreme_boom      # Boom scores in extreme ranges (0-5 or 95-100)
missing_data      # Players with incomplete information
unknown_position  # Positions not in standard set
data_quality      # Other data integrity issues
```

### Analysis Workflow

**1. Flag Priority Assessment:**
```python
# Load and categorize flags
flags = pd.read_csv('flags.csv')

# Count by severity and type
flag_summary = flags.groupby(['flag_type', 'severity']).size().unstack(fill_value=0)

# High-priority flags requiring review
high_priority = flags[flags['severity'].isin(['error', 'warning'])]
```

**2. Large Delta Investigation:**
```python
# Players with significant projection differences
large_deltas = flags[flags['flag_type'] == 'large_delta']

# Join with compare data for context
delta_analysis = large_deltas.merge(
    compare[['player_id', 'PLAYER', 'POS', 'sim_mean', 'site_fpts', 'RST%']], 
    on='player_id'
)

# Sort by magnitude of difference
delta_analysis = delta_analysis.reindex(
    delta_analysis['flag_value'].abs().sort_values(ascending=False).index
)
```

**3. Data Quality Issues:**
```python
# Missing salary data
missing_sal = flags[flags['flag_type'] == 'missing_salary']

# Unknown positions  
unknown_pos = flags[flags['flag_type'] == 'unknown_position']

# Extreme projections
extreme_proj = flags[flags['flag_type'] == 'extreme_projection']
```

### Flag Resolution Guidelines

**Large Delta Flags:**
1. **Review player news**: Injury, role change, coaching decisions
2. **Check data quality**: Ensure correct player matching and stats
3. **Validate inputs**: Confirm salary, ownership, game info accuracy
4. **Consider methodology**: Different scoring systems or usage projections

**Extreme Boom Flags:**
1. **Low boom scores (0-5)**: Check for injury, inactive status, or data errors
2. **High boom scores (95-100)**: Validate ownership data and salary alignment
3. **Review context**: Game script, weather, matchup factors

**Missing Data Flags:**
1. **Prioritize by position**: Focus on skill positions first
2. **Research missing info**: Check alternate data sources
3. **Document assumptions**: Note any manual adjustments made

## Integrated Analysis Workflow

### Step 1: High-Level Review (5 minutes)

```python
# Quick overview of simulation results
print("=== SIMULATION OVERVIEW ===")
print(f"Total Players: {len(sim_players)}")
print(f"By Position: {sim_players['POS'].value_counts()}")
print(f"Accuracy (overall): MAE={diagnostics['mae'].mean():.2f}, r={diagnostics['correlation'].mean():.3f}")
print(f"Flags: {len(flags)} total, {len(flags[flags['severity']=='warning'])} warnings")
```

### Step 2: Value and Upside Identification (10 minutes)

```python
# Top value plays for cash games
print("\n=== TOP VALUE PLAYS ===")
top_value = compare.nlargest(15, 'value_per_1k')[['PLAYER', 'POS', 'value_per_1k', 'sim_mean', 'SAL']]
print(top_value)

# Top tournament upside
print("\n=== TOURNAMENT UPSIDE ===") 
tournament = compare[compare['boom_score'] >= 70].nlargest(15, 'boom_score')[
    ['PLAYER', 'POS', 'boom_score', 'RST%', 'ceil_per_1k']
]
print(tournament)
```

### Step 3: Model Validation (5 minutes)

```python
# Check for systematic issues
print("\n=== MODEL VALIDATION ===")

# Position-level accuracy
print("Accuracy by Position:")
print(diagnostics[['mae', 'correlation', 'coverage_p10_p90']])

# Coverage calibration
poor_coverage = diagnostics[diagnostics['coverage_p10_p90'] < 0.75]
if len(poor_coverage) > 0:
    print(f"\nPoor Coverage Warning: {poor_coverage.index.tolist()}")

# High-priority flags
critical_flags = flags[flags['severity'] == 'error']
if len(critical_flags) > 0:
    print(f"\nCritical Flags: {len(critical_flags)} require immediate attention")
```

### Step 4: Strategic Insights (10 minutes)

```python
# Team stack analysis
print("\n=== TEAM STACK ANALYSIS ===")
team_projections = sim_players.groupby('TEAM').agg({
    'sim_mean': 'sum',
    'ceiling_p90': 'sum',
    'boom_prob': 'mean'
}).round(2).sort_values('sim_mean', ascending=False)
print(team_projections.head(10))

# Game environment analysis
print("\n=== HIGH-SCORING GAME TARGETS ===")
# This would require game totals from schedule/input data
```

### Step 5: Flag Resolution (Variable time)

```python
# Review high-impact flags
print("\n=== FLAGS REQUIRING REVIEW ===")

# Large projection differences
large_delta_flags = flags[
    (flags['flag_type'] == 'large_delta') & 
    (np.abs(flags['flag_value']) > 5)
]

for _, flag in large_delta_flags.iterrows():
    player_info = compare[compare['player_id'] == flag['player_id']].iloc[0]
    print(f"{player_info['PLAYER']} ({player_info['POS']}): "
          f"Sim={player_info['sim_mean']:.1f}, Site={player_info['site_fpts']:.1f}, "
          f"Delta={flag['flag_value']:.1f}")
```

## Export and Integration

### Filtered Outputs for Lineup Construction

```python
# Cash game export (value-focused)
cash_export = compare[
    (compare['value_per_1k'] >= 2.5) &
    (compare['sim_mean'] >= 8.0)  # Minimum projection threshold
][['PLAYER', 'POS', 'TEAM', 'sim_mean', 'value_per_1k', 'SAL']].sort_values('value_per_1k', ascending=False)

cash_export.to_csv('cash_targets.csv', index=False)

# Tournament export (upside-focused)  
tournament_export = compare[
    (compare['boom_score'] >= 60) &
    (compare['RST%'] <= 25)  # Ownership cap
][['PLAYER', 'POS', 'TEAM', 'boom_score', 'ceil_per_1k', 'RST%', 'dart_flag']].sort_values('boom_score', ascending=False)

tournament_export.to_csv('tournament_targets.csv', index=False)
```

### Integration with Optimizer Tools

```python
# Format for optimizer input
optimizer_input = compare[['PLAYER', 'POS', 'TEAM', 'sim_mean', 'ceiling_p90', 'SAL', 'value_per_1k', 'boom_score']].copy()
optimizer_input.columns = ['Name', 'Position', 'Team', 'Projection', 'Ceiling', 'Salary', 'Value', 'Boom']

optimizer_input.to_csv('optimizer_input.csv', index=False)
```

This comprehensive analysis workflow ensures thorough review of simulation outputs, identification of value and upside opportunities, validation of model performance, and preparation of actionable insights for lineup construction and strategy development.