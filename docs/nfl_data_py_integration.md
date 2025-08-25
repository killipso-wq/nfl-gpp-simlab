# NFL Data Python Integration

This document specifies the adapter path for generating simulator-ready inputs from nfl_data_py when no site players.csv file is available.

## Overview

The adapter creates players.csv (and optional ownership.csv) from historical nfl_data_py data, providing an alternative input path to the main simulator workflow that typically uses site-provided projections and salaries.

## Adapter Command

### Basic Usage
```bash
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/
```

### With Rotowire Salaries
```bash
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/ --rotowire path/to/rotowire-NFL-players.csv
```

### Command Parameters

| Parameter | Required | Description | Example |
|-----------|----------|-------------|---------|
| `--season` | Yes | Target season for projections | `2025` |
| `--week` | Yes | Target week (1-18) | `1` |
| `--site` | Yes | Scoring system (dk, fd, sb) | `dk` |
| `--out` | Yes | Output directory for generated files | `data/` |
| `--rotowire` | No | Path to Rotowire salary CSV | `path/to/rotowire.csv` |

## Output Files

### Primary Output: players.csv

**Schema:**
```
player_id,name,team,position,proj_mean,proj_p75,proj_p90,game_id
```

**Example:**
```csv
player_id,name,team,position,proj_mean,proj_p75,proj_p90,game_id
BUF_QB_JOSHALLAN,Josh Allen,BUF,QB,22.4,26.8,31.2,MIA@BUF
KC_RB_ISAIAHPACHECO,Isiah Pacheco,KC,RB,14.6,18.2,22.1,KC@LV
DET_WR_AMONRASTBROWN,Amon-Ra St. Brown,DET,WR,16.8,20.4,24.7,DET@GB
```

**Field Descriptions:**
- `player_id`: Stable ID format (TEAM_POS_NORMALIZEDNAME)
- `name`: Display name for UI
- `team`: Player's team abbreviation
- `position`: QB, RB, WR, TE, DST
- `proj_mean`: Projected DK points (recency-weighted mean)
- `proj_p75`: 75th percentile from historical distribution
- `proj_p90`: 90th percentile (ceiling estimate)
- `game_id`: Format AWAY@HOME for the week

### Optional Output: ownership.csv

**Schema:**
```
player_id,own_proj
```

**Example:**
```csv
player_id,own_proj
BUF_QB_JOSHALLAN,28.5
KC_RB_ISAIAHPACHECO,15.2
DET_WR_AMONRASTBROWN,22.8
```

**Field Descriptions:**
- `player_id`: Matches players.csv player_id  
- `own_proj`: Projected ownership percentage (0-100)

## Stable ID System

### Player ID Format

**Pattern:** `TEAM_POS_NORMALIZEDNAME`

**Normalization Rules:**
1. Convert to uppercase
2. Remove all punctuation (periods, hyphens, apostrophes)
3. Drop common suffixes: JR, SR, II, III, IV, V
4. Collapse multiple spaces to single space
5. Remove all spaces for final ID

**Examples:**
```
"Josh Allen" → "JOSHALLAN"
"Amon-Ra St. Brown" → "AMONRASTBROWN" 
"D.K. Metcalf" → "DKMETCALF"
"Robert Griffin III" → "ROBERTGRIFFIN"
"Odell Beckham Jr." → "ODELLBECKHAM"
```

**Special Cases:**
- DST players: `TEAM_DST` (e.g., "BUF_DST")
- Name conflicts: Append jersey number if needed

### Game ID Format

**Pattern:** `AWAY@HOME`

**Examples:**
```
"MIA@BUF" (Miami at Buffalo)
"KC@LV" (Kansas City at Las Vegas)
"DET@GB" (Detroit at Green Bay)
```

**Derivation:**
- From nfl_data_py schedule for specified season/week
- Restricts output to teams with games that week
- Used for correlation modeling in simulator

## Schedule Restrictions

### Active Teams Filter
- Only include players from teams with games in the specified week
- Bye week teams automatically excluded
- Injured reserve players excluded based on latest status

### Game Mapping
- Schedule data from nfl_data_py for season/week
- Home/away designation from official NFL schedule
- Kickoff times used for ordering but not exposed in output

### Time Cutoffs
- Use most recent data available up to target week
- No future data leakage (no 2025 actuals in 2025 projections)
- Historical baseline limited to 2023-2024 seasons

## Projection Methodology

### Historical Data Window
- **Primary**: 2023-2024 regular season weeks 1-18
- **Recency weighting**: More recent games weighted higher
- **Sample size**: Minimum 4 games for stable projections

### Statistical Approach

**Base Projections:**
```python
# Recency-weighted mean with exponential decay
weights = np.exp(-0.1 * weeks_ago)  # Decay factor
proj_mean = np.average(dk_points, weights=weights)
```

**Quantile Estimation:**
```python
# Empirical quantiles from historical distribution
proj_p75 = np.percentile(dk_points, 75)
proj_p90 = np.percentile(dk_points, 90)
```

