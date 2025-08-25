"""
NFL GPP Simulator & Optimizer
Streamlit application with Simulator and Optimizer tabs
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import os
import sys
import json
from datetime import datetime
import traceback

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

try:
    from src.data.nfl_data import build_players_csv_from_nfl_data
    from src.common.io import (
        normalize_csv_for_simulator, 
        get_salary_cap, 
        get_roster_template
    )
    from src.optimizer.engine import LineupOptimizer
    from src.optimizer.presets import (
        get_gpp_presets, 
        apply_preset_to_constraints,
        get_strategy_tips
    )
except ImportError as e:
    st.error(f"Import error: {e}")
    st.stop()

# Set page config
st.set_page_config(
    page_title="NFL GPP Sim Optimizer",
    page_icon="🏈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'optimizer_players_data' not in st.session_state:
    st.session_state.optimizer_players_data = None
if 'generated_lineups' not in st.session_state:
    st.session_state.generated_lineups = None

def main():
    """Main application entry point"""
    st.title("🏈 NFL GPP Simulator & Optimizer")
    
    # Create tabs
    tab1, tab2 = st.tabs(["📊 Simulator", "⚡ Optimizer"])
    
    with tab1:
        simulator_tab()
    
    with tab2:
        optimizer_tab()

def simulator_tab():
    """Simulator tab implementation - placeholder for now"""
    st.header("Monte Carlo Simulator")
    
    st.info("📋 **Simulator functionality will be implemented here**")
    
    # File upload section
    st.subheader("Upload Players Data")
    uploaded_file = st.file_uploader(
        "Choose a players.csv file",
        type="csv",
        help="Upload your site players file with columns: PLAYER, POS, TEAM, OPP, SAL, FPTS, etc."
    )
    
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.success(f"✅ Loaded {len(df)} players")
            
            # Basic preview
            with st.expander("Preview Data", expanded=False):
                st.dataframe(df.head(10))
                
        except Exception as e:
            st.error(f"❌ Error loading file: {str(e)}")
    
    # Simulation parameters
    col1, col2 = st.columns(2)
    with col1:
        sims = st.number_input("Number of Simulations", min_value=100, max_value=50000, value=10000)
    with col2:
        seed = st.number_input("Random Seed", min_value=1, max_value=99999, value=42)
    
    if st.button("🎯 Run Simulation", disabled=uploaded_file is None):
        st.info("Simulation functionality will be implemented in future updates")

def optimizer_tab():
    """Optimizer tab implementation"""
    st.header("GPP Lineup Optimizer")
    
    # Build from nfl_data_py section
    st.subheader("📥 Build from nfl_data_py")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        season = st.number_input("Season", min_value=2020, max_value=2030, value=2025)
        site = st.selectbox("Site", ["DraftKings", "FanDuel"], index=0)
    with col2:
        week = st.number_input("Week", min_value=1, max_value=22, value=1)
        slate = st.selectbox("Slate", ["Main"], index=0)
    with col3:
        rng_seed = st.number_input("RNG Seed", min_value=1, max_value=99999, value=42)
    
    # Optional salary upload
    st.markdown("**Optional: Upload Salaries CSV**")
    salary_file = st.file_uploader(
        "Upload salaries file to override default placeholders",
        type="csv",
        help="CSV with player names and salaries"
    )
    
    if st.button("🔄 Generate Player Pool"):
        with st.spinner("Fetching data from nfl_data_py and building projections..."):
            try:
                # Generate actual player data
                players_data = build_players_csv_from_nfl_data(
                    season=season,
                    week=week,
                    site=site
                )
                
                # If salary file was uploaded, merge it
                if salary_file is not None:
                    try:
                        salary_df = pd.read_csv(salary_file)
                        st.info("Merging uploaded salary data...")
                        
                        # Simple name-based merge (could be improved with fuzzy matching)
                        if 'name' in salary_df.columns and 'salary' in salary_df.columns:
                            # Update salaries for matching players
                            for _, salary_row in salary_df.iterrows():
                                mask = players_data['name'].str.contains(
                                    salary_row['name'], case=False, na=False
                                )
                                if mask.any():
                                    players_data.loc[mask, 'salary'] = salary_row['salary']
                            
                            st.success("✅ Salary data merged successfully!")
                        else:
                            st.warning("⚠️ Salary file must have 'name' and 'salary' columns")
                    
                    except Exception as e:
                        st.error(f"❌ Error processing salary file: {str(e)}")
                
                st.session_state.optimizer_players_data = players_data
                st.success("✅ Player pool generated successfully!")
                
                # Preview section
                with st.expander("🔍 Preview Generated Data", expanded=True):
                    st.dataframe(players_data.head(20))
                    
                    # Show summary stats
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Players", len(players_data))
                    with col2:
                        st.metric("Avg Salary", f"${players_data['salary'].mean():,.0f}")
                    with col3:
                        st.metric("Avg Projection", f"{players_data['fpts'].mean():.1f}")
                    with col4:
                        st.metric("Positions", len(players_data['pos'].unique()))
                
                # Save data section
                save_dir = Path(f"data/generated/{season}_w{week}")
                save_dir.mkdir(parents=True, exist_ok=True)
                save_path = save_dir / "players.csv"
                
                players_data.to_csv(save_path, index=False)
                st.info(f"📁 Data saved to: `{save_path}`")
                
                # Download button
                csv_data = players_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download Players CSV",
                    data=csv_data,
                    file_name=f"players_{season}_w{week}.csv",
                    mime="text/csv"
                )
                
            except Exception as e:
                st.error(f"❌ Error generating data: {str(e)}")
                st.code(traceback.format_exc())
    
    # Send to optimizer button
    if st.session_state.optimizer_players_data is not None:
        if st.button("📊 Send to Optimizer"):
            st.success("✅ Data loaded into lineup builder below")
    
    st.divider()
    
    # GPP Presets + Lineup Builder section
    st.subheader("🎯 GPP Presets + Lineup Builder")
    
    # Preset selection
    preset = st.selectbox(
        "Select Preset",
        ["Solo Entry", "20-max", "150-max"],
        help="Pre-configured constraint sets for different contest sizes"
    )
    
    # Apply preset button
    if st.button(f"⚙️ Apply {preset} Preset"):
        constraints = apply_preset_to_constraints(preset, site.replace("DraftKings", "DraftKings").replace("FanDuel", "FanDuel"))
        
        # Store in session state
        st.session_state.current_constraints = constraints
        st.success(f"✅ Applied {preset} preset settings")
        
        # Show applied settings
        with st.expander("Applied Settings", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                st.write("**Lineup Settings**")
                st.write(f"- Lineups to build: {constraints['num_lineups']}")
                st.write(f"- Salary cap: ${constraints['salary_cap']:,}")
                st.write(f"- Min spend: ${constraints['min_salary']:,}")
            with col2:
                st.write("**Strategy Settings**")
                st.write(f"- QB stack: {constraints['qb_stack_min']}-{constraints['qb_stack_max']}")
                st.write(f"- Bring-back: {constraints['bring_back_count']}")
                st.write(f"- Max ownership: {constraints['max_total_ownership']}%")
        
        # Show strategy tips
        tips = get_strategy_tips(preset, site.replace("DraftKings", "DraftKings").replace("FanDuel", "FanDuel"))
        with st.expander("💡 Strategy Tips", expanded=False):
            for tip_type, tip_text in tips.items():
                st.write(f"**{tip_type.title()}:** {tip_text}")
    
    # Initialize constraints if not set
    if 'current_constraints' not in st.session_state:
        st.session_state.current_constraints = apply_preset_to_constraints("20-max", site)
    
    # Get current constraints or use defaults
    current_constraints = st.session_state.get('current_constraints', apply_preset_to_constraints("20-max", site))
    
    # Constraints UI
    st.markdown("**Optimization Constraints**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("*Lineup Configuration*")
        num_lineups = st.number_input(
            "Lineups to Build", 
            min_value=1, max_value=500, 
            value=current_constraints.get('num_lineups', 20)
        )
        salary_cap = st.number_input(
            "Salary Cap", 
            min_value=30000, max_value=70000, 
            value=current_constraints.get('salary_cap', 50000)
        )
        min_spend = st.number_input(
            "Minimum Spend", 
            min_value=30000, max_value=70000, 
            value=current_constraints.get('min_salary', 49000)
        )
        
        st.markdown("*Stacking Rules*")
        qb_stack_min = st.number_input(
            "QB Stack Min", 
            min_value=1, max_value=3, 
            value=current_constraints.get('qb_stack_min', 1)
        )
        qb_stack_max = st.number_input(
            "QB Stack Max", 
            min_value=1, max_value=3, 
            value=current_constraints.get('qb_stack_max', 2)
        )
        bring_back = st.number_input(
            "Bring-back Count", 
            min_value=0, max_value=2, 
            value=current_constraints.get('bring_back_count', 1)
        )
        max_per_team = st.number_input(
            "Max Players per Team", 
            min_value=1, max_value=6, 
            value=current_constraints.get('max_players_per_team', 4)
        )
    
    with col2:
        st.markdown("*Ownership & Exposure*")
        max_total_own = st.slider(
            "Max Total Ownership (%)", 
            min_value=100, max_value=1000, 
            value=current_constraints.get('max_total_ownership', 400)
        )
        max_player_exposure = st.slider(
            "Max Player Exposure (%)", 
            min_value=10, max_value=100, 
            value=current_constraints.get('max_player_exposure', 30)
        )
        
        st.markdown("*Randomness*")
        projection_variance = st.slider(
            "Projection Variance", 
            min_value=0.0, max_value=2.0, 
            value=current_constraints.get('projection_variance', 0.15), 
            step=0.05
        )
        diversity_constraint = st.slider(
            "Min Unique Players vs Previous", 
            min_value=1, max_value=8, 
            value=current_constraints.get('min_unique_players', 3)
        )
    
    # Build updated constraints dictionary
    optimization_constraints = {
        'num_lineups': num_lineups,
        'salary_cap': salary_cap,
        'min_salary': min_spend,
        'qb_stack_min': qb_stack_min,
        'qb_stack_max': qb_stack_max,
        'bring_back_count': bring_back,
        'max_players_per_team': max_per_team,
        'max_total_ownership': max_total_own,
        'max_player_exposure': max_player_exposure,
        'projection_variance': projection_variance,
        'min_unique_players': diversity_constraint
    }
    
    # Optimizer engine
    if st.button("🚀 Optimize Lineups"):
        if st.session_state.optimizer_players_data is not None:
            with st.spinner("Building optimal lineups..."):
                try:
                    # Initialize optimizer
                    optimizer = LineupOptimizer(site)
                    optimizer.load_players(st.session_state.optimizer_players_data)
                    
                    # Generate lineups
                    lineups = optimizer.optimize_multiple_lineups(
                        num_lineups=optimization_constraints['num_lineups'],
                        constraints=optimization_constraints,
                        randomize_projections=True,
                        base_seed=rng_seed
                    )
                    
                    if lineups:
                        st.session_state.generated_lineups = lineups
                        st.success(f"✅ Generated {len(lineups)} lineups successfully!")
                        
                        # Display results
                        display_optimization_results(lineups, optimization_constraints, season, week)
                    else:
                        st.error("❌ No feasible lineups found with current constraints")
                        st.info("💡 Try relaxing some constraints (lower min salary, increase max ownership, etc.)")
                    
                except Exception as e:
                    st.error(f"❌ Optimization error: {str(e)}")
                    st.code(traceback.format_exc())
        else:
            st.warning("⚠️ Please generate or upload player data first")


def display_optimization_results(lineups, constraints, season, week):
    """Display optimization results with download functionality"""
    st.subheader("🏆 Generated Lineups")
    
    # Summary statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Lineups", len(lineups))
    with col2:
        avg_fpts = np.mean([l['total_projection'] for l in lineups])
        st.metric("Avg Projected Points", f"{avg_fpts:.1f}")
    with col3:
        avg_salary = np.mean([l['total_salary'] for l in lineups])
        st.metric("Avg Salary Used", f"${avg_salary:,.0f}")
    with col4:
        avg_own = np.mean([l['total_ownership'] for l in lineups])
        st.metric("Avg Total Ownership", f"{avg_own:.1f}%")
    
    # Lineup table with detailed view
    lineup_data = []
    for i, lineup in enumerate(lineups):
        # Get position breakdown
        pos_counts = lineup['lineup_df']['pos'].value_counts()
        pos_summary = ', '.join([f"{pos}({count})" for pos, count in pos_counts.items()])
        
        # Get team breakdown
        team_counts = lineup['lineup_df']['team'].value_counts()
        team_summary = ', '.join([f"{team}({count})" for team, count in team_counts.items() if count > 1])
        
        lineup_data.append({
            'Lineup': i + 1,
            'Projected Points': f"{lineup['total_projection']:.1f}",
            'Salary': f"${lineup['total_salary']:,}",
            'Remaining': f"${constraints['salary_cap'] - lineup['total_salary']:,}",
            'Total Own%': f"{lineup['total_ownership']:.1f}%",
            'Positions': pos_summary,
            'Stacks': team_summary if team_summary else 'None'
        })
    
    lineup_df = pd.DataFrame(lineup_data)
    st.dataframe(lineup_df, use_container_width=True)
    
    # Detailed lineup viewer
    with st.expander("🔍 View Individual Lineups", expanded=False):
        selected_lineup = st.selectbox("Select lineup to view", range(1, len(lineups) + 1))
        
        if selected_lineup:
            lineup = lineups[selected_lineup - 1]
            detailed_df = lineup['lineup_df'][['name', 'pos', 'team', 'opp', 'salary', 'fpts', 'own%']].copy()
            detailed_df = detailed_df.sort_values(['pos', 'fpts'], ascending=[True, False])
            
            st.dataframe(detailed_df, use_container_width=True)
            
            # Show lineup summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Salary", f"${lineup['total_salary']:,}")
            with col2:
                st.metric("Projected Points", f"{lineup['total_projection']:.1f}")
            with col3:
                st.metric("Total Ownership", f"{lineup['total_ownership']:.1f}%")
    
    # Download section
    st.markdown("### 📥 Export Options")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # CSV export
        lineups_csv = create_lineups_csv(lineups)
        st.download_button(
            label="📄 Download Lineups CSV",
            data=lineups_csv,
            file_name=f"lineups_{season}_w{week}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # JSON metadata export
        metadata = create_lineups_metadata(lineups, constraints, season, week)
        st.download_button(
            label="📋 Download Metadata JSON",
            data=json.dumps(metadata, indent=2),
            file_name=f"metadata_{season}_w{week}_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json"
        )
    
    with col3:
        # DraftKings upload format
        if st.button("📤 Generate DK Upload CSV"):
            dk_csv = create_dk_upload_csv(lineups)
            st.download_button(
                label="Download DK Upload Format",
                data=dk_csv,
                file_name=f"dk_upload_{season}_w{week}.csv",
                mime="text/csv"
            )
    
    # Save to data/lineups
    save_lineups_to_disk(lineups, constraints, season, week)


def create_lineups_csv(lineups):
    """Create CSV export of all lineups"""
    all_lineup_data = []
    
    for i, lineup in enumerate(lineups):
        for _, player in lineup['lineup_df'].iterrows():
            all_lineup_data.append({
                'lineup_id': i + 1,
                'name': player['name'],
                'pos': player['pos'],
                'team': player['team'],
                'opp': player['opp'],
                'salary': player['salary'],
                'fpts': player['fpts'],
                'own%': player.get('own%', 0)
            })
    
    df = pd.DataFrame(all_lineup_data)
    return df.to_csv(index=False)


def create_dk_upload_csv(lineups):
    """Create DraftKings upload format CSV"""
    dk_data = []
    
    for i, lineup in enumerate(lineups):
        lineup_dict = {'Entry Id': i + 1}
        
        # Sort players by position for DK format
        sorted_players = lineup['lineup_df'].sort_values('pos')
        
        pos_counters = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0, 'DST': 0}
        
        for _, player in sorted_players.iterrows():
            pos = player['pos']
            if pos in pos_counters:
                pos_counters[pos] += 1
                col_name = f"{pos}" if pos_counters[pos] == 1 else f"{pos}{pos_counters[pos]}"
                lineup_dict[col_name] = player['name']
            elif pos in ['RB', 'WR', 'TE']:
                lineup_dict['FLEX'] = player['name']
        
        dk_data.append(lineup_dict)
    
    df = pd.DataFrame(dk_data)
    return df.to_csv(index=False)


def create_lineups_metadata(lineups, constraints, season, week):
    """Create metadata JSON for the optimization run"""
    return {
        'optimization_info': {
            'season': season,
            'week': week,
            'site': constraints.get('site', 'DraftKings'),
            'timestamp': datetime.now().isoformat(),
            'num_lineups_requested': constraints.get('num_lineups', len(lineups)),
            'num_lineups_generated': len(lineups)
        },
        'constraints_used': constraints,
        'summary_stats': {
            'avg_projection': np.mean([l['total_projection'] for l in lineups]),
            'avg_salary': np.mean([l['total_salary'] for l in lineups]),
            'avg_ownership': np.mean([l['total_ownership'] for l in lineups]),
            'salary_range': {
                'min': min([l['total_salary'] for l in lineups]),
                'max': max([l['total_salary'] for l in lineups])
            }
        }
    }


def save_lineups_to_disk(lineups, constraints, season, week):
    """Save lineups to data/lineups directory"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    save_dir = Path(f"data/lineups/{season}_w{week}_{timestamp}")
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Save lineups CSV
    lineups_csv = create_lineups_csv(lineups)
    with open(save_dir / "lineups.csv", 'w') as f:
        f.write(lineups_csv)
    
    # Save metadata JSON
    metadata = create_lineups_metadata(lineups, constraints, season, week)
    with open(save_dir / "metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2)
    
    st.info(f"💾 Lineups saved to: `{save_dir}`")

if __name__ == "__main__":
    main()