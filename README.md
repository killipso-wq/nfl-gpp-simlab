[Realistic NFL Monte Carlo Simulation.pdf](https://github.com/user-attachments/files/21975791/Realistic.NFL.Monte.Carlo.Simulation.pdf)
# NFL GPP Sim Optimizer — Master Reference (Scope, Design, Commands, UI, Files)

This is the single source of truth for what we are building: end-to-end baseline (2023–2024) from nfl_data_py, a Monte Carlo simulator for the 2025 slate driven by your players.csv, robust outputs (value/boom/diagnostics), and a Streamlit UI. It also includes the “adapter” CLI to generate simulator-ready inputs from nfl_data_py.

Use this document to:
- Verify scope and acceptance criteria
- Find exact commands and where outputs go
- Understand how each piece (priors, sim, diagnostics, UI) works
- Recover quickly if we get lost

--------------------------------------------------------------------------------

## Master Checklist (Issue #15 — single source of truth)

- [ ] Docs
  - [ ] Add docs/master_reference.md (includes Monte Carlo PDF references and GPP blueprint links)
  - [ ] Add docs/gpp_strategy_blueprint.md (stacks, ownership, duplication, presets)
  - [ ] Add docs/research/monte_carlo_football.pdf (source methodology PDF)
  - [ ] Add docs/research/monte_carlo_methodology.md (summary + mapping to code)

- [ ] Baseline (2023–2024) and thresholds
  - [ ] scripts/build_baseline.py (team/player priors from nfl_data_py)
  - [ ] scripts/build_boom_thresholds.py → data/baseline/boom_thresholds.json (default p90)
  - [ ] data/baseline outputs saved (team_priors.csv, player_priors.csv)

- [ ] Simulator (2025 week from site players.csv)
  - [ ] Ingest players.csv with mapping for: PLAYER, POS, TEAM, OPP, FPTS, SAL, RST%, O/U, SPRD, ML, TM/P, VAL
  - [ ] Monte Carlo engine with priors, environment nudges (OU/SPRD), rookies fallback to site FPTS
  - [ ] Outputs saved:
    - [ ] sim_players.csv (sim_mean, p10, p75, p90, p95, boom_prob, rookie_fallback, SAL if present)
    - [ ] compare.csv (site_fpts, delta_mean, pct_delta, beat_site_prob, value_per_1k, ceil_per_1k, site_val, RST%, boom_score, dart_flag)
    - [ ] diagnostics_summary.csv (MAE, RMSE, corr, coverage_p10_p90; rookies excluded)
    - [ ] flags.csv (big deltas, data issues)
    - [ ] metadata.json and simulator_outputs.zip bundle
  - [ ] Boom/value definitions implemented (positional boom, site boost, ownership/value boosts)
  - [ ] RST% normalization (≤1 → fraction×100; >1 → percent)

- [ ] Streamlit — Simulator tab
  - [ ] File upload, Sims, Seed
  - [ ] Detected column mapping table with warnings
  - [ ] Caching + “Clear cache”
  - [ ] Previews with filters/sorts
  - [ ] Downloads (4 CSVs + ZIP with metadata.json)
  - [ ] Methodology link to docs/research/monte_carlo_football.pdf

- [ ] Optimizer tab
  - [ ] “Build from nfl_data_py” section (generate players.csv/sims.csv; optional salaries)
  - [ ] “GPP Presets” section (one-click constraints; uses latest sim outputs)
    - [ ] Preset selector: Small / Mid / Large
    - [ ] Toggles: bring-back, mini-stacks, salary leftover, require darts
    - [ ] Sliders: ownership band, boom_score threshold, value_per_1k threshold
    - [ ] Button: “Apply preset” populates constraints, then “Optimize”

- [ ] Adapter CLI (optional path)
  - [ ] src/ingest/nfl_data_py_to_simulator.py (players.csv + optional ownership.csv)
  - [ ] Ownership heuristic (projection/salary/total); normalize to 0–100%
  - [ ] Stable player_id (TEAM_POS_NORMALIZEDNAME) and game_id (AWAY@HOME)

- [ ] Diagnostics and QA
  - [ ] Verify MAE/RMSE/corr and coverage by position (rookies excluded)
  - [ ] Sanity checks on boom_prob/beat_site_prob distributions
  - [ ] flags.csv highlights plausible outliers
  - [ ] Seed determinism confirmed

- [ ] Acceptance criteria (DoD)
  - [ ] Baseline builds; priors and thresholds present in data/baseline
  - [ ] Simulator artifacts (sim_players, compare, diagnostics, flags, metadata/ZIP)
  - [ ] SAL/VAL/RST% included in compare when present
  - [ ] UI Simulator features complete; methodology link present
  - [ ] Optimizer: GPP Presets implemented and functional

- [ ] Follow-ups (post-MVP)
  - [ ] Opponent adjustments, home/away, weather
  - [ ] Richer dependence model (copulas) and scenario toggles
  - [ ] Backtesting (CRPS/Brier, reliability) and calibration tuning
  - [ ] Performance scaling (100k–500k trials)
  - [ ] DST enhancements in adapter path

1) Goals

