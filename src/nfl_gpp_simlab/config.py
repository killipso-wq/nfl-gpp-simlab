"""Configuration handling for NFL GPP SimLab."""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class SimulationConfig:
    """Configuration class for NFL GPP simulations."""
    
    def __init__(
        self,
        n_trials: int = 10000,
        base_seed: int = 42,
        n_jobs: Optional[int] = None,
        quantiles: Optional[List[float]] = None,
        # Advanced statistics options
        enable_advanced_metrics: bool = True,
        enable_position_breakdown: bool = True,
        enable_risk_metrics: bool = True,
        enable_correlation_analysis: bool = False,
        coverage_quantiles: Optional[List[tuple]] = None,
        **kwargs
    ):
        """Initialize simulation configuration.
        
        Args:
            n_trials: Number of simulation trials to run
            base_seed: Base random seed for reproducibility
            n_jobs: Number of parallel jobs (respects NFL_GPP_SIMLAB_N_JOBS env var)
            quantiles: List of quantiles to compute (0-1 range)
            enable_advanced_metrics: Enable advanced statistical metrics
            enable_position_breakdown: Enable position-specific diagnostics
            enable_risk_metrics: Enable risk-adjusted player metrics
            enable_correlation_analysis: Enable correlation structure analysis
            coverage_quantiles: List of (lower, upper) quantile pairs for coverage analysis
            **kwargs: Additional configuration options
        """
        self.n_trials = n_trials
        self.base_seed = base_seed
        
        # Handle n_jobs with environment variable fallback
        if n_jobs is None:
            env_jobs = os.getenv("NFL_GPP_SIMLAB_N_JOBS")
            if env_jobs:
                try:
                    self.n_jobs = int(env_jobs)
                except ValueError:
                    self.n_jobs = 1
            else:
                self.n_jobs = 1
        else:
            self.n_jobs = n_jobs
            
        # Default quantiles if not provided
        if quantiles is None:
            self.quantiles = [0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
        else:
            # Validate quantiles are in [0, 1] range
            invalid_quantiles = [q for q in quantiles if not (0 <= q <= 1)]
            if invalid_quantiles:
                raise ValueError(f"Quantiles must be in [0, 1] range. Invalid: {invalid_quantiles}")
            self.quantiles = quantiles
        
        # Advanced statistics configuration
        self.enable_advanced_metrics = enable_advanced_metrics
        self.enable_position_breakdown = enable_position_breakdown
        self.enable_risk_metrics = enable_risk_metrics
        self.enable_correlation_analysis = enable_correlation_analysis
        
        # Default coverage quantiles for analysis
        if coverage_quantiles is None:
            self.coverage_quantiles = [(0.1, 0.9), (0.25, 0.75), (0.05, 0.95)]
        else:
            # Validate coverage quantiles
            for lower, upper in coverage_quantiles:
                if not (0 <= lower < upper <= 1):
                    raise ValueError(f"Invalid coverage quantile pair: ({lower}, {upper})")
            self.coverage_quantiles = coverage_quantiles
            
        # Store additional options
        self.additional_options = kwargs
    
    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "SimulationConfig":
        """Load configuration from a TOML or YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            SimulationConfig instance
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If unsupported file format or invalid configuration
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        config_data = {}
        
        if config_path.suffix.lower() == ".toml":
            with open(config_path, "rb") as f:
                config_data = tomllib.load(f)
        elif config_path.suffix.lower() in [".yaml", ".yml"]:
            if not YAML_AVAILABLE:
                raise ValueError(
                    "YAML support not available. Install with: pip install nfl-gpp-simlab[cli]"
                )
            with open(config_path, "r") as f:
                config_data = yaml.safe_load(f)
        else:
            raise ValueError(
                f"Unsupported configuration file format: {config_path.suffix}. "
                "Supported formats: .toml, .yaml, .yml"
            )
        
        # Handle nested configuration sections
        advanced_config = config_data.pop("advanced", {})
        config_data.update(advanced_config)
        
        return cls(**config_data)
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "SimulationConfig":
        """Create configuration from dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            SimulationConfig instance
        """
        return cls(**config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary.
        
        Returns:
            Configuration as dictionary
        """
        return {
            "n_trials": self.n_trials,
            "base_seed": self.base_seed,
            "n_jobs": self.n_jobs,
            "quantiles": self.quantiles,
            "enable_advanced_metrics": self.enable_advanced_metrics,
            "enable_position_breakdown": self.enable_position_breakdown,
            "enable_risk_metrics": self.enable_risk_metrics,
            "enable_correlation_analysis": self.enable_correlation_analysis,
            "coverage_quantiles": self.coverage_quantiles,
            **self.additional_options,
        }
    
    def __repr__(self) -> str:
        """String representation of configuration."""
        return (
            f"SimulationConfig(n_trials={self.n_trials}, base_seed={self.base_seed}, "
            f"n_jobs={self.n_jobs}, quantiles={self.quantiles}, "
            f"advanced_metrics={self.enable_advanced_metrics})"
        )