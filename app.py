"""
NFL GPP Sim Optimizer - Streamlit App

Main entry point for the Streamlit UI as specified in Master Reference.
Implements Simulator tab with file upload, Monte Carlo simulation, and downloads.
"""

import streamlit as st
import os
import sys
import json
import tempfile
from pathlib import Path

# Add project root for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Only import when actually needed to avoid dependency issues
try:
    from src.projections.run_week_from_site_players import (
        load_players_site, validate_players_data, run_simulation as run_mc_simulation
    )
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    IMPORT_ERROR = str(e)


def main():
    """Main Streamlit app entry point."""
    st.set_page_config(
        page_title="NFL GPP Sim Optimizer",
        page_icon="🏈",
        layout="wide"
    )
    
    st.title("🏈 NFL GPP Sim Optimizer")
    st.markdown("Monte Carlo simulation for NFL DFS projections and value analysis")
    
    # Create tabs per Master Reference
    tab1, tab2 = st.tabs(["Simulator", "Optimizer"])
    
    with tab1:
        simulator_tab()
    
    with tab2:
        optimizer_tab()


def simulator_tab():
    """
    Simulator tab implementation per Master Reference specification.
    
    Features:
    - File upload for players.csv
    - Sims and Seed inputs
    - Column mapping table with warnings
    - Caching + "Clear cache" 
    - Previews with filters/sorts
    - Downloads (4 CSVs + ZIP with metadata.json)
    - Methodology link to PDF
    """
    st.header("Monte Carlo Simulator")
    
    # Check dependencies
    if not DEPENDENCIES_AVAILABLE:
        st.error(f"Required dependencies not available: {IMPORT_ERROR}")
        st.info("Please install requirements: `pip install -r requirements.txt`")
        return
    
    # Methodology link per Master Reference
    with st.expander("📖 Methodology"):
        st.markdown("""
        This simulator implements the Monte Carlo methodology described in:
        **docs/research/monte_carlo_football.pdf**
        
        Key features:
        - Position-calibrated outcome distributions
        - Deterministic results via fixed seed
        - Proper statistical estimators (mean, variance, std dev, quantiles)
        - Boom probability and value metrics
        """)
    
    # Input section
    st.subheader("1. Upload Players File")
    
    uploaded_file = st.file_uploader(
        "Upload your players.csv file",
        type=['csv'],
        help="Expected columns: PLAYER, POS, TEAM, OPP. Optional: FPTS, SAL, RST%, O/U, SPRD"
    )
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(mode='w+b', suffix='.csv', delete=False) as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        try:
            # Load and validate players
            players = load_players_site(tmp_file_path)
            validation = validate_players_data(players)
            
            # Display column mapping table
            st.subheader("2. Column Mapping")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Detected Columns:**")
                for col in validation['found_columns']:
                    st.write(f"✓ {col}")
            
            with col2:
                st.write("**Required Mapping:**")
                for req_col, mapped_col in validation['column_mapping'].items():
                    st.write(f"{req_col} → {mapped_col}")
            
            # Show warnings
            if validation['warnings']:
                st.warning("Warnings:")
                for warning in validation['warnings']:
                    st.write(f"⚠️ {warning}")
            
            # Simulation parameters
            st.subheader("3. Simulation Parameters")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sims = st.number_input(
                    "Number of Trials (sims)",
                    min_value=100,
                    max_value=50000, 
                    value=1000,
                    step=100,
                    help="Number of Monte Carlo trials per player"
                )
            
            with col2:
                seed = st.number_input(
                    "Base Seed",
                    min_value=1,
                    max_value=999999,
                    value=42,
                    help="Seed for reproducible results"
                )
            
            with col3:
                if st.button("Clear Cache"):
                    if 'simulation_cache' in st.session_state:
                        del st.session_state.simulation_cache
                    st.success("Cache cleared!")
            
            # Run simulation
            if st.button("🚀 Run Simulation", type="primary"):
                # Check cache
                cache_key = f"{uploaded_file.name}_{sims}_{seed}_{len(players)}"
                
                if 'simulation_cache' not in st.session_state:
                    st.session_state.simulation_cache = {}
                
                if cache_key in st.session_state.simulation_cache:
                    st.info("Using cached results...")
                    results = st.session_state.simulation_cache[cache_key]
                else:
                    # Run simulation
                    with st.spinner("Running Monte Carlo simulation..."):
                        # Create mock args object
                        class MockArgs:
                            def __init__(self):
                                self.season = 2025
                                self.week = 1
                                self.players_site = tmp_file_path
                                self.team_priors = "data/baseline/team_priors.csv"
                                self.player_priors = "data/baseline/player_priors.csv"
                                self.boom_thresholds = "data/baseline/boom_thresholds.json"
                                self.sims = sims
                                self.seed = seed
                                self.n_jobs = 1
                                self.quantiles = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
                                self.alpha = 0.05
                                self.out = "data/sim_week"
                        
                        # Need to ensure baseline files exist
                        ensure_baseline_files()
                        
                        try:
                            results = run_mc_simulation(MockArgs())
                            st.session_state.simulation_cache[cache_key] = results
                            st.success(f"Simulation completed! Processed {len(results['players'])} players.")
                        except Exception as e:
                            st.error(f"Simulation failed: {e}")
                            return
                
                # Display results
                display_simulation_results(results)
                
        except Exception as e:
            st.error(f"Error processing file: {e}")
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)


