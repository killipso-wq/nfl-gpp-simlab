"""
Test runner for NFL GPP Sim Optimizer

Runs all tests and validates core functionality.
"""

import sys
import subprocess
from pathlib import Path


def run_command(cmd, description):
    """Run a command and report results."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {cmd}")
    print(f"{'='*60}")
    
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ SUCCESS")
        if result.stdout.strip():
            print("Output:")
            print(result.stdout)
    else:
        print("❌ FAILED")
        if result.stderr.strip():
            print("Error:")
            print(result.stderr)
        if result.stdout.strip():
            print("Output:")
            print(result.stdout)
    
    return result.returncode == 0


def main():
    """Run all tests and validations."""
    print("NFL GPP Sim Optimizer - Test Suite")
    print("=" * 50)
    
    all_passed = True
    
    # Test 1: Monte Carlo estimators
    success = run_command(
        "python tests/test_monte_carlo_estimators.py",
        "Monte Carlo Estimator Tests"
    )
    all_passed = all_passed and success
    
    # Test 2: Build baseline
    success = run_command(
        "python scripts/build_baseline.py --start 2023 --end 2024 --out data",
        "Build Baseline Priors"
    )
    all_passed = all_passed and success
    
    # Test 3: Build boom thresholds
    success = run_command(
        "python scripts/build_boom_thresholds.py --start 2023 --end 2024 --out data/baseline/boom_thresholds.json --quantile 0.90",
        "Build Boom Thresholds"
    )
    all_passed = all_passed and success
    
    # Test 4: Run simulation
    success = run_command(
        "python -m src.projections.run_week_from_site_players --season 2025 --week 1 --players-site test_players.csv --team-priors data/baseline/team_priors.csv --player-priors data/baseline/player_priors.csv --boom-thresholds data/baseline/boom_thresholds.json --sims 100 --out data/sim_week",
        "Monte Carlo Simulation"
    )
    all_passed = all_passed and success
    
    # Test 5: Validate outputs
    required_files = [
        "data/sim_week/sim_players.csv",
        "data/sim_week/compare.csv", 
        "data/sim_week/diagnostics_summary.csv",
        "data/sim_week/flags.csv",
        "data/sim_week/metadata.json"
    ]
    
    print(f"\n{'='*60}")
    print("Validating Output Files")
    print(f"{'='*60}")
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_passed = False
    
    # Final result
    print(f"\n{'='*60}")
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("Core MVP functionality is working correctly.")
    else:
        print("❌ SOME TESTS FAILED")
        print("Please check the errors above.")
    print(f"{'='*60}")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())