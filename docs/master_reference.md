# NFL GPP Sim Optimizer — Master Reference

**Sources of Truth:**
- README on main (primary reference)
- Issue #15 (build scaffolding and Python focus)
- Issue #17 (CI enhancements and maintenance)
- [docs/research/monte_carlo_football.pdf](research/monte_carlo_football.pdf) (methodology source)

This document consolidates authoritative commands, outputs, UI behavior, and architecture from the README master reference. Use this as the single source of truth for implementation scope, acceptance criteria, and technical specifications.

## Scope and Goals

- Build Monte Carlo projections (mean, floor, ceiling) and value metrics from 2023–2024 nfl_data_py baseline
- Compare projections to site projections from 2025 players.csv (delta, coverage, accuracy)
- Identify low-owned upside "darts" via Boom score (1–100) and dart_flag
- Provide robust Streamlit UI: upload players.csv, run simulations, analyze outputs, download artifacts
- Offer adapter path to generate players.csv from nfl_data_py when no site file available

## Commands

### Baseline Building (2023–2024)
```bash
# Build team/player priors from nfl_data_py
python scripts/build_baseline.py --start 2023 --end 2024 --out data

# Build boom thresholds (default p90)
python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90
```

### Simulator (2025 Week)
```bash
# Run simulation from site players.csv
python -m src.projections.run_week_from_site_players \
    --season 2025 --week 1 \
    --players-site path/to/players_2025.csv \
    --team-priors data/baseline/team_priors.csv \
    --player-priors data/baseline/player_priors.csv \
    --boom-thresholds data/baseline/boom_thresholds.json \
    --sims 10000 \
    --out data/sim_week
```

### Adapter (Generate from nfl_data_py)
```bash
# Generate players.csv and optional ownership.csv
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/

# With Rotowire salaries
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/ --rotowire path/to/rotowire-NFL-players.csv
```

### Streamlit UI
```bash
streamlit run app.py
```

## Outputs

### Primary Artifacts
- **sim_players.csv**: player_id, PLAYER, POS, TEAM, OPP, sim_mean, floor_p10, p75, ceiling_p90, p95, boom_prob, rookie_fallback, SAL
- **compare.csv**: Adds site_fpts, delta_mean, pct_delta, beat_site_prob, value_per_1k, ceil_per_1k, site_val, RST%, boom_score, dart_flag
- **diagnostics_summary.csv**: Per-position MAE, RMSE, Pearson corr, coverage_p10_p90, counts (excludes rookie_fallback)
- **flags.csv**: Largest discrepancies and notable conditions
- **metadata.json**: sims, seed, run_id, git commit, column mapping, counts, diagnostics
- **simulator_outputs.zip**: Bundle of all above files

### Adapter Outputs
- **players.csv**: player_id, name, team, position, proj_mean, proj_p75, proj_p90, game_id
- **ownership.csv**: player_id, own_proj (0–100) [optional]

## Stable IDs

### Player ID Format
- **Pattern**: `TEAM_POS_NORMALIZEDNAME`
- **NORMALIZEDNAME**: uppercase, punctuation removed, suffixes (JR/SR/II/III/IV/V) dropped, spaces collapsed
- **DST**: Reserved as `TEAM_DST` (adapter MVP skips DST; simulator supports DST)

### Game ID Format
- **Pattern**: `AWAY@HOME` (derived from schedule for the week)

## Architecture Overview

### 1. Metrics Warehouse (2023–2024)
- **Inputs**: nfl_data_py weekly data, optional play-by-play for EPA/WP/CP features
- **Outputs**: team_week.csv, player_week.csv, game_week.csv metrics
- **Purpose**: Feed priors and inform simulation distributions

### 2. Priors Building
- **Team priors**: plays per game, pace, neutral_xpass, proe_neutral, EPA/play
- **Player priors**: usage shares, efficiency rates, position-specific metrics
- **Shrinkage**: Empirical-Bayes toward position/league means for stability

### 3. Simulator Engine
- **Environment**: OU/SPRD/ML/TM/P nudge team expectations per game
- **Sampling**: Team/game shocks for correlation, usage via Dirichlet/Beta, efficiency via Normal/Lognormal
- **Positions**: QB, RB, WR, TE, DST with DK scoring and bonuses
- **Rookies**: Center on site FPTS, position variance, clamp to zero, flagged

### 4. UI Integration
- **Streamlit**: File upload, column mapping, caching, previews, downloads
- **Optimizer**: Planned GPP Presets section with constraint application

## Simulator Behavior

### Input Processing
- **Column mapping**: Auto-detect synonyms (Salary/dk_salary, OWN/OWN%, Value/Pts/$)
- **Normalization**: POS "D" → "DST", RST% ≤1 → fraction×100, else percent
- **Rookies**: No 2023–2024 priors → use site FPTS 100% as sim mean, position-calibrated variance

### Monte Carlo Engine
- **Correlation**: QB-receiver through team/game shocks and catch-rate coupling
- **Environment**: Base pass rate = neutral_xpass + proe_neutral, OU/SPRD nudges
- **Distributions**: Position-specific sampling with DK scoring bonuses
- **Determinism**: Fixed seed for reproducibility across runs

### Output Generation
- **Quantiles**: p10 (floor), p75, p90 (ceiling), p95 from simulation draws
- **Boom metrics**: boom_prob, beat_site_prob, boom_score (1-100), dart_flag
- **Value metrics**: value_per_1k, ceil_per_1k based on salary when available

## Methodology Mapping

See [docs/research/monte_carlo_methodology.md](research/monte_carlo_methodology.md) for detailed mapping between research PDF concepts and code implementation.

