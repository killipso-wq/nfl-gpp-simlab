import io
import json
import os
from datetime import datetime
import pandas as pd
import streamlit as st

from src.ingest.site_players import load_site_players
from src.sim.game_simulator import simulate_week

st.set_page_config(page_title="NFL GPP Sim Optimizer", layout="wide")

st.title("NFL GPP Sim Optimizer")
st.caption("Simulator MVP + Presets scaffold")

sim_tab, opt_tab = st.tabs(["Simulator", "Optimizer (scaffold)"])

with sim_tab:
    st.subheader("Upload players.csv")
    uploaded = st.file_uploader("Upload your players.csv", type=["csv"]) 

    col1, col2, col3 = st.columns(3)
    season = col1.number_input("Season", value=2025, step=1)
    week = col2.number_input("Week", value=1, step=1)
    sims = col3.number_input("Simulations", value=10000, step=1000)
    seed = st.number_input("Random seed", value=1337, step=1)

    if uploaded is not None:
        with st.spinner("Parsing and mapping columns..."):
            site_df, mapping, warnings = load_site_players(uploaded)
        st.success("Parsed players.csv")
        with st.expander("Column mapping"):
            st.json(mapping)
        if warnings:
            with st.expander("Warnings / Notes"):
                for w in warnings:
                    st.warning(w)
        st.dataframe(site_df.head(20), use_container_width=True)

        run_btn = st.button("Run simulator (MVP placeholder)")
        if run_btn:
            with st.spinner("Running placeholder simulator..."):
                sim_df = simulate_week(site_df, sims=int(sims), seed=int(seed))
                ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
                out_dir = f"data/sim_week/{int(season)}_w{int(week)}_{ts}"
                os.makedirs(out_dir, exist_ok=True)

                sim_players_path = os.path.join(out_dir, "sim_players.csv")
                compare_path = os.path.join(out_dir, "compare.csv")
                diagnostics_path = os.path.join(out_dir, "diagnostics_summary.csv")
                flags_path = os.path.join(out_dir, "flags.csv")
                metadata_path = os.path.join(out_dir, "metadata.json")

                sim_df.to_csv(sim_players_path, index=False)
                sim_df[["player_id", "name", "pos", "team", "site_fpts", "sim_mean"]].to_csv(compare_path, index=False)
                pd.DataFrame([{"note": "MVP placeholder run; simulator core will be added next"}]).to_csv(diagnostics_path, index=False)
                pd.DataFrame(columns=["player_id", "flag", "detail"]).to_csv(flags_path, index=False)
                meta = {
                    "season": int(season),
                    "week": int(week),
                    "sims": int(sims),
                    "seed": int(seed),
                    "created_utc": ts,
                    "source": "streamlit_app",
                    "version": "mvp-batch1",
                    "columns_mapping": mapping,
                }
                with open(metadata_path, "w") as f:
                    json.dump(meta, f, indent=2)

                import zipfile
                mem = io.BytesIO()
                with zipfile.ZipFile(mem, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.write(sim_players_path, arcname="sim_players.csv")
                    zf.write(compare_path, arcname="compare.csv")
                    zf.write(diagnostics_path, arcname="diagnostics_summary.csv")
                    zf.write(flags_path, arcname="flags.csv")
                    zf.writestr("metadata.json", json.dumps(meta, indent=2))
                mem.seek(0)

            st.success(f"Done. Outputs written to {out_dir}")
            st.download_button("Download outputs ZIP", data=mem, file_name="simulator_outputs.zip", mime="application/zip")
            st.dataframe(sim_df.head(50), use_container_width=True)

    st.markdown("---")
    st.write("Methodology")
    st.caption("Link to methodology PDF (optional)")
    st.link_button("Open Monte Carlo Methodology (PDF)", "docs/research/monte_carlo_football.pdf")

with opt_tab:
    st.info("Optimizer + GPP Presets scaffold will be added in a subsequent PR.")