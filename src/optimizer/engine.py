"""
PuLP-based MILP optimizer engine for DFS lineup generation
"""

import pandas as pd
import numpy as np
import pulp
from typing import Dict, List, Optional, Tuple
from src.common.io import get_roster_template, get_salary_cap


class LineupOptimizer:
    """DFS lineup optimizer using Mixed Integer Linear Programming"""
    
    def __init__(self, site: str = 'DraftKings'):
        self.site = site
        self.roster_template = get_roster_template(site)
        self.salary_cap = get_salary_cap(site)
        self.players_df = None
        self.optimization_results = []
    
    def load_players(self, players_df: pd.DataFrame):
        """Load player data for optimization"""
        self.players_df = players_df.copy()
        
        # Ensure required columns exist
        required_cols = ['name', 'pos', 'team', 'salary', 'fpts']
        missing = [col for col in required_cols if col not in self.players_df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        
        # Add player index for optimization
        self.players_df = self.players_df.reset_index(drop=True)
        self.players_df['player_idx'] = self.players_df.index
    
    def optimize_lineup(
        self,
        constraints: Dict,
        randomize_projections: bool = True,
        random_seed: int = None
    ) -> Optional[Dict]:
        """
        Optimize a single lineup given constraints
        """
        if self.players_df is None:
            raise ValueError("No player data loaded. Call load_players() first.")
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        # Create randomized projections if requested
        projections = self.players_df['fpts'].copy()
        if randomize_projections:
            variance = constraints.get('projection_variance', 0.15)
            noise = np.random.normal(0, projections * variance, len(projections))
            projections = np.maximum(projections + noise, 0)  # Ensure non-negative
        
        # Create optimization problem
        prob = pulp.LpProblem("DFS_Lineup_Optimization", pulp.LpMaximize)
        
        # Decision variables - binary variable for each player
        player_vars = {}
        for idx, player in self.players_df.iterrows():
            player_vars[idx] = pulp.LpVariable(
                f"player_{idx}",
                cat='Binary'
            )
        
        # Objective function - maximize projected points
        prob += pulp.lpSum([
            projections[idx] * player_vars[idx] 
            for idx in player_vars
        ])
        
        # Salary constraint
        prob += pulp.lpSum([
            self.players_df.loc[idx, 'salary'] * player_vars[idx] 
            for idx in player_vars
        ]) <= constraints.get('salary_cap', self.salary_cap)
        
        prob += pulp.lpSum([
            self.players_df.loc[idx, 'salary'] * player_vars[idx] 
            for idx in player_vars
        ]) >= constraints.get('min_salary', self.salary_cap - 1000)
        
        # Position constraints
        self._add_position_constraints(prob, player_vars, constraints)
        
        # Team constraints
        self._add_team_constraints(prob, player_vars, constraints)
        
        # Stacking constraints
        self._add_stacking_constraints(prob, player_vars, constraints)
        
        # Ownership constraints
        self._add_ownership_constraints(prob, player_vars, constraints)
        
        # Diversity constraints (exclude previous lineups)
        self._add_diversity_constraints(prob, player_vars, constraints)
        
        # Solve the problem
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        # Check if solution was found
        if prob.status != pulp.LpStatusOptimal:
            return None
        
        # Extract lineup
        lineup_players = []
        total_salary = 0
        total_projection = 0
        total_ownership = 0
        
        for idx in player_vars:
            if player_vars[idx].varValue == 1:
                player = self.players_df.loc[idx]
                lineup_players.append(player)
                total_salary += player['salary']
                total_projection += projections[idx]
                total_ownership += player.get('own%', 0)
        
        lineup_df = pd.DataFrame(lineup_players)
        
        return {
            'lineup_df': lineup_df,
            'total_salary': total_salary,
            'total_projection': total_projection,
            'total_ownership': total_ownership,
            'num_players': len(lineup_players)
        }
    
    def optimize_multiple_lineups(
        self,
        num_lineups: int,
        constraints: Dict,
        randomize_projections: bool = True,
        base_seed: int = 42
    ) -> List[Dict]:
        """
        Optimize multiple lineups with diversity constraints
        """
        lineups = []
        
        for i in range(num_lineups):
            # Use different seed for each lineup to get variety
            seed = base_seed + i if randomize_projections else None
            
            # Add diversity constraint to avoid previous lineups
            lineup_constraints = constraints.copy()
            lineup_constraints['previous_lineups'] = lineups
            
            lineup = self.optimize_lineup(
                lineup_constraints,
                randomize_projections=randomize_projections,
                random_seed=seed
            )
            
            if lineup is None:
                print(f"Could not generate lineup {i+1}. Stopping optimization.")
                break
            
            lineups.append(lineup)
        
        return lineups
    
    def _add_position_constraints(self, prob, player_vars, constraints):
        """Add position-based constraints"""
        positions = self.players_df['pos'].unique()
        
        for pos in positions:
            pos_players = self.players_df[self.players_df['pos'] == pos].index.tolist()
            
            if pos in self.roster_template:
                # Exact position requirements
                prob += pulp.lpSum([
                    player_vars[idx] for idx in pos_players
                ]) == self.roster_template[pos]
            elif pos in ['RB', 'WR', 'TE'] and 'FLEX' in self.roster_template:
                # These positions can fill FLEX spot (handled separately)
                pass
            else:
                # Positions not in template (like K for DraftKings)
                if pos != 'K' or self.site == 'FanDuel':
                    prob += pulp.lpSum([
                        player_vars[idx] for idx in pos_players
                    ]) <= self.roster_template.get(pos, 0)
        
        # FLEX constraint (RB/WR/TE)
        if 'FLEX' in self.roster_template:
            flex_positions = ['RB', 'WR', 'TE']
            flex_players = self.players_df[
                self.players_df['pos'].isin(flex_positions)
            ].index.tolist()
            
            # Total RB + WR + TE = position requirements + FLEX
            total_flex_spots = (
                self.roster_template.get('RB', 0) +
                self.roster_template.get('WR', 0) +
                self.roster_template.get('TE', 0) +
                self.roster_template.get('FLEX', 0)
            )
            
            prob += pulp.lpSum([
                player_vars[idx] for idx in flex_players
            ]) == total_flex_spots
        
        # Total lineup size
        prob += pulp.lpSum([
            player_vars[idx] for idx in player_vars
        ]) == self.roster_template['total_players']
    
    def _add_team_constraints(self, prob, player_vars, constraints):
        """Add team-based constraints"""
        max_per_team = constraints.get('max_players_per_team', 4)
        
        teams = self.players_df['team'].unique()
        for team in teams:
            team_players = self.players_df[self.players_df['team'] == team].index.tolist()
            prob += pulp.lpSum([
                player_vars[idx] for idx in team_players
            ]) <= max_per_team
    
    def _add_stacking_constraints(self, prob, player_vars, constraints):
        """Add QB stacking constraints"""
        qb_stack_min = constraints.get('qb_stack_min', 1)
        qb_stack_max = constraints.get('qb_stack_max', 2)
        bring_back = constraints.get('bring_back_count', 0)
        
        qbs = self.players_df[self.players_df['pos'] == 'QB'].index.tolist()
        
        for qb_idx in qbs:
            qb_team = self.players_df.loc[qb_idx, 'team']
            
            # Get skill position players from same team
            skill_positions = ['WR', 'TE', 'RB']
            same_team_skill = self.players_df[
                (self.players_df['team'] == qb_team) & 
                (self.players_df['pos'].isin(skill_positions))
            ].index.tolist()
            
            if len(same_team_skill) > 0:
                # If QB is selected, must have at least min stack players
                prob += pulp.lpSum([
                    player_vars[idx] for idx in same_team_skill
                ]) >= qb_stack_min * player_vars[qb_idx]
                
                # Cannot exceed max stack players
                prob += pulp.lpSum([
                    player_vars[idx] for idx in same_team_skill
                ]) <= qb_stack_max * player_vars[qb_idx] + qb_stack_max * (1 - player_vars[qb_idx])
            
            # Bring-back constraint (opponent skill players)
            if bring_back > 0:
                qb_opp = self.players_df.loc[qb_idx, 'opp']
                opp_skill = self.players_df[
                    (self.players_df['team'] == qb_opp) & 
                    (self.players_df['pos'].isin(skill_positions))
                ].index.tolist()
                
                if len(opp_skill) > 0:
                    prob += pulp.lpSum([
                        player_vars[idx] for idx in opp_skill
                    ]) >= bring_back * player_vars[qb_idx]
    
    def _add_ownership_constraints(self, prob, player_vars, constraints):
        """Add ownership-based constraints"""
        if 'own%' not in self.players_df.columns:
            return
        
        max_total_ownership = constraints.get('max_total_ownership', 400)
        max_player_exposure = constraints.get('max_player_exposure', 100)
        
        # Total ownership constraint
        prob += pulp.lpSum([
            self.players_df.loc[idx, 'own%'] * player_vars[idx] 
            for idx in player_vars
        ]) <= max_total_ownership
        
        # Individual player exposure (for multi-lineup builds)
        # This is handled at the multi-lineup level
    
    def _add_diversity_constraints(self, prob, player_vars, constraints):
        """Add diversity constraints to avoid similar lineups"""
        previous_lineups = constraints.get('previous_lineups', [])
        min_unique_players = constraints.get('min_unique_players', 3)
        
        for prev_lineup in previous_lineups:
            if 'lineup_df' in prev_lineup:
                prev_player_indices = prev_lineup['lineup_df']['player_idx'].tolist()
                
                # Ensure at least min_unique_players are different
                prob += pulp.lpSum([
                    player_vars[idx] for idx in prev_player_indices
                ]) <= len(prev_player_indices) - min_unique_players