- Build our own projections (mean, floor, ceiling) and value metrics from a Monte Carlo simulator that leverages 2023–2024 nfl_data_py data.
- Compare our projections to the site projections from your 2025 players.csv (delta, coverage, accuracy).
- Identify low-owned upside “darts” via a Boom score (1–100) and dart_flag.
- Provide a robust Streamlit UI: upload players.csv, click run, analyze outputs, download all artifacts or a single ZIP.
- Also offer a CLI adapter to produce players.csv (and optional ownership.csv) directly from nfl_data_py when you don’t have a site file.

--------------------------------------------------------------------------------

2) Data sources and seasons

- Historical: nfl_data_py (nflfastR data)
  - Weekly stats (seasons: 2023–2024 baseline only)
  - Play-by-play optional for richer features (EPA/WP/CP/xpass/XYAC)
  - Schedules (to map game_id and limit to active teams/week)
- 2025 slate and players:
  - Your players.csv file defines who’s active, teams/opponents, and site fields (FPTS, SAL, RST%, O/U, SPRD, etc.)

Why 2023–2024 baseline:
- Avoid leakage from 2025
- Stable, recent window for priors and calibration

--------------------------------------------------------------------------------

3) Inputs — players.csv (from the site)

Required columns:
- PLAYER: Player name (we normalize variants)
- POS: Position; D → mapped to DST
- TEAM: Player team
- OPP: Opponent team

Supported columns (optional but used when present):
- FPTS: Site projection (used for compare and rookie fallback center)
- SAL: Salary
- RST%: Projected ownership (percent format if > 1, else fraction)
- O/U: Game total (Vegas); used as environment hint
- SPRD: Spread; used as environment hint
- ML: Moneyline; optional environment hint
- TM/P: Implied team points; optional if present
- VAL: Site’s “value” metric (assumed “points per $1k” unless specified otherwise)

Column mapping:
- We autodetect synonyms (e.g., Salary, dk_salary; OWN, OWN%; Value, Pts/$).
- Streamlit shows a “Detected column mapping” table with warnings for missing/malformed fields.

Rookies/new players policy:
- If no 2023–2024 priors for a player, we use site FPTS 100% as sim mean (no shrinkage).
- Spread by a position-calibrated variance; clamp at 0; mark rookie_fallback=True.
- Excluded from MAE/RMSE/corr/coverage metrics (but retained in compare.csv and flags if extreme).

--------------------------------------------------------------------------------

4) Outputs (primary artifacts)

- sim_players.csv (our projections)
  - Columns: player_id, PLAYER, POS, TEAM, OPP, sim_mean, floor_p10, p75, ceiling_p90, p95, boom_prob, rookie_fallback, SAL (if present)
- compare.csv (joined with site fields)
  - Adds: site_fpts, delta_mean, pct_delta, beat_site_prob, value_per_1k, ceil_per_1k, site_val (if provided), RST%, boom_score (1–100), dart_flag
- diagnostics_summary.csv
  - Per-position MAE, RMSE, Pearson corr, coverage_p10_p90, counts; excludes rookie_fallback by default (also reports fallback counts)
- flags.csv
  - Largest discrepancies and notable conditions (e.g., abs_delta > threshold, pct_delta > threshold)
