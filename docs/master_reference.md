[Realistic NFL Monte Carlo Simulation.pdf](https://github.com/user-attachments/files/21975791/Realistic.NFL.Monte.Carlo.Simulation.pdf)
# NFL GPP Sim Optimizer — Master Reference (Scope, Design, Commands, UI, Files)

This is the single source of truth for what we are building: end-to-end baseline (2023–2024) from nfl_data_py, a Monte Carlo simulator for the 2025 slate driven by your players.csv, robust outputs (value/boom/diagnostics), and a Streamlit UI. It also includes  to generate simulator-ready inputs from nfl_data_py.

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
  - [ ] Caching + "Clear cache"
  - [ ] Previews with filters/sorts
  - [ ] Downloads (4 CSVs + ZIP with metadata.json)
  - [ ] Methodology link to docs/research/monte_carlo_football.pdf

- [ ] Optimizer tab
  - [ ] "Build from nfl_data_py" section (generate players.csv/sims.csv; optional salaries)
  - [ ] "GPP Presets" section (one-click constraints; uses latest sim outputs)
    - [ ] Preset selector: Small / Mid / Large
    - [ ] Toggles: bring-back, mini-stacks, salary leftover, require darts
    - [ ] Sliders: ownership band, boom_score threshold, value_per_1k threshold
    - [ ] Button: "Apply preset" populates constraints, then "Optimize"


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
- Identify low-owned upside "darts" via a Boom score (1–100) and dart_flag.
- Provide a robust Streamlit UI: upload players.csv, click run, analyze outputs, download all artifacts or a single ZIP.
- Also offer a  produce players.csv (and optional ownership.csv) directly from nfl_data_py when you don't have a site file.

--------------------------------------------------------------------------------

2) Data sources and seasons

- Historical: nfl_data_py (nflfastR data)
  - Weekly stats (seasons: 2023–2024 baseline only)
  - Play-by-play optional for richer features (EPA/WP/CP/xpass/XYAC)
  - Schedules (to map game_id and limit to active teams/week)
- 2025 slate and players:
  - Your players.csv file defines who's active, teams/opponents, and site fields (FPTS, SAL, RST%, O/U, SPRD, etc.)

Why 2023–2024 baseline:
- Avoid leakage from 2025
- Consistent with nfl_data_py rollouts (2023 complete, 2024 mostly complete)
- Two seasons provide sufficient sample for positional and team priors
- Includes playoff runs and late-season recency signals

We could extend to 2022 or 2021 for more sample, but gains are likely minimal and data compatibility risk grows.

--------------------------------------------------------------------------------

3) Site players.csv schema (2025 week inputs)

Required:
- PLAYER: Player name (normalized and mapped to player_id)
- POS: Position (QB, RB, WR, TE, DST)
- TEAM: Player's team (3-letter code, mapped to nfl_data_py schedules)
- OPP: Opponent team (3-letter code)
- FPTS: Site's projected fantasy points
- SAL: Salary (DraftKings format; integer; optional for just sim/compare)

Optional (improves environment and value scoring):
- RST%: Rest of site ownership % (0–100; ≤1 treated as fractions)
- O/U: Over/under total for the game
- SPRD: Spread; used as environment hint
- ML: Moneyline; optional environment hint
- TM/P: Implied team points; optional if present
- VAL: Site's "value" metric (assumed "points per $1k" unless specified otherwise)

Column mapping:
- We autodetect synonyms (e.g., Salary, dk_salary; OWN, OWN%; Value, Pts/$).
- Streamlit shows a "Detected column mapping" table with warnings for missing/malformed fields.

Rookies/new players policy:
- If no 2023–2024 priors for a player, we use site FPTS 100% as sim mean (no shrinkage).
- Spread by a position-calibrated variance; clamp at 0; mark rookie_fallback=True.
- Excluded from MAE/RMSE/corr/coverage metrics (but retained in compare.csv and flags if extreme).

--------------------------------------------------------------------------------

4) Outputs (primary artifacts)

