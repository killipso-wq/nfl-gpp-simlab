from typing import Dict, List, Tuple
import pandas as pd
import numpy as np

NAME_COLS = ["name", "player", "player_name", "playername", "player id", "player_id", "PLAYER", "Name", "Player"]
TEAM_COLS = ["team", "tm", "Team"]
OPP_COLS = ["opp", "opponent", "Opp"]
POS_COLS = ["pos", "position", "Pos"]
SAL_COLS = ["salary", "sal", "Salary"]
FPTS_COLS = ["fpts", "proj", "projection", "points", "FPTS", "Proj"]
OWN_COLS = ["rst%", "own%", "ownership", "projected ownership", "own", "Ownership", "OWN%"]


def _first_present(df: pd.DataFrame, candidates: List[str]) -> str:
    lc = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lc:
            return lc[cand.lower()]
    return ""


def load_site_players(fp) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    """
    Load site players CSV and normalize columns:
    - Column mapping for [name, team, opp, pos, salary, site_fpts, site_own]
    - POS: 'D' -> 'DST'
    - Ownership normalization: if <= 1, multiply by 100
    Returns (df, mapping, warnings)
    """
    df = pd.read_csv(fp)
    warnings: List[str] = []

    mapping: Dict[str, str] = {}
    mapping["name"] = _first_present(df, NAME_COLS)
    mapping["team"] = _first_present(df, TEAM_COLS)
    mapping["opp"] = _first_present(df, OPP_COLS)
    mapping["pos"] = _first_present(df, POS_COLS)
    mapping["salary"] = _first_present(df, SAL_COLS)
    mapping["site_fpts"] = _first_present(df, FPTS_COLS)
    mapping["site_own"] = _first_present(df, OWN_COLS)

    out = pd.DataFrame()
    for k, src in mapping.items():
        if src:
            out[k] = df[src]
        else:
            out[k] = np.nan
            warnings.append(f"Missing column for {k}; filled with NaN")

    out["pos"] = out["pos"].astype(str).str.upper().str.replace("D", "DST", regex=False)

    if out["site_own"].notna().any():
        own = pd.to_numeric(out["site_own"], errors="coerce")
        frac_share = (own <= 1).mean(skipna=True)
        if frac_share > 0.5:
            own = own * 100.0
            warnings.append("Ownership looked fractional; multiplied by 100")
        out["site_own"] = own
    else:
        out["site_own"] = np.nan

    out["salary"] = pd.to_numeric(out["salary"], errors="coerce")
    out["site_fpts"] = pd.to_numeric(out["site_fpts"], errors="coerce")

    out["player_id"] = (
        out["name"].astype(str).str.lower().str.replace(r"[^a-z0-9]+", "-", regex=True)
        + "-" + out["team"].astype(str).str.lower()
    )

    cols = ["player_id", "name", "team", "opp", "pos", "salary", "site_fpts", "site_own"]
    out = out[cols]

    return out, mapping, warnings