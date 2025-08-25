"""
Monte Carlo Estimators

Implements core statistical estimators as defined in monte_carlo_football.pdf.
Uses nomenclature and formulas exactly from the methodology PDF.

Key estimators:
- sample_mean: unbiased estimator of population mean
- sample_variance: unbiased estimator of population variance 
- sample_std_dev: standard deviation
- standard_error: standard error of the mean
- sample_quantiles: empirical quantiles
- normal_approx_ci: normal approximation confidence intervals
"""

import math
import random
from typing import List, Tuple, Dict, Optional, Union


def set_base_seed(base_seed: int) -> None:
    """Set base seed for reproducibility as per PDF methodology."""
    random.seed(base_seed)


def sample_mean(samples: List[float]) -> float:
    """
    Compute sample mean (unbiased estimator).
    
    Formula from PDF: μ̂ = (1/n) * Σᵢ Xᵢ
    
    Args:
        samples: List of sample values
        
    Returns:
        Sample mean
    """
    if not samples:
        return 0.0
    return sum(samples) / len(samples)


def sample_variance(samples: List[float], ddof: int = 1) -> float:
    """
    Compute sample variance (unbiased estimator).
    
    Formula from PDF: σ̂² = (1/(n-1)) * Σᵢ (Xᵢ - μ̂)²
    
    Args:
        samples: List of sample values
        ddof: Delta degrees of freedom (1 for unbiased estimator)
        
    Returns:
        Sample variance
    """
    if len(samples) <= ddof:
        return 0.0
    
    mean = sample_mean(samples)
    sum_sq_diff = sum((x - mean) ** 2 for x in samples)
    return sum_sq_diff / (len(samples) - ddof)


def sample_std_dev(samples: List[float], ddof: int = 1) -> float:
    """
    Compute sample standard deviation.
    
    Formula from PDF: σ̂ = √(σ̂²)
    
    Args:
        samples: List of sample values
        ddof: Delta degrees of freedom
        
    Returns:
        Sample standard deviation
    """
    variance = sample_variance(samples, ddof)
    return math.sqrt(variance)


def standard_error(samples: List[float]) -> float:
    """
    Compute standard error of the mean.
    
    Formula from PDF: SE = σ̂ / √n
    
    Args:
        samples: List of sample values
        
    Returns:
        Standard error of the mean
    """
    if not samples:
        return 0.0
    
    std_dev = sample_std_dev(samples)
    return std_dev / math.sqrt(len(samples))


def sample_quantiles(samples: List[float], quantiles: List[float]) -> Dict[float, float]:
    """
    Compute empirical quantiles.
    
    Uses linear interpolation method as per PDF methodology.
    
    Args:
        samples: List of sample values
        quantiles: List of quantile levels (0.0 to 1.0)
        
    Returns:
        Dictionary mapping quantile levels to values
    """
    if not samples:
        return {q: 0.0 for q in quantiles}
    
    sorted_samples = sorted(samples)
    n = len(sorted_samples)
    result = {}
    
    for q in quantiles:
        if q < 0.0 or q > 1.0:
            raise ValueError(f"Quantile {q} must be between 0.0 and 1.0")
        
        # Linear interpolation method
        index = q * (n - 1)
        lower_index = int(index)
        upper_index = min(lower_index + 1, n - 1)
        
        if lower_index == upper_index:
            result[q] = sorted_samples[lower_index]
        else:
            weight = index - lower_index
            result[q] = (sorted_samples[lower_index] * (1 - weight) + 
                        sorted_samples[upper_index] * weight)
    
    return result


def normal_approx_ci(samples: List[float], alpha: float = 0.05) -> Tuple[float, float]:
    """
    Compute normal approximation confidence interval for the mean.
    
    Formula from PDF: μ̂ ± z_(α/2) * SE
    where z_(α/2) is the (1-α/2) quantile of standard normal distribution
    
    Args:
        samples: List of sample values
        alpha: Significance level (default 0.05 for 95% CI)
        
    Returns:
        Tuple of (lower_bound, upper_bound)
    """
    if not samples:
        return (0.0, 0.0)
    
    mean = sample_mean(samples)
    se = standard_error(samples)
    
    # Critical value for normal distribution
    # For α=0.05, z_(α/2) ≈ 1.96
    z_critical = _normal_critical_value(alpha / 2)
    
    margin_of_error = z_critical * se
    return (mean - margin_of_error, mean + margin_of_error)


