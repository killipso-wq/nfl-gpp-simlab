"""
CLI entrypoint for running weekly projections from site players CSV.

Command: python -m src.projections.run_week_from_site_players
"""

import argparse
import json
import os
import uuid
import zipfile
from pathlib import Path
import subprocess
from datetime import datetime

import pandas as pd
import numpy as np

from ..ingest.name_normalizer import build_player_id_from_row, normalize_position
from ..sim.game_simulator import simulate_week
from ..projections.value_metrics import calculate_value_metrics
from ..projections.boom_score import calculate_boom_metrics
from ..projections.diagnostics import generate_diagnostics_summary, identify_flags


def load_players_csv(filepath: str) -> pd.DataFrame:
    """
    Load and normalize players CSV file.
    
    Expected columns: PLAYER, POS, TEAM, OPP (optional), FPTS (optional), SAL (optional), RST% (optional)
    """
    df = pd.read_csv(filepath)
    
    # Ensure required columns exist
    required_cols = ['PLAYER', 'POS', 'TEAM']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Normalize position column
    df['POS'] = df['POS'].apply(normalize_position)
    
    # Generate player IDs
    df['player_id'] = df.apply(lambda row: build_player_id_from_row(row), axis=1)
    
    # Normalize optional columns
    if 'FPTS' in df.columns:
        df['site_fpts'] = pd.to_numeric(df['FPTS'], errors='coerce')
    
    if 'RST%' in df.columns:
        # Normalize ownership: if ≤ 1, treat as fraction and convert to percent
        df['RST%'] = pd.to_numeric(df['RST%'], errors='coerce')
        df.loc[df['RST%'] <= 1, 'RST%'] = df.loc[df['RST%'] <= 1, 'RST%'] * 100
    
    if 'SAL' in df.columns:
        df['SAL'] = pd.to_numeric(df['SAL'], errors='coerce')
    
    # Ensure OPP column exists (can be null for MVP)
    if 'OPP' not in df.columns:
        df['OPP'] = None
    
    return df


def load_priors(team_priors_path: str, player_priors_path: str):
    """Load team and player priors from CSV files."""
    try:
        team_priors = pd.read_csv(team_priors_path)
    except FileNotFoundError:
        print(f"Warning: Team priors file not found: {team_priors_path}")
        team_priors = pd.DataFrame()
    
    try:
        player_priors = pd.read_csv(player_priors_path)
    except FileNotFoundError:
        print(f"Warning: Player priors file not found: {player_priors_path}")
        player_priors = pd.DataFrame()
    
    return team_priors, player_priors


