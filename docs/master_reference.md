# NFL GPP Sim Optimizer — Master Reference (Scope, Design, UI, Files)

This is the single source of truth for what we are building:
- End-to-end baseline (2023–2024) from nfl_data_py for priors.
- A Monte Carlo simulator for the 2025 slate driven by your players.csv.
- Robust outputs (boom/value/diagnostics) with deterministic seeding.
- A Streamlit UI that runs everything without needing CLI for end users.
- An optional adapter to generate simulator-ready inputs from nfl_data_py.

Use this document to:
- Verify scope and acceptance criteria
- Find exact commands and where outputs go (for developers)
- Understand how priors, sim, diagnostics, and UI integrate
- Recover quickly if we get lost (single, canonical reference)

Important: README.md stays UI-first (minimal commands for local runs). All detailed commands and developer notes live here.

## Goals
- Build our own projections (mean, floor, ceiling) and value metrics from a Monte Carlo simulator leveraging 2023–2024 data.
- Compare to site 2025 projections from your players.csv (delta, coverage, accuracy).
- Identify low-owned upside darts via Boom score (1–100) and dart_flag.
- Streamlit UI: upload players.csv, click run, analyze, download outputs/ZIP.
- Optional: produce players.csv (and ownership.csv) directly from nfl_data_py.

## Data sources and seasons
- Historical: nfl_data_py (nflfastR)
  - Weekly stats (2023–2024 baseline)
  - Optional play-by-play for richer features (EPA/WP/CP/xpass/XYAC)
  - Schedules to derive game_id and limit to active teams/week
- 2025 slate and players:
  - Your players.csv defines actives, teams/opponents, and site fields (FPTS, SAL, RST%, O/U, SPRD, VAL, etc.)

Why 2023–2024 baseline:
- Avoid leakage from 2025
- Stable, recent window for priors and calibration

## Inputs — players.csv (from the site)
Required columns:
- PLAYER: Player name (normalized internally)
- POS: Position; D → mapped to DST
- TEAM: Player team
- OPP: Opponent team

Supported columns (optional but used when present):
- FPTS: Site projection (used for compare and rookie fallback center)
- SAL: Salary
- RST%: Projected ownership (format: if ≤1 treat as fraction×100; if >1 treat as percent)
- O/U: Game total (Vegas); environment hint
- SPRD: Spread; environment hint
- ML: Moneyline; optional environment hint
- TM/P: Implied team points
- VAL: Site "value" metric (assumed points per $1k unless specified)

Column mapping:
- We autodetect synonyms (Salary, dk_salary; OWN, OWN%; Value, Pts/$).
- Streamlit shows a "Detected column mapping" table with warnings for missing/malformed fields.

Rookies/new players policy:
- If no 2023–2024 priors for a player, center on site FPTS as sim mean; apply position-calibrated variance; clamp to 0; mark rookie_fallback=True.
- Exclude rookie_fallback rows from MAE/RMSE/corr/coverage metrics but keep them in compare.csv and flags.

## Outputs (primary artifacts)
Written to: data/sim_week/{season}_w{week}_{timestamp}/ and zipped as simulator_outputs.zip

- sim_players.csv (our projections)
  - Columns: player_id, PLAYER, POS, TEAM, OPP, sim_mean, floor_p10, p75, ceiling_p90, p95, boom_prob, rookie_fallback, SAL (if present)
- compare.csv (joined with site fields)
  - Adds: site_fpts, delta_mean, pct_delta, beat_site_prob, value_per_1k, ceil_per_1k, site_val (if provided), RST%, boom_score (1–100), dart_flag
- diagnostics_summary.csv
  - Per-position and overall MAE, RMSE, Pearson corr, coverage_p10_p90, counts; excludes rookie_fallback by default; includes fallback counts
- flags.csv
  - Largest discrepancies and notable conditions (e.g., |delta| or pct_delta thresholds), and data issues