- ZIP bundle (simulator_outputs.zip)
  - sim_players.csv, compare.csv, diagnostics_summary.csv, flags.csv, metadata.json
  - metadata.json: sims, seed, run_id, git commit, column mapping, counts, diagnostics row

Adapter (optional):
- players.csv (from nfl_data_py weekly history): player_id, name, team, position, proj_mean, proj_p75, proj_p90, game_id
- ownership.csv (optional heuristic): player_id, own_proj (0–100)

--------------------------------------------------------------------------------

5) Stable IDs and naming

- player_id: TEAM_POS_NORMALIZEDNAME
  - NORMALIZEDNAME = uppercase, punctuation removed, suffixes (JR/SR/II/III/IV/V) dropped, spaces collapsed
  - DST reserved as TEAM_DST (adapter MVP can skip emitting DST; simulator supports DST)
- game_id: AWAY@HOME (derived from schedule for the week)

--------------------------------------------------------------------------------

6) Architecture

6.1) Metrics Warehouse (2023–2024)

- Inputs:
  - nfl_data_py weekly data (required)
  - Optional: play-by-play for EP/WP/CP/xpass/XYAC (for enriched features)
- Outputs:
  - data/metrics/team_week.csv: pace, neutral_xpass, PROE, EPA/play, success rates
  - data/metrics/player_week.csv: usage shares and efficiency (targets, air yards, carries, red-zone, WOPR/RACR, etc.)
  - data/metrics/game_week.csv: aggregates for game-level correlation
- Purpose:
  - Feed priors (team and player) and inform sim distributions

6.2) Priors (from 2023–2024 baseline)

- Team priors:
  - plays per game, pace (seconds/play), neutral_xpass, proe_neutral (actual pass rate − neutral_xpass), EPA/play
- Player priors:
  - Usage shares (targets, carries, inside-10), efficiency rates (yards/target, yards/carry, TD%), WR/TE WOPR, RB high-value touches
- Storage and shrinkage:
  - Empirical-Bayes shrinkage toward position/league means to stabilize small samples
  - Priors summarized as Beta/Dirichlet/Normal parameters per feature

6.3) Simulator (2025 slate using players.csv)

- Environment per game:
  - Base pass rate = neutral_xpass + proe_neutral
  - OU/SPRD/ML/TM/P nudge team expectations (plays, scoring splits)
  - Home/away factor stub; weather/dome placeholders (extendable later)
- Per-team and per-player sampling:
  - Team/game shocks to create correlation (pace/efficiency shared shocks)
  - Usage shares: Dirichlet/Beta by position roles
  - Efficiency: Normal/Lognormal for yards per touch/target; TD via Poisson/Binomial allocations consistent with team totals
- Distributions and correlations:
  - QB–receiver dependence through team/game shocks and catch-rate/yards coupling
  - Optional richer dependence (copula) can be added behind an “experimental” toggle
- Position-specific handling:
  - QB: yards/TDs/INT, sacks; DK bonuses
  - RB/WR/TE: targets/carries, yards, TD rates; DK receptions/bonuses
  - DST: opponent QB sack and turnover proxies, points-allowed distribution (included in simulator; adapter MVP can skip)
- Rookies/no-history:
  - Center on site FPTS; position variance; clamp to zero; flagged
- Outputs per player (from draws):
  - sim_mean, floor p10, p75, ceiling p90, p95
  - boom_prob, beat_site_prob, value_per_1k, ceil_per_1k, boom_score, dart_flag

6.4) Integration of nflfastR models (EP/WP/CP/xpass/XYAC)

- Team priors:
  - neutral_xpass and PROE via xpass model
  - pace, EPA/play, success rate (already computed)
- QB priors:
  - cpoe_mean, cp_mean, epa_per_dropback, sack_rate, deep_rate, aDOT proxy
- Receiver priors:
  - WOPR, RACR, xyac_mean_yardage, XYAC_epa, aDOT
- Simulator usage:
  - Pass rate per sim = neutral_xpass + proe_neutral (OU/SPRD nudges)
  - Catch rate modulated by QB cp/cpoe
  - Receiving yards modulated by XYAC features
  - TD allocations scaled by EP/red-zone propensity instead of flat rates

--------------------------------------------------------------------------------

