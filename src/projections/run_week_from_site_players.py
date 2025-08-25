"""
CLI for running NFL GPP simulation from players.csv file.
Alternative to Streamlit UI for headless/batch processing.
"""

import argparse
import pandas as pd
import os
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.projections.simulator import (
    normalize_columns,
    run_simulation, 
    save_simulation_outputs
)


def main():
    parser = argparse.ArgumentParser(
        description="Run NFL GPP Monte Carlo simulation from players.csv file"
    )
    
    parser.add_argument(
        "--season",
        type=int,
        required=True,
        help="Season year (e.g., 2025)"
    )
    
    parser.add_argument(
        "--week", 
        type=int,
        required=True,
        help="Week number (1-22)"
    )
    
    parser.add_argument(
        "--players-site",
        type=str,
        required=True,
        help="Path to players.csv file from DFS site"
    )
    
    parser.add_argument(
        "--sims",
        type=int,
        default=10000,
        help="Number of simulations to run (default: 10000)"
    )
    
    parser.add_argument(
        "--seed",
        type=int,
        default=1337,
        help="Random seed for reproducibility (default: 1337)"
    )
    
    parser.add_argument(
        "--out",
        type=str,
        default="data/sim_week",
        help="Output directory (default: data/sim_week)"
    )
    
    args = parser.parse_args()
    
    # Validate inputs
    if not os.path.exists(args.players_site):
        print(f"Error: Players file not found: {args.players_site}")
        sys.exit(1)
    
    if args.week < 1 or args.week > 22:
        print(f"Error: Week must be between 1 and 22, got {args.week}")
        sys.exit(1)
    
    if args.sims < 1:
        print(f"Error: Simulations must be positive, got {args.sims}")
        sys.exit(1)
    
    print(f"🏈 NFL GPP Simulator CLI")
    print(f"Season: {args.season}, Week: {args.week}")
    print(f"Players file: {args.players_site}")
    print(f"Simulations: {args.sims:,}")
    print(f"Random seed: {args.seed}")
    print(f"Output directory: {args.out}")
    print("-" * 50)
    
    try:
        # Load and normalize data
        print("📁 Loading players data...")
        df_raw = pd.read_csv(args.players_site)
        print(f"   Loaded {len(df_raw)} players")
        
        print("🔍 Normalizing columns...")
        df_normalized, column_mapping, warnings = normalize_columns(df_raw)
        
        # Show column mappings
        if column_mapping:
            print("   Column mappings:")
            for normalized, original in column_mapping.items():
                print(f"     {normalized} ← {original}")
        
        # Show warnings
        if warnings:
            print("   ⚠️  Warnings:")
            for warning in warnings:
                print(f"     {warning}")
        
        # Validate required columns
        required_cols = ['player_name', 'position', 'team', 'opponent']
        missing_required = [col for col in required_cols if col not in df_normalized.columns]
        
        if missing_required:
            print(f"❌ Error: Missing required columns: {', '.join(missing_required)}")
            sys.exit(1)
        
        if 'fpts' not in df_normalized.columns:
            print("❌ Error: FPTS column is required for simulation")
            sys.exit(1)
        
        print(f"✅ Data validated: {len(df_normalized)} players")
        
        # Run simulation
        print(f"🚀 Running {args.sims:,} simulations...")
        results = run_simulation(df_normalized, sims=args.sims, seed=args.seed)
        
        # Save outputs
        print(f"💾 Saving outputs to {args.out}...")
        os.makedirs(args.out, exist_ok=True)
        zip_path = save_simulation_outputs(
            results, args.out, args.season, args.week, args.sims, args.seed, column_mapping
        )
        
        print("✅ Simulation complete!")
        print(f"📦 Outputs saved to: {os.path.dirname(zip_path)}")
        print(f"📁 ZIP bundle: {zip_path}")
        
        # Show summary stats
        print("\n📊 Results Summary:")
        for name, df in results.items():
            if isinstance(df, pd.DataFrame):
                print(f"   {name}: {len(df)} rows")
        
        # Show sample results
        if 'compare' in results and not results['compare'].empty:
            compare_df = results['compare']
            if 'delta_mean' in compare_df.columns:
                avg_delta = compare_df['delta_mean'].mean()
                print(f"   Average projection delta: {avg_delta:.2f}")
        
        print("\n🎯 Run complete!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()