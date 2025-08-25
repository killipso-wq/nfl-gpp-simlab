"""
Shared I/O utilities for CSV normalization
Used by both Simulator and Optimizer tabs
"""

import pandas as pd
import numpy as np
import re
from typing import Dict, List, Optional, Tuple


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names to standard format"""
    column_mapping = {
        # Name variations
        'PLAYER': 'name',
        'Player': 'name',
        'player': 'name',
        'NAME': 'name',
        'Name': 'name',
        
        # Position variations
        'POS': 'pos',
        'Pos': 'pos',
        'Position': 'pos',
        'position': 'pos',
        
        # Team variations
        'TEAM': 'team',
        'Team': 'team',
        'Tm': 'team',
        'TM': 'team',
        
        # Opponent variations
        'OPP': 'opp',
        'Opp': 'opp',
        'Opponent': 'opp',
        'opponent': 'opp',
        'VS': 'opp',
        'vs': 'opp',
        
        # Salary variations
        'SAL': 'salary',
        'Sal': 'salary',
        'Salary': 'salary',
        'salary': 'salary',
        'DK Sal': 'salary',
        'FD Sal': 'salary',
        
        # Projected points variations
        'FPTS': 'fpts',
        'Fpts': 'fpts',
        'fpts': 'fpts',
        'Proj': 'fpts',
        'PROJ': 'fpts',
        'Projection': 'fpts',
        'projection': 'fpts',
        'Fantasy Points': 'fpts',
        
        # Ownership variations
        'OWN': 'own%',
        'Own': 'own%',
        'own': 'own%',
        'Ownership': 'own%',
        'ownership': 'own%',
        'RST%': 'own%',
        'rst%': 'own%',
        'Own%': 'own%',
        'OWN%': 'own%',
        
        # Value variations
        'VAL': 'value',
        'Value': 'value',
        'value': 'value',
        
        # Game info
        'Game': 'game_id',
        'game_id': 'game_id',
        'GAME_ID': 'game_id'
    }
    
    # Create a copy and rename columns
    df_normalized = df.copy()
    df_normalized = df_normalized.rename(columns=column_mapping)
    
    return df_normalized


def normalize_position_names(df: pd.DataFrame, pos_col: str = 'pos') -> pd.DataFrame:
    """Normalize position names (e.g., D -> DST)"""
    if pos_col not in df.columns:
        return df
    
    df_normalized = df.copy()
    
    # Map common position variations
    position_mapping = {
        'D': 'DST',
        'DEF': 'DST',
        'Defense': 'DST',
        'K': 'K',  # Keep kicker as is for now
        'PK': 'K',
        'RB/WR': 'RB',  # Handle flex positions
        'WR/RB': 'WR'
    }
    
    df_normalized[pos_col] = df_normalized[pos_col].replace(position_mapping)
    df_normalized[pos_col] = df_normalized[pos_col].str.upper()
    
    return df_normalized


def normalize_ownership_values(df: pd.DataFrame, own_col: str = 'own%') -> pd.DataFrame:
    """Normalize ownership values (handle both percentage and fraction formats)"""
    if own_col not in df.columns:
        return df
    
    df_normalized = df.copy()
    
    # Convert to numeric if it's not already
    df_normalized[own_col] = pd.to_numeric(df_normalized[own_col], errors='coerce')
    
    # If values are ≤1, assume they are fractions and convert to percentages
    mask = df_normalized[own_col] <= 1
    df_normalized.loc[mask, own_col] = df_normalized.loc[mask, own_col] * 100
    
    # Ensure values are within reasonable bounds (0-100%)
    df_normalized[own_col] = df_normalized[own_col].clip(0, 100)
    
    return df_normalized


def validate_required_columns(df: pd.DataFrame, required_columns: List[str]) -> Tuple[bool, List[str]]:
    """Validate that required columns exist"""
    missing_columns = [col for col in required_columns if col not in df.columns]
    is_valid = len(missing_columns) == 0
    return is_valid, missing_columns


def detect_site_format(df: pd.DataFrame) -> str:
    """Detect if the CSV is from DraftKings, FanDuel, or generic format"""
    columns = [col.lower() for col in df.columns]
    
    # DraftKings indicators
    dk_indicators = ['dk sal', 'dk salary', 'draftkings']
    if any(indicator in ' '.join(columns) for indicator in dk_indicators):
        return 'DraftKings'
    
    # FanDuel indicators
    fd_indicators = ['fd sal', 'fd salary', 'fanduel']
    if any(indicator in ' '.join(columns) for indicator in fd_indicators):
        return 'FanDuel'
    
    return 'Generic'


def coerce_numeric_columns(df: pd.DataFrame, numeric_columns: List[str]) -> pd.DataFrame:
    """Coerce specified columns to numeric, handling errors gracefully"""
    df_coerced = df.copy()
    
    for col in numeric_columns:
        if col in df_coerced.columns:
            # Remove any currency symbols or commas first
            if df_coerced[col].dtype == 'object':
                df_coerced[col] = df_coerced[col].astype(str).str.replace(r'[$,]', '', regex=True)
            
            df_coerced[col] = pd.to_numeric(df_coerced[col], errors='coerce')
    
    return df_coerced


def create_player_id(df: pd.DataFrame, team_col: str = 'team', pos_col: str = 'pos', name_col: str = 'name') -> pd.DataFrame:
    """Create standardized player IDs"""
    df_with_id = df.copy()
    
    if all(col in df_with_id.columns for col in [team_col, pos_col, name_col]):
        # Normalize names for ID creation
        normalized_names = (df_with_id[name_col]
                          .str.upper()
                          .str.replace(r'[^\w\s]', '', regex=True)  # Remove punctuation
                          .str.replace(r'\s+', '_', regex=True)  # Replace spaces with underscores
                          .str.replace(r'_(JR|SR|II|III|IV|V)$', '', regex=True))  # Remove suffixes
        
        df_with_id['player_id'] = (df_with_id[team_col].str.upper() + '_' + 
                                  df_with_id[pos_col].str.upper() + '_' + 
                                  normalized_names)
    
    return df_with_id


def normalize_csv_for_simulator(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    """
    Complete normalization pipeline for simulator/optimizer compatibility
    Returns: (normalized_df, column_mapping_applied, warnings)
    """
    warnings = []
    original_columns = df.columns.tolist()
    
    # Step 1: Normalize column names
    df_norm = normalize_column_names(df)
    
    # Track which columns were mapped
    column_mapping = {}
    for orig, norm in zip(original_columns, df_norm.columns):
        if orig != norm:
            column_mapping[orig] = norm
    
    # Step 2: Validate required columns
    required_cols = ['name', 'pos', 'team', 'salary', 'fpts']
    is_valid, missing = validate_required_columns(df_norm, required_cols)
    
    if not is_valid:
        warnings.append(f"Missing required columns: {', '.join(missing)}")
    
    # Step 3: Normalize positions
    if 'pos' in df_norm.columns:
        df_norm = normalize_position_names(df_norm)
        
        # Check for unknown positions
        valid_positions = {'QB', 'RB', 'WR', 'TE', 'DST', 'K'}
        unknown_positions = set(df_norm['pos'].unique()) - valid_positions
        if unknown_positions:
            warnings.append(f"Unknown positions found: {', '.join(unknown_positions)}")
    
    # Step 4: Coerce numeric columns
    numeric_cols = ['salary', 'fpts', 'own%', 'value']
    df_norm = coerce_numeric_columns(df_norm, numeric_cols)
    
    # Step 5: Normalize ownership if present
    if 'own%' in df_norm.columns:
        df_norm = normalize_ownership_values(df_norm)
    
    # Step 6: Create player IDs
    df_norm = create_player_id(df_norm)
    
    # Step 7: Check for missing values in critical columns
    for col in required_cols:
        if col in df_norm.columns:
            null_count = df_norm[col].isnull().sum()
            if null_count > 0:
                warnings.append(f"Column '{col}' has {null_count} missing values")
    
    return df_norm, column_mapping, warnings


def get_roster_template(site: str) -> Dict[str, int]:
    """Get roster template for the specified site"""
    templates = {
        'DraftKings': {
            'QB': 1,
            'RB': 2,
            'WR': 3,
            'TE': 1,
            'FLEX': 1,  # RB/WR/TE
            'DST': 1,
            'total_players': 9
        },
        'FanDuel': {
            'QB': 1,
            'RB': 2,
            'WR': 3,
            'TE': 1,
            'FLEX': 1,  # RB/WR/TE
            'K': 1,
            'DST': 1,
            'total_players': 9
        }
    }
    
    return templates.get(site, templates['DraftKings'])  # Default to DK


def get_salary_cap(site: str) -> int:
    """Get salary cap for the specified site"""
    caps = {
        'DraftKings': 50000,
        'FanDuel': 60000
    }
    
    return caps.get(site, 50000)  # Default to DK