From Monte Carlo simulation (after ingesting players.csv):
- sim_players.csv — per-player stats: sim_mean, p10/p50/p75/p90/p95, boom_prob, rookie_fallback, SAL (if present)
- compare.csv — site vs sim: site_fpts, delta_mean, pct_delta, beat_site_prob; value_per_1k, ceil_per_1k, site_val, RST%, boom_score, dart_flag
- diagnostics_summary.csv — accuracy: MAE, RMSE, correlation, coverage p10–p90 (rookies excluded)
- flags.csv — data quality: large deltas, potential outliers, missing data
- metadata.json — run info: timestamp, sims, seed, methodology, inputs_hash

Zip bundle: simulator_outputs.zip (contains all 5 files for easy download)

UI artifacts:
- Column mapping table (inputs validation)
- Preview tables with filters and sorting
- Individual CSV downloads + bundled ZIP download

--------------------------------------------------------------------------------

5) Monte Carlo engine design

Core approach:
- Start with 2023–2024 priors (see Section 6)
- Apply environmental nudges (O/U, spread, rest, matchup)
- Simulate DK points with position-calibrated distributions
- Export percentiles, exceedance probabilities, boom metrics

Environment modifiers (applied to priors):
- OU adjustment: higher game totals → slight upward bias
- Spread nudge: favorites get slight boost; underdogs get variance increase
- Rest/injury: if RST% very low (<5%), small downward bias
- Matchup: placeholder for defense-vs-position (future enhancement)

Simulation mechanics:
- Position-specific variance calibration (QB more stable, RB/WR more volatile)
- Clamp at 0 (no negative DK points)
- Bootstrap sampling for rookies or tiny samples
- Fixed seed for reproducibility

Why Monte Carlo over closed-form:
- Better handles correlations (team game environments)
- Natural percentile outputs for boom/coverage analysis
- Easier to add complex features (weather, injuries, game script)

--------------------------------------------------------------------------------

6) Priors and baselines (2023–2024)

Team priors (from nfl_data_py schedules + weekly stats):
- Pace (plays per game)
- Scoring environment (points per game, red zone %)
- Pass/rush splits and efficiency
- Home/away adjustments

Player priors (from nfl_data_py weekly logs):
- Recency-weighted DK points (last 8 games emphasized)
- Target share, snap %, usage rate by position
- Boom rate (top-10% scoring weeks) and ceiling metrics
- Floor and injury-replacement patterns

Fallback for small samples:
- Position baseline: median player in that role (e.g., WR2, RB1)
- Rookie rule: site FPTS as mean, position-calibrated variance

Baseline files (generated by build scripts):
- data/baseline/team_priors.csv
- data/baseline/player_priors.csv
- data/baseline/boom_thresholds.json (default p90 by position)

--------------------------------------------------------------------------------

7) Value and boom scoring

Value per $1k:
- value_per_1k = sim_mean / (SAL / 1000)
- ceil_per_1k = p90 / (SAL / 1000)

Boom scoring (1–100 scale):
- Base: percentile of sim_mean within position
- Salary boost: higher at lower salaries (+10 if SAL in bottom quartile)
- Ownership fade: higher at lower RST% (+15 if RST% < 10%)
- Site boost: higher if beat_site_prob > 60% (+10)

Dart flag (binary):
- dart_flag = True if boom_score ≥ 70 AND RST% ≤ 15%
- Identifies low-owned, high-upside tournament plays

beat_site_prob:
- Probability that sim_mean > site_fpts
- Measures confidence in our projections vs. site

--------------------------------------------------------------------------------

8) Diagnostics and accuracy

Coverage analysis:
- p10_coverage: % of actual scores ≥ our p10 (target ~90%)
- p90_coverage: % of actual scores ≤ our p90 (target ~90%)

Accuracy metrics (rookies excluded):
- MAE: Mean absolute error between sim_mean and actual DK points
- RMSE: Root mean squared error
- Correlation: Pearson r between sim and actual

Flags (data quality):
- Large deltas: |delta_mean| > 10 or |pct_delta| > 100%
- Extreme projections: sim_mean > 40 or < 2 for skill positions
- Missing data: key fields absent or malformed

Output: diagnostics_summary.csv and flags.csv

--------------------------------------------------------------------------------

9) Build from nfl_data_py (adapter path)

For slates without a site file, generate players.csv directly from nfl_data_py:

Inputs:
- season: 2024 (or current season)
- week: integer (1–18 regular season, 19+ playoffs)

