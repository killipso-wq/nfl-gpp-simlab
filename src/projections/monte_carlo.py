"""
Monte Carlo simulation engine for NFL projections with rookie fallback policy.
Implements position-calibrated variance and DK scoring per Master Reference.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
import json
from pathlib import Path
import zipfile
import os
from datetime import datetime
import warnings


class MonteCarloSimulator:
    """Monte Carlo simulator for NFL player projections."""
    
    # Position-based variance scaling (temporary until priors are built)
    POSITION_VARIANCE = {
        'QB': 6.5,   # Higher variance for QBs
        'RB': 5.8,   # Moderate variance for RBs
        'WR': 5.2,   # Moderate variance for WRs  
        'TE': 4.8,   # Lower variance for TEs
        'DST': 4.5,  # Lower variance for DST
        'K': 3.5     # Lowest variance for kickers
    }
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize simulator with optional random seed."""
        self.seed = seed
        if seed is not None:
            np.random.seed(seed)
            
        self.sim_results: Optional[pd.DataFrame] = None
        self.metadata: Dict[str, Any] = {}
        
    def simulate_players(self, players_df: pd.DataFrame, n_sims: int = 10000) -> pd.DataFrame:
        """
        Run Monte Carlo simulation for all players.
        
        Args:
            players_df: DataFrame with player data including FPTS column
            n_sims: Number of simulation trials
            
        Returns:
            DataFrame with simulation results and percentiles
        """
        if 'FPTS' not in players_df.columns:
            raise ValueError("Players DataFrame must include FPTS column for simulation")
            
        results = []
        
        for _, player in players_df.iterrows():
            fpts = player['FPTS']
            position = player['POS']
            
            if pd.isna(fpts):
                # Skip players without FPTS
                continue
                
            # Get position-based variance (rookie fallback policy)
            variance = self.POSITION_VARIANCE.get(position, 5.0)
            
            # Generate random samples (normal distribution)
            # Center on site FPTS, scale by position variance
            samples = np.random.normal(fpts, variance, n_sims)
            
            # Clamp at 0 (can't have negative fantasy points)
            samples = np.maximum(samples, 0)
            
            # Calculate percentiles and statistics
            sim_result = {
                'player_id': player['player_id'],
                'PLAYER': player['PLAYER'],
                'POS': position,
                'TEAM': player['TEAM'],
                'site_fpts': fpts,
                'sim_mean': np.mean(samples),
                'sim_std': np.std(samples),
                'floor_p10': np.percentile(samples, 10),
                'p25': np.percentile(samples, 25),
                'p50': np.percentile(samples, 50),
                'p75': np.percentile(samples, 75),
                'ceiling_p90': np.percentile(samples, 90),
                'p95': np.percentile(samples, 95),
                'rookie_fallback': True,  # All players use fallback in MVP
                'samples': samples  # Keep for boom probability calculation
            }
            
            # Add salary if available
            if 'SAL' in player and not pd.isna(player['SAL']):
                sim_result['SAL'] = player['SAL']
                
            results.append(sim_result)
            
        if not results:
            raise ValueError("No players with valid FPTS found for simulation")
            
        # Convert to DataFrame
        sim_df = pd.DataFrame(results)
        
        # Calculate boom probabilities
        sim_df = self._calculate_boom_metrics(sim_df, players_df)
        
        # Store results
        self.sim_results = sim_df
        
        # Remove samples column for output (too large)
        output_df = sim_df.drop('samples', axis=1)
        
        return output_df
        
    def _calculate_boom_metrics(self, sim_df: pd.DataFrame, original_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate boom probabilities and related metrics."""
        
        # Calculate boom thresholds per position (temporary calibration)
        boom_thresholds = {}
        for pos in sim_df['POS'].unique():
            pos_samples = []
            pos_players = sim_df[sim_df['POS'] == pos]
            
            for _, player in pos_players.iterrows():
                pos_samples.extend(player['samples'])
                
            if pos_samples:
                boom_thresholds[pos] = np.percentile(pos_samples, 90)
            else:
                boom_thresholds[pos] = 20.0  # Default fallback
                
        # Store boom thresholds in metadata
        self.metadata['boom_thresholds'] = boom_thresholds
        self.metadata['calibrated_from_current_run'] = True
        
        # Calculate boom metrics for each player
        boom_probs = []
        boom_scores = []
        
        for _, player in sim_df.iterrows():
            pos = player['POS']
            fpts = player['site_fpts']
            samples = player['samples']
            
            # Site boost calculation per Master Reference
            site_boost = max(1.20 * fpts, fpts + 5)
            
            # Boom cut is max of position boom and site boost
            pos_boom = boom_thresholds.get(pos, 20.0)
            boom_cut = max(pos_boom, site_boost)
            
            # Calculate boom probability
            boom_prob = np.mean(samples >= boom_cut) * 100
            boom_probs.append(boom_prob)
            
            # Calculate boom score (1-100 scale)
            # Base score from boom probability, with ownership and value boosts
            boom_score = min(boom_prob, 100)
            
            # Add ownership boost if RST% available
            original_player = original_df[original_df['player_id'] == player['player_id']]
            if not original_player.empty and 'RST%' in original_player.columns:
                rst_pct = original_player.iloc[0]['RST%']
                if pd.notna(rst_pct) and rst_pct <= 10:  # Low ownership boost
                    boom_score = min(boom_score * 1.2, 100)
                    
            # Add value boost if available
            if 'SAL' in player and pd.notna(player['SAL']):
                value_per_1k = (player['sim_mean'] / player['SAL']) * 1000
                if value_per_1k >= 3.0:  # High value boost
                    boom_score = min(boom_score * 1.1, 100)
                    
            boom_scores.append(boom_score)
            
        sim_df['boom_prob'] = boom_probs
        sim_df['boom_score'] = boom_scores
        
        return sim_df
        
    def generate_compare_table(self, sim_df: pd.DataFrame, original_df: pd.DataFrame) -> pd.DataFrame:
        """Generate comparison table with site fields and simulation deltas."""
        
        # Merge simulation results with original site data
        compare_df = original_df.merge(
            sim_df[['player_id', 'sim_mean', 'sim_std', 'floor_p10', 'ceiling_p90', 
                   'boom_prob', 'boom_score', 'rookie_fallback']], 
            on='player_id', 
            how='left'
        )
        
        # Calculate delta metrics
        if 'FPTS' in compare_df.columns:
            compare_df['delta_mean'] = compare_df['sim_mean'] - compare_df['FPTS']
            compare_df['pct_delta'] = (compare_df['delta_mean'] / compare_df['FPTS']) * 100
            
            # Beat site probability (probability sim exceeds site FPTS)
            beat_probs = []
            for _, row in compare_df.iterrows():
                if pd.notna(row['FPTS']) and row['player_id'] in sim_df['player_id'].values:
                    sim_player = sim_df[sim_df['player_id'] == row['player_id']].iloc[0]
                    if 'samples' in sim_player:
                        beat_prob = np.mean(sim_player['samples'] > row['FPTS']) * 100
                        beat_probs.append(beat_prob)
                    else:
                        beat_probs.append(None)
                else:
                    beat_probs.append(None)
                    
            compare_df['beat_site_prob'] = beat_probs
            
        # Calculate value metrics if salary available
        if 'SAL' in compare_df.columns:
            compare_df['value_per_1k'] = (compare_df['sim_mean'] / compare_df['SAL']) * 1000
            compare_df['ceil_per_1k'] = (compare_df['ceiling_p90'] / compare_df['SAL']) * 1000
            
        # Dart flag calculation
        dart_flags = []
        for _, row in compare_df.iterrows():
            is_dart = False
            if 'RST%' in row and pd.notna(row['RST%']) and row['RST%'] <= 5:
                if pd.notna(row['boom_score']) and row['boom_score'] >= 70:
                    is_dart = True
            dart_flags.append(is_dart)
            
        compare_df['dart_flag'] = dart_flags
        
        return compare_df
        
    def generate_diagnostics(self, compare_df: pd.DataFrame) -> pd.DataFrame:
        """Generate diagnostics summary by position and overall."""
        
        if 'FPTS' not in compare_df.columns:
            return pd.DataFrame()  # Can't calculate diagnostics without site FPTS
            
        diagnostics = []
        
        # Calculate for each position
        for pos in compare_df['POS'].unique():
            pos_data = compare_df[
                (compare_df['POS'] == pos) & 
                (compare_df['rookie_fallback'] == False) &  # Exclude rookie fallbacks
                pd.notna(compare_df['FPTS']) & 
                pd.notna(compare_df['sim_mean'])
            ]
            
            if len(pos_data) > 0:
                mae = np.mean(np.abs(pos_data['delta_mean']))
                rmse = np.sqrt(np.mean(pos_data['delta_mean'] ** 2))
                corr = pos_data['FPTS'].corr(pos_data['sim_mean'])
                
                # Coverage calculation (% where site FPTS falls in [p10, p90])
                in_range = (
                    (pos_data['FPTS'] >= pos_data['floor_p10']) & 
                    (pos_data['FPTS'] <= pos_data['ceiling_p90'])
                )
                coverage = np.mean(in_range) * 100 if len(in_range) > 0 else 0
                
                diagnostics.append({
                    'position': pos,
                    'count_total': len(compare_df[compare_df['POS'] == pos]),
                    'count_evaluated': len(pos_data),
                    'count_rookie_fallback': len(compare_df[
                        (compare_df['POS'] == pos) & (compare_df['rookie_fallback'] == True)
                    ]),
                    'mae': mae,
                    'rmse': rmse,
                    'correlation': corr,
                    'coverage_p10_p90': coverage
                })
            else:
                # All players are rookie fallback for this position
                total_count = len(compare_df[compare_df['POS'] == pos])
                diagnostics.append({
                    'position': pos,
                    'count_total': total_count,
                    'count_evaluated': 0,
                    'count_rookie_fallback': total_count,
                    'mae': None,
                    'rmse': None,
                    'correlation': None,
                    'coverage_p10_p90': None
                })
                
        # Overall statistics (excluding rookie fallbacks)
        overall_data = compare_df[
            (compare_df['rookie_fallback'] == False) &
            pd.notna(compare_df['FPTS']) & 
            pd.notna(compare_df['sim_mean'])
        ]
        
        if len(overall_data) > 0:
            overall_mae = np.mean(np.abs(overall_data['delta_mean']))
            overall_rmse = np.sqrt(np.mean(overall_data['delta_mean'] ** 2))
            overall_corr = overall_data['FPTS'].corr(overall_data['sim_mean'])
            
            overall_in_range = (
                (overall_data['FPTS'] >= overall_data['floor_p10']) & 
                (overall_data['FPTS'] <= overall_data['ceiling_p90'])
            )
            overall_coverage = np.mean(overall_in_range) * 100 if len(overall_in_range) > 0 else 0
        else:
            overall_mae = overall_rmse = overall_corr = overall_coverage = None
            
        diagnostics.append({
            'position': 'OVERALL',
            'count_total': len(compare_df),
            'count_evaluated': len(overall_data),
            'count_rookie_fallback': len(compare_df[compare_df['rookie_fallback'] == True]),
            'mae': overall_mae,
            'rmse': overall_rmse,
            'correlation': overall_corr,
            'coverage_p10_p90': overall_coverage
        })
        
        return pd.DataFrame(diagnostics)
        
    def generate_flags(self, compare_df: pd.DataFrame, n_flags: int = 10) -> pd.DataFrame:
        """Generate flags for top deltas and data issues."""
        
        flags = []
        
        # Top absolute deltas
        if 'delta_mean' in compare_df.columns:
            abs_deltas = compare_df.dropna(subset=['delta_mean']).copy()
            abs_deltas['abs_delta'] = abs_deltas['delta_mean'].abs()
            top_abs = abs_deltas.nlargest(n_flags, 'abs_delta')
            
            for _, row in top_abs.iterrows():
                flags.append({
                    'player_id': row['player_id'],
                    'PLAYER': row['PLAYER'],
                    'POS': row['POS'],
                    'flag_type': 'high_abs_delta',
                    'flag_value': row['abs_delta'],
                    'description': f"High absolute delta: {row['delta_mean']:.1f} pts"
                })
                
        # Top percentage deltas
        if 'pct_delta' in compare_df.columns:
            pct_deltas = compare_df.dropna(subset=['pct_delta']).copy()
            pct_deltas['abs_pct_delta'] = pct_deltas['pct_delta'].abs()
            top_pct = pct_deltas.nlargest(n_flags, 'abs_pct_delta')
            
            for _, row in top_pct.iterrows():
                flags.append({
                    'player_id': row['player_id'],
                    'PLAYER': row['PLAYER'],
                    'POS': row['POS'],
                    'flag_type': 'high_pct_delta',
                    'flag_value': row['abs_pct_delta'],
                    'description': f"High percentage delta: {row['pct_delta']:.1f}%"
                })
                
        # Data issues
        for _, row in compare_df.iterrows():
            issues = []
            
            if 'SAL' in row and pd.isna(row['SAL']):
                issues.append("missing_salary")
            if 'RST%' in row and pd.isna(row['RST%']):
                issues.append("missing_ownership")
            if row['POS'] not in ['QB', 'RB', 'WR', 'TE', 'DST', 'K']:
                issues.append("unknown_position")
                
            for issue in issues:
                flags.append({
                    'player_id': row['player_id'],
                    'PLAYER': row['PLAYER'],
                    'POS': row['POS'],
                    'flag_type': 'data_issue',
                    'flag_value': None,
                    'description': issue
                })
                
        return pd.DataFrame(flags)
        
    def save_all_outputs(self, 
                        sim_df: pd.DataFrame, 
                        compare_df: pd.DataFrame, 
                        original_df: pd.DataFrame,
                        output_dir: str,
                        run_metadata: Optional[Dict] = None) -> Dict[str, str]:
        """Save all required output files."""
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        files_created = {}
        
        # 1. sim_players.csv
        sim_output = sim_df[['player_id', 'PLAYER', 'POS', 'TEAM', 'sim_mean', 
                           'floor_p10', 'p75', 'ceiling_p90', 'p95', 'boom_prob', 'rookie_fallback']]
        
        # Add SAL if available
        if 'SAL' in sim_df.columns:
            sim_output = sim_output.merge(
                sim_df[['player_id', 'SAL']], on='player_id', how='left'
            )
            
        sim_file = output_dir / 'sim_players.csv'
        sim_output.to_csv(sim_file, index=False)
        files_created['sim_players'] = str(sim_file)
        
        # 2. compare.csv  
        compare_file = output_dir / 'compare.csv'
        compare_df.to_csv(compare_file, index=False)
        files_created['compare'] = str(compare_file)
        
        # 3. diagnostics_summary.csv
        diagnostics_df = self.generate_diagnostics(compare_df)
        diag_file = output_dir / 'diagnostics_summary.csv'
        diagnostics_df.to_csv(diag_file, index=False)
        files_created['diagnostics'] = str(diag_file)
        
        # 4. flags.csv
        flags_df = self.generate_flags(compare_df)
        flags_file = output_dir / 'flags.csv'
        flags_df.to_csv(flags_file, index=False)
        files_created['flags'] = str(flags_file)
        
        # 5. metadata.json
        metadata = {
            'run_timestamp': datetime.now().isoformat(),
            'seed': self.seed,
            'n_sims': run_metadata.get('n_sims', 10000) if run_metadata else 10000,
            'methodology': 'monte_carlo_pdf',
            'player_count': len(original_df),
            'boom_thresholds': self.metadata.get('boom_thresholds', {}),
            'calibrated_from_current_run': self.metadata.get('calibrated_from_current_run', True)
        }
        
        if run_metadata:
            # Only include JSON-serializable fields from run_metadata
            safe_fields = ['season', 'week', 'players_file', 'n_sims', 'total_players', 
                          'simulated_players', 'column_mapping', 'warnings']
            for field in safe_fields:
                if field in run_metadata:
                    metadata[field] = run_metadata[field]
            
        metadata_file = output_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        files_created['metadata'] = str(metadata_file)
        
        # 6. simulator_outputs.zip
        zip_file = output_dir / 'simulator_outputs.zip'
        with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_key, file_path in files_created.items():
                if file_key != 'zip':  # Don't include the zip in itself
                    zipf.write(file_path, Path(file_path).name)
                    
        files_created['zip'] = str(zip_file)
        
        return files_created