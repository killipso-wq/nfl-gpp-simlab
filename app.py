"""
Streamlit application for NFL GPP Simulation and Optimization.

Main entry point for the web application.
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
from typing import Optional

# Import our simulation modules
from src.sim.pipeline import SimulationPipeline, create_default_pipeline_config

# Configure Streamlit page
st.set_page_config(
    page_title="NFL GPP Sim Lab",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point."""
    st.title("🏈 NFL GPP Sim Lab")
    st.markdown("Monte Carlo simulation and optimization toolkit for NFL fantasy")
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    tab = st.sidebar.radio(
        "Select Tab",
        ["Simulator", "Optimizer", "Help"]
    )
    
    if tab == "Simulator":
        simulator_tab()
    elif tab == "Optimizer":
        optimizer_tab()
    else:
        help_tab()


def simulator_tab():
    """Simulator tab for Monte Carlo simulation."""
    st.header("Monte Carlo Simulator")
    st.markdown("Upload player data and run simulations based on the Realistic NFL Monte Carlo methodology")
    
    # File upload
    st.subheader("1. Upload Player Data")
    uploaded_file = st.file_uploader(
        "Choose a CSV file with player data",
        type="csv",
        help="Upload a CSV file with columns: PLAYER, POS, TEAM, OPP, SAL, FPTS, etc."
    )
    
    if uploaded_file is not None:
        try:
            # Load data
            players_df = pd.read_csv(uploaded_file)
            
            # Display column mapping
            st.subheader("2. Column Mapping")
            display_column_mapping(players_df)
            
            # Simulation configuration
            st.subheader("3. Simulation Settings")
            config = configure_simulation()
            
            # Run simulation button
            if st.button("Run Simulation", type="primary"):
                run_simulation(players_df, config)
                
        except Exception as e:
            st.error(f"Error loading file: {str(e)}")
    else:
        # Show example data format
        st.subheader("Expected Data Format")
        show_example_data_format()


def display_column_mapping(df: pd.DataFrame):
    """Display column mapping and validation."""
    st.markdown("**Detected Columns:**")
    
    # Expected columns
    expected_columns = {
        'PLAYER': 'Player name',
        'POS': 'Position (QB, RB, WR, TE, DST)',
        'TEAM': 'Player team',
        'OPP': 'Opponent team',
        'SAL': 'Salary',
        'FPTS': 'Site projection (optional)',
        'RST%': 'Ownership % (optional)',
        'O/U': 'Game total (optional)',
        'SPRD': 'Spread (optional)'
    }
    
    # Check for required columns
    missing_required = []
    for col in ['PLAYER', 'POS', 'TEAM', 'OPP']:
        if col not in df.columns:
            missing_required.append(col)
    
    if missing_required:
        st.error(f"Missing required columns: {', '.join(missing_required)}")
        return
    
    # Display mapping table
    mapping_data = []
    for col in df.columns:
        status = "✅ Required" if col in ['PLAYER', 'POS', 'TEAM', 'OPP'] else "🔶 Optional"
        description = expected_columns.get(col, "Unknown column")
        sample_value = str(df[col].iloc[0]) if len(df) > 0 else "N/A"
        
        mapping_data.append({
            'Column': col,
            'Status': status,
            'Description': description,
            'Sample Value': sample_value
        })
    
    mapping_df = pd.DataFrame(mapping_data)
    st.dataframe(mapping_df, use_container_width=True)
    
    # Show data preview
    st.markdown("**Data Preview:**")
    st.dataframe(df.head(10), use_container_width=True)
    
    # Data validation warnings
    warnings = validate_data(df)
    if warnings:
        st.warning("Data validation warnings:")
        for warning in warnings:
            st.markdown(f"- {warning}")


def validate_data(df: pd.DataFrame) -> list:
    """Validate the uploaded data and return warnings."""
    warnings = []
    
    # Check for unknown positions
    valid_positions = ['QB', 'RB', 'WR', 'TE', 'DST', 'D']
    if 'POS' in df.columns:
        unknown_positions = set(df['POS'].unique()) - set(valid_positions)
        if unknown_positions:
            warnings.append(f"Unknown positions found: {', '.join(unknown_positions)}")
    
    # Check for missing salaries
    if 'SAL' in df.columns:
        missing_salaries = df['SAL'].isna().sum()
        if missing_salaries > 0:
            warnings.append(f"{missing_salaries} players missing salary data")
    
    # Check for missing projections
    if 'FPTS' in df.columns:
        missing_projections = df['FPTS'].isna().sum()
        if missing_projections > 0:
            warnings.append(f"{missing_projections} players missing projection data")
    
    return warnings


