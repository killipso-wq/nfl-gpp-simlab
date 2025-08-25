"""
Tests for Monte Carlo estimators

Validates estimator correctness against analytical targets per problem statement.
Tests are deterministic (fixed base_seed) and stable across OS.
"""

import sys
import math
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.sim.monte_carlo_estimators import (
    sample_mean, sample_variance, sample_std_dev, standard_error,
    sample_quantiles, normal_approx_ci, MonteCarloEngine, set_base_seed
)


def test_sample_mean():
    """Test sample mean estimator against known values."""
    # Test case 1: Simple sequence
    samples = [1.0, 2.0, 3.0, 4.0, 5.0]
    expected = 3.0
    result = sample_mean(samples)
    assert abs(result - expected) < 1e-10, f"Expected {expected}, got {result}"
    
    # Test case 2: Empty list
    assert sample_mean([]) == 0.0
    
    # Test case 3: Single value
    assert sample_mean([42.0]) == 42.0
    
    print("✓ sample_mean tests passed")


def test_sample_variance():
    """Test sample variance estimator against known values."""
    # Test case: Known variance
    samples = [1.0, 2.0, 3.0, 4.0, 5.0]
    # Unbiased sample variance = sum((x-mean)^2) / (n-1)
    # mean = 3.0, deviations = [-2, -1, 0, 1, 2]
    # sum of squares = 4 + 1 + 0 + 1 + 4 = 10
    # variance = 10 / 4 = 2.5
    expected = 2.5
    result = sample_variance(samples)
    assert abs(result - expected) < 1e-10, f"Expected {expected}, got {result}"
    
    # Test biased variance (ddof=0)
    expected_biased = 2.0  # 10 / 5
    result_biased = sample_variance(samples, ddof=0)
    assert abs(result_biased - expected_biased) < 1e-10
    
    print("✓ sample_variance tests passed")


def test_sample_std_dev():
    """Test sample standard deviation estimator."""
    samples = [1.0, 2.0, 3.0, 4.0, 5.0]
    expected = math.sqrt(2.5)  # sqrt of variance
    result = sample_std_dev(samples)
    assert abs(result - expected) < 1e-10, f"Expected {expected}, got {result}"
    
    print("✓ sample_std_dev tests passed")


def test_standard_error():
    """Test standard error estimator."""
    samples = [1.0, 2.0, 3.0, 4.0, 5.0]
    expected = math.sqrt(2.5) / math.sqrt(5)  # std_dev / sqrt(n)
    result = standard_error(samples)
    assert abs(result - expected) < 1e-10, f"Expected {expected}, got {result}"
    
    print("✓ standard_error tests passed")


def test_sample_quantiles():
    """Test empirical quantiles against known values."""
    samples = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    
    # Test median
    quantiles = [0.5]
    result = sample_quantiles(samples, quantiles)
    expected_median = 5.5  # midpoint of 5 and 6
    assert abs(result[0.5] - expected_median) < 1e-10
    
    # Test extreme quantiles
    quantiles = [0.0, 1.0]
    result = sample_quantiles(samples, quantiles)
    assert abs(result[0.0] - 1.0) < 1e-10  # minimum
    assert abs(result[1.0] - 10.0) < 1e-10  # maximum
    
    # Test 90th percentile
    quantiles = [0.9]
    result = sample_quantiles(samples, quantiles)
    expected_p90 = 9.1  # linear interpolation between 9 and 10
    assert abs(result[0.9] - expected_p90) < 1e-10
    
    print("✓ sample_quantiles tests passed")


def test_normal_approx_ci():
    """Test normal approximation confidence intervals."""
    # Use a large sample from known distribution for testing
    set_base_seed(123)  # Deterministic test
    
    # Generate samples from standard normal
    import random
    samples = [random.gauss(0, 1) for _ in range(1000)]
    
    # 95% CI should contain true mean (0) most of the time
    lower, upper = normal_approx_ci(samples, alpha=0.05)
    
    # Check that CI is reasonable (not too wide or narrow)
    ci_width = upper - lower
    expected_width = 2 * 1.96 * (1.0 / math.sqrt(1000))  # approximately
    assert abs(ci_width - expected_width) < 0.1, f"CI width {ci_width} vs expected {expected_width}"
    
    print("✓ normal_approx_ci tests passed")


def test_monte_carlo_engine_determinism():
    """Test that Monte Carlo engine produces deterministic results."""
    def simple_normal():
        import random
        return random.gauss(0, 1)
    
    # Run same simulation twice with same seed
    engine1 = MonteCarloEngine(base_seed=42)
    results1 = engine1.run_simulation(simple_normal, 100)
    
    engine2 = MonteCarloEngine(base_seed=42)
    results2 = engine2.run_simulation(simple_normal, 100)
    
    # Results should be identical
    assert len(results1) == len(results2)
    for i, (r1, r2) in enumerate(zip(results1, results2)):
        assert abs(r1 - r2) < 1e-10, f"Results differ at index {i}: {r1} vs {r2}"
    
    # Different seeds should give different results
    engine3 = MonteCarloEngine(base_seed=123)
    results3 = engine3.run_simulation(simple_normal, 100)
    
    # Should be different from first run (with very high probability)
    differences = sum(1 for r1, r3 in zip(results1, results3) if abs(r1 - r3) > 1e-10)
    assert differences > 50, f"Only {differences} differences found - seeds may not be working"
    
    print("✓ Monte Carlo engine determinism tests passed")


def test_monte_carlo_convergence():
    """Test that Monte Carlo estimates converge to analytical values."""
    def unit_normal():
        import random
        return random.gauss(0, 1)
    
    engine = MonteCarloEngine(base_seed=42)
    
    # Test with increasing sample sizes
    for n_trials in [100, 1000]:
        summary = engine.get_summary(unit_normal, n_trials)
        
        # Mean should be close to 0
        assert abs(summary['mean']) < 0.2, f"Mean {summary['mean']} too far from 0 with {n_trials} trials"
        
        # Variance should be close to 1
        assert abs(summary['variance'] - 1.0) < 0.3, f"Variance {summary['variance']} too far from 1 with {n_trials} trials"
        
        # Standard error should decrease with sample size
        expected_se = 1.0 / math.sqrt(n_trials)
        assert abs(summary['standard_error'] - expected_se) < 0.1, f"SE {summary['standard_error']} vs expected {expected_se}"
    
    print("✓ Monte Carlo convergence tests passed")


def run_all_tests():
    """Run all Monte Carlo estimator tests."""
    print("Running Monte Carlo Estimator Tests")
    print("=" * 40)
    
    try:
        test_sample_mean()
        test_sample_variance()
        test_sample_std_dev()
        test_standard_error()
        test_sample_quantiles()
        test_normal_approx_ci()
        test_monte_carlo_engine_determinism()
        test_monte_carlo_convergence()
        
        print()
        print("🎉 All tests passed!")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)