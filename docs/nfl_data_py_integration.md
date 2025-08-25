# nfl_data_py Integration — Adapter and Ownership

Purpose
- When a site players.csv is not available, generate simulator-ready inputs from nfl_data_py.

Adapter output
- players.csv: player_id, name, team, position, proj_mean, proj_p75, proj_p90, game_id
- ownership.csv (optional): player_id, own_proj (0–100)

Stable IDs
- player_id = TEAM_POS_NORMALIZEDNAME
- game_id = AWAY@HOME (from schedule)

Ownership heuristic
- Base: own_score ∝ proj_mean
- Adjust by game total (schedule total_line normalized ~44)
- If salaries provided (Rotowire), boost better value
- Normalize to 0–100% → own_proj

Commands
```
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/
# With Rotowire salaries
python -m src.ingest.nfl_data_py_to_simulator --season 2025 --week 1 --site dk --out data/ --rotowire path/to/rotowire.csv
```

Streamlit integration
- Optimizer tab (planned) will include "Build from nfl_data_py" to run this adapter and auto-load outputs for curation.