Process:
- Pull schedule for that week (active teams, opponents, spreads)
- Load player rosters and 2023–2024 stats
- Generate projections using priors + environment
- Build player_id (TEAM_POS_NORMALIZEDNAME), game_id (AWAY@HOME)
- Populate required columns: PLAYER, POS, TEAM, OPP, FPTS
- Optional: SAL from Rotowire, ownership from heuristic

Outputs:
- players.csv: ready for Simulator
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
  - Caching: results cached for identical inputs; "Clear cached results" button
  - Previews: sim_players and compare with filters (by position) and sorting (delta_mean/sim_std/sim_mean)
  - Downloads: 4 CSV buttons + "Download all (ZIP)" with metadata.json
  - Methodology link: small expander linking to docs/research/monte_carlo_football.pdf

- Optimizer (planned next)
  - "Build from nfl_data_py" section: season/week inputs, optional salaries toggle, "Generate players.csv" and auto-loads
  - "GPP Presets" section: preset selector, toggles, sliders, "Apply preset" button
  - Standard optimizer UI (constraints, lineups, export)

Key UX elements:
- Progress bars for long-running tasks (building priors, simulation)
- Error handling and user-friendly messages
- Session state for caching and UI persistence
- Mobile-responsive (Streamlit default)

Methodology linkage:
- Simulator tab includes a small "Methodology" expander linking to docs/research/monte_carlo_football.pdf
- References simulation design, boom scoring, and value calculations

--------------------------------------------------------------------------------

11) File structure (planned)

- app.py / streamlit_app.py — Streamlit entry point/UI tabs
- simulator.py — Monte Carlo engine glue for Streamlit
- src/
  - ingest/
    - site_players.py — loader for your site file schema (PLAYER, POS, TEAM, OPP, O/U, SPRD, SAL, FPTS, VAL, RST%)
    - name_normalizer.py — normalize names; build player_id
    - scoring.py — DK scoring function for game logs
  - metrics/
    - sources.py, prep.py, team_metrics.py, player_metrics.py, pipeline.py — metrics warehouse for 2023–2024
  - projections/
    - prior_builder.py — build team/player priors
    - value_metrics.py — value per $1k, ceiling value, deltas vs site
    - boom_scoring.py — boom score (1–100), dart_flag
  - simulation/
    - monte_carlo.py — engine for trials
    - environment.py — OU/spread/rest adjustments
    - distributions.py — position-calibrated sampling
  - utils/
    - caching.py — Streamlit cache helpers
    - export.py — CSV/ZIP bundling

Data directories:
- data/baseline/ — team_priors.csv, player_priors.csv, boom_thresholds.json
- data/sim_outputs/ — simulation results (timestamped)

Scripts:
- scripts/build_baseline.py — pull nfl_data_py, build 2023–2024 priors
- scripts/build_boom_thresholds.py — position boom percentiles

Docs:
- docs/master_reference.md — this file
- docs/gpp_strategy_blueprint.md — stacking, ownership, optimization strategy
- docs/research/monte_carlo_football.pdf — methodology source
- docs/research/monte_carlo_methodology.md — how PDF maps to our code

--------------------------------------------------------------------------------

12) Commands and execution

Build baseline (run once or when season data updates):
```bash
python scripts/build_baseline.py --seasons 2023,2024 --output data/baseline/
python scripts/build_boom_thresholds.py --input data/baseline/player_priors.csv --output data/baseline/boom_thresholds.json
```

Simulator via CLI (optional):
```bash
python simulator.py --input players.csv --sims 10000 --seed 42 --output data/sim_outputs/
```

Streamlit UI (primary interface):
```bash
streamlit run app.py
```

Render deployment:
- Environment: Python 3.9+
- Requirements: streamlit, pandas, numpy, nfl_data_py, plotly
- Auto-deploy on main branch push

--------------------------------------------------------------------------------

13) Caching and performance

Streamlit caching strategy:
- @st.cache_data for baseline loading (team/player priors)
- @st.cache_data for simulation results (keyed by inputs hash)
- @st.cache_resource for nfl_data_py data pulls (expensive API calls)

Performance targets:
- Baseline build: <2 minutes (acceptable as one-time setup)
- 10k simulation: <30 seconds (Streamlit remains responsive)
- 50k simulation: <2 minutes (for high-accuracy runs)