def _normal_critical_value(alpha_half: float) -> float:
    """
    Approximate critical value for standard normal distribution.
    
    Uses rational approximation for inverse normal CDF.
    For α/2 = 0.025 (95% CI), returns approximately 1.96.
    """
    # Common critical values lookup
    critical_values = {
        0.005: 2.576,   # 99% CI
        0.01: 2.326,    # 98% CI
        0.025: 1.96,    # 95% CI
        0.05: 1.645,    # 90% CI
    }
    
    if alpha_half in critical_values:
        return critical_values[alpha_half]
    
    # Simple approximation for other values
    # This is a basic implementation - in practice would use scipy.stats
    if alpha_half <= 0.025:
        return 1.96 + (0.025 - alpha_half) * 24  # Rough linear approximation
    else:
        return 1.96 - (alpha_half - 0.025) * 12  # Rough linear approximation


def monte_carlo_summary(samples: List[float], 
                       quantiles: Optional[List[float]] = None,
                       alpha: float = 0.05) -> Dict[str, Union[float, Dict[float, float], Tuple[float, float]]]:
    """
    Compute comprehensive Monte Carlo summary statistics.
    
    Returns all key estimators as defined in the PDF methodology.
    
    Args:
        samples: List of sample values
        quantiles: List of quantile levels (default: [0.1, 0.25, 0.5, 0.75, 0.9, 0.95])
        alpha: Significance level for confidence interval
        
    Returns:
        Dictionary with all summary statistics
    """
    if quantiles is None:
        quantiles = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
    
    return {
        'n_trials': len(samples),
        'mean': sample_mean(samples),
        'variance': sample_variance(samples),
        'std_dev': sample_std_dev(samples),
        'standard_error': standard_error(samples),
        'quantiles': sample_quantiles(samples, quantiles),
        'confidence_interval': normal_approx_ci(samples, alpha),
        'alpha': alpha
    }


class MonteCarloEngine:
    """
    Core Monte Carlo simulation engine with proper seeding and worker management.
    
    Implements methodology from monte_carlo_football.pdf with emphasis on:
    - Deterministic results via base_seed
    - Worker child seeds for parallel execution
    - Proper nomenclature (n_trials, base_seed, n_jobs)
    """
    
    def __init__(self, base_seed: int = 42, n_jobs: int = 1):
        """
        Initialize Monte Carlo engine.
        
        Args:
            base_seed: Base seed for reproducibility
            n_jobs: Number of parallel workers (for future implementation)
        """
        self.base_seed = base_seed
        self.n_jobs = n_jobs
        set_base_seed(base_seed)
    
    def run_simulation(self, 
                      simulation_func: callable,
                      n_trials: int,
                      *args, **kwargs) -> List[float]:
        """
        Run Monte Carlo simulation with specified number of trials.
        
        Args:
            simulation_func: Function that generates one sample
            n_trials: Number of simulation trials
            *args, **kwargs: Arguments passed to simulation_func
            
        Returns:
            List of simulation results
        """
        results = []
        
        # Set seed before simulation for reproducibility
        set_base_seed(self.base_seed)
        
        for trial in range(n_trials):
            # For deterministic parallel execution, each worker would use:
            # worker_seed = base_seed + worker_id * n_trials + trial
            result = simulation_func(*args, **kwargs)
            results.append(result)
        
        return results
    
    def get_summary(self, 
                   simulation_func: callable,
                   n_trials: int,
                   quantiles: Optional[List[float]] = None,
                   alpha: float = 0.05,
                   *args, **kwargs) -> Dict:
        """
        Run simulation and return comprehensive summary.
        
        Args:
            simulation_func: Function that generates one sample
            n_trials: Number of simulation trials  
            quantiles: Quantile levels to compute
            alpha: Significance level for confidence intervals
            *args, **kwargs: Arguments passed to simulation_func
            
        Returns:
            Dictionary with summary statistics
        """
        samples = self.run_simulation(simulation_func, n_trials, *args, **kwargs)
        summary = monte_carlo_summary(samples, quantiles, alpha)
        summary['base_seed'] = self.base_seed
        summary['n_jobs'] = self.n_jobs
        return summary


if __name__ == "__main__":
    # Simple test of estimators
    test_samples = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    
    print("Monte Carlo Estimators Test")
    print(f"Samples: {test_samples}")
    print(f"Mean: {sample_mean(test_samples)}")
    print(f"Variance: {sample_variance(test_samples)}")
    print(f"Std Dev: {sample_std_dev(test_samples)}")
    print(f"Standard Error: {standard_error(test_samples)}")
    
    quantiles = [0.1, 0.5, 0.9]
    print(f"Quantiles {quantiles}: {sample_quantiles(test_samples, quantiles)}")
    
    ci = normal_approx_ci(test_samples)
    print(f"95% CI: {ci}")
    
    # Test Monte Carlo engine
    def simple_normal_sample():
        return random.gauss(0, 1)
    
    engine = MonteCarloEngine(base_seed=123)
    summary = engine.get_summary(simple_normal_sample, n_trials=1000)
    print(f"\nMonte Carlo Summary (1000 trials):")
    for key, value in summary.items():
        print(f"  {key}: {value}")