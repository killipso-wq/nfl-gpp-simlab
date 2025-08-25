"""
Player model for position-specific usage/projection distributions, injury/role uncertainty, and tail modeling.

This module implements the player-level simulation components as outlined in the 
Realistic NFL Monte Carlo Simulation PDF methodology.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class Position(Enum):
    """Player positions."""
    QB = "QB"
    RB = "RB"
    WR = "WR"
    TE = "TE"
    DST = "DST"


@dataclass
class PlayerUsage:
    """Player usage distribution parameters."""
    targets_mean: float = 0.0
    targets_std: float = 0.0
    carries_mean: float = 0.0
    carries_std: float = 0.0
    snap_share: float = 0.0
    red_zone_share: float = 0.0
    goal_line_share: float = 0.0


@dataclass
class PlayerEfficiency:
    """Player efficiency distribution parameters."""
    yards_per_target: float = 0.0
    yards_per_carry: float = 0.0
    catch_rate: float = 0.0
    td_rate: float = 0.0
    fumble_rate: float = 0.0


@dataclass
class PlayerProjection:
    """Complete player projection with uncertainty."""
    player_id: str
    name: str
    team: str
    position: Position
    salary: float
    site_projection: Optional[float] = None
    
    # Usage distributions
    usage: PlayerUsage = None
    efficiency: PlayerEfficiency = None
    
    # Projection parameters
    proj_mean: float = 0.0
    proj_std: float = 0.0
    proj_floor: float = 0.0  # p10
    proj_ceiling: float = 0.0  # p90
    
    # Role/injury uncertainty
    active_probability: float = 1.0
    role_volatility: float = 0.1  # volatility in usage share
    
    # Tail modeling
    boom_threshold: float = 0.0  # position-dependent boom threshold
    bust_floor: float = 0.0


class PlayerModel:
    """
    Models player-level distributions for fantasy points simulation.
    
    Based on the PDF methodology for realistic NFL Monte Carlo simulation.
    """
    
    def __init__(self, random_state: Optional[np.random.RandomState] = None):
        """
        Initialize the player model.
        
        Args:
            random_state: Random state for reproducible sampling
        """
        self.random_state = random_state or np.random.RandomState()
        
        # Position-specific parameters
        self.position_params = self._initialize_position_params()
        
        # Scoring parameters (DraftKings scoring)
        self.scoring = {
            'pass_yd': 0.04,
            'pass_td': 4.0,
            'int': -1.0,
            'rush_yd': 0.1,
            'rush_td': 6.0,
            'rec': 1.0,
            'rec_yd': 0.1,
            'rec_td': 6.0,
            'fumble': -1.0,
            'dst_pts_allowed': {0: 10, 1: 7, 7: 4, 14: 1, 21: 0, 28: -1, 35: -4},
            'dst_sack': 1.0,
            'dst_int': 2.0,
            'dst_fumble': 2.0,
            'dst_td': 6.0,
            'dst_safety': 2.0
        }
    
    def _initialize_position_params(self) -> Dict[Position, Dict]:
        """Initialize position-specific parameters."""
        return {
            Position.QB: {
                'base_volatility': 0.20,  # Reduced from 0.25
                'boom_threshold_multiplier': 1.5,
                'floor_percentile': 0.15,
                'ceiling_percentile': 0.90,
                'tail_weight': 0.10  # Reduced from 0.15
            },
            Position.RB: {
                'base_volatility': 0.30,  # Reduced from 0.35
                'boom_threshold_multiplier': 1.8,
                'floor_percentile': 0.10,
                'ceiling_percentile': 0.85,
                'tail_weight': 0.15  # Reduced from 0.20
            },
            Position.WR: {
                'base_volatility': 0.35,  # Reduced from 0.40
                'boom_threshold_multiplier': 2.0,
                'floor_percentile': 0.05,
                'ceiling_percentile': 0.80,
                'tail_weight': 0.20  # Reduced from 0.25
            },
            Position.TE: {
                'base_volatility': 0.40,  # Reduced from 0.45
                'boom_threshold_multiplier': 2.2,
                'floor_percentile': 0.05,
                'ceiling_percentile': 0.75,
                'tail_weight': 0.25  # Reduced from 0.30
            },
            Position.DST: {
                'base_volatility': 0.45,  # Reduced from 0.50
                'boom_threshold_multiplier': 2.5,
                'floor_percentile': 0.00,
                'ceiling_percentile': 0.70,
                'tail_weight': 0.30  # Reduced from 0.35
            }
        }
    
    def simulate_player_performance(self, projection: PlayerProjection, 
                                  team_pace: float = 65.0,
                                  team_pass_rate: float = 0.60,
                                  game_script: float = 1.0) -> float:
        """
        Simulate a single performance for a player.
        
        Args:
            projection: Player projection with distribution parameters
            team_pace: Team plays in this simulation
            team_pass_rate: Team pass rate in this simulation  
            game_script: Game script multiplier (>1 = positive script)
            
        Returns:
            Simulated fantasy points (clamped at 0)
        """
        # Check if player is active
        if self.random_state.random() > projection.active_probability:
            return 0.0
        
        # Get position parameters
        pos_params = self.position_params[projection.position]
        
        # Simulate based on position
        if projection.position == Position.QB:
            points = self._simulate_qb(projection, team_pace, team_pass_rate, game_script)
        elif projection.position == Position.RB:
            points = self._simulate_rb(projection, team_pace, team_pass_rate, game_script)
        elif projection.position in [Position.WR, Position.TE]:
            points = self._simulate_receiver(projection, team_pace, team_pass_rate, game_script)
        elif projection.position == Position.DST:
            points = self._simulate_dst(projection, team_pace, game_script)
        else:
            # Fallback to simple normal distribution
            points = self.random_state.normal(projection.proj_mean, projection.proj_std)
        
        # Apply tail modeling and floor
        points = self._apply_tail_modeling(points, projection, pos_params)
        
        return max(0.0, points)
    
    def _simulate_qb(self, projection: PlayerProjection, 
                     team_pace: float, team_pass_rate: float, 
                     game_script: float) -> float:
        """Simulate QB performance."""
        # Base attempts from team pace and pass rate
        pass_attempts = team_pace * team_pass_rate * game_script
        
        # Add role volatility
        role_multiplier = self.random_state.normal(1.0, projection.role_volatility)
        pass_attempts *= max(0.1, role_multiplier)
        
        # Efficiency sampling (with correlation)
        completion_rate = max(0.45, self.random_state.normal(0.65, 0.08))
        yards_per_attempt = max(4.0, self.random_state.normal(7.2, 1.2))
        td_rate = max(0.01, self.random_state.normal(0.045, 0.015))
        int_rate = max(0.005, self.random_state.normal(0.025, 0.01))
        
        # Calculate stats
        completions = pass_attempts * completion_rate
        pass_yards = completions * yards_per_attempt / completion_rate
        pass_tds = pass_attempts * td_rate
        interceptions = pass_attempts * int_rate
        
        # Add rushing (simplified)
        rush_attempts = max(0, self.random_state.normal(3.5, 2.0))
        rush_yards = rush_attempts * max(0, self.random_state.normal(4.2, 2.5))
        rush_tds = self.random_state.poisson(0.15) if rush_attempts > 0 else 0
        
        # Calculate fantasy points
        points = (
            pass_yards * self.scoring['pass_yd'] +
            pass_tds * self.scoring['pass_td'] +
            interceptions * self.scoring['int'] +
            rush_yards * self.scoring['rush_yd'] +
            rush_tds * self.scoring['rush_td']
        )
        
        return points
    
    def _simulate_rb(self, projection: PlayerProjection,
                     team_pace: float, team_pass_rate: float,
                     game_script: float) -> float:
        """Simulate RB performance."""
        # Usage shares with volatility
        if projection.usage:
            carry_share = max(0, self.random_state.normal(
                projection.usage.carries_mean / (team_pace * (1 - team_pass_rate)),
                projection.role_volatility
            ))
            target_share = max(0, self.random_state.normal(
                projection.usage.targets_mean / (team_pace * team_pass_rate * 0.25),  # RBs get ~25% of targets
                projection.role_volatility
            ))
        else:
            # Fallback to league averages
            carry_share = max(0, self.random_state.normal(0.15, projection.role_volatility))
            target_share = max(0, self.random_state.normal(0.08, projection.role_volatility))
        
        # Calculate opportunities
        rush_attempts = team_pace * (1 - team_pass_rate) * carry_share * game_script
        targets = team_pace * team_pass_rate * 0.25 * target_share
        
        # Efficiency with correlation
        yards_per_carry = max(2.0, self.random_state.normal(4.3, 1.1))
        catch_rate = max(0.6, self.random_state.normal(0.8, 0.12))
        yards_per_target = max(4.0, self.random_state.normal(7.8, 2.2))
        
        # TD rates (goal line and red zone opportunities)
        rush_td_rate = max(0.01, self.random_state.normal(0.08, 0.04))
        rec_td_rate = max(0.01, self.random_state.normal(0.12, 0.06))
        
        # Calculate stats
        rush_yards = rush_attempts * yards_per_carry
        receptions = targets * catch_rate
        rec_yards = receptions * yards_per_target / catch_rate
        rush_tds = self.random_state.poisson(rush_attempts * rush_td_rate)
        rec_tds = self.random_state.poisson(receptions * rec_td_rate)
        
        # Fumbles
        fumbles = self.random_state.poisson((rush_attempts + receptions) * 0.012)
        
        # Calculate fantasy points
        points = (
            rush_yards * self.scoring['rush_yd'] +
            rush_tds * self.scoring['rush_td'] +
            receptions * self.scoring['rec'] +
            rec_yards * self.scoring['rec_yd'] +
            rec_tds * self.scoring['rec_td'] +
            fumbles * self.scoring['fumble']
        )
        
        return points
    
    def _simulate_receiver(self, projection: PlayerProjection,
                          team_pace: float, team_pass_rate: float,
                          game_script: float) -> float:
        """Simulate WR/TE performance."""
        # Target share with volatility
        if projection.usage:
            target_share = max(0, self.random_state.normal(
                projection.usage.targets_mean / (team_pace * team_pass_rate),
                projection.role_volatility
            ))
        else:
            # Position-dependent fallback
            base_share = 0.15 if projection.position == Position.WR else 0.10
            target_share = max(0, self.random_state.normal(base_share, projection.role_volatility))
        
        # Calculate targets
        targets = team_pace * team_pass_rate * target_share * game_script
        
        # Efficiency parameters with position adjustments
        if projection.position == Position.WR:
            catch_rate = max(0.45, self.random_state.normal(0.62, 0.12))
            yards_per_target = max(6.0, self.random_state.normal(9.8, 2.8))
            td_rate = max(0.02, self.random_state.normal(0.08, 0.04))
        else:  # TE
            catch_rate = max(0.55, self.random_state.normal(0.68, 0.10))
            yards_per_target = max(5.0, self.random_state.normal(8.4, 2.2))
            td_rate = max(0.02, self.random_state.normal(0.10, 0.05))
        
        # Calculate stats
        receptions = targets * catch_rate
        rec_yards = receptions * yards_per_target / catch_rate
        rec_tds = self.random_state.poisson(receptions * td_rate)
        
        # Fumbles
        fumbles = self.random_state.poisson(receptions * 0.008)
        
        # Calculate fantasy points
        points = (
            receptions * self.scoring['rec'] +
            rec_yards * self.scoring['rec_yd'] +
            rec_tds * self.scoring['rec_td'] +
            fumbles * self.scoring['fumble']
        )
        
        return points
    
    def _simulate_dst(self, projection: PlayerProjection,
                     team_pace: float, game_script: float) -> float:
        """Simulate DST performance."""
        # Opponent scoring (simplified model)
        opp_pace = team_pace * self.random_state.normal(1.0, 0.15)
        opp_efficiency = max(0.3, self.random_state.normal(1.0, 0.25)) / game_script
        
        # Points allowed
        base_points = opp_pace * 0.35 * opp_efficiency  # ~23 points baseline
        points_allowed = max(0, self.random_state.normal(base_points, base_points * 0.3))
        
        # Defensive stats
        sacks = max(0, self.random_state.poisson(2.2))
        interceptions = max(0, self.random_state.poisson(0.8))
        fumbles = max(0, self.random_state.poisson(0.6))
        def_tds = self.random_state.poisson(0.15)
        safeties = self.random_state.poisson(0.05)
        
        # Points allowed scoring
        pa_points = 0
        for threshold, points in sorted(self.scoring['dst_pts_allowed'].items()):
            if points_allowed >= threshold:
                pa_points = points
                break
        
        # Calculate fantasy points
        points = (
            pa_points +
            sacks * self.scoring['dst_sack'] +
            interceptions * self.scoring['dst_int'] +
            fumbles * self.scoring['dst_fumble'] +
            def_tds * self.scoring['dst_td'] +
            safeties * self.scoring['dst_safety']
        )
        
        return points
    
    def _apply_tail_modeling(self, base_points: float, 
                           projection: PlayerProjection,
                           pos_params: Dict) -> float:
        """Apply tail modeling to enhance boom/bust characteristics."""
        # Probability of tail event
        tail_prob = pos_params['tail_weight']
        
        if self.random_state.random() < tail_prob:
            # Tail event - boost or bust
            if self.random_state.random() < 0.7:  # 70% boom, 30% bust in tail
                # Boom event
                multiplier = self.random_state.lognormal(0.5, 0.4)  # typically 1.5-3x
                return base_points * multiplier
            else:
                # Bust event
                return base_points * self.random_state.uniform(0.1, 0.4)
        
        return base_points
    
    def create_projection_from_data(self, player_data: Dict) -> PlayerProjection:
        """
        Create a PlayerProjection from player data dictionary.
        
        Args:
            player_data: Dictionary with player information
            
        Returns:
            PlayerProjection instance
        """
        position = Position(player_data.get('position', 'WR'))
        
        # Estimate projection parameters if not provided
        site_proj = player_data.get('site_projection', 0.0)
        proj_mean = player_data.get('proj_mean', site_proj if site_proj else 8.0)
        
        # Position-dependent volatility
        base_vol = self.position_params[position]['base_volatility']
        proj_std = player_data.get('proj_std', proj_mean * base_vol)
        
        # Create usage and efficiency objects if data is available
        usage = None
        if any(key in player_data for key in ['targets_mean', 'carries_mean']):
            usage = PlayerUsage(
                targets_mean=player_data.get('targets_mean', 0.0),
                targets_std=player_data.get('targets_std', 0.0),
                carries_mean=player_data.get('carries_mean', 0.0),
                carries_std=player_data.get('carries_std', 0.0),
                snap_share=player_data.get('snap_share', 0.0),
                red_zone_share=player_data.get('red_zone_share', 0.0),
                goal_line_share=player_data.get('goal_line_share', 0.0)
            )
        
        efficiency = None
        if any(key in player_data for key in ['yards_per_target', 'catch_rate']):
            efficiency = PlayerEfficiency(
                yards_per_target=player_data.get('yards_per_target', 0.0),
                yards_per_carry=player_data.get('yards_per_carry', 0.0),
                catch_rate=player_data.get('catch_rate', 0.0),
                td_rate=player_data.get('td_rate', 0.0),
                fumble_rate=player_data.get('fumble_rate', 0.0)
            )
        
        return PlayerProjection(
            player_id=player_data.get('player_id', ''),
            name=player_data.get('name', ''),
            team=player_data.get('team', ''),
            position=position,
            salary=player_data.get('salary', 0.0),
            site_projection=site_proj,
            usage=usage,
            efficiency=efficiency,
            proj_mean=proj_mean,
            proj_std=proj_std,
            proj_floor=player_data.get('proj_floor', proj_mean * 0.4),
            proj_ceiling=player_data.get('proj_ceiling', proj_mean * 2.0),
            active_probability=player_data.get('active_probability', 1.0),
            role_volatility=player_data.get('role_volatility', 0.15),
            boom_threshold=player_data.get('boom_threshold', 
                                         proj_mean * self.position_params[position]['boom_threshold_multiplier']),
            bust_floor=player_data.get('bust_floor', 0.0)
        )