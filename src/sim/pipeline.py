"""
Pipeline to orchestrate N simulations and generate player distributions and lineup pools.

This module implements the full simulation pipeline as outlined in the 
Realistic NFL Monte Carlo Simulation PDF methodology.
"""

import os
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import time

from .sampler import MonteCarloSampler, SamplingConfig, create_default_config


@dataclass
class PipelineConfig:
    """Configuration for the simulation pipeline."""
    # Simulation parameters
    n_simulations: int = 10000
    seed: int = 42
    volatility_multiplier: float = 1.0
    correlation_strength: float = 1.0
    include_correlations: bool = True
    
    # Output parameters
    output_dir: str = "data/sim_week"
    include_lineup_pool: bool = True
    lineup_pool_size: int = 1000
    min_salary_left: int = 200
    max_salary_left: int = 1000
    
    # Processing parameters
    boom_thresholds: Dict[str, float] = None
    value_calculation: bool = True
    diagnostics: bool = True


@dataclass
class PipelineMetadata:
    """Metadata for a pipeline run."""
    run_id: str
    timestamp: str
    season: int
    week: int
    n_simulations: int
    seed: int
    n_players: int
    n_games: int
    methodology: str = "monte_carlo_pdf"
    git_commit: str = ""
    config: Dict = None


