import argparse
import json
import os
from datetime import datetime
import pandas as pd

from src.ingest.site_players import load_site_players
from src.sim.game_simulator import simulate_week


def main():
    ap = argparse.ArgumentParser(description="Run simulator from site players CSV (MVP placeholder)")
    ap.add_argument("--season", type=int, required=True)
    ap.add_argument("--week", type=int, required=True)
    ap.add_argument("--players-site", type=str, required=True)
    ap.add_argument("--sims", type=int, default=10000)
    ap.add_argument("--seed", type=int, default=1337)
    ap.add_argument("--out", type=str, default="data/sim_week")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    df, mapping, warnings = load_site_players(args.players_site)
    sim_df = simulate_week(df, sims=args.sims, seed=args.seed)

    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join(args.out, f"{args.season}_w{args.week}_{ts}")
    os.makedirs(out_dir, exist_ok=True)

    sim_players_path = os.path.join(out_dir, "sim_players.csv")
    compare_path = os.path.join(out_dir, "compare.csv")
    diagnostics_path = os.path.join(out_dir, "diagnostics_summary.csv")
    flags_path = os.path.join(out_dir, "flags.csv")
    metadata_path = os.path.join(out_dir, "metadata.json")
    zip_path = os.path.join(out_dir, "simulator_outputs.zip")

    sim_df.to_csv(sim_players_path, index=False)
    sim_df[["player_id", "name", "pos", "team", "site_fpts", "sim_mean"]].to_csv(compare_path, index=False)
    pd.DataFrame([{"note": "MVP placeholder run; simulator core will be added next"}]).to_csv(diagnostics_path, index=False)
    pd.DataFrame(columns=["player_id", "flag", "detail"]).to_csv(flags_path, index=False)
    meta = {
        "season": int(args.season),
        "week": int(args.week),
        "sims": int(args.sims),
        "seed": int(args.seed),
        "created_utc": ts,
        "source": "cli",
        "version": "mvp-batch1",
        "columns_mapping": mapping,
        "warnings": warnings,
    }
    with open(metadata_path, "w") as f:
        json.dump(meta, f, indent=2)

    import zipfile
    with zipfile.ZipFile(zip_path, mode="w") as zf:
        zf.write(sim_players_path, arcname="sim_players.csv")
        zf.write(compare_path, arcname="compare.csv")
        zf.write(diagnostics_path, arcname="diagnostics_summary.csv")
        zf.write(flags_path, arcname="flags.csv")
        zf.writestr("metadata.json", json.dumps(meta, indent=2))

    print(f"Done. Outputs in {out_dir}")
    print(f"ZIP: {zip_path}")


if __name__ == "__main__":
    main()