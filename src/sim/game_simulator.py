import numpy as np
import pandas as pd

def simulate_week(players: pd.DataFrame, sims: int = 10000, seed: int = 1337) -> pd.DataFrame:
    """
    MVP placeholder: returns basic columns and sets sim_mean = site_fpts (fallback 0 if NaN).
    Will be replaced with Monte Carlo core in a later PR.
    """
    rng = np.random.default_rng(seed)
    df = players.copy()
    df["site_fpts"] = pd.to_numeric(df.get("site_fpts", pd.Series(dtype=float)), errors="coerce").fillna(0.0)
    df["sim_mean"] = df["site_fpts"]
    df["p50"] = df["site_fpts"]
    df["p90"] = df["site_fpts"]
    df["boom_prob"] = 0.0
    df["beat_site_prob"] = 0.5
    return df