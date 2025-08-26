"""
NFL GPP Simulator - Streamlit UI

A robust Streamlit UI for configuring and running Monte Carlo simulations
for NFL DFS lineup optimization.
"""

import streamlit as st
import pandas as pd
import json
import os
import sys
import io
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import logging

# Add src to path for imports
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.projections.run_week_from_site_players import run_simulation

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="NFL GPP Simulator",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
SUPPORTED_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DST']
REQUIRED_COLUMNS = ['PLAYER', 'POS', 'TEAM', 'OPP']
OPTIONAL_COLUMNS = ['FPTS', 'SAL', 'RST%', 'O/U', 'SPRD', 'VAL']
DEFAULT_PRIORS_DIR = str(repo_root / "data" / "baseline")
DEFAULT_OUTPUT_DIR = str(repo_root / "data" / "sim_week")
PRESETS_FILE = str(repo_root / ".ui_presets" / "simulator.json")

def initialize_session_state():
    """Initialize Streamlit session state"""
    if 'simulation_results' not in st.session_state:
        st.session_state.simulation_results = None
    if 'column_mapping' not in st.session_state:
        st.session_state.column_mapping = {}
    if 'uploaded_data' not in st.session_state:
        st.session_state.uploaded_data = None
    if 'run_config' not in st.session_state:
        st.session_state.run_config = {
            'season': 2025,
            'week': 1,
            'sims': 10000,
            'seed': 42,
            'output_dir': DEFAULT_OUTPUT_DIR,
            'validate_only': False
        }

