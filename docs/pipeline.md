# Metrics Warehouse Pipeline (2023–2024)

Purpose
- Build team and player priors that inform the simulator's distributions.

Stages
1) Sources and prep (metrics/sources.py, prep.py)
   - Pull weekly logs via nfl_data_py; optional PBP joins for EP/WP/CP/xpass/XYAC
2) Feature computation
   - team_metrics.py: pace, neutral_xpass, PROE, EPA/play, success rate
   - player_metrics.py: usage shares, efficiency rates, WR/TE WOPR/RACR
3) Summarization and shrinkage
   - projections/prior_builder.py produces team_priors.csv, player_priors.csv
4) Boom thresholds
   - scripts/build_boom_thresholds.py → data/baseline/boom_thresholds.json (default p90)

Commands
```
python scripts/build_baseline.py --start 2023 --end 2024 --out data
python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90
```

Outputs
- data/baseline/team_priors.csv
- data/baseline/player_priors.csv
- data/baseline/boom_thresholds.json