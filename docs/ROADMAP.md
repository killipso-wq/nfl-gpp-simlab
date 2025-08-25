# NFL GPP SimLab — Roadmap and Task Lists

This document tracks planned work, checklists, and post‑MVP follow‑ups. It complements the UI‑first README. See also: "Realistic NFL Monte Carlo Simulation.pdf".

## Master Checklist

- Streamlit — Simulator tab
  - File upload, Sims, Seed
  - Detected column mapping table with warnings
  - Caching + "Clear cache"
  - Previews with filters/sorts
  - Downloads (4 CSVs + ZIP with metadata.json)
  - Methodology link to the PDF
- Optimizer tab
  - "Curate from Simulator" as primary flow
  - Presets (Solo, 20‑max, 150‑max) apply stacking/ownership/salary/diversity constraints
  - "Build from projections" remains optional (load a players.csv without a sim pool)
- Outputs
  - sim_players.csv with p10/p25/mean/p75/p90/p95, sim_std, boom metrics
  - compare.csv with deltas vs site FPTS if present
  - diagnostics_summary.csv (MAE/RMSE/corr/coverage, by position and overall)
  - flags.csv (largest deltas, data quality, unknown positions)
  - metadata.json and simulator_outputs.zip bundle

## Acceptance Criteria (DoD)
- Baseline builds present (if needed for priors)
- Simulator artifacts generated and downloadable via UI
- SAL/VAL/RST% surfaced in compare when provided
- UI Simulator features complete; methodology link present
- Optimizer presets implemented and functional

## Optimizer Presets (Blueprint)
- Preset selector: Solo / 20‑max / 150‑max
- Toggles: bring‑back, mini‑stacks, salary leftover, require darts
- Sliders: ownership band, boom_score threshold, value_per_1k threshold
- Flow: Apply preset → constraints populate → Optimize → Export

## Diagnostics and QA
- Deterministic seeding; identical inputs yield identical outputs
- Sanity checks on boom_prob, beat_site_prob (non‑degenerate)
- Coverage of [p10, p90]; rookies excluded from MAE/RMSE/corr/coverage
- flags.csv highlights plausible outliers

## Follow‑ups (post‑MVP)
- Opponent/home‑away/weather adjustments
- Richer dependence model (copulas) and scenario toggles
- Backtesting and calibration (CRPS/Brier, reliability)
- Performance scaling (100k–500k trials)
- DST enhancements as needed
- UI polish: presets defaults by slate feedback

## Governance and Updates
- Use PRs for changes; keep README UI‑first
- Update cadence and status notes in PR descriptions
- After merges, clear build cache on Render as needed