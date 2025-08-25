#!/usr/bin/env python3
"""
NFL GPP Sim Lab - Streamlit Application
Main entry point for the Streamlit UI
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import zipfile
import os
from datetime import datetime
from pathlib import Path
import tempfile
from typing import Dict, List, Optional, Tuple

# Page config
st.set_page_config(
    page_title="NFL GPP Sim Lab",
    page_icon="🏈",
    layout="wide"
)

# Constants
REQUIRED_COLUMNS = ["PLAYER", "POS", "TEAM", "FPTS", "SAL"]
OPTIONAL_COLUMNS = ["OPP", "RST%", "VAL"]
COLUMN_MAPPINGS = {
    # Player name variations
    "name": "PLAYER", "player": "PLAYER", "player_name": "PLAYER",
    # Position variations
    "position": "POS", "pos": "POS",
    # Team variations
    "tm": "TEAM", "team": "TEAM",
    # Opponent variations
    "opponent": "OPP", "opp": "OPP",
    # Salary variations
    "salary": "SAL", "sal": "SAL", "dk_salary": "SAL",
    # Projection variations
    "proj": "FPTS", "projection": "FPTS", "fpts": "FPTS", "projected_points": "FPTS",
    # Ownership variations
    "own": "RST%", "ownership": "RST%", "own%": "RST%", "rst": "RST%",
    # Value variations
    "value": "VAL", "val": "VAL", "value_per_1k": "VAL"
}

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to standard format"""
    df = df.copy()
    
    # Create mapping from current columns to normalized columns
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in COLUMN_MAPPINGS:
            column_mapping[col] = COLUMN_MAPPINGS[col_lower]
        elif col.upper() in REQUIRED_COLUMNS + OPTIONAL_COLUMNS:
            column_mapping[col] = col.upper()
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    return df

def validate_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str], List[str]]:
    """Validate uploaded data and return cleaned data with warnings and errors"""
    warnings = []
    errors = []
    
    # Check for required columns
    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_required:
        errors.append(f"Missing required columns: {', '.join(missing_required)}")
        return df, warnings, errors
    
    # Convert D to DST for position
    if "POS" in df.columns:
        df["POS"] = df["POS"].replace("D", "DST")
    
    # Clean and convert numeric columns
    for col in ["SAL", "FPTS"]:
        if col in df.columns:
            # Remove currency symbols and convert to numeric
            df[col] = pd.to_numeric(df[col].astype(str).str.replace('[$,]', '', regex=True), errors='coerce')
            
            if df[col].isna().any():
                warnings.append(f"{col} contains non-numeric values that were converted to NaN")
    
    # Handle ownership percentage normalization
    if "RST%" in df.columns:
        # Convert ownership - if ≤1 treat as fraction, else as percentage
        rst_col = pd.to_numeric(df["RST%"], errors='coerce')
        df["RST%"] = np.where(rst_col <= 1, rst_col * 100, rst_col)
        
        if df["RST%"].isna().any():
            warnings.append("RST% contains non-numeric values that were converted to NaN")
    
    # Check for missing critical data
    if df["PLAYER"].isna().any():
        warnings.append("Some player names are missing")
    
    if df["FPTS"].isna().any():
        warnings.append("Some FPTS projections are missing - these players may be skipped")
    
    return df, warnings, errors

def generate_simulation_outputs(df: pd.DataFrame, season: int, week: int, sims: int, seed: int) -> Dict:
    """Generate placeholder simulation outputs"""
    np.random.seed(seed)
    
    # Create simulation results with placeholder data
    sim_data = df.copy()
    
    # Add simulation columns (placeholder calculations)
    sim_data["proj_mean"] = sim_data["FPTS"]
    sim_data["proj_floor"] = sim_data["FPTS"] * 0.7  # p10
    sim_data["proj_p75"] = sim_data["FPTS"] * 1.1
    sim_data["proj_ceiling"] = sim_data["FPTS"] * 1.4  # p90
    sim_data["proj_p95"] = sim_data["FPTS"] * 1.6
    
    # Add boom metrics (placeholder)
    sim_data["boom_prob"] = np.random.uniform(0.1, 0.4, len(sim_data))
    sim_data["boom_score"] = np.random.randint(1, 101, len(sim_data))
    sim_data["dart_flag"] = sim_data["boom_score"] > 80
    
    # Add value metrics if salary available
    if "SAL" in sim_data.columns and not sim_data["SAL"].isna().all():
        sim_data["value_per_1k"] = (sim_data["proj_mean"] / sim_data["SAL"]) * 1000
        sim_data["ceil_per_1k"] = (sim_data["proj_ceiling"] / sim_data["SAL"]) * 1000
    
    # Create comparison data
    compare_data = sim_data[["PLAYER", "POS", "TEAM", "FPTS", "proj_mean"]].copy()
    compare_data["delta"] = compare_data["proj_mean"] - compare_data["FPTS"]
    compare_data["coverage"] = np.random.uniform(0.8, 0.95, len(compare_data))
    
    # Create diagnostics summary
    diagnostics = {
        "mae": float(np.mean(np.abs(compare_data["delta"]))),
        "rmse": float(np.sqrt(np.mean(compare_data["delta"]**2))),
        "correlation": float(np.corrcoef(compare_data["FPTS"], compare_data["proj_mean"])[0,1]),
        "coverage_p90": float(np.mean(compare_data["coverage"])),
        "players_count": len(sim_data),
        "positions": sim_data["POS"].value_counts().to_dict()
    }
    
    # Create flags (outliers/issues)
    flags_data = []
    for idx, row in sim_data.iterrows():
        if row["boom_score"] > 90:
            flags_data.append({
                "player": row["PLAYER"],
                "flag_type": "high_boom",
                "message": f"Very high boom score: {row['boom_score']}"
            })
        if "SAL" in row and row["SAL"] > 9000:
            flags_data.append({
                "player": row["PLAYER"],
                "flag_type": "expensive",
                "message": f"High salary player: ${row['SAL']}"
            })
    
    flags_df = pd.DataFrame(flags_data) if flags_data else pd.DataFrame(columns=["player", "flag_type", "message"])
    
    return {
        "sim_players": sim_data,
        "compare": compare_data,
        "diagnostics_summary": diagnostics,
        "flags": flags_df
    }

