"""Configuration for Monte Carlo simulations."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulations.

    Attributes:
        n_trials: Number of simulation trials to run
        n_jobs: Number of parallel workers (default: 1). Set to -1 to use all CPUs.
        base_seed: Base random seed for reproducible results (optional)
        show_progress: Whether to show progress bars (auto-disabled when n_jobs > 1)
    """
    n_trials: int = 10000
    n_jobs: int = 1
    base_seed: Optional[int] = None
    show_progress: bool = True

    def __post_init__(self):
        """Post-initialization processing."""
        # Apply environment override for n_jobs if not explicitly set
        env_n_jobs = os.environ.get('NFL_GPP_SIMLAB_N_JOBS')
        if env_n_jobs is not None and self.n_jobs == 1:  # Only override default
            try:
                self.n_jobs = int(env_n_jobs)
            except ValueError:
                # Invalid environment variable, keep default
                pass

        # Disable progress bars when running in parallel to avoid interleaved output
        if self.n_jobs != 1:
            self.show_progress = False

        # Handle n_jobs = -1 (use all CPUs)
        if self.n_jobs == -1:
            self.n_jobs = os.cpu_count() or 1

        # Clamp n_jobs to available CPU count
        max_cpus = os.cpu_count() or 1
        if self.n_jobs > max_cpus:
            self.n_jobs = max_cpus

        # Ensure n_jobs is at least 1
        self.n_jobs = max(1, self.n_jobs)