7) Boom, floor, ceiling, value, and compare — definitions

From per-player sim draws X = {X1..XT}:

- Floor: Q10(X) (robust; optional ES: mean below Q10)
- Median: Q50(X)
- Ceiling: Q90(X) (robust; optional ES: mean above Q90)
- Value per $1k: sim_mean / (SAL/1000)
- Ceiling per $1k: p90 / (SAL/1000)
- Boom threshold:
  - pos_boom: position-level p90 from 2023–2024 (or calibrated)
  - site_boost (if FPTS provided): max(1.20 × FPTS, FPTS + 5)
  - boom_cut = max(pos_boom, site_boost)
- boom_prob: P(X ≥ boom_cut)
- beat_site_prob (if site FPTS provided): P(X ≥ FPTS)
- Boom score (1–100):
  - composite = 0.6 × boom_prob + 0.4 × beat_site_prob
  - normalize within position to percentile rank
  - ownership boost: +20% if RST% ≤ 5; +10% if ≤ 10; +5% if ≤ 20; else 0
  - value boost: up to +15% if value_per_1k > position median (linear scale)
  - boom_score = 100 × min(1, norm_pos(composite) × (1 + own_boost) × (1 + value_boost))
- dart_flag: (RST% ≤ 5) AND (boom_score ≥ 70)

Compare fields:
- delta_mean = sim_mean − site_fpts (if FPTS available)
- pct_delta = delta_mean / max(1, |site_fpts|)
- coverage_p10_p90: share where site_fpts lies in [p10, p90] (reported in diagnostics_summary)

--------------------------------------------------------------------------------

8) Diagnostics and flags

- diagnostics_summary.csv (per position and overall):
  - MAE, RMSE, Pearson corr between sim_mean and site_fpts (excludes rookie_fallback)
  - coverage_p10_p90 (% of players where site FPTS in [p10, p90])
  - counts (total, rookies excluded, rookies included)
- flags.csv:
  - Top absolute and percent deltas
  - Data issues (missing SAL/RST% if required downstream, unknown positions)
- Reproducibility and caching:
  - Seeded RNG; seed exposed in metadata.json
  - Streamlit caching for identical inputs (players file bytes + sims + seed)
  - “Clear cached results” button

--------------------------------------------------------------------------------

9) CLI tools and example commands

Dependencies:
- pip install nfl_data_py pandas numpy pyarrow python-slugify

9.1) Build baseline (2023–2024)
- Purpose: compute metrics and build team/player priors
- Command:
  - python scripts/build_baseline.py --start 2023 --end 2024 --out data

9.2) Build boom thresholds from history
- Purpose: set position-level boom cutoffs (default p90)
- Command:
  - python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90

9.3) Run a 2025 week from your site players.csv
- Purpose: full simulator run using your roster/OU/SPRD/SAL/RST%
- Command:
  - python -m src.projections.run_week_from_site_players \
      --season 2025 --week 1 \
      --players-site path/to/players_2025.csv \
      --team-priors data/baseline/team_priors.csv \
      --player-priors data/baseline/player_priors.csv \
      --boom-thresholds data/baseline/boom_thresholds.json \
      --sims 10000 \
      --out data/sim_week

9.4) Adapter: Generate players.csv (and optional ownership.csv) from nfl_data_py
- Purpose: when no site players.csv is available; produces simulator-ready players.csv
- Command:
  - python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/
  - With Rotowire salaries: add --rotowire path/to/rotowire-NFL-players.csv

Outputs:
- data/players.csv: player_id, name, team, position, proj_mean, proj_p75, proj_p90, game_id
- data/ownership.csv (optional): player_id, own_proj (0–100)

Adapter notes:
- Uses 2023–2024 weekly logs; projections are recency-weighted DK points with p75/p90 from empirical quantiles; position baselines for tiny samples.
- Schedule restricts to teams active that week; game_id = AWAY@HOME.
- DST initially skipped in adapter MVP (can extend later). Simulator itself includes DST.

--------------------------------------------------------------------------------

10) Streamlit UI