def load_presets() -> Dict[str, Any]:
    """Load presets from JSON file"""
    try:
        if os.path.exists(PRESETS_FILE):
            with open(PRESETS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load presets: {e}")
    return {}

def save_presets(presets: Dict[str, Any]):
    """Save presets to JSON file"""
    try:
        os.makedirs(os.path.dirname(PRESETS_FILE), exist_ok=True)
        with open(PRESETS_FILE, 'w') as f:
            json.dump(presets, f, indent=2)
    except Exception as e:
        logger.error(f"Could not save presets: {e}")
        st.error(f"Could not save presets: {e}")

def normalize_position(pos: str) -> str:
    """Normalize position names"""
    pos = str(pos).upper().strip()
    if pos == 'D':
        return 'DST'
    return pos

def validate_file_exists(file_path: str) -> bool:
    """Check if file exists and is readable"""
    if not file_path:
        return False
    try:
        return os.path.isfile(file_path) and os.access(file_path, os.R_OK)
    except:
        return False

def detect_column_mapping(df: pd.DataFrame) -> Dict[str, str]:
    """Auto-detect column mapping from DataFrame"""
    mapping = {}
    columns = [col.upper() for col in df.columns]
    
    # Required mappings
    for req_col in REQUIRED_COLUMNS:
        if req_col in columns:
            mapping[req_col] = df.columns[columns.index(req_col)]
        else:
            # Try some common variations
            variations = {
                'PLAYER': ['NAME', 'PLAYER_NAME', 'FULL_NAME'],
                'POS': ['POSITION', 'SLOT'],
                'TEAM': ['TM'],
                'OPP': ['OPPONENT', 'VS']
            }
            found = False
            for var in variations.get(req_col, []):
                if var in columns:
                    mapping[req_col] = df.columns[columns.index(var)]
                    found = True
                    break
            if not found:
                mapping[req_col] = None
    
    # Optional mappings
    for opt_col in OPTIONAL_COLUMNS:
        if opt_col in columns:
            mapping[opt_col] = df.columns[columns.index(opt_col)]
        else:
            mapping[opt_col] = None
    
    return mapping

def create_column_mapping_widget(df: pd.DataFrame) -> Dict[str, str]:
    """Create interactive column mapping widget"""
    st.subheader("🗃️ Column Mapping")
    st.write("Map your CSV columns to the required fields:")
    
    mapping = {}
    available_columns = [''] + list(df.columns)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Required Fields:**")
        for req_col in REQUIRED_COLUMNS:
            current_value = st.session_state.column_mapping.get(req_col, '')
            if current_value not in available_columns:
                current_value = ''
            
            mapping[req_col] = st.selectbox(
                f"{req_col}",
                available_columns,
                index=available_columns.index(current_value) if current_value else 0,
                key=f"mapping_{req_col}",
                help=f"Select column for {req_col}"
            )
    
    with col2:
        st.write("**Optional Fields:**")
        for opt_col in OPTIONAL_COLUMNS:
            current_value = st.session_state.column_mapping.get(opt_col, '')
            if current_value not in available_columns:
                current_value = ''
                
            mapping[opt_col] = st.selectbox(
                f"{opt_col}",
                available_columns,
                index=available_columns.index(current_value) if current_value else 0,
                key=f"mapping_{opt_col}",
                help=f"Select column for {opt_col} (optional)"
            )
    
    return mapping

def validate_mapping_and_data(df: pd.DataFrame, mapping: Dict[str, str]) -> Tuple[List[str], List[str], pd.DataFrame]:
    """Validate column mapping and return warnings, errors, and preview data"""
    warnings = []
    errors = []
    
    # Check required columns
    for req_col in REQUIRED_COLUMNS:
        if not mapping.get(req_col):
            errors.append(f"Required field {req_col} is not mapped")
    
    if errors:
        return warnings, errors, pd.DataFrame()
    
    # Create mapped dataframe
    mapped_df = pd.DataFrame()
    for field, column in mapping.items():
        if column and column in df.columns:
            mapped_df[field] = df[column]
    
    # Validate positions
    if 'POS' in mapped_df.columns:
        positions = mapped_df['POS'].apply(normalize_position)
        unknown_positions = set(positions) - set(SUPPORTED_POSITIONS)
        if unknown_positions:
            warnings.append(f"Unknown positions found: {', '.join(unknown_positions)}")
        
        # Filter out unknown positions for preview
        mapped_df['POS'] = positions
        mapped_df = mapped_df[mapped_df['POS'].isin(SUPPORTED_POSITIONS)]
    
    # Validate FPTS if present
    if 'FPTS' in mapped_df.columns:
        try:
            mapped_df['FPTS'] = pd.to_numeric(mapped_df['FPTS'], errors='coerce')
            missing_fpts = mapped_df['FPTS'].isna().sum()
            if missing_fpts > 0:
                warnings.append(f"{missing_fpts} players have missing/invalid FPTS values")
        except:
            warnings.append("FPTS column contains non-numeric values")
    
    # Validate salary if present
    if 'SAL' in mapped_df.columns:
        try:
            mapped_df['SAL'] = pd.to_numeric(mapped_df['SAL'], errors='coerce')
            negative_sal = (mapped_df['SAL'] < 0).sum()
            if negative_sal > 0:
                warnings.append(f"{negative_sal} players have negative salary values")
        except:
            warnings.append("SAL column contains non-numeric values")
    
    # Normalize RST% if present
    if 'RST%' in mapped_df.columns:
        try:
            rst_values = pd.to_numeric(mapped_df['RST%'], errors='coerce')
            # If values are <= 1, assume they're fractions and convert to percentages
            rst_values = rst_values.apply(lambda x: x * 100 if x <= 1 else x)
            mapped_df['RST%'] = rst_values
        except:
            warnings.append("RST% column contains non-numeric values")
    
    # Generate player_id for preview
    if all(col in mapped_df.columns for col in ['TEAM', 'POS', 'PLAYER']):
        mapped_df['player_id'] = (
            mapped_df['TEAM'].astype(str) + '_' + 
            mapped_df['POS'].astype(str) + '_' + 
            mapped_df['PLAYER'].astype(str).str.upper().str.replace(' ', '_').str.replace(r'[^\w]', '', regex=True)
        )
    
    return warnings, errors, mapped_df

def create_file_input_section():
    """Create file input section"""
    st.subheader("📁 File Inputs")
    
    upload_method = st.radio(
        "Choose input method:",
        ["Upload CSV file", "Enter file path"],
        horizontal=True
    )
    
    players_data = None
    players_path = None
    
    if upload_method == "Upload CSV file":
        uploaded_file = st.file_uploader(
            "Upload players CSV file",
            type=['csv'],
            help="Upload your site's player CSV file"
        )
        
        if uploaded_file is not None:
            try:
                players_data = pd.read_csv(uploaded_file)
                st.success(f"✅ Loaded {len(players_data)} rows from uploaded file")
            except Exception as e:
                st.error(f"❌ Error reading CSV file: {e}")
                return None, None
    else:
        players_path = st.text_input(
            "Enter path to players CSV file",
            help="Enter the full path to your players CSV file"
        )
        
        if players_path:
            if validate_file_exists(players_path):
                try:
                    players_data = pd.read_csv(players_path)
                    st.success(f"✅ Loaded {len(players_data)} rows from {players_path}")
                except Exception as e:
                    st.error(f"❌ Error reading CSV file: {e}")
                    return None, None
            else:
                st.error(f"❌ File not found or not readable: {players_path}")
                return None, None
    
    # Prior files with defaults
    col1, col2, col3 = st.columns(3)
    
    with col1:
        team_priors_path = st.text_input(
            "Team priors CSV",
            value=os.path.join(DEFAULT_PRIORS_DIR, "team_priors.csv"),
            help="Path to team priors CSV file"
        )
    
    with col2:
        player_priors_path = st.text_input(
            "Player priors CSV",
            value=os.path.join(DEFAULT_PRIORS_DIR, "player_priors.csv"),
            help="Path to player priors CSV file"
        )
    
    with col3:
        boom_thresholds_path = st.text_input(
            "Boom thresholds JSON",
            value=os.path.join(DEFAULT_PRIORS_DIR, "boom_thresholds.json"),
            help="Path to boom thresholds JSON file"
        )
    
    # Validate prior files
    prior_files = {
        'Team priors': team_priors_path,
        'Player priors': player_priors_path,
        'Boom thresholds': boom_thresholds_path
    }
    
    for name, path in prior_files.items():
        if path and not validate_file_exists(path):
            st.warning(f"⚠️ {name} file not found: {path}")
    
    return players_data, {
        'players_site_path': players_path,
        'team_priors_path': team_priors_path,
        'player_priors_path': player_priors_path,
        'boom_thresholds_path': boom_thresholds_path
    }

def create_run_config_section():
    """Create run configuration section"""
    st.subheader("⚙️ Run Configuration")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        season = st.number_input(
            "Season",
            min_value=2020,
            max_value=2030,
            value=st.session_state.run_config.get('season', 2025),
            help="Season year"
        )
        
        week = st.number_input(
            "Week",
            min_value=1,
            max_value=18,
            value=st.session_state.run_config.get('week', 1),
            help="Week number"
        )
    
    with col2:
        sims = st.number_input(
            "Simulations",
            min_value=1,
            max_value=1000000,
            value=st.session_state.run_config.get('sims', 10000),
            help="Number of Monte Carlo simulations"
        )
        
        seed = st.number_input(
            "Random Seed",
            min_value=0,
            max_value=2147483647,
            value=st.session_state.run_config.get('seed', 42),
            help="Random seed for reproducibility"
        )
    
    with col3:
        output_dir = st.text_input(
            "Output Directory",
            value=st.session_state.run_config.get('output_dir', DEFAULT_OUTPUT_DIR),
            help="Directory to save simulation outputs"
        )
        
        validate_only = st.checkbox(
            "Validate only",
            value=st.session_state.run_config.get('validate_only', False),
            help="Only validate inputs without running simulation"
        )
    
    # Update session state
    st.session_state.run_config.update({
        'season': season,
        'week': week,
        'sims': sims,
        'seed': seed,
        'output_dir': output_dir,
        'validate_only': validate_only
    })
    
    # Show deterministic run info
    if seed:
        st.info(f"🎯 **Deterministic run**: seed={seed} (results will be reproducible)")
    
    return st.session_state.run_config

def create_presets_section():
    """Create presets save/load section"""
    st.subheader("💾 Presets")
    
    presets = load_presets()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Save preset
        preset_name = st.text_input("Preset name", placeholder="Enter preset name")
        if st.button("Save Current Settings") and preset_name:
            current_preset = {
                'column_mapping': st.session_state.column_mapping,
                'run_config': st.session_state.run_config,
                'saved_at': datetime.now().isoformat()
            }
            presets[preset_name] = current_preset
            save_presets(presets)
            st.success(f"✅ Saved preset: {preset_name}")
            st.rerun()
    
    with col2:
        # Load preset
        if presets:
            preset_to_load = st.selectbox(
                "Load preset",
                [''] + list(presets.keys()),
                help="Select a preset to load"
            )
            
            if st.button("Load Preset") and preset_to_load:
                preset_data = presets[preset_to_load]
                st.session_state.column_mapping.update(preset_data.get('column_mapping', {}))
                st.session_state.run_config.update(preset_data.get('run_config', {}))
                st.success(f"✅ Loaded preset: {preset_to_load}")
                st.rerun()
        else:
            st.info("No presets saved yet")

def create_data_preview_section(df: pd.DataFrame, mapping: Dict[str, str]):
    """Create data preview section"""
    if df.empty:
        return
    
    st.subheader("👀 Data Preview")
    
    # Show first 10 rows with mapped columns
    preview_df = df.head(10).copy()
    
    # Add computed player_id if possible
    if 'player_id' in preview_df.columns:
        cols_to_show = ['player_id'] + [col for col in preview_df.columns if col != 'player_id']
        preview_df = preview_df[cols_to_show]
    
    st.dataframe(preview_df, use_container_width=True)
    
    # Show statistics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Players", len(df))
    
    with col2:
        if 'POS' in df.columns:
            position_counts = df['POS'].value_counts()
            st.write("**Position Breakdown:**")
            for pos, count in position_counts.items():
                st.write(f"• {pos}: {count}")
    
    with col3:
        if 'TEAM' in df.columns:
            team_count = df['TEAM'].nunique()
            st.metric("Unique Teams", team_count)

def run_simulation_section(players_data: pd.DataFrame, file_paths: Dict[str, str], run_config: Dict[str, Any]):
    """Run simulation section"""
    st.subheader("🚀 Run Simulation")
    
    if players_data is None or players_data.empty:
        st.warning("⚠️ Please upload or select a players CSV file first")
        return
    
    # Validation summary
    warnings, errors, validated_df = validate_mapping_and_data(players_data, st.session_state.column_mapping)
    
    if errors:
        st.error("❌ **Cannot run simulation due to errors:**")
        for error in errors:
            st.error(f"• {error}")
        return
    
    if warnings:
        st.warning("⚠️ **Warnings (simulation can still run):**")
        for warning in warnings:
            st.warning(f"• {warning}")
    
    # Check missing priors
    missing_priors_count = 0  # This would be calculated from actual prior files
    if missing_priors_count > 0:
        st.info(f"ℹ️ {missing_priors_count} players missing from priors - rookie fallback will be used")
    
    # Run button
    col1, col2 = st.columns([1, 4])
    
    with col1:
        run_button = st.button(
            "🚀 Run Simulation",
            type="primary",
            use_container_width=True
        )
    
    with col2:
        if st.button("🗑️ Clear Cached Results"):
            st.session_state.simulation_results = None
            st.success("✅ Cleared cached results")
            st.rerun()
    
    if run_button:
        # Save mapped data to temporary file for simulation
        temp_players_path = os.path.join(run_config['output_dir'], 'temp_players.csv')
        os.makedirs(run_config['output_dir'], exist_ok=True)
        validated_df.to_csv(temp_players_path, index=False)
        
        # Run simulation
        with st.spinner("🔄 Running simulation..."):
            try:
                result = run_simulation(
                    season=run_config['season'],
                    week=run_config['week'],
                    players_site_path=temp_players_path,
                    team_priors_path=file_paths['team_priors_path'],
                    player_priors_path=file_paths['player_priors_path'],
                    boom_thresholds_path=file_paths['boom_thresholds_path'],
                    sims=run_config['sims'],
                    seed=run_config['seed'],
                    output_dir=run_config['output_dir'],
                    validate_only=run_config['validate_only']
                )
                
                if result.get('status') == 'completed':
                    st.session_state.simulation_results = result
                    st.success("✅ Simulation completed successfully!")
                elif result.get('status') == 'validated':
                    st.success("✅ Validation completed successfully!")
                else:
                    st.error(f"❌ Simulation failed: {result.get('message', 'Unknown error')}")
                    
            except Exception as e:
                st.error(f"❌ Simulation error: {str(e)}")
            finally:
                # Clean up temp file
                if os.path.exists(temp_players_path):
                    os.remove(temp_players_path)

def create_results_section():
    """Create results exploration section"""
    if not st.session_state.simulation_results:
        return
    
    results = st.session_state.simulation_results
    output_dir = results.get('output_dir', DEFAULT_OUTPUT_DIR)
    
    st.header("📊 Results Explorer")
    
    # Load result files
    result_files = {
        'sim_players': os.path.join(output_dir, 'sim_players.csv'),
        'compare': os.path.join(output_dir, 'compare.csv'),
        'diagnostics': os.path.join(output_dir, 'diagnostics.csv'),
        'flags': os.path.join(output_dir, 'flags.csv')
    }
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Sim Players", "⚖️ Compare", "🔍 Diagnostics", "🚩 Flags"])
    
    with tab1:
        create_sim_players_tab(result_files['sim_players'])
    
    with tab2:
        create_compare_tab(result_files['compare'])
    
    with tab3:
        create_diagnostics_tab(result_files['diagnostics'])
    
    with tab4:
        create_flags_tab(result_files['flags'])
    
    # Download section
    st.subheader("📥 Downloads")
    create_download_section(output_dir, result_files)

def create_sim_players_tab(file_path: str):
    """Create sim players tab"""
    if not os.path.exists(file_path):
        st.warning("Sim players file not found")
        return
    
    try:
        df = pd.read_csv(file_path)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            position_filter = st.multiselect(
                "Filter by position",
                options=df['position'].unique() if 'position' in df.columns else [],
                default=df['position'].unique() if 'position' in df.columns else []
            )
        
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                options=['sim_mean', 'sim_std', 'boom_score', 'boom_prob'] if len(df) > 0 else [],
                index=0
            )
        
        with col3:
            sort_ascending = st.checkbox("Ascending", value=False)
        
        # Apply filters
        filtered_df = df.copy()
        if position_filter and 'position' in df.columns:
            filtered_df = filtered_df[filtered_df['position'].isin(position_filter)]
        
        if sort_by and sort_by in filtered_df.columns:
            filtered_df = filtered_df.sort_values(sort_by, ascending=sort_ascending)
        
        # Display data
        st.dataframe(filtered_df, use_container_width=True)
        
        # Charts
        if len(filtered_df) > 0:
            st.subheader("📊 Charts")
            
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                if 'sim_mean' in filtered_df.columns and 'position' in filtered_df.columns:
                    fig = px.box(filtered_df, x='position', y='sim_mean', title="Sim Mean by Position")
                    st.plotly_chart(fig, use_container_width=True)
            
            with chart_col2:
                if 'boom_score' in filtered_df.columns and 'position' in filtered_df.columns:
                    fig = px.scatter(filtered_df, x='sim_mean', y='boom_score', color='position', 
                                   title="Boom Score vs Sim Mean")
                    st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading sim players data: {e}")

