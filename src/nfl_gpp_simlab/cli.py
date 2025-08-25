"""Command Line Interface for NFL GPP SimLab."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

from .config import SimulationConfig
from .simulation import NFLSimulator


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.
    
    Args:
        verbose: Enable verbose logging
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser for CLI.
    
    Returns:
        Configured ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="NFL GPP Monte Carlo Simulation Laboratory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run simulation with config file
  nfl-gpp-sim --config config.toml --input players.csv --output results/

  # Run with command line parameters
  nfl-gpp-sim --input players.csv --output results/ --n-trials 50000 --seed 123

  # Generate sample config
  nfl-gpp-sim --generate-config sample_config.toml
        """
    )
    
    # Input/Output
    parser.add_argument(
        "--input", "-i",
        type=Path,
        help="Input CSV file with player data"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("simulation_output"),
        help="Output directory for results (default: simulation_output)"
    )
    
    # Configuration
    parser.add_argument(
        "--config", "-c",
        type=Path,
        help="Configuration file (TOML or YAML)"
    )
    
    # Simulation parameters
    parser.add_argument(
        "--n-trials",
        type=int,
        help="Number of simulation trials"
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--n-jobs",
        type=int,
        help="Number of parallel jobs"
    )
    parser.add_argument(
        "--quantiles",
        type=float,
        nargs="+",
        help="Quantiles to compute (space-separated, e.g., 0.1 0.5 0.9)"
    )
    
    # Utility commands
    parser.add_argument(
        "--generate-config",
        type=Path,
        help="Generate sample configuration file and exit"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 0.1.0"
    )
    
    return parser


def generate_sample_config(config_path: Path) -> None:
    """Generate a sample configuration file.
    
    Args:
        config_path: Path to save the configuration file
    """
    config_content = """# NFL GPP SimLab Configuration File
# This file configures simulation parameters for the Monte Carlo engine

# Simulation parameters
n_trials = 10000        # Number of Monte Carlo trials
base_seed = 42          # Random seed for reproducibility  
n_jobs = 1              # Number of parallel jobs (or set NFL_GPP_SIMLAB_N_JOBS env var)

# Statistical quantiles to compute (0-1 range)
quantiles = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95]

# Advanced options (optional)
# These are placeholders for future functionality
[advanced]
enable_boom_analysis = true
enable_value_metrics = true
coverage_threshold = 0.8
"""
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        f.write(config_content)
    
    print(f"Sample configuration generated: {config_path}")
    print("Edit the file to customize your simulation parameters.")


def main() -> int:
    """Main CLI entry point.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    try:
        # Handle config generation
        if args.generate_config:
            generate_sample_config(args.generate_config)
            return 0
        
        # Validate required arguments
        if not args.input:
            parser.error("--input is required when not generating config")
        
        if not args.input.exists():
            parser.error(f"Input file does not exist: {args.input}")
        
        # Load configuration
        config = None
        if args.config:
            if not args.config.exists():
                parser.error(f"Config file does not exist: {args.config}")
            
            logger.info(f"Loading configuration from {args.config}")
            config = SimulationConfig.from_file(args.config)
        else:
            # Create config from command line arguments
            config_kwargs = {}
            if args.n_trials:
                config_kwargs['n_trials'] = args.n_trials
            if args.seed:
                config_kwargs['base_seed'] = args.seed
            if args.n_jobs:
                config_kwargs['n_jobs'] = args.n_jobs
            if args.quantiles:
                config_kwargs['quantiles'] = args.quantiles
            
            config = SimulationConfig(**config_kwargs)
        
        # Override config with command line arguments if provided
        if args.n_trials:
            config.n_trials = args.n_trials
        if args.seed:
            config.base_seed = args.seed
        if args.n_jobs:
            config.n_jobs = args.n_jobs
        if args.quantiles:
            config.quantiles = args.quantiles
        
        logger.info(f"Simulation configuration: {config}")
        
        # Run simulation
        simulator = NFLSimulator(config)
        logger.info(f"Starting simulation with input: {args.input}")
        
        results = simulator.run_simulation(input_file=args.input)
        
        # Save results
        args.output.mkdir(parents=True, exist_ok=True)
        results.save_to_directory(args.output)
        
        logger.info("Simulation completed successfully")
        logger.info(f"Results saved to: {args.output}")
        
        # Print summary
        print(f"\nSimulation Summary:")
        print(f"  Players processed: {len(results.sim_players)}")
        print(f"  Trials run: {config.n_trials}")
        print(f"  Seed used: {config.base_seed}")
        print(f"  Output directory: {args.output}")
        print(f"  Files generated:")
        print(f"    - sim_players.csv")
        if results.compare is not None:
            print(f"    - compare.csv")
        if results.diagnostics is not None:
            print(f"    - diagnostics_summary.csv")
        if results.flags is not None:
            print(f"    - flags.csv")
        print(f"    - metadata.json")
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Simulation failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())