"""Monte Carlo simulator components."""

from typing import Any, Callable, Dict, Optional
import numpy as np
from numpy.typing import NDArray


class MonteCarloConfig:
    """Configuration for Monte Carlo simulation."""
    
    def __init__(self, n_trials: int, random_seed: Optional[int] = None) -> None:
        """Initialize Monte Carlo configuration.
        
        Args:
            n_trials: Number of simulation trials to run
            random_seed: Optional random seed for reproducibility
        """
        self.n_trials = n_trials
        self.random_seed = random_seed


class MonteCarloSimulator:
    """Monte Carlo simulator for NFL projections."""
    
    def __init__(self, config: MonteCarloConfig) -> None:
        """Initialize simulator with configuration.
        
        Args:
            config: Monte Carlo configuration
        """
        self.config = config
        self._rng = np.random.default_rng(config.random_seed)
    
    def simulate(self, trial_fn: Callable[[np.random.Generator], NDArray[Any]]) -> NDArray[Any]:
        """Run Monte Carlo simulation.
        
        Args:
            trial_fn: Function that takes an RNG and returns trial results
            
        Returns:
            Array of simulation results with shape (n_trials, n_metrics)
        """
        results = []
        for _ in range(self.config.n_trials):
            trial_result = trial_fn(self._rng)
            results.append(trial_result)
        
        return np.array(results)
    
    def summarize(self, results: NDArray[Any]) -> Dict[str, NDArray[Any]]:
        """Summarize simulation results.
        
        Args:
            results: Array of simulation results
            
        Returns:
            Dictionary with summary statistics
        """
        return {
            "mean": np.mean(results, axis=0),
            "q05": np.percentile(results, 5, axis=0),
            "q95": np.percentile(results, 95, axis=0),
        }