def create_compare_tab(file_path: str):
    """Create compare tab"""
    if not os.path.exists(file_path):
        st.warning("Compare file not found")
        return
    
    try:
        df = pd.read_csv(file_path)
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            position_filter = st.multiselect(
                "Filter by position",
                options=df['position'].unique() if 'position' in df.columns else [],
                default=df['position'].unique() if 'position' in df.columns else [],
                key="compare_position_filter"
            )
        
        with col2:
            sort_by = st.selectbox(
                "Sort by",
                options=['delta_mean', 'beat_site_prob', 'value_per_1k'] if len(df) > 0 else [],
                index=0,
                key="compare_sort"
            )
        
        with col3:
            sort_ascending = st.checkbox("Ascending", value=False, key="compare_ascending")
        
        # Apply filters
        filtered_df = df.copy()
        if position_filter and 'position' in df.columns:
            filtered_df = filtered_df[filtered_df['position'].isin(position_filter)]
        
        if sort_by and sort_by in filtered_df.columns:
            filtered_df = filtered_df.sort_values(sort_by, ascending=sort_ascending)
        
        # Display data
        st.dataframe(filtered_df, use_container_width=True)
        
        # Charts
        if len(filtered_df) > 0:
            st.subheader("📊 Charts")
            
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                if 'site_fpts' in filtered_df.columns and 'sim_mean' in filtered_df.columns:
                    fig = px.scatter(filtered_df, x='site_fpts', y='sim_mean', color='position',
                                   title="Site FPTS vs Sim Mean")
                    # Add diagonal line
                    min_val = min(filtered_df['site_fpts'].min(), filtered_df['sim_mean'].min())
                    max_val = max(filtered_df['site_fpts'].max(), filtered_df['sim_mean'].max())
                    fig.add_shape(type="line", x0=min_val, y0=min_val, x1=max_val, y1=max_val,
                                line=dict(dash="dash", color="gray"))
                    st.plotly_chart(fig, use_container_width=True)
            
            with chart_col2:
                if 'delta_mean' in filtered_df.columns and 'position' in filtered_df.columns:
                    fig = px.box(filtered_df, x='position', y='delta_mean', title="Delta Mean by Position")
                    st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Error loading compare data: {e}")

