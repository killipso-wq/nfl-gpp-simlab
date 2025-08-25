"""
NFL GPP Simulator - Streamlit UI
Main entrypoint for the web application.
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
from typing import Dict, List
import zipfile
import tempfile

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.projections.simulator import (
    normalize_columns, 
    run_simulation, 
    save_simulation_outputs
)

# Configure Streamlit page
st.set_page_config(
    page_title="NFL GPP Simulator",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    st.title("🏈 NFL GPP Simulator")
    st.markdown("Upload players.csv, run Monte Carlo simulations, and analyze projections vs site data.")
    
    # Sidebar inputs
    st.sidebar.header("Simulation Parameters")
    
    season = st.sidebar.number_input("Season", min_value=2020, max_value=2030, value=2025)
    week = st.sidebar.number_input("Week", min_value=1, max_value=22, value=1)
    sims = st.sidebar.number_input("Simulations", min_value=100, max_value=100000, value=10000, step=1000)
    seed = st.sidebar.number_input("Random Seed", value=1337)
    
    # File upload
    st.header("📁 Upload Players Data")
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=['csv'],
        help="Upload players.csv with columns like PLAYER, POS, TEAM, OPP, SAL, FPTS, RST%"
    )
    
    if uploaded_file is not None:
        try:
            # Load and display raw data
            df_raw = pd.read_csv(uploaded_file)
            st.subheader("Raw Data Preview")
            st.dataframe(df_raw.head(), use_container_width=True)
            
            # Normalize columns
            df_normalized, column_mapping, warnings = normalize_columns(df_raw)
            
            # Display column mapping
            st.subheader("🔍 Column Detection & Mapping")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Detected Mappings:**")
                if column_mapping:
                    for normalized, original in column_mapping.items():
                        st.write(f"• {normalized} ← {original}")
                else:
                    st.warning("No standard columns detected")
            
            with col2:
                if warnings:
                    st.write("**⚠️ Warnings:**")
                    for warning in warnings:
                        st.warning(warning)
                else:
                    st.success("✅ No validation warnings")
            
            # Show normalized data
            st.subheader("Normalized Data")
            st.dataframe(df_normalized.head(), use_container_width=True)
            
            # Validation summary
            required_cols = ['player_name', 'position', 'team', 'opponent']
            missing_required = [col for col in required_cols if col not in df_normalized.columns]
            
            if missing_required:
                st.error(f"Missing required columns: {', '.join(missing_required)}")
                st.stop()
            
            if 'fpts' not in df_normalized.columns:
                st.error("FPTS column is required for simulation")
                st.stop()
                
            st.success(f"✅ Data validated: {len(df_normalized)} players loaded")
            
            # Run simulation button
            if st.button("🚀 Run Simulation", type="primary"):
                with st.spinner(f"Running {sims:,} simulations..."):
                    try:
                        # Run simulation
                        results = run_simulation(df_normalized, sims=sims, seed=seed)
                        
                        # Save outputs
                        output_dir = "data/sim_week"
                        os.makedirs(output_dir, exist_ok=True)
                        zip_path = save_simulation_outputs(
                            results, output_dir, season, week, sims, seed, column_mapping
                        )
                        
                        st.success("✅ Simulation complete!")
                        
                        # Display results tabs
                        tab1, tab2, tab3, tab4 = st.tabs(["Sim Players", "Compare", "Diagnostics", "Flags"])
                        
                        with tab1:
                            st.subheader("📊 Simulation Results")
                            sim_players = results['sim_players']
                            
                            # Add filters
                            positions = ['All'] + sorted(sim_players['position'].dropna().unique().tolist())
                            pos_filter = st.selectbox("Filter by Position", positions)
                            
                            if pos_filter != 'All':
                                display_df = sim_players[sim_players['position'] == pos_filter]
                            else:
                                display_df = sim_players
                            
                            # Sort options
                            sort_by = st.selectbox("Sort by", ['sim_mean', 'ceiling_p90', 'boom_prob'])
                            display_df = display_df.sort_values(sort_by, ascending=False)
                            
                            st.dataframe(display_df, use_container_width=True)
                        
                        with tab2:
                            st.subheader("🔄 Site vs Sim Comparison")
                            compare_df = results['compare']
                            
                            if not compare_df.empty:
                                # Add filters
                                pos_filter_comp = st.selectbox("Filter by Position ", positions, key="compare_filter")
                                
                                if pos_filter_comp != 'All':
                                    display_comp = compare_df[compare_df['position'] == pos_filter_comp]
                                else:
                                    display_comp = compare_df
                                
                                # Sort options
                                sort_by_comp = st.selectbox("Sort by ", 
                                    ['delta_mean', 'pct_delta', 'boom_score', 'value_per_1k'], 
                                    key="compare_sort"
                                )
                                display_comp = display_comp.sort_values(sort_by_comp, ascending=False)
                                
                                st.dataframe(display_comp, use_container_width=True)
                            else:
                                st.info("No comparison data available")
                        
                        with tab3:
                            st.subheader("📈 Diagnostics Summary")
                            diagnostics_df = results['diagnostics_summary']
                            
                            if not diagnostics_df.empty:
                                st.dataframe(diagnostics_df, use_container_width=True)
                                
                                # Show some basic stats
                                if 'mae' in diagnostics_df.columns:
                                    avg_mae = diagnostics_df['mae'].mean()
                                    st.metric("Average MAE", f"{avg_mae:.2f}")
                            else:
                                st.info("No diagnostics data available")
                        
                        with tab4:
                            st.subheader("🚩 Notable Flags")
                            flags_df = results['flags']
                            
                            if not flags_df.empty:
                                st.dataframe(flags_df, use_container_width=True)
                            else:
                                st.info("No flags generated")
                        
                        # Download section
                        st.subheader("📥 Download Results")
                        
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            # Individual CSV downloads
                            for name, df in results.items():
                                if isinstance(df, pd.DataFrame) and not df.empty:
                                    csv = df.to_csv(index=False)
                                    st.download_button(
                                        label=f"Download {name}.csv",
                                        data=csv,
                                        file_name=f"{name}.csv",
                                        mime="text/csv"
                                    )
                        
                        with col2:
                            # ZIP download
                            if os.path.exists(zip_path):
                                with open(zip_path, "rb") as file:
                                    st.download_button(
                                        label="📦 Download All (ZIP)",
                                        data=file.read(),
                                        file_name="simulator_outputs.zip",
                                        mime="application/zip"
                                    )
                        
                        with col3:
                            st.info(f"**Output Directory:**\n`{os.path.dirname(zip_path)}`")
                        
                    except Exception as e:
                        st.error(f"Simulation failed: {str(e)}")
                        st.exception(e)
        
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.exception(e)
    
    else:
        # Show sample data format
        st.info("👆 Upload a CSV file to get started")
        
        st.subheader("📋 Expected CSV Format")
        st.markdown("""
        Your CSV should include these columns (case-insensitive):
        
        **Required:**
        - `PLAYER` / `name` / `player_name` - Player name
        - `POS` / `position` - Position (QB, RB, WR, TE, DST)
        - `TEAM` / `tm` - Player's team
        - `OPP` / `opponent` - Opponent team
        - `FPTS` / `proj` / `projection` - Projected fantasy points
        
        **Optional but recommended:**
        - `SAL` / `salary` - Player salary
        - `RST%` / `own` / `ownership` - Projected ownership %
        - `O/U` - Game total (over/under)
        - `SPRD` - Point spread
        """)
        
        # Show sample data
        st.subheader("🔍 Sample Data")
        sample_path = "players_sample.csv"
        if os.path.exists(sample_path):
            sample_df = pd.read_csv(sample_path)
            st.dataframe(sample_df, use_container_width=True)
            
            # Provide sample download
            with open(sample_path, "rb") as file:
                st.download_button(
                    label="📥 Download Sample CSV",
                    data=file.read(),
                    file_name="players_sample.csv",
                    mime="text/csv"
                )
        else:
            st.warning("Sample CSV not found")
    
    # Cache management
    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear Cache"):
        st.cache_data.clear()
        st.sidebar.success("Cache cleared!")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: gray;'>
        NFL GPP Simulator | Monte Carlo projections for DFS optimization<br>
        📊 Telemetry disabled | 🔒 Data processed locally
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()