def configure_simulation():
    """Configure simulation parameters."""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        n_sims = st.number_input(
            "Number of Simulations",
            min_value=1000,
            max_value=100000,
            value=10000,
            step=1000,
            help="More simulations = more accurate but slower"
        )
    
    with col2:
        seed = st.number_input(
            "Random Seed",
            min_value=1,
            max_value=999999,
            value=42,
            help="Set seed for reproducible results"
        )
    
    with col3:
        volatility = st.slider(
            "Volatility Multiplier",
            min_value=0.5,
            max_value=2.0,
            value=1.0,
            step=0.1,
            help="Adjust overall simulation volatility"
        )
    
    # Advanced settings
    with st.expander("Advanced Settings"):
        col1, col2 = st.columns(2)
        
        with col1:
            include_correlations = st.checkbox(
                "Include Correlations",
                value=True,
                help="Model player correlations (QB-WR, RB-DST, etc.)"
            )
            
            correlation_strength = st.slider(
                "Correlation Strength",
                min_value=0.0,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="Scale correlation effects"
            )
        
        with col2:
            include_diagnostics = st.checkbox(
                "Generate Diagnostics",
                value=True,
                help="Generate diagnostic reports"
            )
            
            value_calculation = st.checkbox(
                "Calculate Value Metrics",
                value=True,
                help="Calculate value per $1k and other value metrics"
            )
    
    # Create config
    config = create_default_pipeline_config()
    config.n_simulations = n_sims
    config.seed = seed
    config.volatility_multiplier = volatility
    config.include_correlations = include_correlations
    config.correlation_strength = correlation_strength
    config.diagnostics = include_diagnostics
    config.value_calculation = value_calculation
    
    return config


def run_simulation(players_df: pd.DataFrame, config):
    """Run the Monte Carlo simulation."""
    with st.spinner("Running Monte Carlo simulation..."):
        try:
            # Initialize pipeline
            pipeline = SimulationPipeline(config)
            
            # Run simulation
            output_dir, metadata = pipeline.run_full_pipeline(
                players_df, season=2024, week=1
            )
            
            st.success(f"Simulation completed! Results saved to {output_dir}")
            
            # Display results
            display_results(output_dir)
            
        except Exception as e:
            st.error(f"Simulation failed: {str(e)}")
            st.exception(e)


def display_results(output_dir: str):
    """Display simulation results."""
    st.subheader("Simulation Results")
    
    # Load results
    try:
        sim_players = pd.read_csv(os.path.join(output_dir, "sim_players.csv"))
        compare = pd.read_csv(os.path.join(output_dir, "compare.csv"))
        
        # Results tabs
        result_tab = st.tabs(["Players", "Compare", "Diagnostics", "Flags", "Downloads"])
        
        with result_tab[0]:
            display_sim_players(sim_players)
        
        with result_tab[1]:
            display_compare(compare)
        
        with result_tab[2]:
            display_diagnostics(output_dir)
        
        with result_tab[3]:
            display_flags(output_dir)
        
        with result_tab[4]:
            display_downloads(output_dir)
            
    except Exception as e:
        st.error(f"Error loading results: {str(e)}")


def display_sim_players(df: pd.DataFrame):
    """Display simulated player results."""
    st.markdown("**Simulated Player Projections**")
    
    # Filters
    col1, col2 = st.columns(2)
    with col1:
        position_filter = st.multiselect(
            "Filter by Position",
            options=df['position'].unique(),
            default=df['position'].unique()
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            options=['sim_mean', 'sim_std', 'p90', 'boom_prob', 'value_per_1k'],
            index=0
        )
    
    # Apply filters
    filtered_df = df[df['position'].isin(position_filter)]
    filtered_df = filtered_df.sort_values(sort_by, ascending=False)
    
    # Display
    display_columns = [
        'name', 'team', 'position', 'salary', 'sim_mean', 'sim_std',
        'p10', 'p50', 'p90', 'boom_prob'
    ]
    
    # Add value columns if available
    if 'value_per_1k' in filtered_df.columns:
        display_columns.extend(['value_per_1k', 'ceil_per_1k'])
    
    st.dataframe(
        filtered_df[display_columns].round(2),
        use_container_width=True
    )


def display_compare(df: pd.DataFrame):
    """Display comparison analysis."""
    st.markdown("**Comparison vs Site Projections**")
    
    if 'site_projection' not in df.columns:
        st.info("No site projections available for comparison")
        return
    
    # Show players with biggest differences
    if 'vs_site_delta' in df.columns:
        st.markdown("**Biggest Differences from Site:**")
        
        # Top overperformers
        st.markdown("*Projected to outperform site:*")
        overperformers = df[df['vs_site_delta'] > 0].nlargest(10, 'vs_site_delta')
        st.dataframe(
            overperformers[['name', 'position', 'site_projection', 'sim_mean', 'vs_site_delta']].round(2),
            use_container_width=True
        )
        
        # Top underperformers  
        st.markdown("*Projected to underperform site:*")
        underperformers = df[df['vs_site_delta'] < 0].nsmallest(10, 'vs_site_delta')
        st.dataframe(
            underperformers[['name', 'position', 'site_projection', 'sim_mean', 'vs_site_delta']].round(2),
            use_container_width=True
        )