def create_diagnostics_tab(file_path: str):
    """Create diagnostics tab"""
    if not os.path.exists(file_path):
        st.warning("Diagnostics file not found")
        return
    
    try:
        df = pd.read_csv(file_path)
        
        if len(df) > 0:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No diagnostics data available")
        
    except Exception as e:
        st.error(f"Error loading diagnostics data: {e}")

def create_flags_tab(file_path: str):
    """Create flags tab"""
    if not os.path.exists(file_path):
        st.warning("Flags file not found")
        return
    
    try:
        df = pd.read_csv(file_path)
        
        if len(df) > 0:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No flags data available")
        
    except Exception as e:
        st.error(f"Error loading flags data: {e}")

def create_download_section(output_dir: str, result_files: Dict[str, str]):
    """Create download section"""
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Individual Files:**")
        for name, file_path in result_files.items():
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    st.download_button(
                        f"📁 Download {name}.csv",
                        data=f.read(),
                        file_name=f"{name}.csv",
                        mime="text/csv",
                        key=f"download_{name}"
                    )
    
    with col2:
        st.write("**Bundle Download:**")
        if st.button("📦 Create ZIP Bundle"):
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add all result files
                for name, file_path in result_files.items():
                    if os.path.exists(file_path):
                        zip_file.write(file_path, f"{name}.csv")
                
                # Add metadata
                metadata_path = os.path.join(output_dir, 'metadata.json')
                if os.path.exists(metadata_path):
                    zip_file.write(metadata_path, 'metadata.json')
            
            zip_buffer.seek(0)
            
            st.download_button(
                "📥 Download Complete Bundle",
                data=zip_buffer.getvalue(),
                file_name=f"simulator_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                mime="application/zip"
            )

