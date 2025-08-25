"""Tests for Monte Carlo simulator parallelism and determinism."""

import os
from unittest import TestCase

import numpy as np

from src.simulator.config import MonteCarloConfig
from src.simulator.monte_carlo import MonteCarloSimulator, sample_simulation_trial


class TestMonteCarloConfig(TestCase):
    """Test MonteCarloConfig functionality."""

    def setUp(self):
        """Clean environment before each test."""
        if 'NFL_GPP_SIMLAB_N_JOBS' in os.environ:
            del os.environ['NFL_GPP_SIMLAB_N_JOBS']

    def test_default_config(self):
        """Test default configuration values."""
        config = MonteCarloConfig()
        self.assertEqual(config.n_trials, 10000)
        self.assertEqual(config.n_jobs, 1)
        self.assertIsNone(config.base_seed)
        self.assertTrue(config.show_progress)

    def test_environment_override(self):
        """Test n_jobs environment variable override."""
        os.environ['NFL_GPP_SIMLAB_N_JOBS'] = '4'
        config = MonteCarloConfig()
        self.assertEqual(config.n_jobs, 4)
        self.assertFalse(config.show_progress)  # Should be disabled for parallel

    def test_environment_override_invalid(self):
        """Test invalid environment variable is ignored."""
        os.environ['NFL_GPP_SIMLAB_N_JOBS'] = 'invalid'
        config = MonteCarloConfig()
        self.assertEqual(config.n_jobs, 1)  # Should keep default

    def test_environment_override_explicit_value(self):
        """Test environment variable doesn't override explicit value."""
        os.environ['NFL_GPP_SIMLAB_N_JOBS'] = '4'
        config = MonteCarloConfig(n_jobs=2)
        self.assertEqual(config.n_jobs, 2)  # Should keep explicit value

    def test_n_jobs_all_cpus(self):
        """Test n_jobs = -1 uses all CPUs."""
        config = MonteCarloConfig(n_jobs=-1)
        expected_cpus = os.cpu_count() or 1
        self.assertEqual(config.n_jobs, expected_cpus)

    def test_n_jobs_clamping(self):
        """Test n_jobs is clamped to available CPU count."""
        max_cpus = os.cpu_count() or 1
        config = MonteCarloConfig(n_jobs=max_cpus + 10)
        self.assertEqual(config.n_jobs, max_cpus)

    def test_progress_bar_disabled_parallel(self):
        """Test progress bar is disabled when n_jobs > 1."""
        config = MonteCarloConfig(n_jobs=2, show_progress=True)
        self.assertFalse(config.show_progress)


class TestMonteCarloDeterminism(TestCase):
    """Test deterministic behavior of Monte Carlo simulator."""

    def test_sequential_determinism(self):
        """Test that sequential runs with same seed produce identical results."""
        config = MonteCarloConfig(n_trials=100, n_jobs=1, base_seed=42)
        simulator = MonteCarloSimulator(config)

        # Run simulation twice with same configuration
        results1 = simulator.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)
        results2 = simulator.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)

        # Results should be identical
        np.testing.assert_array_equal(results1, results2)

    def test_parallel_vs_sequential_determinism(self):
        """Test that parallel and sequential runs produce identical results."""
        n_trials = 100
        base_seed = 42

        # Sequential run
        config_seq = MonteCarloConfig(n_trials=n_trials, n_jobs=1, base_seed=base_seed)
        simulator_seq = MonteCarloSimulator(config_seq)
        results_seq = simulator_seq.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)

        # Parallel run with 4 workers
        config_par = MonteCarloConfig(n_trials=n_trials, n_jobs=4, base_seed=base_seed)
        simulator_par = MonteCarloSimulator(config_par)
        results_par = simulator_par.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)

        # Results should be identical
        np.testing.assert_array_equal(results_seq, results_par)

    def test_repeated_parallel_determinism(self):
        """Test that repeated parallel runs with same seed produce identical results."""
        config = MonteCarloConfig(n_trials=100, n_jobs=4, base_seed=42)
        simulator = MonteCarloSimulator(config)

        # Run simulation twice with same configuration
        results1 = simulator.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)
        results2 = simulator.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)

        # Results should be identical
        np.testing.assert_array_equal(results1, results2)

    def test_different_seeds_different_results(self):
        """Test that different seeds produce different results."""
        config1 = MonteCarloConfig(n_trials=100, n_jobs=1, base_seed=42)
        config2 = MonteCarloConfig(n_trials=100, n_jobs=1, base_seed=123)

        simulator1 = MonteCarloSimulator(config1)
        simulator2 = MonteCarloSimulator(config2)

        results1 = simulator1.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)
        results2 = simulator2.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)

        # Results should be different with very high probability
        # Using a tolerance-based check since exact inequality might fail by chance
        mean_diff = abs(np.mean(results1) - np.mean(results2))
        self.assertGreater(mean_diff, 0.01)  # Should be substantially different

    def test_no_seed_randomness(self):
        """Test that runs without seed produce different results."""
        config = MonteCarloConfig(n_trials=100, n_jobs=1, base_seed=None)
        simulator = MonteCarloSimulator(config)

        results1 = simulator.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)
        results2 = simulator.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)

        # Results should be different (very high probability)
        mean_diff = abs(np.mean(results1) - np.mean(results2))
        self.assertGreater(mean_diff, 0.01)


