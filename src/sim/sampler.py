"""
Seeded Monte Carlo sampling routines with reproducible results and volatility control.

This module implements the sampling engine as outlined in the 
Realistic NFL Monte Carlo Simulation PDF methodology.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import time

from .game_model import GameModel, GameEnvironment, TeamGameState
from .player_model import PlayerModel, PlayerProjection, Position
from .correlation import CorrelationModel


@dataclass
class SamplingConfig:
    """Configuration for Monte Carlo sampling."""
    n_simulations: int = 10000
    seed: int = 42
    volatility_multiplier: float = 1.0  # Scale all volatilities
    correlation_strength: float = 1.0   # Scale correlation effects
    include_correlations: bool = True
    parallel: bool = False
    batch_size: int = 1000


@dataclass
class SimulationResult:
    """Results from a single simulation."""
    sim_id: int
    player_scores: Dict[str, float]  # player_id -> fantasy points
    game_states: Dict[str, Dict]     # game_id -> game state info
    random_seed: int


class MonteCarloSampler:
    """
    Monte Carlo sampling engine for NFL fantasy simulations.
    
    Provides seeded, reproducible sampling with correlation structures
    and volatility controls as specified in the PDF methodology.
    """
    
    def __init__(self, config: SamplingConfig):
        """
        Initialize the Monte Carlo sampler.
        
        Args:
            config: Sampling configuration
        """
        self.config = config
        self.random_state = np.random.RandomState(config.seed)
        
        # Initialize sub-models
        self.game_model = GameModel(random_state=self.random_state)
        self.player_model = PlayerModel(random_state=self.random_state)
        self.correlation_model = CorrelationModel(random_state=self.random_state)
        
        # Results cache
        self._last_results = None
        self._last_config_hash = None
    
    def run_simulation(self, players: List[Dict], 
                      games: List[Dict],
                      config_override: Optional[SamplingConfig] = None) -> List[SimulationResult]:
        """
        Run the full Monte Carlo simulation.
        
        Args:
            players: List of player dictionaries
            games: List of game dictionaries  
            config_override: Override default config for this run
            
        Returns:
            List of simulation results
        """
        config = config_override or self.config
        
        # Check cache
        config_hash = self._hash_inputs(players, games, config)
        if config_hash == self._last_config_hash and self._last_results:
            print(f"Using cached results for {config.n_simulations} simulations")
            return self._last_results
        
        print(f"Running {config.n_simulations} Monte Carlo simulations...")
        start_time = time.time()
        
        # Prepare data structures
        player_projections = self._prepare_player_projections(players)
        game_environments = self._prepare_game_environments(games)
        
        # Build correlation matrix if needed
        correlation_matrix = None
        player_ids = None
        if config.include_correlations:
            correlation_matrix, player_ids = self.correlation_model.build_correlation_matrix(
                players, games
            )
            # Scale correlation strength
            if config.correlation_strength != 1.0:
                correlation_matrix = self._scale_correlation_matrix(
                    correlation_matrix, config.correlation_strength
                )
        
        # Run simulations
        results = []
        if config.parallel and config.n_simulations > config.batch_size:
            results = self._run_parallel_simulations(
                player_projections, game_environments, 
                correlation_matrix, player_ids, config
            )
        else:
            results = self._run_sequential_simulations(
                player_projections, game_environments,
                correlation_matrix, player_ids, config
            )
        
        elapsed = time.time() - start_time
        print(f"Completed {len(results)} simulations in {elapsed:.2f} seconds "
              f"({len(results)/elapsed:.1f} sims/sec)")
        
        # Cache results
        self._last_results = results
        self._last_config_hash = config_hash
        
        return results
    
    def _run_sequential_simulations(self, player_projections: List[PlayerProjection],
                                   game_environments: List[GameEnvironment],
                                   correlation_matrix: Optional[np.ndarray],
                                   player_ids: Optional[List[str]],
                                   config: SamplingConfig) -> List[SimulationResult]:
        """Run simulations sequentially."""
        results = []
        
        # Sample correlated shocks if using correlations
        correlated_shocks = None
        if correlation_matrix is not None:
            correlated_shocks = self.correlation_model.sample_correlated_shocks(
                correlation_matrix, config.n_simulations
            )
        
        for sim_id in range(config.n_simulations):
            # Get correlation shocks for this simulation
            player_shocks = {}
            if correlated_shocks is not None:
                for i, player_id in enumerate(player_ids):
                    player_shocks[player_id] = correlated_shocks[sim_id, i]
            
            # Run single simulation
            result = self._run_single_simulation(
                sim_id, player_projections, game_environments,
                player_shocks, config
            )
            results.append(result)
            
            # Progress reporting
            if (sim_id + 1) % 1000 == 0:
                print(f"  Completed {sim_id + 1}/{config.n_simulations} simulations")
        
        return results
    
    def _run_parallel_simulations(self, player_projections: List[PlayerProjection],
                                 game_environments: List[GameEnvironment],
                                 correlation_matrix: Optional[np.ndarray],
                                 player_ids: Optional[List[str]],
                                 config: SamplingConfig) -> List[SimulationResult]:
        """Run simulations in parallel batches."""
        # For now, fall back to sequential (parallel implementation would require multiprocessing)
        print("Parallel simulation not yet implemented, falling back to sequential")
        return self._run_sequential_simulations(
            player_projections, game_environments,
            correlation_matrix, player_ids, config
        )
    
    def _run_single_simulation(self, sim_id: int,
                              player_projections: List[PlayerProjection],
                              game_environments: List[GameEnvironment],
                              player_shocks: Dict[str, float],
                              config: SamplingConfig) -> SimulationResult:
        """Run a single simulation trial."""
        # Set random seed for this simulation
        sim_seed = config.seed + sim_id
        sim_random = np.random.RandomState(sim_seed)
        
        # Update models with new random state
        self.game_model.random_state = sim_random
        self.player_model.random_state = sim_random
        
        # Simulate game states first
        game_states = {}
        team_game_states = {}
        
        for game_env in game_environments:
            game_state = self._simulate_game_state(game_env, sim_random)
            game_states[game_env.game_id] = game_state
            
            # Store team states for player simulation
            for team in [game_env.home_team, game_env.away_team]:
                team_game_states[team] = game_state
        
        # Simulate player performances
        player_scores = {}
        for projection in player_projections:
            # Get team game state
            team_state = team_game_states.get(projection.team, {})
            team_pace = team_state.get('pace', 65.0)
            team_pass_rate = team_state.get('pass_rate', 0.60)
            game_script = team_state.get('game_script', 1.0)
            
            # Apply correlation shock if available
            base_score = self.player_model.simulate_player_performance(
                projection, team_pace, team_pass_rate, game_script
            )
            
            # Apply correlation shock
            shock = player_shocks.get(projection.player_id, 0.0)
            if abs(shock) > 0.01:  # Only apply significant shocks
                # Convert shock to multiplicative factor - make it more pronounced
                shock_multiplier = 1.0 + (shock * 0.5 * config.volatility_multiplier)  # Increased from 0.3 to 0.5
                base_score *= max(0.1, shock_multiplier)  # Floor at 10% of base
            
            # Apply global volatility multiplier
            if config.volatility_multiplier != 1.0:
                base_score *= self._apply_volatility_adjustment(
                    base_score, config.volatility_multiplier, sim_random
                )
            
            player_scores[projection.player_id] = max(0.0, base_score)
        
        return SimulationResult(
            sim_id=sim_id,
            player_scores=player_scores,
            game_states=game_states,
            random_seed=sim_seed
        )
    
    def _simulate_game_state(self, game_env: GameEnvironment,
                           sim_random: np.random.RandomState) -> Dict[str, Any]:
        """Simulate the state of a single game."""
        # Create team states (simplified - would normally come from data)
        home_state = TeamGameState(
            team=game_env.home_team,
            opponent=game_env.away_team,
            is_home=True,
            base_pace=65.0,  # Default values - would be data-driven
            base_pass_rate=0.60
        )
        
        away_state = TeamGameState(
            team=game_env.away_team,
            opponent=game_env.home_team,
            is_home=False,
            base_pace=65.0,
            base_pass_rate=0.60
        )
        
        # Simulate pace and pass rates
        home_pace, away_pace = self.game_model.simulate_game_pace(
            game_env, home_state, away_state
        )
        home_pass_rate, away_pass_rate = self.game_model.simulate_pass_rates(
            game_env, home_state, away_state
        )
        
        # Simulate scoring environment
        scoring_env = self.game_model.simulate_scoring_environment(game_env)
        
        # Game script (simplified)
        if game_env.spread:
            home_script = 1.0 + (game_env.spread * 0.02)  # 2% per point favored
            away_script = 1.0 - (game_env.spread * 0.02)
        else:
            home_script = away_script = 1.0
        
        return {
            game_env.home_team: {
                'pace': home_pace,
                'pass_rate': home_pass_rate,
                'game_script': home_script,
                'scoring_multiplier': scoring_env['scoring_multiplier']
            },
            game_env.away_team: {
                'pace': away_pace,
                'pass_rate': away_pass_rate,
                'game_script': away_script,
                'scoring_multiplier': scoring_env['scoring_multiplier']
            },
            'game_totals': {
                'total_pace': home_pace + away_pace,
                'avg_pass_rate': (home_pass_rate + away_pass_rate) / 2,
                'scoring_environment': scoring_env
            }
        }
    
    def _prepare_player_projections(self, players: List[Dict]) -> List[PlayerProjection]:
        """Convert player data to PlayerProjection objects."""
        projections = []
        for player_data in players:
            projection = self.player_model.create_projection_from_data(player_data)
            projections.append(projection)
        return projections
    
    def _prepare_game_environments(self, games: List[Dict]) -> List[GameEnvironment]:
        """Convert game data to GameEnvironment objects."""
        from .game_model import create_game_environment
        return [create_game_environment(game_data) for game_data in games]
    
    def _scale_correlation_matrix(self, matrix: np.ndarray, 
                                 strength: float) -> np.ndarray:
        """Scale correlation matrix by strength factor."""
        if strength == 1.0:
            return matrix
        
        # Scale off-diagonal elements
        scaled = matrix.copy()
        n = matrix.shape[0]
        for i in range(n):
            for j in range(n):
                if i != j:
                    scaled[i, j] *= strength
        
        # Regularize to maintain positive semi-definite property
        eigenvals = np.linalg.eigvals(scaled)
        if np.min(eigenvals) < 0:
            regularization = abs(np.min(eigenvals)) + 0.01
            scaled += np.eye(n) * regularization
            # Rescale diagonal to 1
            diag = np.sqrt(np.diag(scaled))
            scaled = scaled / np.outer(diag, diag)
        
        return scaled
    
    def _apply_volatility_adjustment(self, base_score: float,
                                   volatility_multiplier: float,
                                   sim_random: np.random.RandomState) -> float:
        """Apply global volatility adjustment to a score."""
        if volatility_multiplier == 1.0:
            return 1.0
        
        # Add extra volatility proportional to the multiplier
        extra_vol = abs(volatility_multiplier - 1.0) * 0.2  # 20% extra vol per unit
        shock = sim_random.normal(0, extra_vol)
        return max(0.5, 1.0 + shock)  # Floor at 50% of base
    
    def _hash_inputs(self, players: List[Dict], games: List[Dict],
                    config: SamplingConfig) -> str:
        """Create a hash of inputs for caching."""
        import hashlib
        
        # Simplified hash - in practice would be more sophisticated
        player_hash = str(len(players)) + str(sum(p.get('salary', 0) for p in players))
        game_hash = str(len(games))
        config_hash = f"{config.n_simulations}_{config.seed}_{config.volatility_multiplier}"
        
        combined = f"{player_hash}_{game_hash}_{config_hash}"
        return hashlib.md5(combined.encode()).hexdigest()[:16]
    
    def generate_summary_statistics(self, results: List[SimulationResult],
                                   players: List[Dict]) -> pd.DataFrame:
        """
        Generate summary statistics from simulation results.
        
        Args:
            results: List of simulation results
            players: Original player data
            
        Returns:
            DataFrame with player statistics
        """
        player_lookup = {p['player_id']: p for p in players}
        
        # Collect all scores by player
        player_scores = {}
        for result in results:
            for player_id, score in result.player_scores.items():
                if player_id not in player_scores:
                    player_scores[player_id] = []
                player_scores[player_id].append(score)
        
        # Calculate statistics
        stats = []
        for player_id, scores in player_scores.items():
            if player_id not in player_lookup:
                continue
                
            player_data = player_lookup[player_id]
            scores_array = np.array(scores)
            
            # Basic statistics
            stat_row = {
                'player_id': player_id,
                'name': player_data.get('name', ''),
                'team': player_data.get('team', ''),
                'position': player_data.get('position', ''),
                'salary': player_data.get('salary', 0),
                'site_projection': player_data.get('site_projection', 0),
                
                # Simulation statistics
                'sim_mean': np.mean(scores_array),
                'sim_std': np.std(scores_array),
                'sim_min': np.min(scores_array),
                'sim_max': np.max(scores_array),
                
                # Percentiles
                'p10': np.percentile(scores_array, 10),
                'p25': np.percentile(scores_array, 25),
                'p50': np.percentile(scores_array, 50),
                'p75': np.percentile(scores_array, 75),
                'p90': np.percentile(scores_array, 90),
                'p95': np.percentile(scores_array, 95),
                
                # Additional metrics
                'zeros': np.sum(scores_array == 0.0),
                'zero_rate': np.mean(scores_array == 0.0),
                'n_sims': len(scores_array)
            }
            
            # Comparison to site projection
            if stat_row['site_projection'] > 0:
                stat_row['vs_site_delta'] = stat_row['sim_mean'] - stat_row['site_projection']
                stat_row['vs_site_pct'] = (stat_row['vs_site_delta'] / stat_row['site_projection']) * 100
                stat_row['beat_site_prob'] = np.mean(scores_array > stat_row['site_projection'])
            
            # Boom/bust metrics (position-dependent thresholds)
            boom_threshold = self._get_boom_threshold(player_data.get('position', 'WR'))
            stat_row['boom_prob'] = np.mean(scores_array >= boom_threshold)
            stat_row['boom_score'] = np.mean(scores_array[scores_array >= boom_threshold]) if stat_row['boom_prob'] > 0 else 0
            
            stats.append(stat_row)
        
        df = pd.DataFrame(stats)
        return df.sort_values('sim_mean', ascending=False)
    
    def _get_boom_threshold(self, position: str) -> float:
        """Get position-specific boom threshold."""
        thresholds = {
            'QB': 25.0,
            'RB': 20.0,
            'WR': 18.0,
            'TE': 15.0,
            'DST': 12.0
        }
        return thresholds.get(position, 18.0)


def create_default_config(n_simulations: int = 10000, 
                         seed: int = 42) -> SamplingConfig:
    """Create a default sampling configuration."""
    return SamplingConfig(
        n_simulations=n_simulations,
        seed=seed,
        volatility_multiplier=1.0,
        correlation_strength=1.0,
        include_correlations=True,
        parallel=False,
        batch_size=1000
    )