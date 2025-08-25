# Contributing to NFL GPP Sim Optimizer

This document contains developer guidance, CLI tools, and advanced usage for maintainers. **End users should use the Streamlit UI** as documented in README.md.

## Developer Notes

CLI and headless examples here are for optional/advanced usage by maintainers. CI and local development may use CLI for batch processing and backtesting, but end users should use the UI.

## CLI Tools and Commands

Dependencies:
- pip install nfl_data_py pandas numpy pyarrow python-slugify

### Build Baseline (2023–2024)

Purpose: compute metrics and build team/player priors

```bash
python scripts/build_baseline.py --start 2023 --end 2024 --out data
```

### Build Boom Thresholds from History

Purpose: set position-level boom cutoffs (default p90)

```bash
python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90
```

### Run a 2025 Week from Site players.csv

Purpose: full simulator run using your roster/OU/SPRD/SAL/RST%

```bash
python -m src.projections.run_week_from_site_players \
    --season 2025 --week 1 \
    --players-site path/to/players_2025.csv \
    --team-priors data/baseline/team_priors.csv \
    --player-priors data/baseline/player_priors.csv \
    --boom-thresholds data/baseline/boom_thresholds.json \
    --sims 10000 \
    --out data/sim_week
```

### Adapter: Generate players.csv from nfl_data_py

Purpose: when no site players.csv is available; produces simulator-ready players.csv

```bash
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/
```

With Rotowire salaries:
```bash
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/ --rotowire path/to/rotowire-NFL-players.csv
```

Outputs:
- data/players.csv: player_id, name, team, position, proj_mean, proj_p75, proj_p90, game_id  
- data/ownership.csv (optional): player_id, own_proj (0–100)

Adapter notes:
- Uses 2023–2024 weekly logs; projections are recency-weighted DK points with p75/p90 from empirical quantiles; position baselines for tiny samples
- Schedule restricts to teams active that week; game_id = AWAY@HOME
- DST initially skipped in adapter MVP (can extend later). Simulator itself includes DST

## Local Development Runbook

```bash
# Install dependencies
pip install -r requirements.txt

# Build baseline once
python scripts/build_baseline.py --start 2023 --end 2024 --out data
python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90

# Run a 2025 week from your site players.csv
python -m src.projections.run_week_from_site_players \
    --season 2025 --week 1 \
    --players-site path/to/players.csv \
    --team-priors data/baseline/team_priors.csv \
    --player-priors data/baseline/player_priors.csv \
    --boom-thresholds data/baseline/boom_thresholds.json \
    --sims 10000 \
    --out data/sim_week
```

## Adapter Path (Optional)

For generating inputs when you don't have a site players.csv:

```bash
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/ [--rotowire path/to/rotowire.csv]
```

Upload the produced data/players.csv (and ownership.csv if desired) to the Simulator/Optimizer flows.

## Testing and Validation

- Smoke tests: Deterministic runs with fixed seed; compare outputs stable across runs
- Unit tests for sampling distributions and seed determinism (planned)
- Accuracy diagnostics: diagnostics_summary.csv: MAE/RMSE/corr vs site FPTS; coverage of [p10, p90]; rookies excluded by default
- Sanity checks: beat_site_prob distribution; boom_prob not degenerate; flags.csv shows plausible outliers for review
- Backtesting (follow-up): Run a 2023–2024 holdout week; examine PIT histograms, reliability curves, CRPS/Brier

## File Structure (Development)

```
app.py / streamlit_app.py — Streamlit entry point/UI tabs
simulator.py — Monte Carlo engine glue for Streamlit
src/
  ingest/
    nfl_data_py_to_simulator.py — adapter CLI (players.csv + optional ownership.csv)
    site_players.py — loader for your site file schema
    name_normalizer.py — normalize names; build player_id
    scoring.py — DK scoring function for game logs
  metrics/
    sources.py, prep.py, team_metrics.py, player_metrics.py, pipeline.py — metrics warehouse for 2023–2024
  projections/
    prior_builder.py — build team/player priors
    run_week_from_site_players.py — main CLI for 2025 sim using your players.csv
    value_metrics.py — value per $1k, ceiling value, deltas vs site
    boom_score.py — boom_prob, boom_score (1–100), dart_flag
    diagnostics.py — MAE/RMSE/corr/coverage, flags
  sim/
    game_simulator.py — core Monte Carlo, environment/usage/efficiency/correlation sampling
scripts/
  build_baseline.py — create priors from 2023–2024
  generate_metrics.py — build team/player/game metrics from nfl_data_py
  build_boom_thresholds.py — compute boom cutoffs from 2023–2024
```

## Requirements

- Python 3.10+
- pip install -r requirements.txt (includes: nfl_data_py, pandas, numpy, pyarrow, python-slugify, streamlit)
- Optional: virtualenv (.venv) for local runs

## Acceptance Criteria for Development

- Baseline (2023–2024) priors build without errors; files saved to data/baseline
- Simulator produces sim_players.csv, compare.csv, diagnostics_summary.csv, flags.csv
- Floor p10, Ceiling p90, p75/p95 present; Boom metrics present (boom_prob, boom_score, dart_flag)
- Value metrics present: value_per_1k, ceil_per_1k; SAL and RST% used if available
- Compare to site FPTS (if present): delta_mean, pct_delta, beat_site_prob; diagnostics include MAE/RMSE/corr/coverage (rookies excluded)
- Adapter CLI: Generates players.csv and (optionally) ownership.csv from nfl_data_py, using schedule and 2023–2024 baseline
- Stable player_id format and game_id mapping