Caching persistence:
- Streamlit session state for UI persistence
- File-based caching for baseline data (date-stamped)
- Optional disk caching for large simulations (metadata.json tracks inputs)

Bottlenecks and optimizations:
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
  - Decrease for expensive players unless elite projection
- Position tiers:
  - QB: top-3 get 15–25%; mid-tier 8–15%; punt 2–8%
  - RB: bellcows 12–20%; timeshares 4–12%; punt 1–6%
  - WR: alpha 10–18%; solid 6–12%; dart 2–8%
  - TE: elite 8–15%; serviceable 3–8%; punt 1–4%
  - DST: top 8–15%; mid 3–8%; punt 1–4%
- Apply noise and normalize to sum=100
- Export: ownership.csv [player_id, own_proj]

Inputs (adapter path):
- 2023–2024 priors → proj_mean baseline
- Schedule → total_line adjustments
- Rotowire salaries → salary/value considerations (optional)

Flow:
- Extract teams active for specified week
- Calculate base ownership score: f(proj_mean, position tier, game total)
- Apply salary adjustments if available
- Add noise (~10% CV) and normalize
- Export ownership.csv with stable player_id mapping
- Link to players.csv via player_id = TEAM_POS_NORMALIZEDNAME

Status:
- Base ownership heuristic: implemented in src/projections/ownership.py
- Salary integration: planned (requires Rotowire parsing)
- Fine-tuning: planned after optimizer integration and backtests

Algorithm details:
- Start with proj_mean percentile within position (0–100)
- Apply game total boost: +10 if total_line ≥ 50; -5 if ≤ 40
- Position modifiers:
  - QB: ×1.5 if proj_mean ≥ p80; ×0.7 if ≤ p40
  - RB: ×1.3 if touches ≥ 18; ×0.8 if ≤ 10
  - WR: ×1.2 if targets ≥ 8; ×0.9 if ≤ 4
  - TE: ×1.1 if targets ≥ 6; ×0.8 if ≤ 3
  - DST: ×1.0 (neutral baseline)
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
  - POS "D" → "DST"
  - Ownership normalization: if RST% ≤ 1, treat as fraction × 100; else as percent
  - VAL preserved as site_val (assumed points per $1k unless specified)

--------------------------------------------------------------------------------

16) Runbook (short)

Local:
1. `git clone <repo>`
2. `pip install -r requirements.txt`
3. `python scripts/build_baseline.py` (one-time setup)
4. `streamlit run app.py`

Production (Render):
1. Push to main branch
2. Auto-deploy triggers
3. Check logs for baseline build completion
4. Test UI and simulation via public URL

Week-of workflow:
1. Get players.csv from site
2. Upload via Streamlit UI
3. Review column mapping and warnings
4. Set sims (10k–50k) and seed
5. Run simulation
6. Download compare.csv and flags.csv
7. Review darts and value plays in optimizer

Debugging:
- Check metadata.json for run info and input hash
- Verify baseline files exist and are recent
- Test with known good players.csv first
- Check flags.csv for data quality issues

--------------------------------------------------------------------------------

17) Testing and validation

Unit tests (planned):
- Simulation determinism with fixed seed
- Column mapping and normalization accuracy
- Boom scoring and dart flag logic
- Value calculation edge cases

Integration tests:
- End-to-end: players.csv → simulation → outputs
- UI tests: upload, preview, download flow
- Caching behavior and cache invalidation

Manual validation (week-of):
- Spot-check sim_mean vs site_fpts for star players
- Verify boom_score distribution (should span 1–100)
- Check dart_flag prevalence (expect 5–15% of pool)
- Review flags.csv for obvious data errors

Performance benchmarks:
- 10k sims: baseline target <30s
- Memory usage: <2GB for typical slate (150–200 players)
- UI responsiveness: preview tables load <3s

Error cases:
- Empty or malformed players.csv → clear error message
- Missing baseline files → prompt to run build_baseline.py
- Network issues during nfl_data_py pulls → retry with backoff

Status:
- Core simulation: functional, needs seed determinism test
- UI components: partially implemented, needs caching tests
- Performance: not yet benchmarked

--------------------------------------------------------------------------------

18) Roadmap (post-MVP polish)

