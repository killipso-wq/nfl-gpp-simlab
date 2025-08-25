# NFL GPP Sim Optimizer — Master Reference (Scope, Design, UI, Files)

> Quick links: [Methodology PDF](research/monte_carlo_football.pdf) • [Methodology summary](research/monte_carlo_methodology.md) • [GPP Strategy Blueprint](gpp_strategy_blueprint.md)

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
  - Methodology link: [docs/research/monte_carlo_football.pdf](research/monte_carlo_football.pdf)
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

## References
- Methodology PDF: [research/monte_carlo_football.pdf](research/monte_carlo_football.pdf)
- Methodology summary + mapping: [research/monte_carlo_methodology.md](research/monte_carlo_methodology.md)
- GPP strategy: [gpp_strategy_blueprint.md](gpp_strategy_blueprint.md)
- Adapter details: [nfl_data_py_integration.md](nfl_data_py_integration.md)
- Metrics catalog: [metrics_catalog.md](metrics_catalog.md)
- Pipeline overview: [pipeline.md](pipeline.md)
- Compare analysis: [compare_projections.md](compare_projections.md)