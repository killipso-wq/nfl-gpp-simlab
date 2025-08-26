"""
Site players CSV loader with strict column mapping per Master Reference.
Handles autodetection of common synonyms and data normalization.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import warnings
from pathlib import Path

from .name_normalizer import build_player_id, normalize_position, normalize_ownership


class SitePlayersLoader:
    """Loads and processes site players CSV with column mapping and validation."""
    
    # Required columns
    REQUIRED_COLUMNS = ['PLAYER', 'POS', 'TEAM', 'OPP']
    
    # Optional columns that are used when present
    OPTIONAL_COLUMNS = ['FPTS', 'SAL', 'RST%', 'O/U', 'SPRD', 'ML', 'TM/P', 'VAL']
    
    # Column synonyms for autodetection
    COLUMN_SYNONYMS = {
        'PLAYER': ['player', 'name', 'player_name', 'full_name'],
        'POS': ['pos', 'position'],
        'TEAM': ['team', 'tm'],
        'OPP': ['opp', 'opponent', 'vs'],
        'FPTS': ['fpts', 'proj', 'projection', 'projected_points', 'points'],
        'SAL': ['sal', 'salary', 'dk_salary', 'cost'],
        'RST%': ['rst%', 'rst', 'own', 'own%', 'ownership', 'projected_ownership'],
        'O/U': ['o/u', 'ou', 'total', 'game_total'],
        'SPRD': ['sprd', 'spread', 'line'],
        'ML': ['ml', 'moneyline'],
        'TM/P': ['tm/p', 'tmp', 'team_points', 'implied_points'],
        'VAL': ['val', 'value', 'pts/$', 'value_per_1k', 'points_per_dollar']
    }
    
    def __init__(self):
        self.column_mapping: Dict[str, str] = {}
        self.warnings: List[str] = []
        self.data: Optional[pd.DataFrame] = None
        
    def load_players_csv(self, file_path: str) -> pd.DataFrame:
        """
        Load and process players CSV file.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Processed DataFrame with normalized columns and player_id
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If required columns are missing
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Players CSV not found: {file_path}")
            
        # Load CSV
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            raise ValueError(f"Failed to load CSV: {e}")
            
        if df.empty:
            raise ValueError("CSV file is empty")
            
        # Detect column mapping
        self._detect_column_mapping(df.columns.tolist())
        
        # Validate required columns
        self._validate_required_columns()
        
        # Rename columns to standard names
        df_renamed = self._rename_columns(df)
        
        # Process and normalize data
        df_processed = self._process_data(df_renamed)
        
        self.data = df_processed
        return df_processed
        
    def _detect_column_mapping(self, csv_columns: List[str]) -> None:
        """Detect column mapping using synonyms."""
        self.column_mapping = {}
        
        # Create lowercase mapping of CSV columns
        csv_lower = {col.lower(): col for col in csv_columns}
        
        # Try to map each standard column
        for std_col in self.REQUIRED_COLUMNS + self.OPTIONAL_COLUMNS:
            mapped_col = None
            
            # First try exact match (case insensitive)
            if std_col.lower() in csv_lower:
                mapped_col = csv_lower[std_col.lower()]
            else:
                # Try synonyms
                synonyms = self.COLUMN_SYNONYMS.get(std_col, [])
                for synonym in synonyms:
                    if synonym in csv_lower:
                        mapped_col = csv_lower[synonym]
                        break
                        
            if mapped_col:
                self.column_mapping[std_col] = mapped_col
                
    def _validate_required_columns(self) -> None:
        """Validate that all required columns are mapped."""
        missing = []
        for req_col in self.REQUIRED_COLUMNS:
            if req_col not in self.column_mapping:
                missing.append(req_col)
                
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
            
    def _rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Rename columns to standard names."""
        rename_map = {v: k for k, v in self.column_mapping.items()}
        return df.rename(columns=rename_map)
        
    def _process_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process and normalize the data."""
        df = df.copy()
        
        # Normalize position (D → DST)
        df['POS'] = df['POS'].apply(normalize_position)
        
        # Normalize ownership if present
        if 'RST%' in df.columns:
            df['RST%'] = df['RST%'].apply(normalize_ownership)
            
        # Generate player_id
        try:
            df['player_id'] = df.apply(
                lambda row: build_player_id(row['TEAM'], row['POS'], row['PLAYER']),
                axis=1
            )
        except Exception as e:
            raise ValueError(f"Failed to generate player_id: {e}")
            
        # Validate numeric columns
        self._validate_numeric_columns(df)
        
        # Check for unknown positions
        self._check_unknown_positions(df)
        
        return df
        
    def _validate_numeric_columns(self, df: pd.DataFrame) -> None:
        """Validate and warn about numeric column issues."""
        numeric_cols = ['FPTS', 'SAL', 'RST%', 'O/U', 'SPRD', 'ML', 'TM/P', 'VAL']
        
        for col in numeric_cols:
            if col in df.columns:
                # Convert to numeric, coercing errors to NaN
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Check for missing/invalid values
                null_count = df[col].isnull().sum()
                if null_count > 0:
                    self.warnings.append(
                        f"Column {col}: {null_count} missing/invalid numeric values"
                    )
                    
    def _check_unknown_positions(self, df: pd.DataFrame) -> None:
        """Check for unknown position values."""
        known_positions = {'QB', 'RB', 'WR', 'TE', 'DST', 'K'}
        unknown_pos = set(df['POS'].unique()) - known_positions
        
        if unknown_pos:
            self.warnings.append(f"Unknown positions found: {list(unknown_pos)}")
            
    def get_column_mapping_table(self) -> pd.DataFrame:
        """
        Get column mapping table for display.
        
        Returns:
            DataFrame showing standard column, mapped column, and status
        """
        rows = []
        all_columns = self.REQUIRED_COLUMNS + self.OPTIONAL_COLUMNS
        
        for std_col in all_columns:
            mapped_col = self.column_mapping.get(std_col, '')
            required = std_col in self.REQUIRED_COLUMNS
            found = std_col in self.column_mapping
            
            status = 'Found' if found else ('Missing' if required else 'Not found')
            
            rows.append({
                'Standard Column': std_col,
                'Mapped To': mapped_col,
                'Required': required,
                'Status': status
            })
            
        return pd.DataFrame(rows)
        
    def get_warnings(self) -> List[str]:
        """Get list of warnings from data processing."""
        return self.warnings.copy()
        
    def get_data_summary(self) -> Dict[str, Any]:
        """Get summary statistics of loaded data."""
        if self.data is None:
            return {}
            
        df = self.data
        summary = {
            'total_players': len(df),
            'positions': df['POS'].value_counts().to_dict(),
            'teams': df['TEAM'].nunique(),
            'has_fpts': 'FPTS' in df.columns and not df['FPTS'].isnull().all(),
            'has_salary': 'SAL' in df.columns and not df['SAL'].isnull().all(),
            'has_ownership': 'RST%' in df.columns and not df['RST%'].isnull().all(),
        }
        
        return summary


def load_site_players(file_path: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Convenience function to load site players CSV.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Tuple of (processed DataFrame, metadata dict)
    """
    loader = SitePlayersLoader()
    df = loader.load_players_csv(file_path)
    
    metadata = {
        'column_mapping': loader.column_mapping,
        'warnings': loader.get_warnings(),
        'column_mapping_table': loader.get_column_mapping_table(),
        'data_summary': loader.get_data_summary()
    }
    
    return df, metadata