- metadata.json
  - sims, seed, run_id, column mapping, counts, file hashes, optional git commit and diagnostics summary row
- simulator_outputs.zip
  - Bundle of all the above

## Stable IDs and naming
- player_id: TEAM_POS_NORMALIZEDNAME
  - NORMALIZEDNAME = uppercase, punctuation removed, suffixes (JR/SR/II/III/IV/V) dropped, spaces collapsed
  - DST reserved as TEAM_DST
- game_id: AWAY@HOME (derived from schedule for the week)

## Architecture overview
- Metrics Warehouse (2023–2024)
  - Inputs: nfl_data_py weekly data; optional PBP for EP/WP/CP/xpass/XYAC
  - Outputs: team_week.csv, player_week.csv, game_week.csv
  - Purpose: feed priors and inform simulation distributions
- Priors (from 2023–2024 baseline)
  - Team priors: plays/game, pace, neutral_xpass, PROE, EPA/play
  - Player priors: usage shares (targets, carries, RZ), efficiency (yards/touch, TD%), WR/TE WOPR/RACR
  - Storage and shrinkage: Empirical-Bayes toward league/position means
- Simulator (2025 slate using players.csv)
  - Environment per game: pass rate = neutral_xpass + PROE; OU/SPRD/ML/TM/P nudges; home/away placeholder; weather placeholders
  - Per-team/player sampling: team/game shocks for correlation; Beta/Dirichlet for shares; Normal/Lognormal for yards; Poisson/Binomial for events
  - Position-specific handling: QB/RB/WR/TE scoring; DST via opponent sacks/TO/points allowed proxy
  - Rookies: fallback on site FPTS with pos-calibrated variance; flagged
  - Outputs per player: sim_mean, p10/p75/p90/p95, boom_prob, beat_site_prob, value metrics, boom_score, dart_flag
- Integration of nflfastR models (EP/WP/CP/xpass/XYAC)
  - Team priors: neutral_xpass and PROE via xpass; pace, EPA/play, success rate
  - QB priors: cpoe_mean, cp_mean, epa/dropback, sack_rate, deep_rate, aDOT
  - Receiver priors: WOPR, RACR, XYAC measures
  - Simulator usage: pass rate = neutral_xpass + PROE (OU/SPRD nudges); catch rate modulated by QB; TDs scaled by EP/RZ propensity

## Boom, floor, ceiling, value, and compare — definitions
Let X = sim draws {X1..XT}
- Floor: Q10(X) (robust; optional ES below Q10)
- Median: Q50(X)
- Ceiling: Q90(X) (robust; optional ES above Q90)
- Value per $1k: sim_mean / (SAL/1000)
- Ceiling per $1k: p90 / (SAL/1000)

Boom threshold:
- pos_boom: position-level p90 from 2023–2024 (or calibrated)
- site_boost (if FPTS provided): max(1.20 × FPTS, FPTS + 5)
- boom_cut = max(pos_boom, site_boost)
- boom_prob: P(X ≥ boom_cut)
- beat_site_prob: P(X ≥ FPTS) if site FPTS provided

Boom score (1–100):
- composite = 0.6 × boom_prob + 0.4 × beat_site_prob
- normalize within position to percentile rank
- ownership boost: +20% if RST% ≤ 5; +10% if ≤ 10; +5% if ≤ 20; else 0
- value boost: up to +15% if value_per_1k > position median (linear)
- boom_score = 100 × min(1, norm_pos(composite) × (1 + own_boost) × (1 + value_boost))
- dart_flag: (RST% ≤ 5) AND (boom_score ≥ 70)

Compare fields:
- delta_mean = sim_mean − site_fpts
- pct_delta = delta_mean / max(1, |site_fpts|)
- coverage_p10_p90: share where site_fpts ∈ [p10, p90] (reported in diagnostics_summary)