**Position Baselines** (for low-sample players):
```python
# Position-level medians as fallback
if game_count < 4:
    proj_mean = position_baseline_mean
    proj_p75 = position_baseline_p75
    proj_p90 = position_baseline_p90
```

### DK Scoring Integration
- All projections in DraftKings points
- Include passing/rushing/receiving bonuses
- Account for 0.5 PPR scoring
- DST scoring: sacks, turnovers, points allowed, yards allowed

## Ownership Heuristic

### Base Score Calculation
```python
# Proportional to projected points
base_score = proj_mean
```

### Game Total Adjustment
```python
# Boost for higher-total games (more plays/scoring)
game_total_factor = game_total / 44.0  # Normalize to ~44 point average
adjusted_score = base_score * game_total_factor
```

### Salary Integration (when Rotowire provided)

**Value Boost:**
```python
# Higher projection at lower salary gets boost
if salary > 0:
    value_factor = proj_mean / (salary / 1000)  # Points per $1k
    salary_boost = min(1.5, 1.0 + (value_factor - 2.0) * 0.1)
    adjusted_score *= salary_boost
```

**Position Salary Tiers:**
```python
# Adjust within position salary ranges
position_salary_median = np.median(position_salaries)
salary_tier_factor = salary / position_salary_median
# Lower salaries get slight ownership boost
```

### Normalization to Percentages
```python
# Normalize all scores to sum to 100
total_score = sum(all_player_scores)
own_proj = (player_score / total_score) * 100
```

## DST Handling

### MVP Implementation
- **Adapter**: DST skipped in initial MVP version
- **Simulator**: Supports DST when provided in input
- **Future enhancement**: Team defense stats → DST projections

### Extension Path
```python
# Future DST projection methodology
def generate_dst_projections(team, opponents, defense_stats):
    sack_rate = defense_stats['sack_rate_vs_position'] 
    turnover_rate = defense_stats['turnover_rate']
    points_allowed = defense_stats['points_allowed_mean']
    # Combine into DK DST scoring
```

## Error Handling and Validation

### Missing Data
- **No salary data**: Skip salary-based ownership adjustments
- **Insufficient games**: Use position baselines with warning flag
- **Missing players**: Log warnings but continue processing
- **Schedule conflicts**: Skip players from teams with no game

### Data Quality Checks
```python
# Validation before output
assert all(proj_mean >= 0), "Negative projections detected"
assert all(proj_p90 >= proj_p75), "Quantile ordering violation"
assert game_ids_valid(game_ids), "Invalid game_id format"
assert sum(own_proj) == pytest.approx(100, abs=0.1), "Ownership not normalized"
```

### Logging and Diagnostics
- Player count by position
- Teams included/excluded
- Games processed from schedule
- Warnings for data quality issues
- Runtime summary with key statistics

## Integration with Main Simulator

### File Compatibility
- Generated players.csv compatible with main simulator input schema
- Optional ownership.csv can be used for ownership-based boom scoring
- Same stable player_id format ensures consistent joins

### Workflow Integration
```bash
# Step 1: Generate from nfl_data_py
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/

# Step 2: Run simulator with generated files
python -m src.projections.run_week_from_site_players \
    --season 2025 --week 1 \
    --players-site data/players.csv \
    --team-priors data/baseline/team_priors.csv \
    --player-priors data/baseline/player_priors.csv \
    --boom-thresholds data/baseline/boom_thresholds.json \
    --sims 10000 \
    --out data/sim_week
```

### UI Integration (Planned)
- **Optimizer tab**: "Build from nfl_data_py" section
- **Auto-loading**: Generated files automatically loaded into UI
- **Parameter selection**: Season, week, site via form inputs
- **Status feedback**: Progress indicators and error messages

## Limitations and Notes

### Current Scope
- Regular season weeks 1-18 only (no playoffs in MVP)
- DraftKings scoring focus (FanDuel/SuperBet planned)
- DST projections not included in adapter MVP
- No injury/inactive status integration

### Data Dependencies
- Requires nfl_data_py installation and access
- Internet connection for initial data download
- Schedule data availability for target season/week

### Performance Considerations
- Processing time: ~30-60 seconds for full week
- Memory usage: ~100MB for full season data
- Caching: Historical data cached locally by nfl_data_py

## Future Enhancements

### Planned Improvements
1. **Multi-site support**: FanDuel, SuperBet scoring systems
2. **DST integration**: Team defense stats → DST projections
3. **Injury awareness**: Incorporate injury reports and status
4. **Weather integration**: Weather conditions for outdoor games
5. **Advanced ownership**: News sentiment, beat reporter updates

### Integration Roadmap
1. **MVP**: Basic projections and ownership heuristic
2. **V1.1**: DST support and multi-site scoring
3. **V1.2**: Injury and weather integration
4. **V2.0**: Advanced ownership modeling with external data sources