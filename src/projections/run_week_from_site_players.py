"""
CLI for running Monte Carlo simulation from site players CSV.
Implements the complete simulation pipeline per Master Reference.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Optional, Dict, Any

from ..ingest.site_players import load_site_players
from .monte_carlo import MonteCarloSimulator


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run Monte Carlo simulation from site players CSV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.projections.run_week_from_site_players \\
    --season 2025 --week 1 \\
    --players-site data/site/2025_w1_players.csv \\
    --sims 5000 --seed 42 --out data/sim_week

  python -m src.projections.run_week_from_site_players \\
    --season 2025 --week 1 \\
    --players-site data/site/players.csv \\
    --boom-thresholds data/boom_thresholds.json \\
    --sims 10000 --out results/
        """
    )
    
    # Required arguments
    parser.add_argument('--season', type=int, required=True,
                       help='NFL season year (e.g., 2025)')
    parser.add_argument('--week', type=int, required=True,
                       help='NFL week number (1-18)')
    parser.add_argument('--players-site', required=True,
                       help='Path to site players CSV file')
    parser.add_argument('--sims', type=int, default=10000,
                       help='Number of simulation trials (default: 10000)')
    parser.add_argument('--seed', type=int,
                       help='Random seed for reproducibility')
    parser.add_argument('--out', required=True,
                       help='Output directory for simulation artifacts')
    
    # Optional arguments (for future integration)
    parser.add_argument('--team-priors',
                       help='Path to team priors JSON file (not used in MVP)')
    parser.add_argument('--player-priors', 
                       help='Path to player priors JSON file (not used in MVP)')
    parser.add_argument('--boom-thresholds',
                       help='Path to boom thresholds JSON file')
    
    return parser.parse_args()


def load_boom_thresholds(file_path: Optional[str]) -> Optional[Dict[str, float]]:
    """Load boom thresholds from JSON file."""
    if not file_path:
        return None
        
    try:
        with open(file_path, 'r') as f:
            thresholds = json.load(f)
        print(f"Loaded boom thresholds from {file_path}")
        return thresholds
    except Exception as e:
        print(f"Warning: Could not load boom thresholds from {file_path}: {e}")
        print("Will use calibrated thresholds from current run")
        return None


def main():
    """Main execution function."""
    args = parse_args()
    
    print(f"NFL GPP Simulator - Season {args.season}, Week {args.week}")
    print(f"Players file: {args.players_site}")
    print(f"Simulations: {args.sims:,}")
    print(f"Seed: {args.seed}")
    print(f"Output directory: {args.out}")
    print()
    
    # Validate inputs
    players_file = Path(args.players_site)
    if not players_file.exists():
        print(f"Error: Players file not found: {players_file}")
        sys.exit(1)
        
    # Load site players data
    print("Loading site players data...")
    try:
        players_df, load_metadata = load_site_players(str(players_file))
        print(f"Loaded {len(players_df)} players")
        
        # Display column mapping
        mapping_table = load_metadata['column_mapping_table']
        print("\nColumn Mapping:")
        for _, row in mapping_table.iterrows():
            status_symbol = "✓" if row['Status'] == 'Found' else "✗" if row['Required'] else "-"
            print(f"  {status_symbol} {row['Standard Column']:>8} -> {row['Mapped To']:<15} ({row['Status']})")
        
        # Display warnings
        if load_metadata['warnings']:
            print("\nWarnings:")
            for warning in load_metadata['warnings']:
                print(f"  ⚠ {warning}")
        
        print()
        
    except Exception as e:
        print(f"Error loading players data: {e}")
        sys.exit(1)
        
    # Check for FPTS column (required for simulation)
    if 'FPTS' not in players_df.columns or players_df['FPTS'].isnull().all():
        print("Error: No valid FPTS (projections) found in players data")
        print("FPTS column is required for Monte Carlo simulation")
        sys.exit(1)
        
    # Load boom thresholds if provided
    boom_thresholds = load_boom_thresholds(args.boom_thresholds)
    
    # Initialize simulator
    print(f"Initializing Monte Carlo simulator (seed: {args.seed})...")
    simulator = MonteCarloSimulator(seed=args.seed)
    
    # Override boom thresholds if provided
    if boom_thresholds:
        simulator.metadata['boom_thresholds'] = boom_thresholds
        simulator.metadata['calibrated_from_current_run'] = False
    
    # Run simulation
    print(f"Running {args.sims:,} Monte Carlo trials...")
    try:
        sim_df = simulator.simulate_players(players_df, args.sims)
        print(f"Simulation complete for {len(sim_df)} players")
    except Exception as e:
        print(f"Error during simulation: {e}")
        sys.exit(1)
        
    # Generate comparison table
    print("Generating comparison metrics...")
    compare_df = simulator.generate_compare_table(sim_df, players_df)
    
    # Prepare run metadata
    run_metadata = {
        'season': args.season,
        'week': args.week,
        'players_file': str(players_file),
        'n_sims': args.sims,
        'total_players': len(players_df),
        'simulated_players': len(sim_df),
        **load_metadata
    }
    
    # Save all outputs
    print(f"Saving outputs to {args.out}...")
    try:
        files_created = simulator.save_all_outputs(
            sim_df, compare_df, players_df, args.out, run_metadata
        )
        
        print("Output files created:")
        for file_type, file_path in files_created.items():
            print(f"  {file_type:>12}: {file_path}")
            
    except Exception as e:
        print(f"Error saving outputs: {e}")
        sys.exit(1)
        
    # Display summary statistics
    print("\nSimulation Summary:")
    print(f"  Players simulated: {len(sim_df)}")
    print(f"  Rookie fallbacks: {sim_df['rookie_fallback'].sum()}")
    
    if 'FPTS' in compare_df.columns:
        mean_delta = compare_df['delta_mean'].mean()
        print(f"  Mean delta (sim - site): {mean_delta:.2f} pts")
        
    if boom_thresholds:
        print(f"  Boom thresholds: Loaded from file")
    else:
        print(f"  Boom thresholds: Calibrated from current run")
        if simulator.metadata.get('boom_thresholds'):
            for pos, threshold in simulator.metadata['boom_thresholds'].items():
                print(f"    {pos}: {threshold:.1f} pts")
    
    print(f"\nSimulation complete! All outputs saved to: {args.out}")


if __name__ == "__main__":
    main()