## Streamlit UI
- Simulator tab
  - Inputs: file_uploader for players.csv; Sims; Seed
  - Column mapping table; warnings for missing/invalid fields and unknown positions
  - Caching: cache results for identical inputs; "Clear cache" button
  - Previews: sim_players, compare (filters/sorts by position, delta, sim_std, sim_mean)
  - Downloads: four CSV buttons + "Download all (zip)" including metadata.json
  - Metrics surfaced: value_per_1k, ceil_per_1k, boom_prob, beat_site_prob, boom_score, dart_flag; SAL/RST%/site_val shown if provided
  - Methodology link: docs/research/monte_carlo_football.pdf
- Optimizer tab (planned in Stage 3)
  - "Build from nfl_data_py" section:
    - Inputs: season, week; optional salaries CSV
    - Buttons: "Build players.csv" (adapter) and "Generate sims.csv" (Monte Carlo around adapter projections)
    - Auto-loads generated players.csv and sims.csv into Optimizer inputs
  - "GPP Presets" section:
    - Preset selector: Small / Mid / Large
    - Toggles: bring-back, mini-stacks, salary leftover, require darts
    - Sliders: ownership band, boom_score threshold, value_per_1k threshold
    - Apply flow: "Apply preset" populates constraints → "Optimize" builds lineups

## File structure (planned and in-progress)
- app.py / streamlit_app.py — Streamlit entry/UI tabs
- simulator.py — Monte Carlo engine glue for Streamlit
- sim/ or simlab/ — simulation core and utilities
- src/
  - ingest/
    - site_players.py — loader/mapping for site file (PLAYER, POS, TEAM, OPP, O/U, SPRD, SAL, FPTS, VAL, RST%)
    - name_normalizer.py — normalize names; build player_id
  - metrics/ (warehouse)
    - sources.py, prep.py, team_metrics.py, player_metrics.py, pipeline.py
  - projections/
    - prior_builder.py — build team/player priors
    - value_metrics.py — value per $1k, ceiling value, deltas
    - boom_score.py — boom_prob, boom_score (1–100), dart_flag
    - diagnostics.py — MAE/RMSE/corr/coverage, flags
  - sim/
    - game_simulator.py — core Monte Carlo: environment/usage/efficiency/correlation
- scripts/
  - build_baseline.py — create priors from 2023–2024
  - generate_metrics.py — build team/player/game metrics from nfl_data_py
  - build_boom_thresholds.py — compute boom cutoffs from 2023–2024
- docs/
  - master_reference.md — this file
  - nfl_data_py_integration.md — adapter usage
  - metrics_catalog.md — derived features inventory
  - pipeline.md — metrics warehouse overview
  - compare_projections.md — how to analyze compare.csv and diagnostics
  - research/
    - monte_carlo_football.pdf — source methodology (your PDF)
    - monte_carlo_methodology.md — summary + mapping to code
  - gpp_strategy_blueprint.md — stacking/ownership/duplication playbook

## Staged build plan and acceptance criteria

Stage 0 — Foundation (done)
- UI-first README
- docs/ROADMAP.md, docs/master_reference.md, CONTRIBUTING.md, legacy README archived
- Optional: minimal branch protection

Stage 1 — Simulator MVP (independent model)
- UI: upload → Sims/Seed → Run → previews → ZIP; "Send to Curation"
- Engine: independent normal around base_fpts with derived std; quantiles; boom_prob
- I/O: write sim_players.csv, compare.csv, diagnostics_summary.csv, flags.csv, metadata.json; zip bundle
- Diagnostics: MAE/RMSE/corr, rough coverage proxy if FPTS present
- Determinism: seeded RNG; cache reads
Acceptance:
- Same inputs + seed => identical artifacts
- 4 CSVs + metadata.json + ZIP delivered
- Clear warnings for missing columns

Stage 1.1 — UX polish
- "Download players.csv template" button
- Column mapping/warnings table; unknown positions/duplicate IDs highlighted
- "Clear cache" button
- Richer metadata.json (parameters, file checksum, mapping)