def ensure_baseline_files():
    """Ensure baseline files exist for simulation."""
    baseline_dir = "data/baseline"
    
    # Create minimal baseline files if they don't exist
    if not os.path.exists(f"{baseline_dir}/team_priors.csv"):
        st.info("Creating baseline files...")
        os.system("python scripts/build_baseline.py --start 2023 --end 2024 --out data")
        os.system("python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90")


def display_simulation_results(results):
    """Display simulation results with previews and download options."""
    st.subheader("4. Results")
    
    players = results['players']
    
    # Preview section
    st.write("**Preview (first 10 players):**")
    
    # Create preview data
    preview_data = []
    for player in players[:10]:
        preview_data.append({
            'Player': player['PLAYER'],
            'Pos': player['POS'],
            'Team': player['TEAM'],
            'Sim Mean': f"{player['sim_mean']:.2f}",
            'P90': f"{player['ceiling_p90']:.2f}",
            'P10': f"{player['floor_p10']:.2f}",
            'Site FPTS': player['site_fpts']
        })
    
    st.dataframe(preview_data)
    
    # Download section
    st.subheader("5. Downloads")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    # Generate output files for download
    output_dir = "data/sim_week"
    
    with col1:
        if os.path.exists(f"{output_dir}/sim_players.csv"):
            with open(f"{output_dir}/sim_players.csv", "r") as f:
                st.download_button(
                    "📊 sim_players.csv",
                    data=f.read(),
                    file_name="sim_players.csv",
                    mime="text/csv"
                )
    
    with col2:
        if os.path.exists(f"{output_dir}/compare.csv"):
            with open(f"{output_dir}/compare.csv", "r") as f:
                st.download_button(
                    "📈 compare.csv",
                    data=f.read(),
                    file_name="compare.csv",
                    mime="text/csv"
                )
    
    with col3:
        if os.path.exists(f"{output_dir}/diagnostics_summary.csv"):
            with open(f"{output_dir}/diagnostics_summary.csv", "r") as f:
                st.download_button(
                    "🔍 diagnostics.csv",
                    data=f.read(),
                    file_name="diagnostics_summary.csv",
                    mime="text/csv"
                )
    
    with col4:
        if os.path.exists(f"{output_dir}/flags.csv"):
            with open(f"{output_dir}/flags.csv", "r") as f:
                st.download_button(
                    "🚩 flags.csv",
                    data=f.read(),
                    file_name="flags.csv",
                    mime="text/csv"
                )
    
    with col5:
        if os.path.exists(f"{output_dir}/metadata.json"):
            with open(f"{output_dir}/metadata.json", "r") as f:
                st.download_button(
                    "📋 metadata.json",
                    data=f.read(),
                    file_name="metadata.json",
                    mime="application/json"
                )


def optimizer_tab():
    """
    Optimizer tab placeholder per Master Reference.
    
    Planned features:
    - "Build from nfl_data_py" section
    - "GPP Presets" section
    """
    st.header("GPP Optimizer")
    st.info("🚧 This tab will be implemented in a future update")
    
    st.subheader("Planned Features:")
    st.write("""
    - **Build from nfl_data_py**: Generate players.csv from historical data
    - **GPP Presets**: One-click constraint presets (Small/Mid/Large contests)
    - **Lineup Optimization**: Generate optimal DFS lineups using simulation results
    """)


if __name__ == "__main__":
    main()