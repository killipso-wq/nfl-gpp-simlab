"""
Core simulation engine for NFL GPP Monte Carlo simulator.
Placeholder implementation that will be replaced with real Monte Carlo logic.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import json
import os
from datetime import datetime
import zipfile


def normalize_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    """
    Normalize column names and detect column mappings.
    
    Returns:
        - Normalized dataframe
        - Column mapping dictionary  
        - List of warnings
    """
    warnings = []
    column_mapping = {}
    
    # Define column mappings
    name_variants = ['name', 'player', 'player_name', 'PLAYER']
    team_variants = ['team', 'tm', 'TEAM']
    opp_variants = ['opp', 'opponent', 'OPP']
    pos_variants = ['pos', 'position', 'POS']
    salary_variants = ['salary', 'sal', 'SAL']
    fpts_variants = ['fpts', 'proj', 'projection', 'points', 'FPTS']
    own_variants = ['own%', 'own', 'ownership', 'RST%']
    
    df = df.copy()
    
    # Normalize column names
    for col in df.columns:
        if col.lower() in [v.lower() for v in name_variants]:
            df = df.rename(columns={col: 'player_name'})
            column_mapping['player_name'] = col
        elif col.lower() in [v.lower() for v in team_variants]:
            df = df.rename(columns={col: 'team'})
            column_mapping['team'] = col
        elif col.lower() in [v.lower() for v in opp_variants]:
            df = df.rename(columns={col: 'opponent'})
            column_mapping['opponent'] = col
        elif col.lower() in [v.lower() for v in pos_variants]:
            df = df.rename(columns={col: 'position'})
            column_mapping['position'] = col
        elif col.lower() in [v.lower() for v in salary_variants]:
            df = df.rename(columns={col: 'salary'})
            column_mapping['salary'] = col
        elif col.lower() in [v.lower() for v in fpts_variants]:
            df = df.rename(columns={col: 'fpts'})
            column_mapping['fpts'] = col
        elif col.lower() in [v.lower() for v in own_variants]:
            df = df.rename(columns={col: 'ownership'})
            column_mapping['ownership'] = col
    
    # Check for required columns
    required_cols = ['player_name', 'position', 'team', 'opponent']
    for col in required_cols:
        if col not in df.columns:
            warnings.append(f"Missing required column: {col}")
    
    # Convert D to DST for position
    if 'position' in df.columns:
        df['position'] = df['position'].replace('D', 'DST')
    
    # Normalize ownership (handle both fraction and percent)
    if 'ownership' in df.columns:
        df['ownership'] = pd.to_numeric(df['ownership'], errors='coerce')
        # If values are <= 1, assume fraction and convert to percent
        mask = df['ownership'] <= 1
        df.loc[mask, 'ownership'] = df.loc[mask, 'ownership'] * 100
    
    # Coerce numeric fields
    numeric_fields = ['salary', 'fpts', 'ownership']
    for field in numeric_fields:
        if field in df.columns:
            original_count = len(df[df[field].notna()])
            df[field] = pd.to_numeric(df[field], errors='coerce')
            new_count = len(df[df[field].notna()])
            if new_count < original_count:
                warnings.append(f"Some {field} values could not be converted to numeric")
    
    # Create player_id
    if 'player_name' in df.columns and 'team' in df.columns and 'position' in df.columns:
        df['player_id'] = df.apply(lambda row: create_player_id(
            row.get('team', ''), 
            row.get('position', ''), 
            row.get('player_name', '')
        ), axis=1)
    
    return df, column_mapping, warnings


def create_player_id(team: str, position: str, name: str) -> str:
    """Create normalized player ID: TEAM_POS_NORMALIZEDNAME"""
    if pd.isna(name) or pd.isna(team) or pd.isna(position):
        return f"UNK_UNK_UNK"
    
    # Normalize name: uppercase, remove punctuation, drop suffixes
    normalized_name = str(name).upper()
    # Remove common suffixes
    suffixes = ['JR', 'SR', 'II', 'III', 'IV', 'V']
    for suffix in suffixes:
        normalized_name = normalized_name.replace(f' {suffix}', '')
    # Remove punctuation and collapse spaces
    normalized_name = ''.join(c for c in normalized_name if c.isalnum() or c.isspace())
    normalized_name = '_'.join(normalized_name.split())
    
    return f"{str(team).upper()}_{str(position).upper()}_{normalized_name}"


def run_simulation(df: pd.DataFrame, sims: int = 10000, seed: int = 1337) -> Dict[str, pd.DataFrame]:
    """
    Run Monte Carlo simulation (placeholder implementation).
    
    Args:
        df: Normalized player data
        sims: Number of simulations
        seed: Random seed for reproducibility
        
    Returns:
        Dictionary containing simulation results
    """
    np.random.seed(seed)
    
    if 'fpts' not in df.columns:
        raise ValueError("FPTS column is required for simulation")
    
    # Placeholder simulation logic
    results = df.copy()
    
    # Generate placeholder Monte Carlo results
    results['sim_mean'] = results['fpts']
    results['floor_p10'] = results['fpts'] * 0.8  # Placeholder: 80% of projection
    results['p75'] = results['fpts'] * 1.1
    results['ceiling_p90'] = results['fpts'] * 1.2  # Placeholder: 120% of projection
    results['p95'] = results['fpts'] * 1.3
    results['boom_prob'] = np.random.uniform(0.1, 0.4, len(results))  # Placeholder boom probability
    results['rookie_fallback'] = False  # Placeholder
    
    # Create compare data if we have site projections
    compare = results.copy()
    if 'fpts' in results.columns:
        compare['site_fpts'] = results['fpts']
        compare['delta_mean'] = results['sim_mean'] - results['fpts']
        compare['pct_delta'] = (compare['delta_mean'] / results['fpts']) * 100
        compare['beat_site_prob'] = np.random.uniform(0.3, 0.7, len(results))
        
        # Calculate value metrics if salary exists
        if 'salary' in results.columns:
            compare['value_per_1k'] = (results['sim_mean'] / results['salary']) * 1000
            compare['ceil_per_1k'] = (results['ceiling_p90'] / results['salary']) * 1000
        
        # Boom score (placeholder: 1-100 based on ceiling and ownership)
        compare['boom_score'] = np.random.randint(1, 101, len(results))
        compare['dart_flag'] = compare['boom_score'] >= 70
    
    # Create diagnostics summary
    diagnostics_data = []
    if 'position' in results.columns and 'fpts' in results.columns:
        for pos in results['position'].unique():
            if pd.isna(pos):
                continue
            pos_data = results[results['position'] == pos]
            if len(pos_data) > 0:
                mae = np.mean(np.abs(pos_data['sim_mean'] - pos_data['fpts']))
                rmse = np.sqrt(np.mean((pos_data['sim_mean'] - pos_data['fpts']) ** 2))
                corr = np.corrcoef(pos_data['sim_mean'], pos_data['fpts'])[0, 1] if len(pos_data) > 1 else 0
                
                diagnostics_data.append({
                    'position': pos,
                    'count': len(pos_data),
                    'mae': mae,
                    'rmse': rmse,
                    'correlation': corr,
                    'coverage_p10_p90': 0.8  # Placeholder
                })
    
    diagnostics = pd.DataFrame(diagnostics_data)
    
    # Create flags for notable discrepancies
    flags_data = []
    if 'delta_mean' in compare.columns:
        # Top absolute deltas
        top_abs = compare.nlargest(5, 'delta_mean')
        for _, row in top_abs.iterrows():
            flags_data.append({
                'player_id': row.get('player_id', ''),
                'player_name': row.get('player_name', ''),
                'flag_type': 'high_absolute_delta',
                'value': row['delta_mean'],
                'description': f"High absolute delta: {row['delta_mean']:.2f}"
            })
    
    flags = pd.DataFrame(flags_data)
    
    return {
        'sim_players': results,
        'compare': compare,
        'diagnostics_summary': diagnostics,
        'flags': flags
    }


def save_simulation_outputs(results: Dict[str, pd.DataFrame], output_dir: str, 
                          season: int, week: int, sims: int, seed: int,
                          column_mapping: Dict[str, str]) -> str:
    """
    Save simulation outputs to directory structure.
    
    Returns:
        Path to the created ZIP file
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(output_dir, f"{season}_w{week}_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    
    # Save CSV files
    csv_files = []
    for name, df in results.items():
        if isinstance(df, pd.DataFrame):
            csv_path = os.path.join(run_dir, f"{name}.csv")
            df.to_csv(csv_path, index=False)
            csv_files.append(csv_path)
    
    # Create metadata
    metadata = {
        'sims': sims,
        'seed': seed,
        'run_id': timestamp,
        'season': season,
        'week': week,
        'git_commit': 'placeholder',  # Would be actual git commit in real implementation
        'column_mapping': column_mapping,
        'counts': {name: len(df) for name, df in results.items() if isinstance(df, pd.DataFrame)},
        'timestamp': timestamp
    }
    
    metadata_path = os.path.join(run_dir, "metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    # Create ZIP bundle
    zip_path = os.path.join(run_dir, "simulator_outputs.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for csv_file in csv_files:
            zipf.write(csv_file, os.path.basename(csv_file))
        zipf.write(metadata_path, "metadata.json")
    
    return zip_path