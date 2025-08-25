# Comparing Projections and Reading Diagnostics

compare.csv fields
- site_fpts, sim_mean
- delta_mean = sim_mean − site_fpts
- pct_delta = delta_mean / max(1, |site_fpts|)
- beat_site_prob: P(sim ≥ site_fpts)
- value_per_1k = sim_mean / (SAL/1000)
- ceil_per_1k = p90 / (SAL/1000)
- boom_score (1–100) and dart_flag
- RST% and site_val if provided

diagnostics_summary.csv
- MAE/RMSE/corr vs site FPTS (rookies excluded)
- coverage_p10_p90: share where site_fpts ∈ [p10, p90]
- Counts and rookie_fallback counts

flags.csv
- Top absolute or percent deltas
- Data quality issues (missing salary/pos, unknown positions)

Workflow
- Check diagnostics_summary for coverage and correlation sanity.
- Sort compare by delta_mean, value_per_1k, boom_score; filter by position.
- Use flags.csv to inspect outliers; confirm mapping and SAL/RST% normals.