Tabs:
- Simulator (PR #14)
  - Inputs: file_uploader for players.csv; Sims; Seed
  - Column mapping table; warnings for missing/invalid fields and unknown positions
  - Caching: results cached for identical inputs; “Clear cached results” button
  - Previews: sim_players and compare with filters (by position) and sorting (delta_mean/sim_std/sim_mean)
  - Downloads: four CSV buttons + “Download all (zip)” including metadata.json
  - Metrics surfaced: value_per_1k, ceil_per_1k, boom_prob, beat_site_prob, boom_score, dart_flag; SAL/RST%/site_val shown if provided
  - Methodology link: points to docs/research/monte_carlo_football.pdf (see Section 19)

- Optimizer
  - “Build from nfl_data_py” section (planned)
    - Inputs: season, week, slate type; sims per player (for sims.csv); optional salaries CSV
    - Buttons: “Build players.csv” (from nfl_data_py) and “Generate sims.csv” (Monte Carlo around those projections)
    - Integration: auto-loads the generated players.csv and sims.csv into the Optimizer inputs so you can immediately run/download optimized lineups
  - “GPP Presets” section (planned; see Section 22)
    - One-click application of the GPP Strategy Blueprint to constraints before you optimize.

--------------------------------------------------------------------------------

11) File structure (planned)

- app.py / streamlit_app.py — Streamlit entry point/UI tabs
- simulator.py — Monte Carlo engine glue for Streamlit
- src/
  - ingest/
    - nfl_data_py_to_simulator.py — adapter CLI (players.csv + optional ownership.csv)
    - site_players.py — loader for your site file schema (PLAYER, POS, TEAM, OPP, O/U, SPRD, SAL, FPTS, VAL, RST%)
    - name_normalizer.py — normalize names; build player_id
    - scoring.py — DK scoring function for game logs
  - metrics/
    - sources.py, prep.py, team_metrics.py, player_metrics.py, pipeline.py — metrics warehouse for 2023–2024
  - projections/
    - prior_builder.py — build team/player priors
    - run_week_from_site_players.py — main CLI for 2025 sim using your players.csv
    - value_metrics.py — value per $1k, ceiling value, deltas vs site
    - boom_score.py — boom_prob, boom_score (1–100), dart_flag
    - diagnostics.py — MAE/RMSE/corr/coverage, flags
  - sim/
    - game_simulator.py — core Monte Carlo, environment/usage/efficiency/correlation sampling
- scripts/
  - build_baseline.py — create priors from 2023–2024
  - generate_metrics.py — build team/player/game metrics from nfl_data_py
  - build_boom_thresholds.py — compute boom cutoffs from 2023–2024
- docs/
  - master_reference.md — this file
  - nfl_data_py_integration.md — adapter usage
  - metrics_catalog.md — derived features inventory (MVP)
  - pipeline.md — metrics warehouse overview
  - compare_projections.md — how to analyze compare.csv and diagnostics
  - research/
    - monte_carlo_football.pdf — source methodology (your PDF)
    - monte_carlo_methodology.md — summary + mapping to code
    - README.md — how research artifacts map into the simulator
  - gpp_strategy_blueprint.md — full GPP stacking/ownership/duplication playbook

--------------------------------------------------------------------------------

12) Requirements and environment

- Python 3.10+
- pip install -r requirements.txt (will include: nfl_data_py, pandas, numpy, pyarrow, python-slugify, streamlit)
- Optional: virtualenv (.venv) for local runs
- Render deployment:
  - Service connected to GitHub repository
  - Start command: streamlit run app.py (or python -m streamlit run app.py)
  - Environment: STREAMLIT_SERVER_MAX_UPLOAD_SIZE=300 (optional, for larger uploads)
  - Manual Deploy → Clear build cache & deploy after merges

--------------------------------------------------------------------------------

13) Testing, validation, and calibration

- Smoke tests:
  - Deterministic runs with fixed seed; compare outputs stable across runs
  - Unit tests for sampling distributions and seed determinism (planned)
- Accuracy diagnostics:
  - diagnostics_summary.csv: MAE/RMSE/corr vs site FPTS; coverage of [p10, p90]; rookies excluded by default
- Sanity checks:
  - beat_site_prob distribution; boom_prob not degenerate
  - flags.csv shows plausible outliers for review
