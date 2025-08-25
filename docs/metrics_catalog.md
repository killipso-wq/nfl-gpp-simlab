# Metrics Catalog (2023–2024 Warehouse)

Team-level (team_week.csv)
- pace (sec/play), plays/game, neutral_xpass, PROE (actual pass rate − neutral_xpass)
- EPA/play, success rate, scoring rates
- Optional: home/away, dome/outdoor, weather placeholders

Player-level (player_week.csv)
- Usage shares: targets, carries, RZ targets/carries, inside-10 carries
- Efficiency: yards/target, yards/carry, TD%, receptions, aDOT, RACR, WOPR
- QB: cpoe_mean, cp_mean, epa per dropback, sack_rate, deep_rate, aDOT

Game-level (game_week.csv)
- Aggregates to support correlation and environment sampling

Derived simulator metrics
- sim_mean, p10/p75/p90/p95, sim_std
- boom_prob, beat_site_prob, value_per_1k, ceil_per_1k, boom_score, dart_flag
- Diagnostics: MAE, RMSE, corr, coverage_p10_p90