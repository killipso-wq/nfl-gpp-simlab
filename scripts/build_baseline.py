#!/usr/bin/env python3
"""
Build baseline player and team priors from historical NFL data.

Usage: python scripts/build_baseline.py --start 2023 --end 2024 --out data
"""
import argparse
import json
import os
import sys
from pathlib import Path

# Add src to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import pandas as pd
    import numpy as np
    import nfl_data_py as nfl
except ImportError as e:
    print(f"Error: Required packages not available: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

from ingest.scoring import dk_points
from ingest.name_normalizer import build_player_id


def load_weekly_data(start_year, end_year):
    """Load weekly data for skill positions from nfl_data_py."""
    print(f"Loading weekly data for seasons {start_year}-{end_year}...")
    
    # Load weekly data for the specified seasons
    seasons = list(range(start_year, end_year + 1))
    weekly_data = nfl.import_weekly_data(seasons)
    
    # Filter to skill positions only (QB, RB, WR, TE)
    skill_positions = ['QB', 'RB', 'WR', 'TE']
    weekly_data = weekly_data[weekly_data['position'].isin(skill_positions)]
    
    print(f"Loaded {len(weekly_data)} weekly records for skill positions")
    return weekly_data


def compute_player_priors(weekly_data):
    """Compute player priors from weekly data."""
    print("Computing player priors...")
    
    # Calculate DK points for each weekly record
    weekly_data['dk_points'] = weekly_data.apply(dk_points, axis=1)
    
    # Group by player and compute aggregates
    player_stats = []
    
    for (player_name, team, position), group in weekly_data.groupby(['player_name', 'recent_team', 'position']):
        # Skip if no valid data
        if len(group) == 0:
            continue
            
        # Calculate statistics
        dk_scores = group['dk_points'].dropna()
        if len(dk_scores) == 0:
            continue
            
        games = len(dk_scores)
        dk_mean = dk_scores.mean()
        dk_std = dk_scores.std() if len(dk_scores) > 1 else 0.0
        dk_p75 = dk_scores.quantile(0.75)
        dk_p90 = dk_scores.quantile(0.90)
        
        # Build player ID
        player_id = build_player_id(team, position, player_name)
        
        player_stats.append({
            'player_id': player_id,
            'name': player_name,
            'team': team,
            'position': position,
            'games': games,
            'dk_mean': round(dk_mean, 2),
            'dk_std': round(dk_std, 2),
            'dk_p75': round(dk_p75, 2),
            'dk_p90': round(dk_p90, 2)
        })
    
    player_priors = pd.DataFrame(player_stats)
    print(f"Generated priors for {len(player_priors)} players")
    return player_priors


def compute_team_priors(weekly_data):
    """Compute team priors from weekly data."""
    print("Computing team priors...")
    
    # We need team-level data, so we'll aggregate from player data
    # This is a simplified approach - ideally we'd use team-level stats
    team_stats = []
    
    for team, team_data in weekly_data.groupby('recent_team'):
        # Get unique games for this team
        games = team_data[['season', 'week']].drop_duplicates()
        num_games = len(games)
        
        if num_games == 0:
            continue
            
        # Aggregate stats across all players/games for this team
        total_pass_attempts = team_data['passing_attempts'].fillna(0).sum()
        total_rush_attempts = team_data['rushing_attempts'].fillna(0).sum()
        total_plays = total_pass_attempts + total_rush_attempts
        
        # Calculate rates
        plays_pg = total_plays / num_games if num_games > 0 else 0
        pass_rate = total_pass_attempts / total_plays if total_plays > 0 else 0
        rush_rate = total_rush_attempts / total_plays if total_plays > 0 else 0
        
        # Estimate points per game (simplified - using total DK points as proxy)
        team_data['dk_points'] = team_data.apply(dk_points, axis=1)
        total_points = team_data['dk_points'].sum()
        points_pg = total_points / num_games if num_games > 0 else 0
        
        team_stats.append({
            'team': team,
            'games': num_games,
            'plays_pg': round(plays_pg, 1),
            'pass_rate': round(pass_rate, 3),
            'rush_rate': round(rush_rate, 3),
            'points_pg': round(points_pg, 1)
        })
    
    team_priors = pd.DataFrame(team_stats)
    print(f"Generated priors for {len(team_priors)} teams")
    return team_priors


def main():
    parser = argparse.ArgumentParser(description='Build baseline player and team priors')
    parser.add_argument('--start', type=int, required=True, help='Start year (e.g., 2023)')
    parser.add_argument('--end', type=int, required=True, help='End year (e.g., 2024)')
    parser.add_argument('--out', type=str, default='data', help='Output directory (default: data)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.start > args.end:
        print("Error: Start year must be <= end year")
        sys.exit(1)
    
    # Create output directories
    baseline_dir = Path(args.out) / "baseline"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load data
        weekly_data = load_weekly_data(args.start, args.end)
        
        # Compute priors
        player_priors = compute_player_priors(weekly_data)
        team_priors = compute_team_priors(weekly_data)
        
        # Save outputs
        player_output = baseline_dir / "player_priors.csv"
        team_output = baseline_dir / "team_priors.csv"
        
        player_priors.to_csv(player_output, index=False)
        team_priors.to_csv(team_output, index=False)
        
        print(f"\nOutputs saved:")
        print(f"  Player priors: {player_output}")
        print(f"  Team priors: {team_output}")
        print(f"\nBaseline build complete!")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()