- Backtesting (follow-up):
  - Run a 2023–2024 holdout week; examine PIT histograms, reliability curves, CRPS/Brier
  - Tune boom threshold (e.g., p85/p95) and site_boost margins (1.2× or +5) if needed

--------------------------------------------------------------------------------

14) Ownership heuristic (adapter path)

- Base: own_score ∝ proj_mean
- Adjust by game total (from schedule total_line, normalized to ~44)
- If salaries provided via Rotowire:
  - Increase score for higher projection at lower salary
  - Normalize to sum to 100 → own_proj (%)
- Output: ownership.csv [player_id, own_proj]

Note: In Simulator path (your site file), we use your RST% directly for compare and Boom scoring.

--------------------------------------------------------------------------------

15) Data quality and error handling

- Column mapping table shows detected fields and whether found
- Warnings:
  - Missing required columns → fill placeholders where possible, or stop with error
  - Missing/invalid FPTS → flagged; treated as NaN; rookie fallback requires FPTS if no priors
  - Unknown positions → mapped to UNK (skipped from some metrics)
- players.csv normalization:
  - POS “D” → “DST”
  - Ownership normalization: if RST% ≤ 1, treat as fraction × 100; else as percent
  - VAL preserved as site_val (assumed points per $1k unless specified)

--------------------------------------------------------------------------------

16) Runbook (short)

Local:
- pip install -r requirements.txt
- Build baseline once:
  - python scripts/build_baseline.py --start 2023 --end 2024 --out data
  - python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90
- Run a 2025 week from your site players.csv:
  - python -m src.projections.run_week_from_site_players --season 2025 --week 1 --players-site path/to/players.csv --team-priors data/baseline/team_priors.csv --player-priors data/baseline/player_priors.csv --boom-thresholds data/baseline/boom_thresholds.json --sims 10000 --out data/sim_week
- Streamlit:
  - streamlit run app.py → Simulator tab → upload players.csv → set Sims/Seed → Run → download outputs

Adapter (optional):
- python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/ [--rotowire path/to/rotowire.csv]
- Upload produced data/players.csv (and ownership.csv if desired) to the Simulator/Optimizer flows.

--------------------------------------------------------------------------------

17) Acceptance criteria checklist

- Baseline (2023–2024) priors build without errors; files saved to data/baseline
- Simulator produces sim_players.csv, compare.csv, diagnostics_summary.csv, flags.csv
- Floor p10, Ceiling p90, p75/p95 present; Boom metrics present (boom_prob, boom_score, dart_flag)
- Value metrics present: value_per_1k, ceil_per_1k; SAL and RST% used if available
- Compare to site FPTS (if present): delta_mean, pct_delta, beat_site_prob; diagnostics include MAE/RMSE/corr/coverage (rookies excluded)
- Streamlit:
  - Column mapping table, warnings shown
  - Caching works; Clear cache button
  - Previews with filters/sorts
  - 4 CSV download buttons + “Download all (zip)” including metadata.json
- Adapter CLI:
  - Generates players.csv and (optionally) ownership.csv from nfl_data_py, using schedule and 2023–2024 baseline
  - Stable player_id format and game_id mapping
- Optimizer (planned next):
  - “Build from nfl_data_py” section present and auto-loads players/sims into Optimizer
  - “GPP Presets” section present for one-click constraints application (see Section 22)

--------------------------------------------------------------------------------

18) Roadmap (post-MVP polish)

- Opponent adjustments (defense vs position) and home/away/weather
- Richer dependence model (copulas) and scenario toggles
- Hierarchical priors (role/archetype) for low-sample players
- Calibration/backtests with CRPS/Brier and reliability plots
- Performance: vectorization for 100k–500k trials
- Optimizer integration:
  - “Build from nfl_data_py” section that auto-loads outputs into Optimizer tab
  - “GPP Presets” section for one-click constraint presets (Small/Mid/Large)
- DST enhancements in adapter path (team defense stats → DST)

--------------------------------------------------------------------------------

19) Methodology and Research PDF (source of truth)

