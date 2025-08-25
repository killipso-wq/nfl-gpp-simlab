"""Summary metrics and statistics calculation."""

from collections.abc import Sequence

import numpy as np


def summarize(
    data: list[float] | np.ndarray, quantiles: Sequence[float] | None = None
) -> dict[str, float]:
    """Compute summary statistics for simulation results.

    Args:
        data: Array or list of numerical values
        quantiles: Optional list of quantiles to compute. If None, uses [0.05, 0.95]

    Returns:
        Dictionary containing summary statistics with keys:
        - mean: arithmetic mean
        - median: 50th percentile
        - std: sample standard deviation (ddof=1)
        - q05, q95: default quantiles (or custom qXX keys if quantiles provided)
    """
    if quantiles is None:
        quantiles = [0.05, 0.95]

    data_array = np.asarray(data)

    if len(data_array) == 0:
        return {}

    result = {
        "mean": float(np.mean(data_array)),
        "median": float(np.median(data_array)),
        "std": float(np.std(data_array, ddof=1)) if len(data_array) > 1 else 0.0,
    }

    # Add quantiles
    for q in quantiles:
        if not (0 <= q <= 1):
            continue
        key = f"q{int(q * 100):02d}"
        result[key] = float(np.percentile(data_array, q * 100))

    return result


def summarize_simulation_results(
    simulation_results: dict[str, list[float]], quantiles: Sequence[float] | None = None
) -> dict[str, dict[str, float]]:
    """Compute summary statistics for all players in simulation results.

    Args:
        simulation_results: Dictionary mapping player names to simulation outcomes
        quantiles: Optional list of quantiles to compute

    Returns:
        Dictionary mapping player names to their summary statistics
    """
    return {
        player: summarize(outcomes, quantiles)
        for player, outcomes in simulation_results.items()
    }
