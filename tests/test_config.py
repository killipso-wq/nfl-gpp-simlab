"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path
import pytest

from nfl_gpp_simlab.config import SimulationConfig


class TestSimulationConfig:
    """Test SimulationConfig class."""
    
    def test_default_config(self):
        """Test default configuration."""
        config = SimulationConfig()
        
        assert config.n_trials == 10000
        assert config.base_seed == 42
        assert config.n_jobs == 1
        assert config.quantiles == [0.1, 0.25, 0.5, 0.75, 0.9, 0.95]
    
    def test_custom_config(self):
        """Test custom configuration."""
        config = SimulationConfig(
            n_trials=50000,
            base_seed=123,
            n_jobs=4,
            quantiles=[0.1, 0.5, 0.9]
        )
        
        assert config.n_trials == 50000
        assert config.base_seed == 123
        assert config.n_jobs == 4
        assert config.quantiles == [0.1, 0.5, 0.9]
    
    def test_env_var_n_jobs(self):
        """Test n_jobs from environment variable."""
        # Set environment variable
        os.environ["NFL_GPP_SIMLAB_N_JOBS"] = "8"
        
        config = SimulationConfig()
        assert config.n_jobs == 8
        
        # Clean up
        del os.environ["NFL_GPP_SIMLAB_N_JOBS"]
    
    def test_invalid_quantiles(self):
        """Test validation of quantiles."""
        with pytest.raises(ValueError, match="Quantiles must be in \\[0, 1\\] range"):
            SimulationConfig(quantiles=[0.1, 0.5, 1.5])
    
    def test_toml_config(self):
        """Test loading from TOML file."""
        toml_content = """
n_trials = 25000
base_seed = 999
n_jobs = 2
quantiles = [0.2, 0.5, 0.8]
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()
            
            config = SimulationConfig.from_file(f.name)
            
            assert config.n_trials == 25000
            assert config.base_seed == 999
            assert config.n_jobs == 2
            assert config.quantiles == [0.2, 0.5, 0.8]
        
        # Clean up
        os.unlink(f.name)
    
    def test_yaml_config(self):
        """Test loading from YAML file (if pyyaml available)."""
        yaml_content = """
n_trials: 15000
base_seed: 555
n_jobs: 3
quantiles: [0.1, 0.9]
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                config = SimulationConfig.from_file(f.name)
                
                assert config.n_trials == 15000
                assert config.base_seed == 555
                assert config.n_jobs == 3
                assert config.quantiles == [0.1, 0.9]
            except ValueError as e:
                if "YAML support not available" in str(e):
                    pytest.skip("YAML support not available")
                else:
                    raise
        
        # Clean up
        os.unlink(f.name)
    
    def test_nonexistent_file(self):
        """Test error handling for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            SimulationConfig.from_file("nonexistent.toml")
    
    def test_unsupported_format(self):
        """Test error handling for unsupported file format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{"n_trials": 1000}')
            f.flush()
            
            with pytest.raises(ValueError, match="Unsupported configuration file format"):
                SimulationConfig.from_file(f.name)
        
        # Clean up
        os.unlink(f.name)
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        config = SimulationConfig(
            n_trials=5000,
            base_seed=42,
            custom_option="test"
        )
        
        config_dict = config.to_dict()
        
        assert config_dict["n_trials"] == 5000
        assert config_dict["base_seed"] == 42
        assert config_dict["custom_option"] == "test"
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        config_dict = {
            "n_trials": 7500,
            "base_seed": 100,
            "n_jobs": 2,
        }
        
        config = SimulationConfig.from_dict(config_dict)
        
        assert config.n_trials == 7500
        assert config.base_seed == 100
        assert config.n_jobs == 2