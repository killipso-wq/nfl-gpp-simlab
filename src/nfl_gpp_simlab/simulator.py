"""Monte Carlo simulator implementation."""

import logging

import numpy as np

from .config import MonteCarloConfig

logger = logging.getLogger(__name__)


class MonteCarloSimulator:
    """Monte Carlo simulator for NFL fantasy football projections."""

    def __init__(self, config: MonteCarloConfig) -> None:
        """Initialize the simulator with configuration.

        Args:
            config: Configuration object for the simulation
        """
        self.config = config
        self._tqdm_warned = False

    def simulate(self, base_projections: dict[str, float]) -> dict[str, list[float]]:
        """Run Monte Carlo simulation on base projections.

        Args:
            base_projections: Dictionary mapping player names to base projections

        Returns:
            Dictionary mapping player names to lists of simulated outcomes
        """
        np.random.seed(self.config.seed)

        results = {}
        # Note: In this simple implementation, we use vectorized operations
        # so there's no per-trial loop to show progress on. A real implementation
        # might have per-trial logic where tqdm would be more useful.
        if self.config.show_progress:
            try:
                from tqdm import tqdm  # type: ignore[import-untyped]

                player_iter = tqdm(
                    base_projections.items(), desc="Simulating players"
                )
            except ImportError:
                if not self._tqdm_warned:
                    logger.info(
                        "tqdm not available for progress bar. "
                        "Install with 'pip install .[ui]' to enable."
                    )
                    self._tqdm_warned = True
                player_iter = base_projections.items()
        else:
            player_iter = base_projections.items()

        for player, base_proj in player_iter:
            # Simple simulation: normal distribution around base projection
            # In a real implementation, this would be much more sophisticated
            std = max(base_proj * 0.3, 1.0)  # 30% std dev, minimum 1.0
            simulated = np.random.normal(
                loc=base_proj, scale=std, size=self.config.n_trials
            )
            # Clamp at 0 (no negative fantasy points)
            simulated = np.maximum(simulated, 0.0)
            results[player] = simulated.tolist()

        return results
