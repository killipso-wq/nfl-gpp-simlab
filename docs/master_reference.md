# NFL GPP SimLab — Master Reference (UI‑First)

This document centralizes methodology, outputs, and governance while keeping README concise.

## Methodology
- Simulator is governed by "Realistic NFL Monte Carlo Simulation.pdf".
- High‑level: game/team environment, player usage distributions, correlations, seeded sampling, and lineup pool generation for curation.

## Outputs
- Primary artifacts:
  - sim_players.csv, compare.csv, diagnostics_summary.csv, flags.csv
  - metadata.json and simulator_outputs.zip
- File locations:
  - data/sim_week/{season}_w{week}_{timestamp}/
  - data/lineups/{season}_w{week}_{timestamp}/
  - data/generated/ (optional)

## UI Features
- Simulator: upload, set Sims/Seed, run, preview, download, send to curation
- Optimizer: curate from Simulator outputs; presets for Solo/20‑max/150‑max; export CSV/JSON

## Diagnostics
- MAE/RMSE/corr, coverage p10–p90; rookies excluded from aggregate metrics
- Seed determinism and caching notes

## Acceptance and Governance
- Definition of Done aligned to Roadmap
- PR flow, review guidance, and update cadence