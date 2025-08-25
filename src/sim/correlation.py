"""
Correlation modeling for intra-team and inter-team dependencies.

This module implements correlation structures as outlined in the 
Realistic NFL Monte Carlo Simulation PDF methodology.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from enum import Enum

from .player_model import Position


@dataclass
class CorrelationPair:
    """Represents a correlation between two players or teams."""
    entity1: str  # player_id or team
    entity2: str  # player_id or team
    correlation: float
    correlation_type: str  # 'positive', 'negative', 'zero'


class CorrelationType(Enum):
    """Types of correlations in the model."""
    QB_RECEIVER = "qb_receiver"  # QB ↔ WR/TE positive
    RB_TEAM_PASSING = "rb_team_passing"  # RB ↔ team passing negative
    RB_DST = "rb_dst"  # RB ↔ opposing DST negative
    INTER_TEAM_SCORING = "inter_team_scoring"  # opposing teams negative
    SAME_POSITION = "same_position"  # same position players negative
    GAME_STACK = "game_stack"  # players in same game positive


class CorrelationModel:
    """
    Models correlations between player performances and team outcomes.
    
    Implements the correlation structure outlined in the PDF methodology:
    - Intra-team: QB↔WR/TE positive, RB↔DST negative correlations
    - Inter-team: negative correlations between opposing teams
    - Position: same-position players compete for opportunities
    """
    
    def __init__(self, random_state: Optional[np.random.RandomState] = None):
        """
        Initialize the correlation model.
        
        Args:
            random_state: Random state for reproducible sampling
        """
        self.random_state = random_state or np.random.RandomState()
        
        # Correlation parameters
        self.correlation_params = self._initialize_correlation_params()
        
        # Correlation matrices (built dynamically)
        self._correlation_cache = {}
    
    def _initialize_correlation_params(self) -> Dict[CorrelationType, Dict]:
        """Initialize correlation parameters by type."""
        return {
            CorrelationType.QB_RECEIVER: {
                'base_correlation': 0.35,  # QB-WR/TE moderate positive
                'distance_decay': 0.1,     # decay with target share difference
                'max_correlation': 0.55    # cap on correlation
            },
            CorrelationType.RB_TEAM_PASSING: {
                'base_correlation': -0.25, # RB-passing game negative
                'script_sensitivity': 0.3, # stronger in extreme game scripts
                'max_correlation': -0.45   # floor on correlation
            },
            CorrelationType.RB_DST: {
                'base_correlation': -0.15, # RB vs opposing DST
                'efficiency_factor': 0.2,  # stronger for efficient RBs
                'max_correlation': -0.35
            },
            CorrelationType.INTER_TEAM_SCORING: {
                'base_correlation': -0.20, # opposing teams compete
                'pace_factor': 0.1,        # less negative in high-pace games
                'max_correlation': -0.40
            },
            CorrelationType.SAME_POSITION: {
                'base_correlation': -0.15, # same position compete
                'target_competition': 0.3, # stronger for target-competing positions
                'max_correlation': -0.50
            },
            CorrelationType.GAME_STACK: {
                'base_correlation': 0.10,  # players in same game
                'pace_boost': 0.15,        # stronger in high-pace games
                'max_correlation': 0.30
            }
        }
    
    def build_correlation_matrix(self, players: List[Dict], 
                                games: List[Dict]) -> Tuple[np.ndarray, List[str]]:
        """
        Build a correlation matrix for a set of players and games.
        
        Args:
            players: List of player dictionaries
            games: List of game dictionaries
            
        Returns:
            Tuple of (correlation_matrix, player_ids)
        """
        player_ids = [p['player_id'] for p in players]
        n_players = len(player_ids)
        
        # Initialize correlation matrix as identity
        corr_matrix = np.eye(n_players)
        
        # Build mappings
        player_lookup = {pid: i for i, pid in enumerate(player_ids)}
        team_players = self._group_players_by_team(players)
        game_players = self._group_players_by_game(players, games)
        
        # Apply each correlation type
        self._apply_qb_receiver_correlations(corr_matrix, players, player_lookup)
        self._apply_rb_team_correlations(corr_matrix, players, player_lookup, team_players)
        self._apply_inter_team_correlations(corr_matrix, players, player_lookup, games)
        self._apply_same_position_correlations(corr_matrix, players, player_lookup, team_players)
        self._apply_game_stack_correlations(corr_matrix, players, player_lookup, game_players)
        
        # Ensure matrix is positive semi-definite
        corr_matrix = self._regularize_correlation_matrix(corr_matrix)
        
        return corr_matrix, player_ids
    
    def sample_correlated_shocks(self, correlation_matrix: np.ndarray,
                                n_samples: int = 1) -> np.ndarray:
        """
        Sample correlated shocks using the correlation matrix.
        
        Args:
            correlation_matrix: Correlation matrix
            n_samples: Number of sample sets to generate
            
        Returns:
            Array of shape (n_samples, n_players) with correlated shocks
        """
        n_players = correlation_matrix.shape[0]
        
        # Cholesky decomposition for sampling
        try:
            L = np.linalg.cholesky(correlation_matrix)
        except np.linalg.LinAlgError:
            # Fallback to eigenvalue decomposition
            eigenvals, eigenvecs = np.linalg.eigh(correlation_matrix)
            eigenvals = np.maximum(eigenvals, 0.01)  # regularize
            L = eigenvecs @ np.diag(np.sqrt(eigenvals))
        
        # Sample independent normal variables
        independent_shocks = self.random_state.normal(0, 1, (n_samples, n_players))
        
        # Apply correlation structure
        correlated_shocks = independent_shocks @ L.T
        
        return correlated_shocks
    
    def _group_players_by_team(self, players: List[Dict]) -> Dict[str, List[Dict]]:
        """Group players by team."""
        team_players = {}
        for player in players:
            team = player['team']
            if team not in team_players:
                team_players[team] = []
            team_players[team].append(player)
        return team_players
    
    def _group_players_by_game(self, players: List[Dict], 
                              games: List[Dict]) -> Dict[str, List[Dict]]:
        """Group players by game."""
        # Build team to game mapping
        team_to_game = {}
        for game in games:
            team_to_game[game['home_team']] = game['game_id']
            team_to_game[game['away_team']] = game['game_id']
        
        game_players = {}
        for player in players:
            game_id = team_to_game.get(player['team'])
            if game_id:
                if game_id not in game_players:
                    game_players[game_id] = []
                game_players[game_id].append(player)
        
        return game_players
    
    def _apply_qb_receiver_correlations(self, corr_matrix: np.ndarray,
                                       players: List[Dict],
                                       player_lookup: Dict[str, int]):
        """Apply QB-WR/TE positive correlations."""
        params = self.correlation_params[CorrelationType.QB_RECEIVER]
        
        for i, player1 in enumerate(players):
            if player1['position'] != 'QB':
                continue
                
            for j, player2 in enumerate(players):
                if (player2['position'] not in ['WR', 'TE'] or 
                    player1['team'] != player2['team'] or i == j):
                    continue
                
                # Base correlation with target share weighting
                target_share = player2.get('target_share', 0.15)
                correlation = params['base_correlation'] * (1 + target_share)
                correlation = min(correlation, params['max_correlation'])
                
                corr_matrix[i, j] = correlation
                corr_matrix[j, i] = correlation
    
    def _apply_rb_team_correlations(self, corr_matrix: np.ndarray,
                                   players: List[Dict],
                                   player_lookup: Dict[str, int],
                                   team_players: Dict[str, List[Dict]]):
        """Apply RB negative correlations with team passing game."""
        params = self.correlation_params[CorrelationType.RB_TEAM_PASSING]
        
        for team, team_roster in team_players.items():
            rbs = [p for p in team_roster if p['position'] == 'RB']
            passers = [p for p in team_roster if p['position'] in ['QB', 'WR', 'TE']]
            
            for rb in rbs:
                rb_idx = player_lookup[rb['player_id']]
                
                for passer in passers:
                    if rb['player_id'] == passer['player_id']:
                        continue
                        
                    passer_idx = player_lookup[passer['player_id']]
                    
                    # Negative correlation between RB and passing game
                    correlation = params['base_correlation']
                    
                    # Adjust for RB usage (higher usage = stronger negative correlation)
                    rb_usage = rb.get('carry_share', 0.15)
                    correlation *= (1 + rb_usage)
                    correlation = max(correlation, params['max_correlation'])
                    
                    corr_matrix[rb_idx, passer_idx] = correlation
                    corr_matrix[passer_idx, rb_idx] = correlation
    
    def _apply_inter_team_correlations(self, corr_matrix: np.ndarray,
                                      players: List[Dict],
                                      player_lookup: Dict[str, int],
                                      games: List[Dict]):
        """Apply negative correlations between opposing teams."""
        params = self.correlation_params[CorrelationType.INTER_TEAM_SCORING]
        
        # Build opponent mapping
        opponents = {}
        for game in games:
            opponents[game['home_team']] = game['away_team']
            opponents[game['away_team']] = game['home_team']
        
        for i, player1 in enumerate(players):
            team1 = player1['team']
            opponent = opponents.get(team1)
            
            if not opponent:
                continue
                
            for j, player2 in enumerate(players):
                if player2['team'] != opponent or i == j:
                    continue
                
                # Base negative correlation between opposing players
                correlation = params['base_correlation']
                
                # Weaker for DST vs offensive players (already captured elsewhere)
                if (player1['position'] == 'DST' or player2['position'] == 'DST'):
                    correlation *= 0.5
                
                corr_matrix[i, j] = correlation
                corr_matrix[j, i] = correlation
    
    def _apply_same_position_correlations(self, corr_matrix: np.ndarray,
                                         players: List[Dict],
                                         player_lookup: Dict[str, int],
                                         team_players: Dict[str, List[Dict]]):
        """Apply negative correlations between same-position players on same team."""
        params = self.correlation_params[CorrelationType.SAME_POSITION]
        
        for team, team_roster in team_players.items():
            # Group by position
            by_position = {}
            for player in team_roster:
                pos = player['position']
                if pos not in by_position:
                    by_position[pos] = []
                by_position[pos].append(player)
            
            # Apply correlations within each position group
            for position, pos_players in by_position.items():
                if len(pos_players) < 2:
                    continue
                
                for i, player1 in enumerate(pos_players):
                    for j, player2 in enumerate(pos_players):
                        if i >= j:
                            continue
                        
                        idx1 = player_lookup[player1['player_id']]
                        idx2 = player_lookup[player2['player_id']]
                        
                        # Negative correlation (competing for opportunities)
                        correlation = params['base_correlation']
                        
                        # Stronger for target-competing positions
                        if position in ['WR', 'TE']:
                            correlation *= (1 + params['target_competition'])
                        
                        correlation = max(correlation, params['max_correlation'])
                        
                        corr_matrix[idx1, idx2] = correlation
                        corr_matrix[idx2, idx1] = correlation
    
    def _apply_game_stack_correlations(self, corr_matrix: np.ndarray,
                                      players: List[Dict],
                                      player_lookup: Dict[str, int],
                                      game_players: Dict[str, List[Dict]]):
        """Apply positive correlations for players in the same game."""
        params = self.correlation_params[CorrelationType.GAME_STACK]
        
        for game_id, game_roster in game_players.items():
            if len(game_roster) < 2:
                continue
            
            for i, player1 in enumerate(game_roster):
                for j, player2 in enumerate(game_roster):
                    if (i >= j or player1['team'] == player2['team']):
                        continue  # Skip same team (handled elsewhere)
                    
                    idx1 = player_lookup[player1['player_id']]
                    idx2 = player_lookup[player2['player_id']]
                    
                    # Weak positive correlation for game pace/scoring
                    correlation = params['base_correlation']
                    
                    # Skip if stronger correlation already applied
                    if abs(corr_matrix[idx1, idx2]) > abs(correlation):
                        continue
                    
                    corr_matrix[idx1, idx2] = correlation
                    corr_matrix[idx2, idx1] = correlation
    
    def _regularize_correlation_matrix(self, corr_matrix: np.ndarray) -> np.ndarray:
        """
        Ensure correlation matrix is positive semi-definite.
        
        Args:
            corr_matrix: Input correlation matrix
            
        Returns:
            Regularized correlation matrix
        """
        # Check if already positive semi-definite
        eigenvals = np.linalg.eigvals(corr_matrix)
        min_eigenval = np.min(eigenvals)
        
        if min_eigenval >= 0:
            return corr_matrix
        
        # Regularize by adding small positive constant to diagonal
        regularization = abs(min_eigenval) + 0.01
        regularized = corr_matrix + np.eye(corr_matrix.shape[0]) * regularization
        
        # Rescale to maintain correlation structure
        diag = np.sqrt(np.diag(regularized))
        regularized = regularized / np.outer(diag, diag)
        
        return regularized
    
    def get_correlation_summary(self, correlation_matrix: np.ndarray,
                               player_ids: List[str],
                               players: List[Dict]) -> pd.DataFrame:
        """
        Generate a summary of correlations for analysis.
        
        Args:
            correlation_matrix: Correlation matrix
            player_ids: List of player IDs
            players: List of player dictionaries
            
        Returns:
            DataFrame with correlation summary
        """
        player_lookup = {p['player_id']: p for p in players}
        correlations = []
        
        n = len(player_ids)
        for i in range(n):
            for j in range(i + 1, n):
                if abs(correlation_matrix[i, j]) < 0.01:
                    continue  # Skip near-zero correlations
                
                player1 = player_lookup[player_ids[i]]
                player2 = player_lookup[player_ids[j]]
                
                correlations.append({
                    'player1_id': player_ids[i],
                    'player1_name': player1['name'],
                    'player1_team': player1['team'],
                    'player1_position': player1['position'],
                    'player2_id': player_ids[j],
                    'player2_name': player2['name'],
                    'player2_team': player2['team'],
                    'player2_position': player2['position'],
                    'correlation': correlation_matrix[i, j],
                    'correlation_type': self._classify_correlation_type(player1, player2)
                })
        
        df = pd.DataFrame(correlations)
        return df.sort_values('correlation', key=abs, ascending=False)
    
    def _classify_correlation_type(self, player1: Dict, player2: Dict) -> str:
        """Classify the type of correlation between two players."""
        if player1['team'] == player2['team']:
            if (player1['position'] == 'QB' and 
                player2['position'] in ['WR', 'TE']):
                return 'QB-Receiver'
            elif (player1['position'] == 'RB' and 
                  player2['position'] in ['QB', 'WR', 'TE']):
                return 'RB-PassingGame'
            elif player1['position'] == player2['position']:
                return 'SamePosition'
            else:
                return 'SameTeam'
        else:
            return 'OpposingTeam'


def create_simple_correlation_matrix(n_players: int, 
                                   base_correlation: float = 0.05,
                                   random_state: Optional[np.random.RandomState] = None) -> np.ndarray:
    """
    Create a simple correlation matrix with weak positive correlations.
    
    Args:
        n_players: Number of players
        base_correlation: Base correlation between all players
        random_state: Random state for reproducible generation
        
    Returns:
        Correlation matrix
    """
    if random_state is None:
        random_state = np.random.RandomState()
    
    # Start with identity matrix
    corr_matrix = np.eye(n_players)
    
    # Add weak correlations
    for i in range(n_players):
        for j in range(i + 1, n_players):
            correlation = random_state.normal(base_correlation, base_correlation * 0.5)
            correlation = np.clip(correlation, -0.3, 0.3)
            corr_matrix[i, j] = correlation
            corr_matrix[j, i] = correlation
    
    # Regularize to ensure positive semi-definite
    eigenvals = np.linalg.eigvals(corr_matrix)
    if np.min(eigenvals) < 0:
        regularization = abs(np.min(eigenvals)) + 0.01
        corr_matrix += np.eye(n_players) * regularization
        # Rescale
        diag = np.sqrt(np.diag(corr_matrix))
        corr_matrix = corr_matrix / np.outer(diag, diag)
    
    return corr_matrix