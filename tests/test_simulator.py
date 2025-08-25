"""Tests for MonteCarloConfig and MonteCarloSimulator."""

from nfl_gpp_simlab import MonteCarloConfig, MonteCarloSimulator


def test_monte_carlo_config_defaults():
    """Test MonteCarloConfig default values."""
    config = MonteCarloConfig()

    assert config.n_trials == 10000
    assert config.seed == 42
    assert config.show_progress is False
    assert config.quantiles == [0.05, 0.95]


def test_monte_carlo_config_custom():
    """Test MonteCarloConfig with custom values."""
    config = MonteCarloConfig(
        n_trials=5000, seed=123, show_progress=True, quantiles=[0.1, 0.25, 0.75, 0.9]
    )

    assert config.n_trials == 5000
    assert config.seed == 123
    assert config.show_progress is True
    assert config.quantiles == [0.1, 0.25, 0.75, 0.9]


def test_monte_carlo_config_none_quantiles():
    """Test that None quantiles get set to defaults."""
    config = MonteCarloConfig(quantiles=None)
    assert config.quantiles == [0.05, 0.95]


def test_monte_carlo_simulator_basic():
    """Test basic MonteCarloSimulator functionality."""
    config = MonteCarloConfig(n_trials=100, seed=42, show_progress=False)
    simulator = MonteCarloSimulator(config)

    base_projections = {"Player1": 15.0, "Player2": 20.0}

    results = simulator.simulate(base_projections)

    # Check structure
    assert "Player1" in results
    assert "Player2" in results
    assert len(results["Player1"]) == 100
    assert len(results["Player2"]) == 100

    # Check all values are non-negative (clamped at 0)
    assert all(x >= 0 for x in results["Player1"])
    assert all(x >= 0 for x in results["Player2"])


def test_monte_carlo_simulator_deterministic():
    """Test that simulator produces deterministic results with fixed seed."""
    config = MonteCarloConfig(n_trials=50, seed=42, show_progress=False)
    simulator1 = MonteCarloSimulator(config)
    simulator2 = MonteCarloSimulator(config)

    base_projections = {"Player1": 10.0}

    results1 = simulator1.simulate(base_projections)
    results2 = simulator2.simulate(base_projections)

    # Should be identical with same seed
    assert results1["Player1"] == results2["Player1"]


def test_monte_carlo_simulator_different_seeds():
    """Test that different seeds produce different results."""
    config1 = MonteCarloConfig(n_trials=50, seed=42, show_progress=False)
    config2 = MonteCarloConfig(n_trials=50, seed=123, show_progress=False)

    simulator1 = MonteCarloSimulator(config1)
    simulator2 = MonteCarloSimulator(config2)

    base_projections = {"Player1": 10.0}

    results1 = simulator1.simulate(base_projections)
    results2 = simulator2.simulate(base_projections)

    # Should be different with different seeds
    assert results1["Player1"] != results2["Player1"]


def test_monte_carlo_simulator_empty_projections():
    """Test simulator with empty projections."""
    config = MonteCarloConfig(n_trials=10, seed=42, show_progress=False)
    simulator = MonteCarloSimulator(config)

    results = simulator.simulate({})
    assert results == {}


def test_monte_carlo_simulator_zero_projection():
    """Test simulator handles zero base projection correctly."""
    config = MonteCarloConfig(n_trials=100, seed=42, show_progress=False)
    simulator = MonteCarloSimulator(config)

    results = simulator.simulate({"Player1": 0.0})

    # Should have 100 results, all non-negative
    assert len(results["Player1"]) == 100
    assert all(x >= 0 for x in results["Player1"])


def test_monte_carlo_simulator_progress_flag():
    """Test that show_progress flag is properly handled (no tqdm available)."""
    config = MonteCarloConfig(n_trials=10, seed=42, show_progress=True)
    simulator = MonteCarloSimulator(config)

    # Should work even without tqdm installed (graceful fallback)
    results = simulator.simulate({"Player1": 15.0})
    assert len(results["Player1"]) == 10
