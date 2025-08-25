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
        # Placeholder diagnostics
        diagnostics_data = []
        
        # Overall statistics
        site_fpts_values = []
        sim_mean_values = []
        
        for orig, sim in zip(original_data, sim_results):
            if 'FPTS' in orig and orig['FPTS']:
                try:
                    site_fpts = float(orig['FPTS'])
                    sim_mean = sim['sim_mean']
                    site_fpts_values.append(site_fpts)
                    sim_mean_values.append(sim_mean)
                except (ValueError, TypeError):
                    pass
        
        if site_fpts_values and sim_mean_values:
            # Simple MAE calculation
            mae = sum(abs(s - f) for s, f in zip(sim_mean_values, site_fpts_values)) / len(site_fpts_values)
            # Simple RMSE calculation
            rmse = (sum((s - f) ** 2 for s, f in zip(sim_mean_values, site_fpts_values)) / len(site_fpts_values)) ** 0.5
            # Simple correlation approximation
            correlation = 0.7  # Placeholder
        else:
            mae = rmse = correlation = 0.0
        
        diagnostics_data.append({
            'position': 'ALL',
            'mae': mae,
            'rmse': rmse,
            'correlation': correlation,
            'coverage_p10_p90': 0.8,  # Placeholder
            'count_total': len(sim_results),
            'count_rookies_excluded': len([r for r in sim_results if not r['rookie_fallback']]),
        })
        
        return diagnostics_data
    
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
            if 'RST%' in orig or 'OWN' in orig:
                own_col = 'RST%' if 'RST%' in orig else 'OWN'
                compare_row['RST%'] = orig[own_col]
            
            # Boom score (1-100 scale)
            compare_row['boom_score'] = sim['boom_prob'] * 100
            
            # Dart flag (high boom, low ownership)
            own_pct = 50  # Default ownership
            if 'RST%' in compare_row:
                try:
                    own_pct = float(compare_row['RST%'])
                except (ValueError, TypeError):
                    pass
            
            compare_row['dart_flag'] = (compare_row['boom_score'] > 70) and (own_pct < 10)
            
            compare_data.append(compare_row)
        
        return compare_data