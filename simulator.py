"""
Monte Carlo simulation engine glue for Streamlit integration.

This module provides the interface between the Streamlit UI and the core simulation engine.
"""

import pandas as pd
from typing import Dict, List, Optional, Tuple
import os
import time

from src.sim.pipeline import SimulationPipeline, create_default_pipeline_config, PipelineConfig


def run_monte_carlo_simulation(players_df: pd.DataFrame,
                              n_simulations: int = 10000,
                              seed: int = 42,
                              volatility_multiplier: float = 1.0,
                              include_correlations: bool = True,
                              correlation_strength: float = 1.0) -> Tuple[str, Dict]:
    """
    Run Monte Carlo simulation on player data.
    
    Args:
        players_df: DataFrame with player data
        n_simulations: Number of simulations to run
        seed: Random seed for reproducibility
        volatility_multiplier: Scale factor for volatility
        include_correlations: Whether to include player correlations
        correlation_strength: Scale factor for correlations
        
    Returns:
        Tuple of (output_directory, metadata_dict)
    """
    # Create configuration
    config = create_default_pipeline_config()
    config.n_simulations = n_simulations
    config.seed = seed
    config.volatility_multiplier = volatility_multiplier
    config.include_correlations = include_correlations
    config.correlation_strength = correlation_strength
    
    # Initialize and run pipeline
    pipeline = SimulationPipeline(config)
    output_dir, metadata = pipeline.run_full_pipeline(
        players_df, season=2024, week=1
    )
    
    return output_dir, metadata


def load_simulation_results(output_dir: str) -> Dict[str, pd.DataFrame]:
    """
    Load simulation results from output directory.
    
    Args:
        output_dir: Directory containing simulation outputs
        
    Returns:
        Dictionary of DataFrames with simulation results
    """
    results = {}
    
    # Load main result files
    file_mapping = {
        'sim_players': 'sim_players.csv',
        'compare': 'compare.csv',
        'diagnostics': 'diagnostics_summary.csv',
        'flags': 'flags.csv',
        'lineup_pool': 'lineup_pool.csv'
    }
    
    for key, filename in file_mapping.items():
        filepath = os.path.join(output_dir, filename)
        if os.path.exists(filepath):
            try:
                results[key] = pd.read_csv(filepath)
            except Exception as e:
                print(f"Warning: Could not load {filename}: {e}")
    
    return results


def get_cached_simulation_key(players_df: pd.DataFrame, 
                             n_simulations: int,
                             seed: int,
                             volatility_multiplier: float) -> str:
    """
    Generate a cache key for simulation results.
    
    Args:
        players_df: Player DataFrame
        n_simulations: Number of simulations
        seed: Random seed
        volatility_multiplier: Volatility multiplier
        
    Returns:
        Cache key string
    """
    # Simple cache key based on data hash and parameters
    data_hash = str(hash(str(players_df.values.tobytes())))
    params = f"{n_simulations}_{seed}_{volatility_multiplier}"
    return f"{data_hash}_{params}"


def validate_player_data(players_df: pd.DataFrame) -> List[str]:
    """
    Validate player data and return list of issues.
    
    Args:
        players_df: Player DataFrame
        
    Returns:
        List of validation error messages
    """
    errors = []
    
    # Check required columns
    required_columns = ['PLAYER', 'POS', 'TEAM', 'OPP']
    for col in required_columns:
        if col not in players_df.columns:
            errors.append(f"Missing required column: {col}")
    
    if errors:
        return errors
    
    # Check data quality
    if players_df.empty:
        errors.append("No players found in data")
    
    # Check for invalid positions
    valid_positions = ['QB', 'RB', 'WR', 'TE', 'DST', 'D']
    invalid_positions = set(players_df['POS'].unique()) - set(valid_positions)
    if invalid_positions:
        errors.append(f"Invalid positions found: {', '.join(invalid_positions)}")
    
    # Check for missing critical data
    if players_df['PLAYER'].isna().sum() > 0:
        errors.append("Some players have missing names")
    
    if players_df['TEAM'].isna().sum() > 0:
        errors.append("Some players have missing team data")
    
    return errors


def format_simulation_summary(metadata: Dict) -> str:
    """
    Format simulation metadata into a readable summary.
    
    Args:
        metadata: Simulation metadata dictionary
        
    Returns:
        Formatted summary string
    """
    summary = f"""
    **Simulation Summary**
    
    - Run ID: {metadata.get('run_id', 'Unknown')}
    - Timestamp: {metadata.get('timestamp', 'Unknown')}
    - Season/Week: {metadata.get('season', 'N/A')} Week {metadata.get('week', 'N/A')}
    - Simulations: {metadata.get('n_simulations', 0):,}
    - Seed: {metadata.get('seed', 'N/A')}
    - Players: {metadata.get('n_players', 0)}
    - Games: {metadata.get('n_games', 0)}
    - Methodology: {metadata.get('methodology', 'monte_carlo_pdf')}
    """
    
    return summary


def create_example_player_data() -> pd.DataFrame:
    """
    Create example player data for testing/demonstration.
    
    Returns:
        DataFrame with example player data
    """
    example_data = {
        'PLAYER': [
            'Josh Allen', 'Lamar Jackson', 'Patrick Mahomes',
            'Christian McCaffrey', 'Austin Ekeler', 'Nick Chubb',
            'Cooper Kupp', 'Stefon Diggs', 'Tyreek Hill',
            'Travis Kelce', 'Mark Andrews', 'George Kittle',
            'Buffalo Bills', 'San Francisco 49ers'
        ],
        'POS': [
            'QB', 'QB', 'QB',
            'RB', 'RB', 'RB', 
            'WR', 'WR', 'WR',
            'TE', 'TE', 'TE',
            'DST', 'DST'
        ],
        'TEAM': [
            'BUF', 'BAL', 'KC',
            'SF', 'LAC', 'CLE',
            'LAR', 'BUF', 'MIA',
            'KC', 'BAL', 'SF',
            'BUF', 'SF'
        ],
        'OPP': [
            'MIA', 'CLE', 'LV',
            'SEA', 'KC', 'BAL',
            'SEA', 'MIA', 'BUF',
            'LV', 'CLE', 'SEA',
            'MIA', 'SEA'
        ],
        'SAL': [
            8200, 8100, 8000,
            9000, 6800, 7200,
            8500, 8000, 8400,
            7000, 6200, 6000,
            2800, 3000
        ],
        'FPTS': [
            22.5, 21.8, 21.2,
            18.5, 14.2, 15.8,
            17.9, 16.5, 18.1,
            12.8, 10.9, 11.5,
            8.2, 7.8
        ],
        'RST%': [
            15.2, 12.8, 18.5,
            25.1, 8.9, 11.2,
            22.1, 19.8, 24.3,
            18.7, 9.4, 12.1,
            5.2, 4.8
        ]
    }
    
    return pd.DataFrame(example_data)


class SimulationCache:
    """Simple caching mechanism for simulation results."""
    
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str) -> Optional[Tuple[str, Dict]]:
        """Get cached simulation results."""
        return self._cache.get(key)
    
    def set(self, key: str, output_dir: str, metadata: Dict):
        """Cache simulation results."""
        self._cache[key] = (output_dir, metadata)
    
    def clear(self):
        """Clear all cached results."""
        self._cache.clear()
    
    def size(self) -> int:
        """Get number of cached items."""
        return len(self._cache)


# Global cache instance
_simulation_cache = SimulationCache()


def get_simulation_cache() -> SimulationCache:
    """Get the global simulation cache instance."""
    return _simulation_cache