- Primary source: docs/research/monte_carlo_football.pdf (the PDF you posted; used as the methodology reference).
- Summary mapping: docs/research/monte_carlo_methodology.md (how PDF concepts map to our code and outputs).
- Implementation alignment:
  - Trials (`--sims`) with fixed `--seed` (reproducible).
  - Position-calibrated outcome distributions; clamp at 0.
  - DK scoring with bonuses; export p10/p50/p75/p90/p95 and exceedance probabilities.
  - Boom and beat-site exceedances; value per $1k; diagnostics and coverage.
- Metadata linkage: Each Simulator run includes metadata.json referencing sims, seed, and a “methodology”: "monte_carlo_pdf" pointer.
- Optional UI link: the Simulator tab includes a small “Methodology” expander linking to docs/research/monte_carlo_football.pdf.

--------------------------------------------------------------------------------

20) Governance and updates

- PRs:
  - PR #10: nfl_data_py-based simulator (2023–2024 baseline) + Streamlit Simulator tab with boom/value/diagnostics (rookie fallback policy applied)
  - PR #14: Simulator tab QoL: mapping/warnings, caching, preview filters/sorting, Clear cache, ZIP with metadata.json
- Update cadence:
  - Hourly visible progress during heavy coding phases (commits/checkpoints)
  - If blockers arise, push WIP and note the blocker and next ETA in the PR
- Where to click:
  - GitHub → PR → Files changed for review → Merge pull request
  - Render → Service → Manual Deploy → Clear build cache & deploy → Logs for confirmation

--------------------------------------------------------------------------------

21) GPP Strategy Blueprint (Stacks, Correlation, Ownership, Uniqueness)

Full document: docs/gpp_strategy_blueprint.md

Summary (applied AFTER simulation, in the Optimizer):
- Stacking:
  - Always stack QB; Single (QB+1) or Double (QB+2) by contest size; bring-back 0–1 (LF commonly 1).
  - Mini-correlations: WR vs opp WR/TE or RB vs opp WR/TE; RB+DST viable.
- Ownership/leverage:
  - Suggested total ownership bands (sum RST%): SF ~80–140%, MF ~60–110%, LF ~30–80%.
  - Limit clustering of chalk; use leverage pivots (teammates/role/salary tier).
- Salary/duplication:
  - SF spend near max; MF leave 0–800; LF leave 300–1,500 to reduce dupes.
  - Avoid the most common mega-chalk stack combos without leverage.
- Simulator-driven thresholds:
  - Darts: require ≥1 dart_flag (RST% ≤ 5 and boom_score ≥ 70) in LF.
  - Boom: aim ≥2 players with boom_score ≥ 70 in LF.
  - Value: include at least one anchor value (value_per_1k ≥ ~3.0; slate-dependent).
- Optimizer constraints (examples):
  - Exactly 1 QB; enforce 1–2 same-team WR/TE; bring-back 0–1.
  - Ownership band by contest size; cap players with RST% ≥ 20% (e.g., ≤2 in LF).
  - Avg value_per_1k ≥ 2.4–2.6; total salary ≤ 50,000 with min leftover in LF.
  - Max 1 RB per team (unless receiving RB in stack); max 4 from one game unless full game-stack mode.

Workflow:
- Run Simulator → review compare/diagnostics → apply blueprint as constraints → optimize → review dup/ownership → iterate.

--------------------------------------------------------------------------------

22) UI Recommendation — “GPP Presets” (Optimizer tab)

Purpose:
- One-click application of the GPP Strategy Blueprint using the latest Simulator outputs.

Design:
- Preset selector:
  - Small / Mid / Large (contest size presets).
- Toggle checkboxes:
  - Enforce bring-back (0/1)
  - Enforce mini-stacks (1–2)
  - Enforce salary leftover band (e.g., LF ≥ 200)
  - Require darts (≥1 dart_flag)
- Sliders:
  - Ownership band (min/max sum of RST%)
  - Boom threshold (e.g., boom_score ≥ 70)
  - Value threshold (min value_per_1k and/or ceil_per_1k)
- Apply flow:
  - Button: “Apply preset” populates constraints
  - Then click “Optimize” to generate lineups
- Notes:
  - Presets can be edited after applying (constraints panel stays editable).
  - Defaults per preset will be tuned by slate and diagnostics feedback.

Status:
- Planned next. We will add this “GPP Presets” section to the Optimizer tab so it’s one click to apply these rules using the latest sim outputs.
