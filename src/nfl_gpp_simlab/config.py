"""Configuration classes for Monte Carlo simulation."""

from dataclasses import dataclass


@dataclass
class MonteCarloConfig:
    """Configuration for Monte Carlo simulation.

    Attributes:
        n_trials: Number of simulation trials to run
        seed: Random seed for reproducibility
        show_progress: Whether to display a progress bar during simulation
        quantiles: List of quantiles to compute in summary statistics
    """

    n_trials: int = 10000
    seed: int = 42
    show_progress: bool = False
    quantiles: list[float] | None = None

    def __post_init__(self) -> None:
        """Initialize default quantiles if not provided."""
        if self.quantiles is None:
            self.quantiles = [0.05, 0.95]