- Opponent adjustments (defense vs position) and home/away/weather
- Richer dependence model (copulas) and scenario toggles
- Hierarchical priors (role/archetype) for low-sample players
- Calibration/backtests with CRPS/Brier and reliability plots
- Performance: vectorization for 100k–500k trials
- Optimizer integration:
  - "Build from nfl_data_py" section that auto-loads outputs into Optimizer tab
  - "GPP Presets" section for one-click constraint presets (Small/Mid/Large)
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
- Metadata linkage: Each Simulator run includes metadata.json referencing sims, seed, and a "methodology": "monte_carlo_pdf" pointer.
- Optional UI link: the Simulator tab includes a small "Methodology" expander linking to docs/research/monte_carlo_football.pdf.

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
  - Mini-stacks: 2 pass catchers from same team (WR+WR, WR+TE) in good game environments.
- Correlation:
  - Positive: QB+WR, QB+TE, RB+DST (via game script)
  - Negative: RB+WR from same team (target competition)
  - Avoid: excessive same-game exposure (>5 from one game) unless shootout
- Ownership:
  - Target 15–30% total RST% for large-field GPPs
  - One "chalk" (>20% RST%), one "dart" (<10% RST%)
  - Ownership distribution matters more than raw sum
- Salary:
  - Leave $0–800 (DK format) for lineup flexibility
  - Balance stars and values; avoid "no man's land" ($6k–7k players without clear role)
- Uniqueness:
  - Low-owned stacks (QB+2 from <20% RST% game)
  - Game theory pivots off chalk in similar spots
  - Contrarian DST in projected high-scoring games

Optimizer integration (planned):
- Select preset: Small / Mid / Large (contest type)
- Sliders: min/max ownership sum, min boom_score, min value_per_1k
- Checkboxes: enforce bring-back, require mini-stack, salary leftover band
- Auto-constraints from latest sim outputs (boom_score, dart_flag, own_proj)

Status:
- Blueprint complete: docs/gpp_strategy_blueprint.md
- Preset logic: documented, not yet implemented
- Optimizer integration: planned next. We will add this "GPP Presets" section to the Optimizer tab so it's one click to apply these rules using the latest sim outputs.

--------------------------------------------------------------------------------

22) GPP Presets (Optimizer integration)

Purpose:
- Apply stacking, ownership, and value rules from docs/gpp_strategy_blueprint.md using sim outputs (boom_score, dart_flag, value_per_1k) to quickly generate tournament-ready constraints.

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
  - Button: "Apply preset" populates constraints
  - Then click "Optimize" to generate lineups
- Notes:
  - Presets can be edited after applying (constraints panel stays editable).
  - Defaults per preset will be tuned by slate and diagnostics feedback.

Status:
- Design complete
- Implementation: planned in next PR
- Integration: requires sim outputs (boom_score, dart_flag, value_per_1k) available in optimizer context

Default presets (draft):
- Small (≤150 entries):
  - RST% sum: 40–70% (some chalk acceptable)
  - Min boom_score: 50
  - Min value_per_1k: 3.0
  - Require: QB stack (single), 0–1 mini-stacks
- Mid (150–1000 entries):
  - RST% sum: 25–50% (more contrarian)
  - Min boom_score: 60
  - Min value_per_1k: 3.5
  - Require: QB stack (single/double), 1 mini-stack, ≥1 dart
- Large (>1000 entries):
  - RST% sum: 15–35% (highly contrarian)
  - Min boom_score: 70
  - Min value_per_1k: 4.0
  - Require: QB stack (double preferred), 1–2 mini-stacks, ≥2 darts

Compare to site FPTS (if present): delta_mean, pct_delta, beat_site_prob; diagnostics include MAE/RMSE/corr/coverage (rookies excluded)
- Streamlit:
  - Column mapping table, warnings shown
  - Caching works; Clear cache button
  - Previews with filters/sorts
  - 4 CSV download buttons + "Download all (zip)" including metadata.json

  - Generates players.csv and (optionally) ownership.csv from nfl_data_py, using schedule and 2023–2024 baseline
  - Stable player_id format and game_id mapping
- Optimizer (planned next):
  - "Build from nfl_data_py" section present and auto-loads players/sims into Optimizer
  - "GPP Presets" section present for one-click constraints application (see Section 22)

Planned next. We will add this "GPP Presets" section to the Optimizer tab so it's one click to apply these rules using the latest sim outputs.