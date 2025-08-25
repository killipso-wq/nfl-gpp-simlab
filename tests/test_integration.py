"""Tests for package imports and integration."""


def test_package_imports():
    """Test that main package components can be imported."""
    from nfl_gpp_simlab import MonteCarloConfig, MonteCarloSimulator, summarize

    # Test basic instantiation
    config = MonteCarloConfig()
    _ = MonteCarloSimulator(config)  # Assign to unused variable

    # Test basic functionality
    data = [1.0, 2.0, 3.0]
    result = summarize(data)

    assert "mean" in result
    assert "median" in result
    assert "std" in result


def test_integration_workflow():
    """Test complete workflow from config to simulation to summary."""
    from nfl_gpp_simlab import MonteCarloConfig, MonteCarloSimulator, summarize

    # Setup
    config = MonteCarloConfig(n_trials=100, seed=42, show_progress=False)
    simulator = MonteCarloSimulator(config)

    # Simulate
    projections = {"Player1": 15.0, "Player2": 20.0}
    results = simulator.simulate(projections)

    # Summarize
    summary = {}
    for player, outcomes in results.items():
        summary[player] = summarize(outcomes, config.quantiles)

    # Validate
    assert "Player1" in summary
    assert "Player2" in summary

    for player_stats in summary.values():
        assert "mean" in player_stats
        assert "median" in player_stats
        assert "std" in player_stats
        assert "q05" in player_stats
        assert "q95" in player_stats