class TestMonteCarloParallelism(TestCase):
    """Test parallel execution functionality."""

    def test_batch_size_calculation(self):
        """Test that batch sizes are calculated correctly."""
        # Test even distribution
        config = MonteCarloConfig(n_trials=100, n_jobs=4)
        simulator = MonteCarloSimulator(config)
        batch_sizes = simulator._calculate_batch_sizes()
        self.assertEqual(batch_sizes, [25, 25, 25, 25])

        # Test uneven distribution
        config = MonteCarloConfig(n_trials=101, n_jobs=4)
        simulator = MonteCarloSimulator(config)
        batch_sizes = simulator._calculate_batch_sizes()
        self.assertEqual(batch_sizes, [26, 25, 25, 25])  # First worker gets remainder

        # Test fewer trials than workers
        config = MonteCarloConfig(n_trials=2, n_jobs=4)
        simulator = MonteCarloSimulator(config)
        batch_sizes = simulator._calculate_batch_sizes()
        self.assertEqual(batch_sizes, [1, 1, 0, 0])

    def test_parallel_execution_correctness(self):
        """Test that parallel execution produces correct number of results."""
        config = MonteCarloConfig(n_trials=100, n_jobs=4, base_seed=42)
        simulator = MonteCarloSimulator(config)

        results = simulator.run_simulation(sample_simulation_trial, mean=1.0, std=2.0)

        # Should have correct number of results
        self.assertEqual(len(results), 100)

        # Results should be numeric
        self.assertTrue(all(isinstance(r, (int, float)) for r in results))

    def test_edge_case_more_workers_than_cpus(self):
        """Test behavior when n_jobs exceeds CPU count."""
        max_cpus = os.cpu_count() or 1
        config = MonteCarloConfig(n_jobs=max_cpus + 5)  # More than available

        # Should be clamped to max CPUs
        self.assertEqual(config.n_jobs, max_cpus)

    def test_edge_case_zero_workers(self):
        """Test that n_jobs is always at least 1."""
        config = MonteCarloConfig(n_jobs=0)
        self.assertEqual(config.n_jobs, 1)


class TestSimulationFunction(TestCase):
    """Test the example simulation function."""

    def test_sample_simulation_with_rng(self):
        """Test sample simulation function with provided RNG."""
        rng = np.random.Generator(np.random.PCG64(42))
        result = sample_simulation_trial(mean=5.0, std=2.0, rng=rng)

        self.assertIsInstance(result, (int, float))
        # With a fixed seed, result should be deterministic
        expected = rng.normal(5.0, 2.0)  # This will advance the RNG state

        # Reset RNG and test again
        rng = np.random.Generator(np.random.PCG64(42))
        result = sample_simulation_trial(mean=5.0, std=2.0, rng=rng)
        rng = np.random.Generator(np.random.PCG64(42))
        expected = rng.normal(5.0, 2.0)

        self.assertAlmostEqual(result, expected, places=10)

    def test_sample_simulation_default_rng(self):
        """Test sample simulation function with default RNG."""
        result = sample_simulation_trial(mean=0.0, std=1.0)
        self.assertIsInstance(result, (int, float))
