#!/usr/bin/env python3
"""
Build boom thresholds from historical NFL data.

Usage: python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90
"""
import argparse
import json
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


def compute_boom_thresholds(weekly_data, quantile=0.90):
    """Compute boom thresholds by position."""
    print(f"Computing boom thresholds at {quantile:.2f} quantile...")
    
    # Calculate DK points for each weekly record
    weekly_data['dk_points'] = weekly_data.apply(dk_points, axis=1)
    
    # Remove rows with NaN dk_points
    weekly_data = weekly_data.dropna(subset=['dk_points'])
    
    # Compute quantiles by position
    boom_thresholds = {}
    
    for position in ['QB', 'RB', 'WR', 'TE']:
        pos_data = weekly_data[weekly_data['position'] == position]
        
        if len(pos_data) == 0:
            print(f"Warning: No data found for position {position}")
            boom_thresholds[position] = 0.0
            continue
            
        # Calculate the quantile threshold
        threshold = pos_data['dk_points'].quantile(quantile)
        boom_thresholds[position] = round(threshold, 1)
        
        print(f"  {position}: {threshold:.1f} (from {len(pos_data)} weekly performances)")
    
    return boom_thresholds


def main():
    parser = argparse.ArgumentParser(description='Build boom thresholds from historical data')
    parser.add_argument('--start', type=int, required=True, help='Start year (e.g., 2023)')
    parser.add_argument('--end', type=int, required=True, help='End year (e.g., 2024)')
    parser.add_argument('--out', type=str, required=True, help='Output file path (e.g., data/baseline/boom_thresholds.json)')
    parser.add_argument('--quantile', type=float, default=0.90, help='Quantile for boom threshold (default: 0.90)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.start > args.end:
        print("Error: Start year must be <= end year")
        sys.exit(1)
        
    if not (0 < args.quantile < 1):
        print("Error: Quantile must be between 0 and 1")
        sys.exit(1)
    
    # Create output directory if needed
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load data
        weekly_data = load_weekly_data(args.start, args.end)
        
        # Compute boom thresholds
        boom_thresholds = compute_boom_thresholds(weekly_data, args.quantile)
        
        # Save output with deterministic ordering
        ordered_thresholds = {pos: boom_thresholds[pos] for pos in ['QB', 'RB', 'WR', 'TE']}
        
        with open(output_path, 'w') as f:
            json.dump(ordered_thresholds, f, indent=2, sort_keys=True)
        
        print(f"\nBoom thresholds saved to: {output_path}")
        print("Thresholds:")
        for pos, threshold in ordered_thresholds.items():
            print(f"  {pos}: {threshold}")
        print(f"\nBoom thresholds build complete!")
        
    except Exception as e:
        print(f"Error during processing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()