class SimulationPipeline:
    """
    Complete simulation pipeline for NFL fantasy projections.
    
    Orchestrates the full process from player/game data through Monte Carlo
    simulation to final outputs including player distributions and lineup pools.
    """
    
    def __init__(self, config: Optional[PipelineConfig] = None):
        """
        Initialize the simulation pipeline.
        
        Args:
            config: Pipeline configuration
        """
        self.config = config or PipelineConfig()
        
        # Initialize boom thresholds if not provided
        if self.config.boom_thresholds is None:
            self.config.boom_thresholds = {
                'QB': 25.0,
                'RB': 20.0,
                'WR': 18.0,
                'TE': 15.0,
                'DST': 12.0
            }
        
        # Initialize sampler
        sampling_config = create_default_config(
            n_simulations=self.config.n_simulations,
            seed=self.config.seed
        )
        sampling_config.volatility_multiplier = self.config.volatility_multiplier
        sampling_config.correlation_strength = self.config.correlation_strength
        sampling_config.include_correlations = self.config.include_correlations
        
        self.sampler = MonteCarloSampler(sampling_config)
    
    def run_full_pipeline(self, players_df: pd.DataFrame, 
                         games_df: Optional[pd.DataFrame] = None,
                         season: int = 2024, week: int = 1) -> Tuple[str, Dict]:
        """
        Run the complete simulation pipeline.
        
        Args:
            players_df: DataFrame with player data
            games_df: DataFrame with game data (optional)
            season: Season year
            week: Week number
            
        Returns:
            Tuple of (output_directory, metadata_dict)
        """
        print(f"Starting NFL Monte Carlo simulation pipeline for {season} Week {week}")
        print(f"Players: {len(players_df)}, Simulations: {self.config.n_simulations}")
        
        start_time = time.time()
        
        # Generate run ID and setup output directory
        run_id = self._generate_run_id(season, week)
        output_dir = os.path.join(self.config.output_dir, run_id)
        os.makedirs(output_dir, exist_ok=True)
        
        # Prepare data
        players_list = self._prepare_players_data(players_df)
        games_list = self._prepare_games_data(games_df, players_df) if games_df is not None else self._infer_games_from_players(players_df)
        
        print(f"Prepared {len(players_list)} players and {len(games_list)} games")
        
        # Run simulations
        print("Running Monte Carlo simulations...")
        sim_results = self.sampler.run_simulation(players_list, games_list)
        
        # Generate summary statistics
        print("Generating player statistics...")
        sim_players_df = self.sampler.generate_summary_statistics(sim_results, players_list)
        
        # Add derived metrics
        sim_players_df = self._add_derived_metrics(sim_players_df, players_df)
        
        # Generate comparison with site projections
        print("Generating comparison analysis...")
        compare_df = self._generate_comparison_analysis(sim_players_df, players_df)
        
        # Generate diagnostics
        diagnostics_df = None
        if self.config.diagnostics:
            print("Generating diagnostics...")
            diagnostics_df = self._generate_diagnostics(sim_players_df, players_df)
        
        # Generate flags for outliers
        print("Generating flags...")
        flags_df = self._generate_flags(sim_players_df, compare_df)
        
        # Generate lineup pool if requested
        lineup_pool_df = None
        if self.config.include_lineup_pool:
            print(f"Generating lineup pool ({self.config.lineup_pool_size} lineups)...")
            lineup_pool_df = self._generate_lineup_pool(sim_results, players_df)
        
        # Create metadata
        metadata = PipelineMetadata(
            run_id=run_id,
            timestamp=datetime.now().isoformat(),
            season=season,
            week=week,
            n_simulations=self.config.n_simulations,
            seed=self.config.seed,
            n_players=len(players_list),
            n_games=len(games_list),
            git_commit=self._get_git_commit(),
            config=asdict(self.config)
        )
        
        # Save all outputs
        print("Saving outputs...")
        self._save_outputs(
            output_dir, sim_players_df, compare_df, diagnostics_df, 
            flags_df, lineup_pool_df, metadata
        )
        
        elapsed = time.time() - start_time
        print(f"Pipeline completed in {elapsed:.2f} seconds")
        print(f"Outputs saved to: {output_dir}")
        
        return output_dir, asdict(metadata)
    
    def _generate_run_id(self, season: int, week: int) -> str:
        """Generate a unique run ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{season}_w{week:02d}_{timestamp}"
    
    def _prepare_players_data(self, players_df: pd.DataFrame) -> List[Dict]:
        """Convert players DataFrame to list of dictionaries."""
        # Standardize column names
        column_mapping = {
            'PLAYER': 'name',
            'POS': 'position',
            'TEAM': 'team',
            'OPP': 'opponent',
            'SAL': 'salary',
            'FPTS': 'site_projection',
            'RST%': 'ownership',
            'O/U': 'total',
            'SPRD': 'spread'
        }
        
        df = players_df.copy()
        
        # Apply column mapping
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]
        
        # Generate player IDs if not present
        if 'player_id' not in df.columns:
            df['player_id'] = df.apply(self._generate_player_id, axis=1)
        
        # Convert to list of dictionaries
        players_list = df.to_dict('records')
        
        # Clean and validate each player
        for player in players_list:
            self._clean_player_data(player)
        
        return players_list
    
    def _prepare_games_data(self, games_df: pd.DataFrame, 
                           players_df: pd.DataFrame) -> List[Dict]:
        """Convert games DataFrame to list of dictionaries."""
        return games_df.to_dict('records')
    
    def _infer_games_from_players(self, players_df: pd.DataFrame) -> List[Dict]:
        """Infer games from player team/opponent data."""
        games = []
        seen_matchups = set()
        
        for _, player in players_df.iterrows():
            team = player.get('team', player.get('TEAM', ''))
            opponent = player.get('opponent', player.get('OPP', ''))
            
            if not team or not opponent:
                continue
            
            # Create consistent game_id (alphabetical order)
            teams = sorted([team, opponent])
            game_id = f"{teams[1]}@{teams[0]}"  # away@home
            
            if game_id not in seen_matchups:
                seen_matchups.add(game_id)
                
                # Determine home/away (second team alphabetically is home)
                home_team = teams[0]
                away_team = teams[1]
                
                game_data = {
                    'game_id': game_id,
                    'home_team': home_team,
                    'away_team': away_team,
                    'total': player.get('total', player.get('O/U')),
                    'spread': player.get('spread', player.get('SPRD')),
                    'weather': None,
                    'venue_type': 'outdoor'
                }
                
                games.append(game_data)
        
        return games
    
    def _generate_player_id(self, row) -> str:
        """Generate a standardized player ID."""
        name = row.get('name', row.get('PLAYER', ''))
        team = row.get('team', row.get('TEAM', ''))
        position = row.get('position', row.get('POS', ''))
        
        # Normalize name
        normalized_name = self._normalize_name(name)
        
        return f"{team}_{position}_{normalized_name}"
    
    def _normalize_name(self, name: str) -> str:
        """Normalize a player name for ID generation."""
        if not name:
            return "UNKNOWN"
        
        # Convert to uppercase and remove punctuation
        normalized = name.upper()
        normalized = ''.join(c for c in normalized if c.isalnum() or c.isspace())
        
        # Remove suffixes
        suffixes = ['JR', 'SR', 'II', 'III', 'IV', 'V']
        words = normalized.split()
        words = [w for w in words if w not in suffixes]
        
        # Join with underscores
        return '_'.join(words)
    
    def _clean_player_data(self, player: Dict):
        """Clean and validate player data."""
        # Ensure required fields
        player.setdefault('name', 'Unknown')
        player.setdefault('team', 'UNK')
        player.setdefault('position', 'WR')
        player.setdefault('salary', 0.0)
        player.setdefault('site_projection', 0.0)
        
        # Convert types
        if 'salary' in player:
            try:
                player['salary'] = float(player['salary'])
            except (ValueError, TypeError):
                player['salary'] = 0.0
        
        if 'site_projection' in player:
            try:
                player['site_projection'] = float(player['site_projection'])
            except (ValueError, TypeError):
                player['site_projection'] = 0.0
        
        # Clean ownership percentage
        if 'ownership' in player and player['ownership']:
            try:
                ownership = float(player['ownership'])
                # Convert to fraction if it looks like a percentage
                if ownership > 1.0:
                    ownership = ownership / 100.0
                player['ownership'] = ownership
            except (ValueError, TypeError):
                player['ownership'] = 0.0
    
    def _add_derived_metrics(self, sim_players_df: pd.DataFrame, 
                           players_df: pd.DataFrame) -> pd.DataFrame:
        """Add derived metrics like boom probability, value calculations."""
        df = sim_players_df.copy()
        
        # Boom probability and scores
        for _, row in df.iterrows():
            position = row['position']
            boom_threshold = self.config.boom_thresholds.get(position, 18.0)
            
            # Boom metrics already calculated in sampler, but add boom_score if missing
            if 'boom_score' not in df.columns:
                df.loc[df.index == row.name, 'boom_score'] = row['p75']  # Fallback
        
        # Value calculations if salary is available
        if self.config.value_calculation and 'salary' in df.columns:
            df['value_per_1k'] = np.where(
                df['salary'] > 0,
                (df['sim_mean'] / df['salary']) * 1000,
                0
            )
            df['ceil_per_1k'] = np.where(
                df['salary'] > 0,
                (df['p90'] / df['salary']) * 1000,
                0
            )
        
        # Dart flag (high ceiling relative to salary)
        if 'salary' in df.columns:
            df['dart_flag'] = (
                (df['p90'] / df['sim_mean'] > 2.0) & 
                (df['salary'] < 6000) &
                (df['sim_mean'] > 5.0)
            ).astype(int)
        
        return df
    
    def _generate_comparison_analysis(self, sim_players_df: pd.DataFrame,
                                    players_df: pd.DataFrame) -> pd.DataFrame:
        """Generate comparison between simulated and site projections."""
        # Merge with original data to get site projections
        compare_df = sim_players_df.copy()
        
        # Add comparison metrics (already calculated in sampler for most)
        if 'site_projection' in compare_df.columns:
            # Additional comparison metrics
            compare_df['coverage_p10_p90'] = (
                (compare_df['site_projection'] >= compare_df['p10']) &
                (compare_df['site_projection'] <= compare_df['p90'])
            ).astype(int)
            
            # Value over/under site
            compare_df['value_vs_site'] = compare_df['sim_mean'] - compare_df['site_projection']
        
        return compare_df
    
    def _generate_diagnostics(self, sim_players_df: pd.DataFrame,
                            players_df: pd.DataFrame) -> pd.DataFrame:
        """Generate diagnostic summary by position."""
        diagnostics = []
        
        # Overall diagnostics
        overall_stats = self._calculate_diagnostic_stats(sim_players_df, "ALL")
        diagnostics.append(overall_stats)
        
        # By position
        for position in sim_players_df['position'].unique():
            pos_df = sim_players_df[sim_players_df['position'] == position]
            pos_stats = self._calculate_diagnostic_stats(pos_df, position)
            diagnostics.append(pos_stats)
        
        return pd.DataFrame(diagnostics)
    
    def _calculate_diagnostic_stats(self, df: pd.DataFrame, group_name: str) -> Dict:
        """Calculate diagnostic statistics for a group."""
        valid_comparisons = df[(df['site_projection'] > 0) & (df['site_projection'].notna())]
        
        stats = {
            'group': group_name,
            'n_total': len(df),
            'n_with_site_proj': len(valid_comparisons),
            'mean_sim_mean': df['sim_mean'].mean(),
            'mean_site_proj': valid_comparisons['site_projection'].mean() if len(valid_comparisons) > 0 else 0,
            'mae': 0,
            'rmse': 0,
            'correlation': 0,
            'coverage_p10_p90': 0
        }
        
        if len(valid_comparisons) > 1:
            # Calculate error metrics
            errors = valid_comparisons['sim_mean'] - valid_comparisons['site_projection']
            stats['mae'] = np.mean(np.abs(errors))
            stats['rmse'] = np.sqrt(np.mean(errors ** 2))
            
            # Correlation
            stats['correlation'] = np.corrcoef(
                valid_comparisons['sim_mean'], 
                valid_comparisons['site_projection']
            )[0, 1]
            
            # Coverage
            if 'coverage_p10_p90' in valid_comparisons.columns:
                stats['coverage_p10_p90'] = valid_comparisons['coverage_p10_p90'].mean()
        
        return stats
    
    def _generate_flags(self, sim_players_df: pd.DataFrame,
                       compare_df: pd.DataFrame) -> pd.DataFrame:
        """Generate flags for outliers and data issues."""
        flags = []
        
        # Large absolute deltas
        if 'vs_site_delta' in compare_df.columns:
            large_deltas = compare_df[
                np.abs(compare_df['vs_site_delta']) > 5.0
            ].copy()
            
            for _, row in large_deltas.iterrows():
                flags.append({
                    'player_id': row['player_id'],
                    'name': row['name'],
                    'team': row['team'],
                    'position': row['position'],
                    'flag_type': 'large_delta',
                    'flag_value': row['vs_site_delta'],
                    'description': f"Large difference vs site projection ({row['vs_site_delta']:.1f})"
                })
        
        # High volatility players
        high_vol = sim_players_df[
            (sim_players_df['sim_std'] / sim_players_df['sim_mean']) > 0.8
        ].copy()
        
        for _, row in high_vol.iterrows():
            flags.append({
                'player_id': row['player_id'],
                'name': row['name'],
                'team': row['team'],
                'position': row['position'],
                'flag_type': 'high_volatility',
                'flag_value': row['sim_std'] / row['sim_mean'],
                'description': f"High volatility (CV={row['sim_std']/row['sim_mean']:.2f})"
            })
        
        # Missing data flags
        for _, row in sim_players_df.iterrows():
            if row['salary'] == 0:
                flags.append({
                    'player_id': row['player_id'],
                    'name': row['name'],
                    'team': row['team'],
                    'position': row['position'],
                    'flag_type': 'missing_salary',
                    'flag_value': 0,
                    'description': "Missing salary data"
                })
        
        return pd.DataFrame(flags)
    
    def _generate_lineup_pool(self, sim_results, players_df: pd.DataFrame) -> pd.DataFrame:
        """Generate a pool of optimized lineups from simulation results."""
        # Simplified lineup generation - would be more sophisticated in practice
        # This is a placeholder implementation
        
        lineups = []
        
        # Sample from simulation results
        for i in range(min(self.config.lineup_pool_size, len(sim_results))):
            result = sim_results[i]
            
            # Create a simple lineup by selecting top scorers from this simulation
            # (Real implementation would use optimization with constraints)
            scores = [(pid, score) for pid, score in result.player_scores.items()]
            scores.sort(key=lambda x: x[1], reverse=True)
            
            # Simple lineup construction (1 QB, 2 RB, 3 WR, 1 TE, 1 DST)
            lineup = {
                'lineup_id': i + 1,
                'sim_id': result.sim_id,
                'total_salary': 0,
                'projected_score': 0,
                'QB': '',
                'RB1': '',
                'RB2': '',
                'WR1': '',
                'WR2': '',
                'WR3': '',
                'TE': '',
                'DST': ''
            }
            
            # This is a very simplified selection - real implementation would be much more complex
            lineups.append(lineup)
        
        return pd.DataFrame(lineups)
    
    def _save_outputs(self, output_dir: str, sim_players_df: pd.DataFrame,
                     compare_df: pd.DataFrame, diagnostics_df: Optional[pd.DataFrame],
                     flags_df: pd.DataFrame, lineup_pool_df: Optional[pd.DataFrame],
                     metadata: PipelineMetadata):
        """Save all pipeline outputs."""
        
        # Save main outputs
        sim_players_df.to_csv(os.path.join(output_dir, "sim_players.csv"), index=False)
        compare_df.to_csv(os.path.join(output_dir, "compare.csv"), index=False)
        flags_df.to_csv(os.path.join(output_dir, "flags.csv"), index=False)
        
        if diagnostics_df is not None:
            diagnostics_df.to_csv(os.path.join(output_dir, "diagnostics_summary.csv"), index=False)
        
        if lineup_pool_df is not None:
            lineup_pool_df.to_csv(os.path.join(output_dir, "lineup_pool.csv"), index=False)
        
        # Save metadata
        with open(os.path.join(output_dir, "metadata.json"), 'w') as f:
            json.dump(asdict(metadata), f, indent=2)
        
        print(f"Saved outputs:")
        print(f"  - sim_players.csv ({len(sim_players_df)} players)")
        print(f"  - compare.csv ({len(compare_df)} players)")
        print(f"  - flags.csv ({len(flags_df)} flags)")
        if diagnostics_df is not None:
            print(f"  - diagnostics_summary.csv ({len(diagnostics_df)} groups)")
        if lineup_pool_df is not None:
            print(f"  - lineup_pool.csv ({len(lineup_pool_df)} lineups)")
        print(f"  - metadata.json")
    
    def _get_git_commit(self) -> str:
        """Get current git commit hash."""
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'], 
                capture_output=True, text=True, cwd=os.path.dirname(__file__)
            )
            return result.stdout.strip()[:8] if result.returncode == 0 else "unknown"
        except:
            return "unknown"


def create_default_pipeline_config() -> PipelineConfig:
    """Create a default pipeline configuration."""
    return PipelineConfig(
        n_simulations=10000,
        seed=42,
        volatility_multiplier=1.0,
        correlation_strength=1.0,
        include_correlations=True,
        output_dir="data/sim_week",
        include_lineup_pool=False,  # Disabled by default for WIP
        lineup_pool_size=1000,
        boom_thresholds={
            'QB': 25.0,
            'RB': 20.0,
            'WR': 18.0,
            'TE': 15.0,
            'DST': 12.0
        },
        value_calculation=True,
        diagnostics=True
    )