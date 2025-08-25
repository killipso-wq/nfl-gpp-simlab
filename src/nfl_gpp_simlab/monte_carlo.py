from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Sequence
import numpy as np


@dataclass
class MonteCarloConfig:
    """
    Basic configuration for Monte Carlo simulations in the NFL GPP SimLab.

    See the methodology PDF for background and notation:
    docs/research/monte_carlo_football.pdf
    """

    n_trials: int = 10_000
    random_seed: int | None = 42


class MonteCarloSimulator:
    """A minimal Monte Carlo simulator stub.

    This class is intentionally simple to allow quick iteration. It supports a user-provided
    sampling function that returns samples for one trial; aggregation is handled by numpy.
    """

    def __init__(self, cfg: MonteCarloConfig):
        self.cfg = cfg
        self._rng = np.random.default_rng(cfg.random_seed)

    def simulate(
        self,
        sample_fn: Callable[[np.random.Generator], Sequence[float] | np.ndarray],
    ) -> np.ndarray:
        """
        Run n_trials simulations using the provided sampling function.

        sample_fn should accept the RNG and return a 1D sequence/array of numeric values
        for a single trial (e.g., scores for a lineup). The result is a 2D array of shape
        (n_trials, n_values_per_trial).
        """
        samples: list[np.ndarray] = []
        for _ in range(self.cfg.n_trials):
            vals = np.asarray(sample_fn(self._rng), dtype=float)
            if vals.ndim != 1:
                raise ValueError("sample_fn must return a 1D sequence/array")
            samples.append(vals)
        return np.vstack(samples)

    def summarize(self, results: np.ndarray) -> dict[str, np.ndarray]:
        """Return simple statistics over trials (mean, std, quantiles)."""
        if results.ndim != 2:
            raise ValueError("results must be a 2D array (n_trials, n_values)")
        return {
            "mean": results.mean(axis=0),
            "std": results.std(axis=0, ddof=1),
            "q05": np.quantile(results, 0.05, axis=0),
            "q50": np.quantile(results, 0.50, axis=0),
            "q95": np.quantile(results, 0.95, axis=0),
        }