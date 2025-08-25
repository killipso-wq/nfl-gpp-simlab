"""
Build baseline data from nfl_data_py for seasons 2023-2024
Creates team/player priors and boom thresholds for the simulator
"""

import argparse
import pandas as pd
import numpy as np
import nfl_data_py as nfl
from pathlib import Path
import json
from typing import Dict, List


def fetch_historical_data(start_year: int, end_year: int) -> pd.DataFrame:
    """Fetch weekly stats for the specified year range"""
    print(f"Fetching NFL data for seasons {start_year}-{end_year}...")
    
    seasons = list(range(start_year, end_year + 1))
    weekly_data = nfl.import_weekly_data(seasons)
    
    print(f"Loaded {len(weekly_data)} player-week records")
    return weekly_data


def calculate_dk_points(stats_df: pd.DataFrame) -> pd.Series:
    """Calculate DraftKings fantasy points from stats"""
    points = pd.Series(0.0, index=stats_df.index)
    
    # Passing (1 pt per 25 yards, 4 pts per TD, -1 per INT)
    if 'passing_yards' in stats_df.columns:
        points += stats_df['passing_yards'].fillna(0) * 0.04
    if 'passing_tds' in stats_df.columns:
        points += stats_df['passing_tds'].fillna(0) * 4
    if 'interceptions' in stats_df.columns:
        points -= stats_df['interceptions'].fillna(0) * 1
    
    # Rushing (1 pt per 10 yards, 6 pts per TD)
    if 'rushing_yards' in stats_df.columns:
        points += stats_df['rushing_yards'].fillna(0) * 0.1
    if 'rushing_tds' in stats_df.columns:
        points += stats_df['rushing_tds'].fillna(0) * 6
    
    # Receiving (1 pt per 10 yards, 6 pts per TD, 1 pt per reception)
    if 'receiving_yards' in stats_df.columns:
        points += stats_df['receiving_yards'].fillna(0) * 0.1
    if 'receiving_tds' in stats_df.columns:
        points += stats_df['receiving_tds'].fillna(0) * 6
    if 'receptions' in stats_df.columns:
        points += stats_df['receptions'].fillna(0) * 1
    
    # Bonuses for long plays
    if 'rushing_yards' in stats_df.columns:
        points += (stats_df['rushing_yards'].fillna(0) >= 100) * 3
    if 'receiving_yards' in stats_df.columns:
        points += (stats_df['receiving_yards'].fillna(0) >= 100) * 3
    if 'passing_yards' in stats_df.columns:
        points += (stats_df['passing_yards'].fillna(0) >= 300) * 3
    
    # Fumbles lost (-1 pt)
    if 'fumbles_lost' in stats_df.columns:
        points -= stats_df['fumbles_lost'].fillna(0) * 1
    
    return points


def build_team_priors(weekly_data: pd.DataFrame, output_dir: Path) -> None:
    """Build team-level statistical priors"""
    print("Building team priors...")
    
    # Calculate DK points for all records
    weekly_data['dk_points'] = calculate_dk_points(weekly_data)
    
    # Filter to regular season only (weeks 1-18)
    regular_season = weekly_data[weekly_data['week'] <= 18].copy()
    
    # Aggregate by team and season
    team_stats = regular_season.groupby(['season', 'recent_team']).agg({
        'dk_points': ['mean', 'std', 'count'],
        'passing_yards': 'sum',
        'rushing_yards': 'sum',
        'receiving_yards': 'sum',
        'passing_tds': 'sum',
        'rushing_tds': 'sum',
        'receiving_tds': 'sum'
    }).round(2)
    
    # Flatten column names
    team_stats.columns = ['_'.join(col).strip() for col in team_stats.columns]
    team_stats = team_stats.reset_index()
    
    # Calculate overall team averages across seasons
    team_priors = team_stats.groupby('recent_team').agg({
        'dk_points_mean': 'mean',
        'dk_points_std': 'mean',
        'dk_points_count': 'sum',
        'passing_yards_sum': 'mean',
        'rushing_yards_sum': 'mean',
        'receiving_yards_sum': 'mean',
        'passing_tds_sum': 'mean',
        'rushing_tds_sum': 'mean',
        'receiving_tds_sum': 'mean'
    }).round(2)
    
    team_priors = team_priors.reset_index()
    team_priors.columns = [
        'team', 'avg_dk_points_per_game', 'avg_dk_points_std', 'total_games',
        'avg_passing_yards_per_season', 'avg_rushing_yards_per_season', 
        'avg_receiving_yards_per_season', 'avg_passing_tds_per_season',
        'avg_rushing_tds_per_season', 'avg_receiving_tds_per_season'
    ]
    
    # Save team priors
    output_path = output_dir / 'team_priors.csv'
    team_priors.to_csv(output_path, index=False)
    print(f"Saved team priors to {output_path}")