def load_boom_thresholds(filepath: str) -> dict:
    """Load boom thresholds from JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Warning: Boom thresholds file not found: {filepath}")
        # Default thresholds for MVP
        return {
            'QB': 25.0,
            'RB': 20.0, 
            'WR': 20.0,
            'TE': 15.0,
            'DST': 12.0,
            'K': 10.0
        }


def join_with_priors(players_df: pd.DataFrame, 
                    team_priors: pd.DataFrame, 
                    player_priors: pd.DataFrame) -> pd.DataFrame:
    """
    Join players with priors and handle rookie fallback.
    
    Returns DataFrame with dk_mean, dk_std, rookie_fallback columns.
    """
    result_df = players_df.copy()
    
    # Initialize rookie fallback flag
    result_df['rookie_fallback'] = False
    result_df['dk_mean'] = np.nan
    result_df['dk_std'] = np.nan
    
    # Join with player priors if available
    if len(player_priors) > 0 and 'player_id' in player_priors.columns:
        merged = result_df.merge(
            player_priors[['player_id', 'dk_mean', 'dk_std']], 
            on='player_id', 
            how='left',
            suffixes=('', '_prior')
        )
        
        # Use prior values where available
        result_df['dk_mean'] = merged['dk_mean_prior']
        result_df['dk_std'] = merged['dk_std_prior']
    
    # Handle missing priors with position-level fallback
    missing_priors = pd.isna(result_df['dk_mean']) | pd.isna(result_df['dk_std'])
    
    if missing_priors.sum() > 0:
        # Calculate position-level means and stds from available priors
        if len(player_priors) > 0 and 'POS' in player_priors.columns:
            pos_stats = player_priors.groupby('POS').agg({
                'dk_mean': 'mean',
                'dk_std': 'mean'
            }).reset_index()
            
            # Fill missing values with position averages
            for _, pos_row in pos_stats.iterrows():
                pos = pos_row['POS']
                pos_mask = (result_df['POS'] == pos) & missing_priors
                
                result_df.loc[pos_mask, 'dk_mean'] = pos_row['dk_mean']
                result_df.loc[pos_mask, 'dk_std'] = pos_row['dk_std']
                result_df.loc[pos_mask, 'rookie_fallback'] = True
        
        # For players still missing priors, use site FPTS if available
        still_missing = pd.isna(result_df['dk_mean']) | pd.isna(result_df['dk_std'])
        if still_missing.sum() > 0 and 'site_fpts' in result_df.columns:
            # Use site FPTS as mean with position-calibrated variance
            pos_var_map = {'QB': 5.0, 'RB': 4.0, 'WR': 4.0, 'TE': 3.0, 'DST': 3.0, 'K': 2.0}
            
            for pos, default_std in pos_var_map.items():
                pos_mask = (result_df['POS'] == pos) & still_missing & pd.notna(result_df['site_fpts'])
                
                result_df.loc[pos_mask, 'dk_mean'] = result_df.loc[pos_mask, 'site_fpts']
                result_df.loc[pos_mask, 'dk_std'] = default_std
                result_df.loc[pos_mask, 'rookie_fallback'] = True
    
    return result_df


def get_git_commit() -> str:
    """Get current git commit hash if available."""
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return result.stdout.strip()[:8]  # Short hash
    except:
        pass
    return "unknown"


def create_metadata(args, players_df: pd.DataFrame, diagnostics_dict: dict) -> dict:
    """Create metadata dictionary for the simulation run."""
    return {
        'run_id': str(uuid.uuid4()),
        'timestamp': datetime.now().isoformat(),
        'sims': args.sims,
        'seed': args.seed,
        'season': args.season,
        'week': args.week,
        'git_commit': get_git_commit(),
        'methodology': 'docs/research/monte_carlo_football.pdf',
        'column_mapping': {
            'players_file': args.players_site,
            'detected_columns': list(players_df.columns),
            'required_columns': ['PLAYER', 'POS', 'TEAM'],
            'optional_columns': ['OPP', 'FPTS', 'SAL', 'RST%']
        },
        'counts': {
            'total_players': len(players_df),
            'by_position': players_df['POS'].value_counts().to_dict() if 'POS' in players_df.columns else {}
        },
        'diagnostics': diagnostics_dict
    }


def save_outputs(sim_df: pd.DataFrame, compare_df: pd.DataFrame, 
                diagnostics_df: pd.DataFrame, flags_df: pd.DataFrame,
                metadata: dict, output_dir: str):
    """Save all output files."""
    # Ensure output directory exists
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Save CSV files
    sim_df.to_csv(f"{output_dir}/sim_players.csv", index=False)
    compare_df.to_csv(f"{output_dir}/compare.csv", index=False)
    diagnostics_df.to_csv(f"{output_dir}/diagnostics_summary.csv", index=False)
    flags_df.to_csv(f"{output_dir}/flags.csv", index=False)
    
    # Save metadata JSON
    with open(f"{output_dir}/metadata.json", 'w') as f:
        json.dump(metadata, f, indent=2, default=str)
    
    # Create ZIP bundle
    zip_path = f"{output_dir}/simulator_outputs.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.write(f"{output_dir}/sim_players.csv", "sim_players.csv")
        zf.write(f"{output_dir}/compare.csv", "compare.csv") 
        zf.write(f"{output_dir}/diagnostics_summary.csv", "diagnostics_summary.csv")
        zf.write(f"{output_dir}/flags.csv", "flags.csv")
        zf.write(f"{output_dir}/metadata.json", "metadata.json")
    
    print(f"Outputs saved to {output_dir}/")
    print(f"ZIP bundle: {zip_path}")


def main():
    parser = argparse.ArgumentParser(description='Run weekly projections from site players CSV')
    parser.add_argument('--season', type=int, required=True, help='Season year')
    parser.add_argument('--week', type=int, required=True, help='Week number')
    parser.add_argument('--players-site', required=True, help='Path to players CSV file')
    parser.add_argument('--team-priors', required=True, help='Path to team priors CSV')
    parser.add_argument('--player-priors', required=True, help='Path to player priors CSV')
    parser.add_argument('--boom-thresholds', required=True, help='Path to boom thresholds JSON')
    parser.add_argument('--sims', type=int, default=10000, help='Number of simulations')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    parser.add_argument('--out', required=True, help='Output directory')
    
    args = parser.parse_args()
    
    print(f"Running simulation for {args.season} week {args.week}")
    print(f"Players file: {args.players_site}")
    print(f"Simulations: {args.sims}, Seed: {args.seed}")
    
    # Load data
    print("Loading players...")
    players_df = load_players_csv(args.players_site)
    print(f"Loaded {len(players_df)} players")
    
    print("Loading priors...")
    team_priors, player_priors = load_priors(args.team_priors, args.player_priors)
    
    print("Loading boom thresholds...")
    boom_thresholds = load_boom_thresholds(args.boom_thresholds)
    
    # Join with priors
    print("Joining with priors...")
    players_with_priors = join_with_priors(players_df, team_priors, player_priors)
    
    # Run simulation
    print("Running Monte Carlo simulation...")
    sim_results = simulate_week(players_with_priors, boom_thresholds, args.sims, args.seed)
    
    # Create sim_players.csv
    sim_columns = ['player_id', 'PLAYER', 'POS', 'TEAM', 'OPP', 
                   'sim_mean', 'floor_p10', 'p75', 'ceiling_p90', 'p95', 
                   'boom_prob', 'rookie_fallback']
    if 'SAL' in sim_results.columns:
        sim_columns.append('SAL')
    
    sim_players = sim_results[sim_columns].copy()
    
    # Create compare.csv with additional metrics
    print("Calculating value metrics...")
    compare_df = calculate_value_metrics(sim_results)
    
    print("Calculating boom scores...")
    compare_df = calculate_boom_metrics(compare_df, boom_thresholds)
    
    # Select compare columns
    compare_columns = ['player_id', 'PLAYER', 'POS', 'TEAM', 'OPP']
    if 'site_fpts' in compare_df.columns:
        compare_columns.extend(['site_fpts', 'delta_mean', 'pct_delta', 'beat_site_prob'])
    compare_columns.extend(['value_per_1k', 'ceil_per_1k'])
    if 'site_fpts' in compare_df.columns:
        compare_columns.append('site_fpts')  # site_val alias
    if 'RST%' in compare_df.columns:
        compare_columns.append('RST%')
    compare_columns.extend(['boom_score', 'dart_flag'])
    
    # Filter to available columns
    available_compare_cols = [col for col in compare_columns if col in compare_df.columns]
    compare_final = compare_df[available_compare_cols].copy()
    
    # Generate diagnostics
    print("Generating diagnostics...")
    diagnostics_df, diagnostics_dict = generate_diagnostics_summary(compare_df)
    
    # Generate flags
    print("Identifying flags...")
    flags_df = identify_flags(compare_df)
    
    # Create metadata
    metadata = create_metadata(args, players_df, diagnostics_dict)
    
    # Save outputs
    print("Saving outputs...")
    save_outputs(sim_players, compare_final, diagnostics_df, flags_df, metadata, args.out)
    
    print("Simulation complete!")


if __name__ == '__main__':
    main()