Stage 2 — Realistic Monte Carlo per PDF
- Environment nudges: OU/SPRD/ML/TM/P; pass rate = neutral_xpass + PROE; home/away stub; weather placeholders
- Player usage distributions and efficiency draws (Beta/Dirichlet, Normal/Lognormal, Poisson/Binomial)
- Team/game shocks for correlation; QB↔WR/TE dependence; RB vs WR competition
- Rookies fallback and flags
- Expanded outputs: beat_site_prob, value_per_1k, ceil_per_1k, boom_score, dart_flag
- Diagnostics coverage via empirical quantiles
Acceptance:
- Sensible correlation effects; reasonable coverage; acceptable runtime 20k–50k sims

Stage 2.5 — Calibration and QA
- Exclude rookie_fallback from MAE/RMSE/corr/coverage aggregates
- Reliability plots (optional PNG artifacts)
- Golden tests: fixed seed + input → assert quantile tolerances
- Data guards on probabilities; DST negative scoring rules as needed

Stage 3 — Optimizer integration
- Optimizer tab with "Curate from Simulator" as primary flow
- Presets Small/Mid/Large; constraints for stacking/ownership/salary/diversity; require darts option
- Optional "Build from nfl_data_py" to generate players.csv/sims.csv when site file isn't available
Acceptance:
- Presets alter portfolio; constraints respected; exports to data/lineups/{season}_w{week}_{timestamp}/

Stage 4 — Scale and robustness
- Chunking/parallel; progress bars; graceful failures; caching of intermediates

Stage 5 — Polish, docs, release hygiene
- Update docs and screenshots; tag version; CHANGELOG in PR description

## Runbook (developer commands; not for end users)
Requirements:
- Python 3.10+
- pip install -r requirements.txt (includes: nfl_data_py, pandas, numpy, pyarrow, python-slugify, streamlit)

9.1) Build baseline (2023–2024)
```
python scripts/build_baseline.py --start 2023 --end 2024 --out data
```

9.2) Build boom thresholds from history
```
python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90
```

9.3) Run a 2025 week from your site players.csv
```
python -m src.projections.run_week_from_site_players \
  --season 2025 --week 1 \
  --players-site path/to/players_2025.csv \
  --team-priors data/baseline/team_priors.csv \
  --player-priors data/baseline/player_priors.csv \
  --boom-thresholds data/baseline/boom_thresholds.json \
  --sims 10000 \
  --out data/sim_week
```

9.4) Adapter: Generate players.csv (and optional ownership.csv) from nfl_data_py
```
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/
# With Rotowire salaries:
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/ --rotowire path/to/rotowire-NFL-players.csv
```

Outputs:
- data/players.csv: player_id, name, team, position, proj_mean, proj_p75, proj_p90, game_id
- data/ownership.csv (optional): player_id, own_proj (0–100)

Ownership heuristic (adapter path):
- Base: own_score ∝ proj_mean; adjust by game total (schedule total_line normalized to ~44)
- If salaries provided: boost for better value; normalize to 0–100% → own_proj

## Diagnostics and QA
- diagnostics_summary.csv: MAE/RMSE/corr vs site FPTS; coverage of [p10, p90]; rookies excluded by default
- Sanity checks: beat_site_prob distribution; boom_prob not degenerate
- flags.csv: plausible outliers (big deltas or data issues)
- Reproducibility: seeded RNG; cache; "Clear cached results" button

## Governance and updates
- PRs flow by stages above; README remains UI-first
- After merges, Render deploy: clear build cache if deps change
- If Actions appear for the first time, click "Approve workflows to run"

## References
- Primary methodology PDF: docs/research/monte_carlo_football.pdf
- Summary + mapping: docs/research/monte_carlo_methodology.md
- GPP strategy: docs/gpp_strategy_blueprint.md
- Adapter details: docs/nfl_data_py_integration.md
- Metrics catalog: docs/metrics_catalog.md
- Pipeline overview: docs/pipeline.md
- Compare analysis: docs/compare_projections.md