def build_player_priors(weekly_data: pd.DataFrame, output_dir: Path) -> None:
    """Build player-level statistical priors"""
    print("Building player priors...")
    
    # Calculate DK points for all records
    weekly_data['dk_points'] = calculate_dk_points(weekly_data)
    
    # Filter to regular season and players with meaningful data
    regular_season = weekly_data[
        (weekly_data['week'] <= 18) & 
        (weekly_data['dk_points'] >= 0)
    ].copy()
    
    # Aggregate by player
    player_stats = regular_season.groupby(['player_display_name', 'position']).agg({
        'dk_points': ['mean', 'std', 'count', 'min', 'max'],
        'season': ['min', 'max']  # Track career span in data
    }).round(2)
    
    # Flatten column names
    player_stats.columns = ['_'.join(col).strip() for col in player_stats.columns]
    player_stats = player_stats.reset_index()
    
    # Rename columns for clarity
    player_stats.columns = [
        'player_name', 'position', 'avg_dk_points', 'std_dk_points', 
        'games_played', 'min_dk_points', 'max_dk_points',
        'first_season', 'last_season'
    ]
    
    # Filter to players with at least 5 games
    player_priors = player_stats[player_stats['games_played'] >= 5].copy()
    
    # Add position-based percentiles
    for pos in player_priors['position'].unique():
        pos_mask = player_priors['position'] == pos
        pos_players = player_priors[pos_mask]
        
        if len(pos_players) > 0:
            player_priors.loc[pos_mask, 'position_rank_avg'] = pos_players['avg_dk_points'].rank(pct=True) * 100
            player_priors.loc[pos_mask, 'position_rank_ceiling'] = pos_players['max_dk_points'].rank(pct=True) * 100
    
    player_priors = player_priors.round(1)
    
    # Save player priors
    output_path = output_dir / 'player_priors.csv'
    player_priors.to_csv(output_path, index=False)
    print(f"Saved player priors to {output_path}")


def build_boom_thresholds(weekly_data: pd.DataFrame, output_dir: Path, quantile: float = 0.90) -> None:
    """Build position-specific boom thresholds"""
    print(f"Building boom thresholds at {quantile:.0%} quantile...")
    
    # Calculate DK points
    weekly_data['dk_points'] = calculate_dk_points(weekly_data)
    
    # Filter to regular season and meaningful performances
    regular_season = weekly_data[
        (weekly_data['week'] <= 18) & 
        (weekly_data['dk_points'] >= 0)
    ].copy()
    
    # Calculate boom thresholds by position
    boom_thresholds = {}
    
    for position in regular_season['position'].unique():
        pos_data = regular_season[regular_season['position'] == position]
        
        if len(pos_data) >= 50:  # Minimum sample size
            threshold = pos_data['dk_points'].quantile(quantile)
            boom_thresholds[position] = {
                'threshold': round(threshold, 1),
                'games_analyzed': len(pos_data),
                'quantile': quantile,
                'position_avg': round(pos_data['dk_points'].mean(), 1)
            }
    
    # Save boom thresholds
    output_path = output_dir / 'boom_thresholds.json'
    with open(output_path, 'w') as f:
        json.dump(boom_thresholds, f, indent=2)
    
    print(f"Saved boom thresholds to {output_path}")
    
    # Print summary
    print("\nBoom Thresholds Summary:")
    for pos, data in boom_thresholds.items():
        print(f"  {pos}: {data['threshold']:.1f} points ({data['games_analyzed']} games)")