def display_diagnostics(output_dir: str):
    """Display diagnostic information."""
    st.markdown("**Diagnostic Summary**")
    
    try:
        diagnostics = pd.read_csv(os.path.join(output_dir, "diagnostics_summary.csv"))
        st.dataframe(diagnostics.round(3), use_container_width=True)
    except FileNotFoundError:
        st.info("No diagnostic data available")


def display_flags(output_dir: str):
    """Display flagged players."""
    st.markdown("**Flagged Players**")
    
    try:
        flags = pd.read_csv(os.path.join(output_dir, "flags.csv"))
        if len(flags) > 0:
            st.dataframe(flags, use_container_width=True)
        else:
            st.info("No flags generated")
    except FileNotFoundError:
        st.info("No flags data available")


def display_downloads(output_dir: str):
    """Display download options."""
    st.markdown("**Download Results**")
    
    # List available files
    files = []
    for filename in os.listdir(output_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(output_dir, filename)
            files.append((filename, filepath))
    
    # Download buttons
    for filename, filepath in files:
        with open(filepath, 'rb') as f:
            st.download_button(
                label=f"Download {filename}",
                data=f.read(),
                file_name=filename,
                mime='text/csv'
            )


def show_example_data_format():
    """Show example of expected data format."""
    example_data = {
        'PLAYER': ['Josh Allen', 'Derrick Henry', 'Tyreek Hill', 'Travis Kelce'],
        'POS': ['QB', 'RB', 'WR', 'TE'],
        'TEAM': ['BUF', 'TEN', 'MIA', 'KC'],
        'OPP': ['NE', 'JAX', 'BUF', 'LV'],
        'SAL': [8200, 7000, 8400, 6800],
        'FPTS': [22.5, 16.2, 18.8, 13.4],
        'RST%': [15.2, 8.9, 22.1, 11.5]
    }
    
    example_df = pd.DataFrame(example_data)
    st.dataframe(example_df, use_container_width=True)
    
    st.markdown("""
    **Required Columns:**
    - `PLAYER`: Player name
    - `POS`: Position (QB, RB, WR, TE, DST)
    - `TEAM`: Player's team
    - `OPP`: Opponent team
    
    **Optional Columns:**
    - `SAL`: Salary
    - `FPTS`: Site projection
    - `RST%`: Ownership percentage
    - `O/U`: Game total
    - `SPRD`: Point spread
    """)


def optimizer_tab():
    """Optimizer tab for lineup optimization."""
    st.header("Lineup Optimizer")
    st.info("Optimizer functionality coming soon! This will include GPP strategy presets and constraint optimization.")
    
    # Placeholder for optimizer
    st.markdown("""
    **Planned Features:**
    - Import simulation results
    - GPP strategy presets (Small/Mid/Large contests)
    - Correlation and stacking constraints
    - Ownership optimization
    - Multi-lineup generation
    """)


def help_tab():
    """Help and methodology tab."""
    st.header("Help & Methodology")
    
    st.markdown("""
    ## NFL GPP Sim Lab
    
    This application implements the Monte Carlo simulation methodology outlined in the 
    "Realistic NFL Monte Carlo Simulation" PDF.
    
    ### Key Features:
    
    **Monte Carlo Simulation:**
    - Position-specific usage and efficiency distributions
    - Correlation modeling (QB-WR, RB-DST, etc.)
    - Game script and pace adjustments
    - Reproducible seeded sampling
    
    **Output Metrics:**
    - Percentile distributions (p10, p50, p90, etc.)
    - Boom probability and scores
    - Value per $1k calculations
    - Beat-site probability
    
    **Diagnostic Analysis:**
    - Model accuracy vs site projections
    - Coverage analysis
    - Flag outliers and data issues
    
    ### Methodology Reference:
    
    The simulation is based on the research methodology documented in 
    `docs/research/monte_carlo_football.pdf`.
    
    ### Getting Started:
    
    1. Upload a CSV file with player data
    2. Review column mappings and data validation
    3. Configure simulation parameters
    4. Run simulation and analyze results
    5. Use results for lineup optimization
    
    ### Support:
    
    For questions or issues, please refer to the project documentation
    or create an issue in the repository.
    """)


if __name__ == "__main__":
    main()