**Key Estimators:**
- Mean, unbiased variance, standard deviation, standard error
- Quantiles: p10, p75, p90, p95
- Normal-approximation confidence intervals when applicable

**Determinism Strategy:**
- base_seed and child seeds for reproducible draws
- Notes on dtype/rounding stability across operating systems

## UI Specifications

### Simulator Tab
- **Inputs**: File uploader for players.csv, Sims count, Seed value
- **Mapping**: Column detection table with warnings for missing/invalid fields
- **Caching**: Results cached for identical inputs, "Clear cached results" button
- **Previews**: sim_players and compare tables with position filters and delta sorting
- **Downloads**: 4 individual CSV buttons + "Download all (zip)" with metadata.json
- **Methodology**: Link to docs/research/monte_carlo_football.pdf

### Optimizer Tab (Planned)
- **Build Section**: Generate players.csv/sims.csv from nfl_data_py with optional salaries
- **GPP Presets**: One-click constraint application using latest sim outputs
- **Integration**: Auto-load generated files into Optimizer inputs

## Optimizer Planning (GPP Strategy Blueprint)

See [docs/gpp_strategy_blueprint.md](gpp_strategy_blueprint.md) for full specification.

**Preset Structure:**
- Small/Mid/Large contest size presets
- Stacking rules: QB+1/QB+2, bring-back 0-1
- Ownership bands, boom thresholds, value requirements
- Constraint application before optimization

## Adapter Path

See [docs/nfl_data_py_integration.md](nfl_data_py_integration.md) for detailed adapter specifications.

**Command Pattern:**
```bash
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/ [--rotowire path/to/rotowire.csv]
```

**Output Format:**
- Stable player_id and game_id mapping
- Schedule restrictions to active teams for week
- Ownership heuristic with salary adjustments when available

## Diagnostics and QA

### Accuracy Metrics
- **Per-position**: MAE, RMSE, Pearson correlation vs site FPTS
- **Coverage**: Percentage where site FPTS lies within [p10, p90] interval
- **Exclusions**: Rookie fallback players excluded from accuracy metrics

### Sanity Checks
- **Distributions**: boom_prob and beat_site_prob distributions not degenerate
- **Outliers**: flags.csv highlights plausible outliers for review
- **Determinism**: Seed reproducibility confirmed across runs

### Quality Control
- **Missing data**: Column mapping warnings for required fields
- **Invalid positions**: Unknown positions mapped to UNK (skipped from metrics)
- **Data issues**: Flagged in flags.csv for manual review

## Requirements and Environment

### Dependencies
- Python 3.10+
- Core: nfl_data_py, pandas, numpy, pyarrow, python-slugify, streamlit
- Dev: pytest, coverage, ruff, mypy (per CI configuration)

### Deployment
- **Render service**: Connected to GitHub repository
- **Start command**: `streamlit run app.py`
- **Environment**: `STREAMLIT_SERVER_MAX_UPLOAD_SIZE=300` (optional)
- **Deploy process**: Manual Deploy → Clear build cache & deploy

## Acceptance Criteria

### Baseline Requirements
- [ ] Baseline builds without errors; priors and thresholds in data/baseline
- [ ] Team and player priors properly formatted and complete

### Simulator Requirements  
- [ ] All output CSVs generated: sim_players, compare, diagnostics_summary, flags
- [ ] Quantiles present: floor_p10, ceiling_p90, p75, p95
- [ ] Boom metrics implemented: boom_prob, boom_score, dart_flag
- [ ] Value metrics present: value_per_1k, ceil_per_1k
- [ ] Compare functionality: delta_mean, pct_delta, beat_site_prob when site FPTS available

### UI Requirements
- [ ] Column mapping table with warnings displayed
- [ ] Caching functionality with clear cache button
- [ ] Preview tables with position filters and sorting
- [ ] 4 CSV downloads + ZIP bundle with metadata.json
- [ ] Methodology link to research PDF functional

### Adapter Requirements
- [ ] Generates players.csv and optional ownership.csv from nfl_data_py
- [ ] Stable player_id format and game_id mapping implemented
- [ ] Schedule restrictions and ownership heuristics working

## Roadmap

### Current MVP Scope
- [x] Documentation structure (this PR)
- [ ] Baseline and thresholds implementation
- [ ] Simulator core engine and outputs
- [ ] Streamlit Simulator tab with full functionality
- [ ] Adapter path for nfl_data_py integration

### Post-MVP Enhancements
- Opponent adjustments (defense vs position), home/away, weather
- Richer dependence model (copulas) and scenario toggles
- Hierarchical priors (role/archetype) for low-sample players
- Calibration/backtests with CRPS/Brier and reliability plots
- Performance scaling (100k–500k trials)
- Optimizer GPP Presets integration
- DST enhancements in adapter path

## References

### Documentation Links
- [Pipeline Overview](pipeline.md) - End-to-end data flow
- [Metrics Catalog](metrics_catalog.md) - Warehouse metrics inventory
- [Compare Projections](compare_projections.md) - Analysis workflow
- [NFL Data Integration](nfl_data_py_integration.md) - Adapter specifications
- [GPP Strategy Blueprint](gpp_strategy_blueprint.md) - Optimizer presets

### Research and Methodology
- [Monte Carlo Methodology](research/monte_carlo_methodology.md) - PDF summary and code mapping
- [Monte Carlo Football PDF](research/monte_carlo_football.pdf) - Primary methodology source

### Implementation Status
- Current branch: main (single source of truth)
- Issue references: #15 (Python focus), #17 (CI enhancements)
- Next implementations: Baseline scripts, Simulator engine, UI tabs