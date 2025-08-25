"""Core simulation functionality for NFL GPP SimLab."""

import json
import logging
import time
import csv
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import SimulationConfig

logger = logging.getLogger(__name__)


class SimulationResults:
    """Container for simulation results."""
    
    def __init__(self, 
                 sim_players: List[Dict[str, Any]],
                 compare: Optional[List[Dict[str, Any]]] = None,
                 diagnostics: Optional[List[Dict[str, Any]]] = None,
                 flags: Optional[List[Dict[str, Any]]] = None,
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize simulation results.
        
        Args:
            sim_players: Simulated player projections
            compare: Comparison with site projections
            diagnostics: Diagnostic summary statistics
            flags: Flagged outliers and issues
            metadata: Simulation metadata
        """
        self.sim_players = sim_players
        self.compare = compare or []
        self.diagnostics = diagnostics or []
        self.flags = flags or []
        self.metadata = metadata or {}
    
    def save_to_directory(self, output_dir: Path) -> None:
        """Save all results to a directory.
        
        Args:
            output_dir: Directory to save results
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save CSV files
        self._save_csv(output_dir / "sim_players.csv", self.sim_players)
        
        if self.compare:
            self._save_csv(output_dir / "compare.csv", self.compare)
        
        if self.diagnostics:
            self._save_csv(output_dir / "diagnostics_summary.csv", self.diagnostics)
        
        if self.flags:
            self._save_csv(output_dir / "flags.csv", self.flags)
        
        # Save metadata
        metadata_path = output_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(self.metadata, f, indent=2, default=str)
        
        logger.info(f"Results saved to {output_dir}")
    
    def _save_csv(self, filepath: Path, data: List[Dict[str, Any]]) -> None:
        """Save data to CSV file."""
        if not data:
            return
        
        fieldnames = data[0].keys()
        with open(filepath, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)


class NFLSimulator:
    """Main NFL GPP simulation engine."""
    
    def __init__(self, config: SimulationConfig):
        """Initialize simulator with configuration.
        
        Args:
            config: Simulation configuration
        """
        self.config = config
        random.seed(config.base_seed)
        
    def run_simulation(self, 
                      players_data: Optional[List[Dict[str, Any]]] = None,
                      input_file: Optional[Path] = None) -> SimulationResults:
        """Run Monte Carlo simulation.
        
        Args:
            players_data: Player data as list of dictionaries
            input_file: Path to input CSV file
            
        Returns:
            SimulationResults containing all outputs
            
        Raises:
            ValueError: If neither players_data nor input_file provided
        """
        start_time = time.time()
        
        # Load data
        if players_data is not None:
            data = players_data
        elif input_file is not None:
            data = self._load_csv(input_file)
        else:
            raise ValueError("Either players_data or input_file must be provided")
        
        logger.info(f"Starting simulation with {len(data)} players, {self.config.n_trials} trials")
        
        # Basic simulation (placeholder implementation)
        sim_results = self._run_monte_carlo(data)
        
        # Generate summary statistics
        diagnostics = self._compute_diagnostics(sim_results, data)
        flags = self._compute_flags(sim_results, data)
        compare_data = self._create_comparison(sim_results, data)
        
        # Create metadata
        metadata = {
            "n_trials": self.config.n_trials,
            "base_seed": self.config.base_seed,
            "n_jobs": self.config.n_jobs,
            "quantiles": self.config.quantiles,
            "methodology": "monte_carlo_pdf",
            "simulation_time_seconds": time.time() - start_time,
            "n_players": len(data),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }
        
        return SimulationResults(
            sim_players=sim_results,
            compare=compare_data,
            diagnostics=diagnostics,
            flags=flags,
            metadata=metadata
        )
    
    def _load_csv(self, filepath: Path) -> List[Dict[str, Any]]:
        """Load CSV file into list of dictionaries."""
        data = []
        with open(filepath, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                data.append(row)
        return data
    
    def _run_monte_carlo(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Run Monte Carlo simulation on player data.
        
        Args:
            data: Input player data
            
        Returns:
            List of dictionaries with simulation results
        """
        # This is a minimal placeholder implementation
        # In the full implementation, this would use the Monte Carlo methodology
        # described in the research PDFs
        
        results = []
        
        for i, player in enumerate(data):
            result = player.copy()
            
            # Add required columns if missing
            if 'PLAYER' not in result:
                result['PLAYER'] = f"Player_{i}"
            if 'POS' not in result:
                result['POS'] = "QB"
            if 'TEAM' not in result:
                result['TEAM'] = "TM"
            
            # Use site FPTS as baseline if available, otherwise generate placeholder values
            if 'FPTS' in player and player['FPTS']:
                try:
                    baseline_fpts = float(player['FPTS'])
                except (ValueError, TypeError):
                    baseline_fpts = 15.0
            else:
                baseline_fpts = random.uniform(5, 25)
            
            # Generate simulation results
            result['player_id'] = f"player_{i}"
            result['sim_mean'] = max(0, baseline_fpts + random.normalvariate(0, 2))
            
            # Generate quantiles
            for q in self.config.quantiles:
                col_name = f"p{int(q*100)}" if q != 0.5 else "median"
                if q == 0.1:
                    col_name = "floor_p10"
                elif q == 0.9:
                    col_name = "ceiling_p90"
                
                # Generate quantiles with some variance around the mean
                variance = result['sim_mean'] * 0.3  # 30% coefficient of variation
                quantile_value = result['sim_mean'] + random.normalvariate(0, variance) * (q - 0.5) * 2
                result[col_name] = max(0, quantile_value)
            
            # Add boom probability (probability of exceeding 90th percentile)
            result['boom_prob'] = random.uniform(0.05, 0.25)
            
            # Add rookie fallback flag (placeholder)
            result['rookie_fallback'] = False
            
            # Add salary if available in input
            if 'SAL' in player or 'SALARY' in player:
                sal_col = 'SAL' if 'SAL' in player else 'SALARY'
                result['SAL'] = player[sal_col]
            
            results.append(result)
        
        return results
    
    def _compute_diagnostics(self, sim_results: List[Dict[str, Any]], original_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compute diagnostic summary statistics.
        
        Args:
            sim_results: Simulation results
            original_data: Original input data
            
        Returns:
            Diagnostics data
        """
        diagnostics_data = []
        
        # Overall statistics
        site_fpts_values = []
        sim_mean_values = []
        positions = []
        
        for orig, sim in zip(original_data, sim_results):
            if 'FPTS' in orig and orig['FPTS']:
                try:
                    site_fpts = float(orig['FPTS'])
                    sim_mean = sim['sim_mean']
                    pos = orig.get('POS', 'UNK')
                    
                    site_fpts_values.append(site_fpts)
                    sim_mean_values.append(sim_mean)
                    positions.append(pos)
                except (ValueError, TypeError):
                    pass
        
        if site_fpts_values and sim_mean_values:
            # Overall diagnostics
            overall_diag = self._compute_position_diagnostics('ALL', site_fpts_values, sim_mean_values, sim_results)
            diagnostics_data.append(overall_diag)
            
            # Position-specific diagnostics if enabled
            if self.config.enable_position_breakdown:
                unique_positions = set(positions)
                for pos in unique_positions:
                    pos_site_fpts = []
                    pos_sim_mean = []
                    pos_results = []
                    
                    for i, p in enumerate(positions):
                        if p == pos:
                            pos_site_fpts.append(site_fpts_values[i])
                            pos_sim_mean.append(sim_mean_values[i])
                            # Find corresponding sim result
                            for sim in sim_results:
                                if sim.get('POS') == pos and len(pos_results) == len(pos_site_fpts) - 1:
                                    pos_results.append(sim)
                                    break
                    
                    if len(pos_site_fpts) >= 2:  # Need at least 2 players for meaningful stats
                        pos_diag = self._compute_position_diagnostics(pos, pos_site_fpts, pos_sim_mean, pos_results)
                        diagnostics_data.append(pos_diag)
        else:
            # Fallback when no FPTS data available
            diagnostics_data.append({
                'position': 'ALL',
                'mae': 0.0,
                'rmse': 0.0,
                'correlation': 0.0,
                'coverage_p10_p90': 0.0,
                'count_total': len(sim_results),
                'count_rookies_excluded': len([r for r in sim_results if not r['rookie_fallback']]),
            })
        
        return diagnostics_data
    
    def _compute_position_diagnostics(self, position: str, site_fpts: List[float], 
                                    sim_mean: List[float], sim_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compute diagnostics for a specific position.
        
        Args:
            position: Position name ('ALL' for overall)
            site_fpts: Site fantasy points
            sim_mean: Simulated mean points
            sim_results: Simulation results for this position
            
        Returns:
            Dictionary with diagnostic metrics
        """
        n = len(site_fpts)
        
        # Basic error metrics
        mae = sum(abs(s - f) for s, f in zip(sim_mean, site_fpts)) / n
        rmse = (sum((s - f) ** 2 for s, f in zip(sim_mean, site_fpts)) / n) ** 0.5
        
        # Simple correlation approximation (placeholder)
        mean_sim = sum(sim_mean) / n
        mean_site = sum(site_fpts) / n
        
        if n > 1:
            numerator = sum((s - mean_sim) * (f - mean_site) for s, f in zip(sim_mean, site_fpts))
            denom_sim = sum((s - mean_sim) ** 2 for s in sim_mean) ** 0.5
            denom_site = sum((f - mean_site) ** 2 for f in site_fpts) ** 0.5
            
            if denom_sim > 0 and denom_site > 0:
                correlation = numerator / (denom_sim * denom_site)
            else:
                correlation = 0.0
        else:
            correlation = 0.0
        
        # Coverage analysis
        coverage_metrics = {}
        if self.config.enable_advanced_metrics:
            for lower_q, upper_q in self.config.coverage_quantiles:
                coverage_key = f"coverage_p{int(lower_q*100)}_p{int(upper_q*100)}"
                
                # Count how many site values fall within the quantile range
                in_range_count = 0
                for i, site_val in enumerate(site_fpts):
                    if i < len(sim_results):
                        sim_result = sim_results[i]
                        lower_key = f"p{int(lower_q*100)}" if lower_q != 0.1 else "floor_p10"
                        upper_key = f"p{int(upper_q*100)}" if upper_q != 0.9 else "ceiling_p90"
                        
                        if lower_key in sim_result and upper_key in sim_result:
                            lower_val = sim_result[lower_key]
                            upper_val = sim_result[upper_key]
                            if lower_val <= site_val <= upper_val:
                                in_range_count += 1
                
                coverage_metrics[coverage_key] = in_range_count / n if n > 0 else 0.0
        
        # Default coverage (for backward compatibility)
        default_coverage = coverage_metrics.get("coverage_p10_p90", 0.8)
        
        diagnostics = {
            'position': position,
            'mae': mae,
            'rmse': rmse,
            'correlation': correlation,
            'coverage_p10_p90': default_coverage,
            'count_total': len(sim_results),
            'count_rookies_excluded': len([r for r in sim_results if not r['rookie_fallback']]),
        }
        
        # Add advanced metrics if enabled
        if self.config.enable_advanced_metrics:
            diagnostics.update(coverage_metrics)
            
            # Additional advanced metrics
            diagnostics.update({
                'mean_absolute_percentage_error': (mae / (sum(site_fpts) / n)) * 100 if sum(site_fpts) > 0 else 0,
                'bias': sum(sim_mean) / n - sum(site_fpts) / n,
                'median_absolute_error': sorted([abs(s - f) for s, f in zip(sim_mean, site_fpts)])[n // 2] if n > 0 else 0,
                'r_squared': correlation ** 2 if correlation != 0 else 0,
            })
            
            # Risk metrics
            if len(sim_mean) > 1:
                sim_std = (sum((s - mean_sim) ** 2 for s in sim_mean) / (n - 1)) ** 0.5
                site_std = (sum((f - mean_site) ** 2 for f in site_fpts) / (n - 1)) ** 0.5
                
                diagnostics.update({
                    'volatility_ratio': sim_std / site_std if site_std > 0 else 1.0,
                    'prediction_std': sim_std,
                    'actual_std': site_std,
                })
        
        return diagnostics
    
    def _compute_flags(self, sim_results: List[Dict[str, Any]], original_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Compute flags for outliers and issues.
        
        Args:
            sim_results: Simulation results
            original_data: Original input data
            
        Returns:
            Flags data
        """
        flags_data = []
        
        # Check for large discrepancies if site FPTS available
        deltas = []
        for orig, sim in zip(original_data, sim_results):
            if 'FPTS' in orig and orig['FPTS']:
                try:
                    site_fpts = float(orig['FPTS'])
                    sim_mean = sim['sim_mean']
                    delta = sim_mean - site_fpts
                    deltas.append((delta, sim['player_id']))
                except (ValueError, TypeError):
                    pass
        
        if deltas:
            # Find largest absolute deltas
            deltas.sort(key=lambda x: abs(x[0]), reverse=True)
            for i, (delta, player_id) in enumerate(deltas[:3]):  # Top 3 largest deltas
                flags_data.append({
                    'player_id': player_id,
                    'flag_type': 'large_delta',
                    'description': f"Large projection difference: {delta:.2f}",
                    'value': delta,
                })
        
        # Check for missing data
        required_cols = ['PLAYER', 'POS', 'TEAM']
        for i, orig in enumerate(original_data):
            for col in required_cols:
                if col not in orig or not orig[col]:
                    flags_data.append({
                        'player_id': sim_results[i]['player_id'],
                        'flag_type': 'missing_data',
                        'description': f"Missing {col}",
                        'value': None,
                    })
        
        if not flags_data:
            # Return empty flag
            flags_data.append({
                'player_id': 'none',
                'flag_type': 'no_flags',
                'description': 'No flags generated',
                'value': None,
            })
        
        return flags_data
    
    def _create_comparison(self, sim_results: List[Dict[str, Any]], original_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Create comparison data joining simulation with site data.
        
        Args:
            sim_results: Simulation results
            original_data: Original input data
            
        Returns:
            Comparison data
        """
        compare_data = []
        
        for orig, sim in zip(original_data, sim_results):
            compare_row = sim.copy()
            
            # Add site data if available
            if 'FPTS' in orig and orig['FPTS']:
                try:
                    site_fpts = float(orig['FPTS'])
                    compare_row['site_fpts'] = site_fpts
                    compare_row['delta_mean'] = sim['sim_mean'] - site_fpts
                    
                    # Avoid division by zero
                    site_fpts_safe = site_fpts if site_fpts != 0 else 1
                    compare_row['pct_delta'] = (compare_row['delta_mean'] / site_fpts_safe) * 100
                    
                    # Beat site probability (placeholder)
                    compare_row['beat_site_prob'] = random.uniform(0.3, 0.7)
                except (ValueError, TypeError):
                    pass
            
            # Value metrics
            if 'SAL' in compare_row:
                try:
                    sal = float(compare_row['SAL']) if compare_row['SAL'] else 1000
                    sal_safe = sal if sal != 0 else 1000
                    compare_row['value_per_1k'] = (sim['sim_mean'] / sal_safe) * 1000
                    
                    if 'ceiling_p90' in sim:
                        compare_row['ceil_per_1k'] = (sim['ceiling_p90'] / sal_safe) * 1000
                except (ValueError, TypeError):
                    pass
            
            # Add site value if available
            if 'VAL' in orig:
                compare_row['site_val'] = orig['VAL']
            
            # Add ownership if available
            own_pct = 50  # Default ownership
            if 'RST%' in orig or 'OWN' in orig:
                own_col = 'RST%' if 'RST%' in orig else 'OWN'
                compare_row['RST%'] = orig[own_col]
                try:
                    own_pct = float(orig[own_col])
                except (ValueError, TypeError):
                    pass
            
            # Boom score (1-100 scale)
            compare_row['boom_score'] = sim['boom_prob'] * 100
            
            # Dart flag (high boom, low ownership)
            compare_row['dart_flag'] = (compare_row['boom_score'] > 70) and (own_pct < 10)
            
            # Advanced risk metrics if enabled
            if self.config.enable_risk_metrics:
                self._add_risk_metrics(compare_row, sim, orig)
            
            compare_data.append(compare_row)
        
        return compare_data
    
    def _add_risk_metrics(self, compare_row: Dict[str, Any], sim: Dict[str, Any], orig: Dict[str, Any]) -> None:
        """Add advanced risk metrics to comparison row.
        
        Args:
            compare_row: Row being built for comparison data
            sim: Simulation results for this player
            orig: Original input data for this player
        """
        # Calculate volatility (using quantile spread as proxy)
        if 'floor_p10' in sim and 'ceiling_p90' in sim:
            volatility = sim['ceiling_p90'] - sim['floor_p10']
            compare_row['volatility_80pct'] = volatility
            
            # Risk-adjusted value (Sharpe-like ratio)
            if volatility > 0:
                compare_row['risk_adjusted_value'] = sim['sim_mean'] / volatility
            else:
                compare_row['risk_adjusted_value'] = sim['sim_mean']
        
        # Downside risk (below floor)
        if 'floor_p10' in sim:
            downside_risk = max(0, sim['floor_p10'] - sim['sim_mean'])
            compare_row['downside_risk'] = downside_risk
        
        # Upside potential ratio
        if 'ceiling_p90' in sim and 'floor_p10' in sim:
            upside = sim['ceiling_p90'] - sim['sim_mean']
            downside = sim['sim_mean'] - sim['floor_p10']
            if downside > 0:
                compare_row['upside_downside_ratio'] = upside / downside
            else:
                compare_row['upside_downside_ratio'] = upside
        
        # Ownership-adjusted value if ownership available
        if 'RST%' in compare_row:
            try:
                own_pct = float(compare_row['RST%'])
                if own_pct > 0:
                    # Higher value for lower ownership (contrarian value)
                    ownership_factor = 100 / max(own_pct, 1)  # Avoid division by zero
                    compare_row['ownership_adjusted_value'] = sim['sim_mean'] * (ownership_factor / 100)
                else:
                    compare_row['ownership_adjusted_value'] = sim['sim_mean']
            except (ValueError, TypeError):
                compare_row['ownership_adjusted_value'] = sim['sim_mean']
        
        # Salary efficiency metrics
        if 'SAL' in compare_row:
            try:
                sal = float(compare_row['SAL']) if compare_row['SAL'] else 1000
                if sal > 0:
                    # Points per dollar
                    compare_row['points_per_dollar'] = sim['sim_mean'] / sal
                    
                    # Ceiling points per dollar
                    if 'ceiling_p90' in sim:
                        compare_row['ceiling_points_per_dollar'] = sim['ceiling_p90'] / sal
                    
                    # Risk-adjusted points per dollar
                    if 'volatility_80pct' in compare_row and compare_row['volatility_80pct'] > 0:
                        risk_adj_points = sim['sim_mean'] / compare_row['volatility_80pct']
                        compare_row['risk_adj_points_per_dollar'] = risk_adj_points / sal
            except (ValueError, TypeError):
                pass
        
        # Confidence intervals
        if self.config.enable_advanced_metrics:
            # Add confidence level for projection
            site_fpts = None
            if 'site_fpts' in compare_row:
                site_fpts = compare_row['site_fpts']
            
            if site_fpts is not None and 'floor_p10' in sim and 'ceiling_p90' in sim:
                # Check if site projection falls within our confidence interval
                in_ci_80 = sim['floor_p10'] <= site_fpts <= sim['ceiling_p90']
                compare_row['site_in_ci_80pct'] = in_ci_80
                
                # Distance from CI bounds
                if site_fpts < sim['floor_p10']:
                    compare_row['ci_distance'] = site_fpts - sim['floor_p10']  # Negative
                elif site_fpts > sim['ceiling_p90']:
                    compare_row['ci_distance'] = site_fpts - sim['ceiling_p90']  # Positive
                else:
                    compare_row['ci_distance'] = 0.0  # Inside CI