def build_position_baselines(weekly_data: pd.DataFrame, output_dir: Path) -> None:
    """Build position-specific baseline statistics for fallback projections"""
    print("Building position baselines...")
    
    # Calculate DK points
    weekly_data['dk_points'] = calculate_dk_points(weekly_data)
    
    # Filter to regular season
    regular_season = weekly_data[
        (weekly_data['week'] <= 18) & 
        (weekly_data['dk_points'] >= 0)
    ].copy()
    
    # Calculate position statistics
    position_stats = regular_season.groupby('position').agg({
        'dk_points': ['mean', 'std', 'count', 'min', 'max'],
        'player_display_name': 'nunique'  # Number of unique players
    }).round(2)
    
    # Flatten columns
    position_stats.columns = ['_'.join(col).strip() for col in position_stats.columns]
    position_stats = position_stats.reset_index()
    
    position_stats.columns = [
        'position', 'avg_dk_points', 'std_dk_points', 'total_games',
        'min_dk_points', 'max_dk_points', 'unique_players'
    ]
    
    # Add percentiles
    for pos in position_stats['position'].unique():
        pos_data = regular_season[regular_season['position'] == pos]['dk_points']
        position_stats.loc[position_stats['position'] == pos, 'p25'] = pos_data.quantile(0.25)
        position_stats.loc[position_stats['position'] == pos, 'p50'] = pos_data.quantile(0.50)
        position_stats.loc[position_stats['position'] == pos, 'p75'] = pos_data.quantile(0.75)
        position_stats.loc[position_stats['position'] == pos, 'p90'] = pos_data.quantile(0.90)
    
    position_stats = position_stats.round(1)
    
    # Save position baselines
    output_path = output_dir / 'position_baselines.csv'
    position_stats.to_csv(output_path, index=False)
    print(f"Saved position baselines to {output_path}")


def create_metadata(output_dir: Path, start_year: int, end_year: int) -> None:
    """Create metadata file with build information"""
    from datetime import datetime
    import git
    
    metadata = {
        "build_date": datetime.now().isoformat(),
        "data_seasons": f"{start_year}-{end_year}",
        "description": "NFL baseline data for GPP simulator and optimizer",
        "files": {
            "team_priors.csv": "Team-level statistical averages",
            "player_priors.csv": "Player-level career statistics with position rankings",
            "boom_thresholds.json": "Position-specific boom scoring thresholds (90th percentile)",
            "position_baselines.csv": "Position-level statistical distributions for fallbacks"
        }
    }
    
    # Add git commit if available
    try:
        repo = git.Repo(search_parent_directories=True)
        metadata["git_commit"] = repo.head.commit.hexsha[:8]
    except:
        metadata["git_commit"] = "unknown"
    
    # Save metadata
    output_path = output_dir / 'metadata.json'
    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Saved build metadata to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Build baseline NFL data from nfl_data_py')
    parser.add_argument('--start', type=int, default=2023, help='Start year')
    parser.add_argument('--end', type=int, default=2024, help='End year')
    parser.add_argument('--out', type=str, default='data', help='Output directory')
    parser.add_argument('--quantile', type=float, default=0.90, help='Boom threshold quantile')
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.out) / 'baseline'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Building baseline data for {args.start}-{args.end}")
    print(f"Output directory: {output_dir}")
    
    try:
        # Fetch historical data
        weekly_data = fetch_historical_data(args.start, args.end)
        
        # Build all components
        build_team_priors(weekly_data, output_dir)
        build_player_priors(weekly_data, output_dir)
        build_boom_thresholds(weekly_data, output_dir, args.quantile)
        build_position_baselines(weekly_data, output_dir)
        
        # Create metadata
        create_metadata(output_dir, args.start, args.end)
        
        print(f"\n✅ Baseline data build completed successfully!")
        print(f"📁 Files saved to: {output_dir}")
        
    except Exception as e:
        print(f"❌ Error building baseline data: {str(e)}")
        raise


if __name__ == "__main__":
    main()