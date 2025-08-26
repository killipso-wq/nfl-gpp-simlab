"""
NFL GPP Simulator - Streamlit UI
Implements the Simulator tab per Master Reference specifications.
"""

import streamlit as st
import pandas as pd
import numpy as np
import zipfile
import io
import json
from pathlib import Path
import hashlib
from typing import Optional, Dict, Any, Tuple

from src.ingest.site_players import load_site_players
from src.projections.monte_carlo import MonteCarloSimulator


# Page configuration
st.set_page_config(
    page_title="NFL GPP Simulator", 
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Session state initialization
if 'simulation_cache' not in st.session_state:
    st.session_state.simulation_cache = {}


def get_file_hash(file_content: bytes) -> str:
    """Generate hash of file content for caching."""
    return hashlib.md5(file_content).hexdigest()


def cache_key(file_hash: str, sims: int, seed: Optional[int]) -> str:
    """Generate cache key for simulation results."""
    return f"{file_hash}_{sims}_{seed}"


@st.cache_data
def run_simulation_cached(players_df: pd.DataFrame, n_sims: int, seed: Optional[int]) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
    """Cached simulation runner."""
    simulator = MonteCarloSimulator(seed=seed)
    sim_df = simulator.simulate_players(players_df, n_sims)
    compare_df = simulator.generate_compare_table(sim_df, players_df)
    
    # Generate diagnostic data for display
    diagnostics_df = simulator.generate_diagnostics(compare_df)
    flags_df = simulator.generate_flags(compare_df)
    
    metadata = {
        'boom_thresholds': simulator.metadata.get('boom_thresholds', {}),
        'calibrated_from_current_run': simulator.metadata.get('calibrated_from_current_run', True),
        'diagnostics': diagnostics_df,
        'flags': flags_df
    }
    
    return sim_df, compare_df, metadata


def create_download_zip(sim_df: pd.DataFrame, compare_df: pd.DataFrame, 
                       original_df: pd.DataFrame, metadata: Dict) -> bytes:
    """Create ZIP file with all simulation outputs."""
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # sim_players.csv
        sim_output = sim_df[['player_id', 'PLAYER', 'POS', 'TEAM', 'sim_mean', 
                           'floor_p10', 'p75', 'ceiling_p90', 'p95', 'boom_prob', 'rookie_fallback']]
        if 'SAL' in sim_df.columns:
            sim_output = sim_output.merge(sim_df[['player_id', 'SAL']], on='player_id', how='left')
        
        sim_csv = sim_output.to_csv(index=False)
        zipf.writestr('sim_players.csv', sim_csv)
        
        # compare.csv
        compare_csv = compare_df.to_csv(index=False)
        zipf.writestr('compare.csv', compare_csv)
        
        # diagnostics_summary.csv
        if 'diagnostics' in metadata:
            diag_csv = metadata['diagnostics'].to_csv(index=False)
            zipf.writestr('diagnostics_summary.csv', diag_csv)
        
        # flags.csv
        if 'flags' in metadata:
            flags_csv = metadata['flags'].to_csv(index=False)
            zipf.writestr('flags.csv', flags_csv)
        
        # metadata.json
        json_metadata = {
            'run_timestamp': pd.Timestamp.now().isoformat(),
            'methodology': 'monte_carlo_pdf',
            'player_count': len(original_df),
            'boom_thresholds': metadata.get('boom_thresholds', {}),
            'calibrated_from_current_run': metadata.get('calibrated_from_current_run', True)
        }
        zipf.writestr('metadata.json', json.dumps(json_metadata, indent=2))
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def main():
    """Main Streamlit application."""
    
    # Header with methodology links
    st.title("🏈 NFL GPP Simulator")
    
    with st.expander("📚 Documentation & Methodology"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**[Master Reference](docs/master_reference.md)** - Complete specification")
        with col2:
            st.markdown("**[Methodology PDF](docs/research/monte_carlo_football.pdf)** - Research foundation")
    
    st.markdown("---")
    
    # Tab for Simulator (no Optimizer in MVP)
    st.header("Monte Carlo Simulator")
    
    # File input section
    st.subheader("📁 Player Data Input")
    
    input_method = st.radio(
        "Choose input method:",
        ["Upload CSV file", "Use default file path"],
        horizontal=True
    )
    
    players_df = None
    load_metadata = None
    file_content = None
    
    if input_method == "Upload CSV file":
        uploaded_file = st.file_uploader(
            "Upload players CSV file",
            type=['csv'],
            help="Upload a CSV file with player data (PLAYER, POS, TEAM, OPP, FPTS, etc.)"
        )
        
        if uploaded_file is not None:
            file_content = uploaded_file.getvalue()
            
            try:
                # Save uploaded file temporarily
                temp_path = f"/tmp/{uploaded_file.name}"
                with open(temp_path, 'wb') as f:
                    f.write(file_content)
                
                players_df, load_metadata = load_site_players(temp_path)
                st.success(f"✅ Loaded {len(players_df)} players from {uploaded_file.name}")
                
            except Exception as e:
                st.error(f"❌ Error loading file: {e}")
                
    else:
        # Use default file path
        default_path = "data/site/2025_w1_players.csv"
        file_path_input = st.text_input(
            "File path:",
            value=default_path,
            help="Path to players CSV file"
        )
        
        if st.button("Load File") or (file_path_input and Path(file_path_input).exists()):
            try:
                players_df, load_metadata = load_site_players(file_path_input)
                st.success(f"✅ Loaded {len(players_df)} players from {file_path_input}")
                
                # Read file content for caching
                with open(file_path_input, 'rb') as f:
                    file_content = f.read()
                    
            except Exception as e:
                st.error(f"❌ Error loading file: {e}")
    
    # Display column mapping and warnings if data is loaded
    if players_df is not None and load_metadata is not None:
        
        # Column mapping table
        with st.expander("🔍 Column Mapping Detection", expanded=False):
            mapping_df = load_metadata['column_mapping_table']
            
            # Color code the status
            def color_status(val):
                if val == 'Found':
                    return 'background-color: #d4edda'
                elif val == 'Missing':
                    return 'background-color: #f8d7da'
                else:
                    return 'background-color: #fff3cd'
            
            styled_mapping = mapping_df.style.applymap(color_status, subset=['Status'])
            st.dataframe(styled_mapping, use_container_width=True)
        
        # Warnings
        if load_metadata['warnings']:
            with st.expander("⚠️ Data Warnings", expanded=True):
                for warning in load_metadata['warnings']:
                    st.warning(warning)
        
        # Simulation parameters
        st.subheader("⚙️ Simulation Parameters")
        
        col1, col2 = st.columns(2)
        with col1:
            n_sims = st.number_input(
                "Number of simulations:",
                min_value=100,
                max_value=50000,
                value=5000,
                step=500,
                help="Higher values provide more stable results but take longer"
            )
        
        with col2:
            use_seed = st.checkbox("Use random seed (for reproducibility)", value=True)
            if use_seed:
                seed = st.number_input(
                    "Random seed:",
                    min_value=0,
                    max_value=999999,
                    value=42,
                    help="Same seed will produce identical results"
                )
            else:
                seed = None
        
        # Check for required FPTS column
        if 'FPTS' not in players_df.columns or players_df['FPTS'].isnull().all():
            st.error("❌ No valid FPTS (projections) found. FPTS column is required for simulation.")
            return
        
        # Run simulation button
        if st.button("🚀 Run Simulation", type="primary"):
            
            # Check cache if file content is available
            cache_hit = False
            if file_content:
                file_hash = get_file_hash(file_content)
                cache_key_str = cache_key(file_hash, n_sims, seed)
                
                if cache_key_str in st.session_state.simulation_cache:
                    sim_df, compare_df, sim_metadata = st.session_state.simulation_cache[cache_key_str]
                    cache_hit = True
                    st.info("📋 Using cached results for identical parameters")
            
            if not cache_hit:
                # Run new simulation
                with st.spinner(f"Running {n_sims:,} Monte Carlo simulations..."):
                    try:
                        sim_df, compare_df, sim_metadata = run_simulation_cached(players_df, n_sims, seed)
                        
                        # Cache results
                        if file_content:
                            st.session_state.simulation_cache[cache_key_str] = (sim_df, compare_df, sim_metadata)
                        
                        st.success("✅ Simulation completed!")
                        
                    except Exception as e:
                        st.error(f"❌ Simulation failed: {e}")
                        return
            
            # Display results
            st.subheader("📊 Simulation Results")
            
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Players Simulated", len(sim_df))
            with col2:
                st.metric("Rookie Fallbacks", sim_df['rookie_fallback'].sum())
            with col3:
                if 'delta_mean' in compare_df.columns:
                    mean_delta = compare_df['delta_mean'].mean()
                    st.metric("Mean Delta (pts)", f"{mean_delta:.2f}")
            with col4:
                if sim_metadata.get('calibrated_from_current_run'):
                    st.metric("Boom Thresholds", "Calibrated")
                else:
                    st.metric("Boom Thresholds", "From File")
            
            # Show boom thresholds
            if sim_metadata.get('boom_thresholds'):
                with st.expander("🎯 Position Boom Thresholds"):
                    thresholds_df = pd.DataFrame([
                        {'Position': pos, 'Boom Threshold (pts)': f"{threshold:.1f}"}
                        for pos, threshold in sim_metadata['boom_thresholds'].items()
                    ])
                    st.dataframe(thresholds_df, use_container_width=True)
            
            # Data preview tabs
            tab1, tab2, tab3 = st.tabs(["📈 Simulation Results", "🔀 Comparison", "🚩 Diagnostics"])
            
            with tab1:
                # Sim players preview with filters
                st.subheader("Simulation Results Preview")
                
                # Position filter
                positions = ['All'] + sorted(sim_df['POS'].unique().tolist())
                pos_filter = st.selectbox("Filter by position:", positions)
                
                # Sort options
                sort_options = ['sim_mean', 'boom_score', 'ceiling_p90', 'boom_prob']
                sort_by = st.selectbox("Sort by:", sort_options, index=0)
                sort_desc = st.checkbox("Descending order", value=True)
                
                # Apply filters
                display_df = sim_df.copy()
                if pos_filter != 'All':
                    display_df = display_df[display_df['POS'] == pos_filter]
                
                # Sort
                display_df = display_df.sort_values(sort_by, ascending=not sort_desc)
                
                # Show preview
                preview_cols = ['PLAYER', 'POS', 'TEAM', 'sim_mean', 'floor_p10', 
                              'ceiling_p90', 'boom_prob', 'boom_score']
                if 'SAL' in display_df.columns:
                    preview_cols.append('SAL')
                
                st.dataframe(
                    display_df[preview_cols].round(2),
                    use_container_width=True,
                    height=400
                )
            
            with tab2:
                # Compare table preview
                st.subheader("Site vs Simulation Comparison")
                
                # Position filter for compare
                compare_positions = ['All'] + sorted(compare_df['POS'].unique().tolist())
                compare_pos_filter = st.selectbox("Filter by position:", compare_positions, key="compare_pos")
                
                # Sort options for compare
                compare_sort_options = ['delta_mean', 'pct_delta', 'beat_site_prob', 'value_per_1k']
                available_sort = [opt for opt in compare_sort_options if opt in compare_df.columns]
                
                if available_sort:
                    compare_sort_by = st.selectbox("Sort by:", available_sort, key="compare_sort")
                    compare_sort_desc = st.checkbox("Descending order", value=True, key="compare_desc")
                    
                    # Apply filters and sort
                    compare_display = compare_df.copy()
                    if compare_pos_filter != 'All':
                        compare_display = compare_display[compare_display['POS'] == compare_pos_filter]
                    
                    compare_display = compare_display.sort_values(compare_sort_by, ascending=not compare_sort_desc)
                    
                    # Show comparison preview
                    compare_cols = ['PLAYER', 'POS', 'TEAM', 'FPTS', 'sim_mean', 'delta_mean']
                    if 'pct_delta' in compare_display.columns:
                        compare_cols.append('pct_delta')
                    if 'beat_site_prob' in compare_display.columns:
                        compare_cols.append('beat_site_prob')
                    if 'value_per_1k' in compare_display.columns:
                        compare_cols.append('value_per_1k')
                    if 'dart_flag' in compare_display.columns:
                        compare_cols.append('dart_flag')
                    
                    st.dataframe(
                        compare_display[compare_cols].round(2),
                        use_container_width=True,
                        height=400
                    )
            
            with tab3:
                # Diagnostics and flags
                st.subheader("Diagnostics Summary")
                
                if 'diagnostics' in sim_metadata:
                    diag_df = sim_metadata['diagnostics']
                    st.dataframe(diag_df.round(3), use_container_width=True)
                
                st.subheader("Data Quality Flags")
                
                if 'flags' in sim_metadata:
                    flags_df = sim_metadata['flags']
                    if not flags_df.empty:
                        st.dataframe(flags_df, use_container_width=True)
                    else:
                        st.info("No significant flags detected")
            
            # Download buttons
            st.subheader("💾 Download Results")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                # sim_players.csv
                sim_csv = sim_df.to_csv(index=False)
                st.download_button(
                    "📈 sim_players.csv",
                    sim_csv,
                    "sim_players.csv",
                    "text/csv"
                )
            
            with col2:
                # compare.csv
                compare_csv = compare_df.to_csv(index=False)
                st.download_button(
                    "🔀 compare.csv",
                    compare_csv,
                    "compare.csv",
                    "text/csv"
                )
            
            with col3:
                # diagnostics.csv
                if 'diagnostics' in sim_metadata:
                    diag_csv = sim_metadata['diagnostics'].to_csv(index=False)
                    st.download_button(
                        "📊 diagnostics.csv",
                        diag_csv,
                        "diagnostics_summary.csv",
                        "text/csv"
                    )
            
            with col4:
                # flags.csv
                if 'flags' in sim_metadata:
                    flags_csv = sim_metadata['flags'].to_csv(index=False)
                    st.download_button(
                        "🚩 flags.csv",
                        flags_csv,
                        "flags.csv",
                        "text/csv"
                    )
            
            with col5:
                # ZIP bundle
                zip_data = create_download_zip(sim_df, compare_df, players_df, sim_metadata)
                st.download_button(
                    "📦 All Results (ZIP)",
                    zip_data,
                    "simulator_outputs.zip",
                    "application/zip"
                )
    
    # Clear cache button
    if st.session_state.simulation_cache:
        st.markdown("---")
        if st.button("🗑️ Clear Cached Results"):
            st.session_state.simulation_cache.clear()
            st.success("Cache cleared!")
            st.experimental_rerun()


if __name__ == "__main__":
    main()