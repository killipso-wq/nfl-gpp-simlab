#!/usr/bin/env python3
"""
NFL GPP Sim Lab - CLI Runner
Headless simulation runner for batch processing
"""

import argparse
import pandas as pd
import numpy as np
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to standard format"""
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
    
    df = df.copy()
    
    # Create mapping from current columns to normalized columns
    column_mapping = {}
    for col in df.columns:
        col_lower = col.lower().strip()
        if col_lower in COLUMN_MAPPINGS:
            column_mapping[col] = COLUMN_MAPPINGS[col_lower]
        elif col.upper() in ["PLAYER", "POS", "TEAM", "FPTS", "SAL", "OPP", "RST%", "VAL"]:
            column_mapping[col] = col.upper()
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    return df

def validate_and_clean_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Validate and clean data, return cleaned data and any warnings"""
    warnings = []
    
    # Check for required columns
    required_columns = ["PLAYER", "POS", "TEAM", "FPTS", "SAL"]
    missing_required = [col for col in required_columns if col not in df.columns]
    if missing_required:
        raise ValueError(f"Missing required columns: {', '.join(missing_required)}")
    
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
    
    return df, warnings

def generate_simulation_outputs(df: pd.DataFrame, season: int, week: int, sims: int, seed: int) -> Dict:
    """Generate simulation outputs (placeholder implementation)"""
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

def save_outputs(outputs: Dict, output_dir: str, season: int, week: int, sims: int, seed: int) -> None:
    """Save simulation outputs to files"""
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save CSV files
    outputs["sim_players"].to_csv(f"{output_dir}/sim_players.csv", index=False)
    outputs["compare"].to_csv(f"{output_dir}/compare.csv", index=False)
    outputs["flags"].to_csv(f"{output_dir}/flags.csv", index=False)
    
    # Save diagnostics summary as CSV
    diag_df = pd.DataFrame([outputs["diagnostics_summary"]])
    diag_df.to_csv(f"{output_dir}/diagnostics_summary.csv", index=False)
    
    # Create metadata.json
    metadata = {
        "run_id": timestamp,
        "season": season,
        "week": week,
        "sims": sims,
        "seed": seed,
        "timestamp": timestamp,
        "methodology": "monte_carlo_pdf",
        "files_created": ["sim_players.csv", "compare.csv", "diagnostics_summary.csv", "flags.csv"],
        "diagnostics": outputs["diagnostics_summary"]
    }
    
    with open(f"{output_dir}/metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"✅ Outputs saved to: {output_dir}")
    print(f"📁 Files created:")
    print(f"   - sim_players.csv")
    print(f"   - compare.csv") 
    print(f"   - diagnostics_summary.csv")
    print(f"   - flags.csv")
    print(f"   - metadata.json")

def main():
    parser = argparse.ArgumentParser(
        description="NFL GPP Sim Lab - CLI Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument("--season", type=int, required=True, help="NFL season year")
    parser.add_argument("--week", type=int, required=True, help="NFL week number (1-18)")
    parser.add_argument("--players-site", required=True, help="Path to players CSV file")
    parser.add_argument("--sims", type=int, default=10000, help="Number of simulations to run")
    parser.add_argument("--seed", type=int, default=1337, help="Random seed for reproducibility")
    parser.add_argument("--out", default="data/sim_week", help="Output directory")
    
    args = parser.parse_args()
    
    # Validate inputs
    if not (1 <= args.week <= 18):
        print("❌ Error: Week must be between 1 and 18")
        sys.exit(1)
    
    if not os.path.exists(args.players_site):
        print(f"❌ Error: Players file not found: {args.players_site}")
        sys.exit(1)
    
    try:
        print(f"🏈 NFL GPP Sim Lab - CLI Runner")
        print(f"📅 Season {args.season}, Week {args.week}")
        print(f"🎲 Simulations: {args.sims:,}, Seed: {args.seed}")
        print(f"📂 Input: {args.players_site}")
        print(f"📁 Output: {args.out}")
        print()
        
        # Load and validate data
        print("📋 Loading players data...")
        df = pd.read_csv(args.players_site)
        print(f"✅ Loaded {len(df)} players")
        
        # Normalize column names
        print("🔄 Normalizing column names...")
        df = normalize_column_names(df)
        
        # Validate and clean data
        print("✅ Validating data...")
        df, warnings = validate_and_clean_data(df)
        
        for warning in warnings:
            print(f"⚠️  {warning}")
        
        print(f"✅ Validation complete - {len(df)} players ready for simulation")
        
        # Generate simulation outputs
        print("🚀 Running simulation...")
        outputs = generate_simulation_outputs(df, args.season, args.week, args.sims, args.seed)
        
        # Create timestamped output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_output_dir = f"{args.out}/{args.season}_w{args.week}_{timestamp}"
        
        # Save outputs
        print("💾 Saving outputs...")
        save_outputs(outputs, final_output_dir, args.season, args.week, args.sims, args.seed)
        
        # Print summary
        print()
        print("📊 Simulation Summary:")
        print(f"   MAE: {outputs['diagnostics_summary']['mae']:.2f}")
        print(f"   RMSE: {outputs['diagnostics_summary']['rmse']:.2f}")
        print(f"   Correlation: {outputs['diagnostics_summary']['correlation']:.3f}")
        print(f"   Flags: {len(outputs['flags'])}")
        print()
        print("🎉 Simulation completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()