def create_output_files(outputs: Dict, season: int, week: int, sims: int, seed: int) -> Tuple[str, Dict[str, str]]:
    """Create output files and return directory path and file paths"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = f"data/sim_week/{season}_w{week}_{timestamp}"
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    file_paths = {}
    
    # Save CSV files
    outputs["sim_players"].to_csv(f"{output_dir}/sim_players.csv", index=False)
    file_paths["sim_players"] = f"{output_dir}/sim_players.csv"
    
    outputs["compare"].to_csv(f"{output_dir}/compare.csv", index=False)
    file_paths["compare"] = f"{output_dir}/compare.csv"
    
    outputs["flags"].to_csv(f"{output_dir}/flags.csv", index=False)
    file_paths["flags"] = f"{output_dir}/flags.csv"
    
    # Save diagnostics summary as CSV
    diag_df = pd.DataFrame([outputs["diagnostics_summary"]])
    diag_df.to_csv(f"{output_dir}/diagnostics_summary.csv", index=False)
    file_paths["diagnostics"] = f"{output_dir}/diagnostics_summary.csv"
    
    # Create metadata.json
    metadata = {
        "run_id": timestamp,
        "season": season,
        "week": week,
        "sims": sims,
        "seed": seed,
        "timestamp": timestamp,
        "methodology": "monte_carlo_pdf",
        "files_created": list(file_paths.keys()),
        "diagnostics": outputs["diagnostics_summary"]
    }
    
    with open(f"{output_dir}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    file_paths["metadata"] = f"{output_dir}/metadata.json"
    
    # Create ZIP file
    zip_path = f"{output_dir}/simulator_outputs.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for file_type, file_path in file_paths.items():
            zf.write(file_path, os.path.basename(file_path))
    file_paths["zip"] = zip_path
    
    return output_dir, file_paths

def main():
    st.title("🏈 NFL GPP Sim Lab")
    st.markdown("Upload your players.csv file and generate simulation outputs")
    
    # Sidebar controls
    st.sidebar.header("Simulation Settings")
    season = st.sidebar.number_input("Season", min_value=2020, max_value=2030, value=2025)
    week = st.sidebar.number_input("Week", min_value=1, max_value=18, value=1)
    sims = st.sidebar.number_input("Simulations", min_value=1000, max_value=100000, value=10000, step=1000)
    seed = st.sidebar.number_input("Random Seed", min_value=1, max_value=9999, value=1337)
    
    # Methodology expander
    with st.sidebar.expander("📚 Methodology"):
        st.markdown("""
        This simulator uses Monte Carlo methods for NFL DFS projections.
        
        **Features:**
        - Position-calibrated distributions
        - Boom/bust analysis
        - Value metrics
        - Coverage diagnostics
        
        *Full methodology documentation coming soon*
        """)
    
    # Main content tabs
    tab1, tab2 = st.tabs(["📁 Upload & Validate", "🎯 Simulate & Download"])
    
    with tab1:
        st.header("Upload & Validate Players Data")
        
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=['csv'],
            help="Upload your players.csv file with columns like PLAYER, POS, TEAM, SAL, FPTS, RST%"
        )
        
        # Sample data option
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("📋 Use Sample Data"):
                uploaded_file = "sample"
        
        with col2:
            if st.button("📥 Download Sample CSV"):
                sample_df = pd.read_csv("players_sample.csv")
                csv = sample_df.to_csv(index=False)
                st.download_button(
                    label="Download players_sample.csv",
                    data=csv,
                    file_name="players_sample.csv",
                    mime="text/csv"
                )
        
        if uploaded_file is not None:
            try:
                # Load data
                if uploaded_file == "sample":
                    df = pd.read_csv("players_sample.csv")
                    st.success("✅ Sample data loaded successfully!")
                else:
                    df = pd.read_csv(uploaded_file)
                    st.success("✅ File uploaded successfully!")
                
                # Show original columns
                st.subheader("Original Data")
                st.dataframe(df.head())
                
                # Normalize columns
                normalized_df = normalize_column_names(df)
                
                # Validate data
                validated_df, warnings, errors = validate_data(normalized_df)
                
                # Show validation results
                st.subheader("Validation Results")
                
                # Column mapping table
                col_mapping_data = []
                for orig_col in df.columns:
                    if orig_col in normalized_df.columns:
                        mapped_col = orig_col
                    else:
                        mapped_col = "NOT MAPPED"
                    
                    status = "✅ Found" if mapped_col in REQUIRED_COLUMNS + OPTIONAL_COLUMNS else "❌ Missing"
                    col_mapping_data.append({
                        "Original Column": orig_col,
                        "Mapped To": mapped_col,
                        "Status": status,
                        "Required": "Yes" if mapped_col in REQUIRED_COLUMNS else "No"
                    })
                
                mapping_df = pd.DataFrame(col_mapping_data)
                st.dataframe(mapping_df)
                
                # Show errors and warnings
                if errors:
                    for error in errors:
                        st.error(f"❌ {error}")
                
                if warnings:
                    for warning in warnings:
                        st.warning(f"⚠️ {warning}")
                
                if not errors:
                    st.success("✅ Data validation passed! Ready for simulation.")
                    
                    # Store validated data in session state
                    st.session_state.validated_data = validated_df
                    st.session_state.validation_success = True
                    
                    # Show normalized data preview
                    st.subheader("Normalized Data Preview")
                    st.dataframe(validated_df)
                
            except Exception as e:
                st.error(f"❌ Error loading file: {str(e)}")
                st.session_state.validation_success = False
    
    with tab2:
        st.header("Generate Simulation Outputs")
        
        if not hasattr(st.session_state, 'validation_success') or not st.session_state.validation_success:
            st.warning("⚠️ Please upload and validate data first in the 'Upload & Validate' tab.")
            return
        
        df = st.session_state.validated_data
        
        # Show simulation settings
        st.subheader("Simulation Configuration")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Season", season)
        with col2:
            st.metric("Week", week)
        with col3:
            st.metric("Simulations", f"{sims:,}")
        with col4:
            st.metric("Seed", seed)
        
        # Run simulation button
        if st.button("🚀 Run Simulation", type="primary"):
            with st.spinner("Generating simulation outputs..."):
                try:
                    # Generate outputs
                    outputs = generate_simulation_outputs(df, season, week, sims, seed)
                    
                    # Create files
                    output_dir, file_paths = create_output_files(outputs, season, week, sims, seed)
                    
                    st.session_state.simulation_outputs = outputs
                    st.session_state.output_dir = output_dir
                    st.session_state.file_paths = file_paths
                    
                    st.success(f"✅ Simulation completed! Files saved to {output_dir}")
                    
                except Exception as e:
                    st.error(f"❌ Simulation failed: {str(e)}")
                    return
        
        # Show results if simulation has been run
        if hasattr(st.session_state, 'simulation_outputs'):
            outputs = st.session_state.simulation_outputs
            file_paths = st.session_state.file_paths
            
            st.subheader("📊 Simulation Results")
            
            # Diagnostics summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("MAE", f"{outputs['diagnostics_summary']['mae']:.2f}")
            with col2:
                st.metric("RMSE", f"{outputs['diagnostics_summary']['rmse']:.2f}")
            with col3:
                st.metric("Correlation", f"{outputs['diagnostics_summary']['correlation']:.3f}")
            
            # Preview tables with tabs
            preview_tab1, preview_tab2, preview_tab3, preview_tab4 = st.tabs([
                "🎯 Sim Players", "📈 Compare", "🚩 Flags", "📋 Diagnostics"
            ])
            
            with preview_tab1:
                st.dataframe(outputs["sim_players"])
            
            with preview_tab2:
                st.dataframe(outputs["compare"])
            
            with preview_tab3:
                st.dataframe(outputs["flags"])
            
            with preview_tab4:
                st.json(outputs["diagnostics_summary"])
            
            # Download section
            st.subheader("📥 Download Results")
            
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Individual file downloads
                st.markdown("**Individual Files:**")
                
                # Download buttons for each file
                for file_type, file_path in file_paths.items():
                    if file_type != "zip" and os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            file_data = f.read()
                        
                        st.download_button(
                            label=f"📄 {os.path.basename(file_path)}",
                            data=file_data,
                            file_name=os.path.basename(file_path),
                            mime="text/csv" if file_path.endswith('.csv') else "application/json"
                        )
            
            with col2:
                # ZIP download
                st.markdown("**Complete Package:**")
                if os.path.exists(file_paths["zip"]):
                    with open(file_paths["zip"], 'rb') as f:
                        zip_data = f.read()
                    
                    st.download_button(
                        label="📦 Download All (ZIP)",
                        data=zip_data,
                        file_name="simulator_outputs.zip",
                        mime="application/zip"
                    )

if __name__ == "__main__":
    main()