def main():
    """Main application"""
    # Initialize
    initialize_session_state()
    
    # Header
    st.title("🏈 NFL GPP Simulator")
    st.markdown("Monte Carlo simulation for NFL DFS lineup optimization")
    
    # Add methodology link
    with st.expander("📖 Methodology"):
        st.markdown("""
        This simulator uses Monte Carlo methods to generate projections based on:
        - Historical NFL data (2023-2024 baseline)
        - Team and player priors
        - Position-specific boom thresholds
        - DraftKings scoring system
        
        **Reference**: [Monte Carlo Football Methodology](docs/research/monte_carlo_football.pdf)
        """)
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Configuration")
        
        # File inputs
        players_data, file_paths = create_file_input_section()
        
        st.divider()
        
        # Run configuration
        run_config = create_run_config_section()
        
        st.divider()
        
        # Presets
        create_presets_section()
    
    # Main content area
    if players_data is not None:
        # Auto-detect column mapping
        if not st.session_state.column_mapping:
            st.session_state.column_mapping = detect_column_mapping(players_data)
        
        # Column mapping
        st.session_state.column_mapping = create_column_mapping_widget(players_data)
        
        # Validation and preview
        warnings, errors, validated_df = validate_mapping_and_data(players_data, st.session_state.column_mapping)
        
        if not errors:
            create_data_preview_section(validated_df, st.session_state.column_mapping)
        
        st.divider()
        
        # Run simulation
        run_simulation_section(players_data, file_paths, run_config)
        
        st.divider()
        
        # Results
        create_results_section()
    
    else:
        st.info("👆 Please upload or select a players CSV file in the sidebar to get started")

if __name__ == "__main__":
    main()