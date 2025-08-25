#!/usr/bin/env python3
"""
Example demonstrating parallel Monte Carlo simulation with deterministic results.

This example shows how to use the MonteCarloSimulator with both sequential and
parallel execution while maintaining deterministic results.
"""

import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from simulator.config import MonteCarloConfig
from simulator.monte_carlo import MonteCarloSimulator, sample_simulation_trial


def main():
    """Demonstrate parallel Monte Carlo simulation with determinism."""
    print("NFL GPP SimLab - Parallel Monte Carlo Simulation Demo")
    print("=" * 60)
    
    # Configuration
    n_trials = 1000
    base_seed = 42
    
    print(f"Running {n_trials} Monte Carlo trials with seed {base_seed}")
    print()
    
    # Sequential execution
    print("1. Sequential execution (n_jobs=1):")
    config_seq = MonteCarloConfig(n_trials=n_trials, n_jobs=1, base_seed=base_seed)
    simulator_seq = MonteCarloSimulator(config_seq)
    
    start_time = time.time()
    results_seq = simulator_seq.run_simulation(sample_simulation_trial, mean=10.0, std=3.0)
    seq_time = time.time() - start_time
    
    print(f"   Completed in {seq_time:.3f} seconds")
    print(f"   Mean result: {sum(results_seq) / len(results_seq):.3f}")
    print(f"   First 5 results: {results_seq[:5]}")
    print()
    
    # Parallel execution
    print("2. Parallel execution (n_jobs=4):")
    config_par = MonteCarloConfig(n_trials=n_trials, n_jobs=4, base_seed=base_seed)
    simulator_par = MonteCarloSimulator(config_par)
    
    start_time = time.time()
    results_par = simulator_par.run_simulation(sample_simulation_trial, mean=10.0, std=3.0)
    par_time = time.time() - start_time
    
    print(f"   Completed in {par_time:.3f} seconds")
    print(f"   Mean result: {sum(results_par) / len(results_par):.3f}")
    print(f"   First 5 results: {results_par[:5]}")
    print(f"   Speedup: {seq_time / par_time:.2f}x")
    print()
    
    # Verify determinism
    print("3. Determinism verification:")
    if results_seq == results_par:
        print("   ✓ Sequential and parallel results are identical!")
    else:
        print("   ✗ Results differ - determinism issue!")
        return 1
    
    # Test with environment variable
    print()
    print("4. Environment variable test:")
    import os
    os.environ['NFL_GPP_SIMLAB_N_JOBS'] = '2'
    config_env = MonteCarloConfig(n_trials=100, base_seed=base_seed)
    print(f"   n_jobs from environment: {config_env.n_jobs}")
    print(f"   show_progress (auto-disabled): {config_env.show_progress}")
    
    print()
    print("Demo completed successfully! 🎉")
    print()
    print("Key features demonstrated:")
    print("- Parallel execution with ProcessPoolExecutor")
    print("- Deterministic results across n_jobs values")
    print("- Environment variable configuration")
    print("- Automatic progress bar handling")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())