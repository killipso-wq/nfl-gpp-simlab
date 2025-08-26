"""
Monte Carlo game simulator for fantasy football projections.

Implements deterministic RNG with numpy Generator and per-player child seeds.
Generates fantasy point distributions from player priors.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, List
import uuid


class GameSimulator:
    """Monte Carlo simulator for fantasy football projections."""
    
    def __init__(self, seed: int = 42):
        """
        Initialize simulator with deterministic RNG.
        
        Args:
            seed: Base seed for reproducibility
        """
        self.base_seed = seed
        self.rng = np.random.default_rng(seed)
        self.seed_sequence = np.random.SeedSequence(seed)
    
    def simulate_player(self, 
                       dk_mean: float, 
                       dk_std: float, 
                       n_trials: int,
                       player_seed: int = None) -> np.ndarray:
        """
        Simulate fantasy points for a single player.
        
        Uses normal distribution clamped at 0 for MVP implementation.
        
        Args:
            dk_mean: Mean projection 
            dk_std: Standard deviation
            n_trials: Number of simulation trials
            player_seed: Specific seed for this player (for reproducibility)
            
        Returns:
            Array of simulated fantasy points
        """
        # Use player-specific RNG for reproducibility
        if player_seed is not None:
            player_rng = np.random.default_rng(player_seed)
        else:
            player_rng = self.rng
        
        # Sample from normal distribution
        samples = player_rng.normal(dk_mean, dk_std, n_trials)
        
        # Clamp negative values at 0
        samples = np.maximum(samples, 0)
        
        return samples
    
    def calculate_player_stats(self, samples: np.ndarray, boom_threshold: float = 20.0, site_fpts: float = None) -> Dict:
        """
        Calculate statistics from simulation samples.
        
        Args:
            samples: Array of simulated points
            boom_threshold: Threshold for boom probability
            site_fpts: Site projection for beat_site_prob calculation
            
        Returns:
            Dictionary with calculated statistics
        """
        stats = {
            'sim_mean': np.mean(samples),
            'floor_p10': np.percentile(samples, 10),
            'p75': np.percentile(samples, 75),
            'ceiling_p90': np.percentile(samples, 90),
            'p95': np.percentile(samples, 95),
            'boom_prob': np.mean(samples >= boom_threshold)
        }
        
        # Beat site probability if site projection available
        if site_fpts is not None and not np.isnan(site_fpts):
            stats['beat_site_prob'] = np.mean(samples >= site_fpts)
        else:
            stats['beat_site_prob'] = np.nan
        
        # Round to 3 decimals for stability
        for key, value in stats.items():
            if not np.isnan(value):
                stats[key] = round(value, 3)
        
        return stats
    
    def simulate_players(self, 
                        players_df: pd.DataFrame,
                        boom_thresholds: Dict[str, float],
                        n_trials: int = 10000) -> pd.DataFrame:
        """
        Simulate projections for multiple players.
        
        Expected columns in players_df: dk_mean, dk_std, POS, site_fpts (optional)
        
        Args:
            players_df: DataFrame with player data and priors
            boom_thresholds: Position-specific boom thresholds
            n_trials: Number of simulation trials per player
            
        Returns:
            DataFrame with simulation results
        """
        # Create child seeds for each player for reproducibility
        child_seeds = self.seed_sequence.spawn(len(players_df))
        
        results = []
        
        for idx, (_, row) in enumerate(players_df.iterrows()):
            # Get player-specific boom threshold
            position = row.get('POS', 'QB')
            boom_threshold = boom_thresholds.get(position, boom_thresholds.get('QB', 20.0))
            
            # Get player priors
            dk_mean = row.get('dk_mean', 0.0)
            dk_std = row.get('dk_std', 1.0)
            site_fpts = row.get('site_fpts')
            
            # Skip if invalid priors
            if pd.isna(dk_mean) or pd.isna(dk_std) or dk_std <= 0:
                # Create default stats for invalid players
                player_stats = {
                    'sim_mean': 0.0,
                    'floor_p10': 0.0,
                    'p75': 0.0,
                    'ceiling_p90': 0.0,
                    'p95': 0.0,
                    'boom_prob': 0.0,
                    'beat_site_prob': np.nan
                }
            else:
                # Generate player-specific seed
                player_seed = int(np.random.default_rng(child_seeds[idx]).integers(0, 2**31))
                
                # Simulate player
                samples = self.simulate_player(dk_mean, dk_std, n_trials, player_seed)
                
                # Calculate stats
                player_stats = self.calculate_player_stats(samples, boom_threshold, site_fpts)
            
            # Add to results
            result_row = row.to_dict()
            result_row.update(player_stats)
            results.append(result_row)
        
        return pd.DataFrame(results)


def simulate_week(players_df: pd.DataFrame,
                 boom_thresholds: Dict[str, float],
                 n_trials: int = 10000,
                 seed: int = 42) -> pd.DataFrame:
    """
    Convenience function to simulate a full week of players.
    
    Args:
        players_df: DataFrame with player data and priors
        boom_thresholds: Position-specific boom thresholds
        n_trials: Number of simulation trials
        seed: Random seed for reproducibility
        
    Returns:
        DataFrame with simulation results
    """
    simulator = GameSimulator(seed=seed)
    return simulator.simulate_players(players_df, boom_thresholds, n_trials)