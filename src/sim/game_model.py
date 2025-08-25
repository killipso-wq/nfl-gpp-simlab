"""
Game model for team-level pace, pass rate, totals/spread priors, and venue/weather adjustments.

This module implements the game-level simulation components as outlined in the 
Realistic NFL Monte Carlo Simulation PDF methodology.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class GameEnvironment:
    """Environment factors for a specific game."""
    game_id: str
    home_team: str
    away_team: str
    total: Optional[float] = None  # Over/Under
    spread: Optional[float] = None  # Positive = home favored
    weather: Optional[str] = None
    venue_type: str = 'outdoor'  # outdoor, dome, retractable
    
    
@dataclass
class TeamGameState:
    """Team state within a game simulation."""
    team: str
    opponent: str
    is_home: bool
    base_pace: float  # plays per game
    base_pass_rate: float  # neutral pass rate
    proe_adjustment: float = 0.0  # pass rate over expected adjustment
    total_adjustment: float = 1.0  # multiplier for pace from total
    

class GameModel:
    """
    Models game-level factors that affect team and player performance.
    
    Based on the PDF methodology for realistic NFL Monte Carlo simulation.
    """
    
    def __init__(self, random_state: Optional[np.random.RandomState] = None):
        """
        Initialize the game model.
        
        Args:
            random_state: Random state for reproducible sampling
        """
        self.random_state = random_state or np.random.RandomState()
        
        # Default league averages (can be calibrated from historical data)
        self.league_avg_pace = 65.0  # plays per game
        self.league_avg_pass_rate = 0.60  # 60% pass rate
        self.home_field_advantage = 0.02  # 2% pass rate boost for home team
        
        # Volatility parameters
        self.pace_volatility = 0.15  # 15% coefficient of variation
        self.pass_rate_volatility = 0.08  # 8% standard deviation
        
    def simulate_game_pace(self, environment: GameEnvironment, 
                          home_state: TeamGameState, 
                          away_state: TeamGameState) -> Tuple[float, float]:
        """
        Simulate the pace (total plays) for each team in the game.
        
        Args:
            environment: Game environment factors
            home_state: Home team state
            away_state: Away team state
            
        Returns:
            Tuple of (home_plays, away_plays)
        """
        # Base pace from team characteristics
        base_home_pace = home_state.base_pace
        base_away_pace = away_state.base_pace
        
        # Adjust for game total if available
        if environment.total:
            total_factor = environment.total / 45.0  # normalize around 45 point total
            base_home_pace *= home_state.total_adjustment * total_factor
            base_away_pace *= away_state.total_adjustment * total_factor
        
        # Add game-level pace correlation (teams share some pace factors)
        game_pace_shock = self.random_state.normal(0, self.pace_volatility * 0.5)
        
        # Individual team pace variations
        home_pace_shock = self.random_state.normal(0, self.pace_volatility * 0.7)
        away_pace_shock = self.random_state.normal(0, self.pace_volatility * 0.7)
        
        # Calculate final pace with floors
        home_plays = max(35, base_home_pace * (1 + game_pace_shock + home_pace_shock))
        away_plays = max(35, base_away_pace * (1 + game_pace_shock + away_pace_shock))
        
        return home_plays, away_plays
    
    def simulate_pass_rates(self, environment: GameEnvironment,
                           home_state: TeamGameState,
                           away_state: TeamGameState) -> Tuple[float, float]:
        """
        Simulate pass rates for each team incorporating game script.
        
        Args:
            environment: Game environment factors
            home_state: Home team state
            away_state: Away team state
            
        Returns:
            Tuple of (home_pass_rate, away_pass_rate)
        """
        # Start with base pass rates
        home_pass_rate = home_state.base_pass_rate + home_state.proe_adjustment
        away_pass_rate = away_state.base_pass_rate + away_state.proe_adjustment
        
        # Home field adjustment
        if home_state.is_home:
            home_pass_rate += self.home_field_advantage
        
        # Game script adjustment from spread
        if environment.spread:
            # Favorite runs more, underdog passes more
            spread_effect = environment.spread * 0.005  # 0.5% per point
            home_pass_rate -= spread_effect
            away_pass_rate += spread_effect
        
        # Weather/venue adjustments
        weather_adjustment = self._get_weather_adjustment(environment)
        home_pass_rate += weather_adjustment
        away_pass_rate += weather_adjustment
        
        # Add volatility
        home_pass_rate += self.random_state.normal(0, self.pass_rate_volatility)
        away_pass_rate += self.random_state.normal(0, self.pass_rate_volatility)
        
        # Constrain to reasonable bounds
        home_pass_rate = np.clip(home_pass_rate, 0.35, 0.85)
        away_pass_rate = np.clip(away_pass_rate, 0.35, 0.85)
        
        return home_pass_rate, away_pass_rate
    
    def _get_weather_adjustment(self, environment: GameEnvironment) -> float:
        """
        Calculate pass rate adjustment for weather conditions.
        
        Args:
            environment: Game environment
            
        Returns:
            Pass rate adjustment (negative = more running)
        """
        if environment.venue_type == 'dome':
            return 0.01  # Slight pass boost in dome
        
        if environment.weather:
            weather_lower = environment.weather.lower()
            if any(term in weather_lower for term in ['rain', 'snow', 'wind']):
                return -0.03  # 3% less passing in bad weather
            elif 'cold' in weather_lower:
                return -0.01  # 1% less passing in cold
        
        return 0.0
    
    def simulate_scoring_environment(self, environment: GameEnvironment) -> Dict[str, float]:
        """
        Simulate the overall scoring environment for the game.
        
        Args:
            environment: Game environment
            
        Returns:
            Dictionary with scoring modifiers
        """
        base_scoring = 1.0
        
        # Adjust for game total
        if environment.total:
            total_factor = environment.total / 45.0
            base_scoring *= total_factor
        
        # Weather effects on scoring
        if environment.weather:
            weather_lower = environment.weather.lower()
            if any(term in weather_lower for term in ['rain', 'snow']):
                base_scoring *= 0.9  # 10% reduction in bad weather
            elif 'wind' in weather_lower:
                base_scoring *= 0.95  # 5% reduction in wind
        
        # Add some volatility to scoring environment
        scoring_shock = self.random_state.normal(0, 0.12)  # 12% volatility
        final_scoring = max(0.5, base_scoring * (1 + scoring_shock))
        
        return {
            'scoring_multiplier': final_scoring,
            'total_adjustment': environment.total / 45.0 if environment.total else 1.0,
            'weather_factor': 0.9 if (environment.weather and 
                                     any(term in environment.weather.lower() 
                                         for term in ['rain', 'snow', 'wind'])) else 1.0
        }


def create_game_environment(game_data: Dict) -> GameEnvironment:
    """
    Create a GameEnvironment from game data.
    
    Args:
        game_data: Dictionary with game information
        
    Returns:
        GameEnvironment instance
    """
    return GameEnvironment(
        game_id=game_data.get('game_id', ''),
        home_team=game_data.get('home_team', ''),
        away_team=game_data.get('away_team', ''),
        total=game_data.get('total'),
        spread=game_data.get('spread'),
        weather=game_data.get('weather'),
        venue_type=game_data.get('venue_type', 'outdoor')
    )


def create_team_game_state(team_data: Dict, is_home: bool = False) -> TeamGameState:
    """
    Create a TeamGameState from team data.
    
    Args:
        team_data: Dictionary with team information
        is_home: Whether this team is playing at home
        
    Returns:
        TeamGameState instance
    """
    return TeamGameState(
        team=team_data.get('team', ''),
        opponent=team_data.get('opponent', ''),
        is_home=is_home,
        base_pace=team_data.get('base_pace', 65.0),
        base_pass_rate=team_data.get('base_pass_rate', 0.60),
        proe_adjustment=team_data.get('proe_adjustment', 0.0),
        total_adjustment=team_data.get('total_adjustment', 1.0)
    )