"""Basic tests for the simulator package."""

import numpy as np
import pytest

from nfl_gpp_simlab import MonteCarloConfig, MonteCarloSimulator


def test_monte_carlo_config():
    """Test MonteCarloConfig creation."""
    config = MonteCarloConfig(n_trials=100, random_seed=42)
    assert config.n_trials == 100
    assert config.random_seed == 42


def test_monte_carlo_simulator():
    """Test MonteCarloSimulator basic functionality."""
    config = MonteCarloConfig(n_trials=10, random_seed=123)
    sim = MonteCarloSimulator(config)
    
    # Simple test function that returns constant values
    def test_fn(rng):
        return np.array([1.0, 2.0])
    
    results = sim.simulate(test_fn)
    assert results.shape == (10, 2)
    
    # All results should be the same since test_fn returns constants
    np.testing.assert_array_equal(results[0], [1.0, 2.0])
    np.testing.assert_array_equal(results[-1], [1.0, 2.0])


def test_simulator_summarize():
    """Test simulation result summarization."""
    config = MonteCarloConfig(n_trials=100, random_seed=456)
    sim = MonteCarloSimulator(config)
    
    # Function that returns random normal values
    def random_fn(rng):
        return np.array([rng.normal(0, 1), rng.normal(10, 2)])
    
    results = sim.simulate(random_fn)
    stats = sim.summarize(results)
    
    assert "mean" in stats
    assert "q05" in stats
    assert "q95" in stats
    
    # Check that results have expected shape
    assert stats["mean"].shape == (2,)
    assert stats["q05"].shape == (2,)
    assert stats["q95"].shape == (2,)
    
    # Basic sanity check: mean should be roughly around expected values
    assert abs(stats["mean"][0]) < 1.0  # Normal(0,1) should have mean near 0
    assert abs(stats["mean"][1] - 10) < 1.0  # Normal(10,2) should have mean near 10