"""Tests for simulation module."""

import tempfile
from pathlib import Path
import pandas as pd
import pytest

from nfl_gpp_simlab.config import SimulationConfig
from nfl_gpp_simlab.simulation import NFLSimulator, SimulationResults


class TestNFLSimulator:
    """Test NFLSimulator class."""
    
    def test_basic_simulation(self):
        """Test basic simulation functionality."""
        config = SimulationConfig(n_trials=100, base_seed=42)
        simulator = NFLSimulator(config)
        
        # Create sample data
        data = pd.DataFrame({
            'PLAYER': ['Player1', 'Player2', 'Player3'],
            'POS': ['QB', 'RB', 'WR'],
            'TEAM': ['KC', 'DAL', 'BUF'],
            'FPTS': [20.5, 15.2, 12.8],
            'SAL': [8000, 6500, 5500]
        })
        
        results = simulator.run_simulation(players_data=data)
        
        # Verify results structure
        assert isinstance(results, SimulationResults)
        assert len(results.sim_players) == 3
        assert results.compare is not None
        assert results.diagnostics is not None
        assert results.flags is not None
        assert results.metadata is not None
        
        # Verify required columns exist
        required_cols = ['player_id', 'sim_mean', 'floor_p10', 'ceiling_p90', 'boom_prob']
        for col in required_cols:
            assert col in results.sim_players.columns
        
        # Verify metadata
        assert results.metadata['n_trials'] == 100
        assert results.metadata['base_seed'] == 42
        assert results.metadata['methodology'] == 'monte_carlo_pdf'
    
    def test_simulation_from_file(self):
        """Test simulation from CSV file."""
        config = SimulationConfig(n_trials=50, base_seed=123)
        simulator = NFLSimulator(config)
        
        # Create sample CSV file
        data = pd.DataFrame({
            'PLAYER': ['Test Player'],
            'POS': ['QB'],
            'TEAM': ['TEST'],
            'FPTS': [18.5]
        })
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            data.to_csv(f.name, index=False)
            
            results = simulator.run_simulation(input_file=Path(f.name))
            
            assert len(results.sim_players) == 1
            assert results.sim_players['sim_mean'].iloc[0] > 0
        
        # Clean up
        Path(f.name).unlink()
    
    def test_deterministic_results(self):
        """Test that same seed produces same results."""
        config1 = SimulationConfig(n_trials=100, base_seed=42)
        config2 = SimulationConfig(n_trials=100, base_seed=42)
        
        simulator1 = NFLSimulator(config1)
        simulator2 = NFLSimulator(config2)
        
        data = pd.DataFrame({
            'PLAYER': ['Test Player'],
            'POS': ['QB'],
            'TEAM': ['TEST'],
            'FPTS': [20.0]
        })
        
        results1 = simulator1.run_simulation(players_data=data)
        results2 = simulator2.run_simulation(players_data=data)
        
        # Results should be identical for same seed
        assert results1.sim_players['sim_mean'].iloc[0] == results2.sim_players['sim_mean'].iloc[0]
    
    def test_no_input_error(self):
        """Test error when no input provided."""
        config = SimulationConfig()
        simulator = NFLSimulator(config)
        
        with pytest.raises(ValueError, match="Either players_data or input_file must be provided"):
            simulator.run_simulation()
    
    def test_custom_quantiles(self):
        """Test custom quantiles configuration."""
        config = SimulationConfig(quantiles=[0.2, 0.8], base_seed=42)
        simulator = NFLSimulator(config)
        
        data = pd.DataFrame({
            'PLAYER': ['Test Player'],
            'POS': ['QB'],
            'TEAM': ['TEST'],
            'FPTS': [20.0]
        })
        
        results = simulator.run_simulation(players_data=data)
        
        # Should have p20 and p80 columns
        assert 'p20' in results.sim_players.columns
        assert 'p80' in results.sim_players.columns


class TestSimulationResults:
    """Test SimulationResults class."""
    
    def test_save_to_directory(self):
        """Test saving results to directory."""
        # Create sample results
        sim_players = pd.DataFrame({
            'player_id': ['p1', 'p2'],
            'sim_mean': [20.0, 15.0]
        })
        
        metadata = {'test': 'value'}
        results = SimulationResults(sim_players=sim_players, metadata=metadata)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir)
            results.save_to_directory(output_path)
            
            # Verify files were created
            assert (output_path / 'sim_players.csv').exists()
            assert (output_path / 'metadata.json').exists()
            
            # Verify content
            loaded_df = pd.read_csv(output_path / 'sim_players.csv')
            assert len(loaded_df) == 2
            assert 'sim_mean' in loaded_df.columns