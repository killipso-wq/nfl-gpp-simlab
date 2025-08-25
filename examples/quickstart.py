#!/usr/bin/env python3
"""Quickstart example for NFL GPP SimLab.

This script demonstrates basic usage of the Monte Carlo simulator
and serves as a smoke test in CI.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nfl_gpp_simlab import MonteCarloConfig, MonteCarloSimulator, summarize


def main() -> None:
    """Run a basic Monte Carlo simulation example."""
    print("NFL GPP SimLab Quickstart Example")
    print("=" * 40)

    # Sample player projections
    base_projections = {
        "Josh Allen": 24.5,
        "Stefon Diggs": 16.2,
        "Derrick Henry": 18.8,
        "Travis Kelce": 14.3,
        "Justin Jefferson": 19.1,
    }

    # Configure simulation
    config = MonteCarloConfig(
        n_trials=1000,  # Small number for quick execution
        seed=42,
        show_progress=False,  # Disabled for CI
        quantiles=[0.1, 0.25, 0.75, 0.9],
    )

    print(f"Running {config.n_trials} trials with seed {config.seed}")
    print(f"Base projections: {base_projections}")
    print()

    # Run simulation
    simulator = MonteCarloSimulator(config)
    results = simulator.simulate(base_projections)

    # Summarize results
    print("Summary Statistics:")
    print("-" * 60)
    for player, outcomes in results.items():
        stats = summarize(outcomes, config.quantiles)
        print(
            f"{player:15} | Mean: {stats['mean']:6.2f} | "
            f"Median: {stats['median']:6.2f} | Std: {stats['std']:6.2f}"
        )

        # Show quantiles
        quantile_str = " | ".join(
            [
                f"q{int(q * 100):02d}: {stats[f'q{int(q * 100):02d}']:6.2f}"
                for q in config.quantiles
            ]
        )
        print(f"{'':15} | {quantile_str}")
        print()

    # Basic validation
    for player, outcomes in results.items():
        assert len(outcomes) == config.n_trials, (
            f"Wrong number of outcomes for {player}"
        )
        assert all(x >= 0 for x in outcomes), f"Negative outcomes found for {player}"

    print("✓ Quickstart example completed successfully!")
    print(f"✓ Generated {len(results)} player simulations")
    print("✓ All outcomes >= 0 (no negative fantasy points)")
    print("✓ Summary statistics include mean, median, std, and custom quantiles")


if __name__ == "__main__":
    main()
