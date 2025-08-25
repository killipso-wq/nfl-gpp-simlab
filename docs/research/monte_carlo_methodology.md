# Monte Carlo Methodology — Summary and Code Mapping

Primary source: docs/research/monte_carlo_football.pdf (your "Realistic NFL Monte Carlo Simulation.pdf").

Key concepts
- Environment: team/game context, OU/SPRD/ML/TM/P nudges, pass rate = neutral_xpass + PROE.
- Usage: player shares (targets, carries, red-zone) sampled via Beta/Dirichlet.
- Efficiency: yards per target/carry and TD rates via Normal/Lognormal + Poisson/Binomial allocations.
- Correlation: team/game shocks create dependence (QB↔receiver, RB vs WR).
- Rookies: fallback to site FPTS center with position-calibrated variance; flagged.

Mapping to implementation
- metrics/: builds team_week and player_week features from nfl_data_py.
- projections/prior_builder.py: aggregates 2023–2024 to priors with shrinkage.
- sim/game_simulator.py:
  - Draw per-sim environment shocks → consistent within game
  - Sample usage shares per role → allocate volume per team
  - Sample efficiency → convert to DK fantasy points; clamp negatives per position rules
  - Derive p10/p75/p90/p95, mean, boom/beat-site probabilities
- projections/value_metrics.py: value_per_1k, ceil_per_1k, deltas
- projections/boom_score.py: boom_prob, boom_score (1–100), dart_flag
- projections/diagnostics.py: MAE/RMSE/corr/coverage; rookies excluded

Determinism
- Seeded RNG with explicit seed in metadata; cache identical inputs.

Outputs
- sim_players.csv, compare.csv, diagnostics_summary.csv, flags.csv, metadata.json, ZIP bundle.