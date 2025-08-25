"""
Tests for the sampler module - distribution sampling, correlation, and deterministic seeding.
"""

import pytest
import numpy as np
import pandas as pd
from src.sim.sampler import MonteCarloSampler, SamplingConfig, create_default_config
from src.sim.correlation import create_simple_correlation_matrix


class TestMonteCarloSampler:
    """Test the Monte Carlo sampler."""
    
    def test_deterministic_seeding(self):
        """Test that the same seed produces identical results."""
        # Create test data
        players = [
            {
                'player_id': 'BUF_QB_JOSH_ALLEN',
                'name': 'Josh Allen',
                'team': 'BUF',
                'position': 'QB',
                'salary': 8200,
                'site_projection': 22.5
            },
            {
                'player_id': 'BUF_WR_STEFON_DIGGS',
                'name': 'Stefon Diggs',
                'team': 'BUF',
                'position': 'WR',
                'salary': 8000,
                'site_projection': 16.5
            }
        ]
        
        games = [
            {
                'game_id': 'MIA@BUF',
                'home_team': 'BUF',
                'away_team': 'MIA',
                'total': 48.5,
                'spread': 3.5
            }
        ]
        
        # Run simulation twice with same seed
        config = create_default_config(n_simulations=100, seed=42)
        
        sampler1 = MonteCarloSampler(config)
        results1 = sampler1.run_simulation(players, games)
        
        sampler2 = MonteCarloSampler(config)
        results2 = sampler2.run_simulation(players, games)
        
        # Results should be identical
        assert len(results1) == len(results2)
        
        for i in range(len(results1)):
            r1, r2 = results1[i], results2[i]
            assert r1.sim_id == r2.sim_id
            assert r1.random_seed == r2.random_seed
            
            # Player scores should be identical
            for player_id in r1.player_scores:
                assert abs(r1.player_scores[player_id] - r2.player_scores[player_id]) < 1e-10
    
    def test_different_seeds_produce_different_results(self):
        """Test that different seeds produce different results."""
        players = [
            {
                'player_id': 'BUF_QB_JOSH_ALLEN',
                'name': 'Josh Allen',
                'team': 'BUF',
                'position': 'QB',
                'salary': 8200,
                'site_projection': 22.5
            }
        ]
        
        games = [
            {
                'game_id': 'MIA@BUF',
                'home_team': 'BUF',
                'away_team': 'MIA',
                'total': 48.5
            }
        ]
        
        # Run with different seeds
        config1 = create_default_config(n_simulations=100, seed=42)
        config2 = create_default_config(n_simulations=100, seed=123)
        
        sampler1 = MonteCarloSampler(config1)
        sampler2 = MonteCarloSampler(config2)
        
        results1 = sampler1.run_simulation(players, games)
        results2 = sampler2.run_simulation(players, games)
        
        # Calculate means for comparison
        scores1 = [r.player_scores['BUF_QB_JOSH_ALLEN'] for r in results1]
        scores2 = [r.player_scores['BUF_QB_JOSH_ALLEN'] for r in results2]
        
        mean1 = np.mean(scores1)
        mean2 = np.mean(scores2)
        
        # Means should be different (with very high probability)
        assert abs(mean1 - mean2) > 0.1
    
    def test_summary_statistics_shape(self):
        """Test that summary statistics have the correct shape and content."""
        players = [
            {
                'player_id': 'QB1',
                'name': 'QB Player',
                'team': 'TEAM1',
                'position': 'QB',
                'salary': 8000,
                'site_projection': 20.0
            },
            {
                'player_id': 'RB1',
                'name': 'RB Player',
                'team': 'TEAM1',
                'position': 'RB',
                'salary': 7000,
                'site_projection': 15.0
            }
        ]
        
        games = [
            {
                'game_id': 'TEAM2@TEAM1',
                'home_team': 'TEAM1',
                'away_team': 'TEAM2'
            }
        ]
        
        config = create_default_config(n_simulations=1000, seed=42)
        sampler = MonteCarloSampler(config)
        results = sampler.run_simulation(players, games)
        
        # Generate summary statistics
        summary = sampler.generate_summary_statistics(results, players)
        
        # Check shape and columns
        assert len(summary) == 2  # Two players
        
        expected_columns = [
            'player_id', 'name', 'team', 'position', 'salary', 'site_projection',
            'sim_mean', 'sim_std', 'sim_min', 'sim_max',
            'p10', 'p25', 'p50', 'p75', 'p90', 'p95',
            'n_sims'
        ]
        
        for col in expected_columns:
            assert col in summary.columns
        
        # Check that all statistics are reasonable
        for _, row in summary.iterrows():
            assert row['sim_mean'] >= 0
            assert row['sim_std'] >= 0
            assert row['p10'] <= row['p50'] <= row['p90']
            assert row['sim_min'] <= row['sim_mean'] <= row['sim_max']
            assert row['n_sims'] == 1000
    
    def test_volatility_multiplier_effect(self):
        """Test that volatility multiplier affects result spread."""
        players = [
            {
                'player_id': 'QB1',
                'name': 'QB Player',
                'team': 'TEAM1',
                'position': 'QB',
                'salary': 8000,
                'site_projection': 20.0
            }
        ]
        
        games = [
            {
                'game_id': 'TEAM2@TEAM1',
                'home_team': 'TEAM1',
                'away_team': 'TEAM2'
            }
        ]
        
        # Test with different volatility multipliers
        config_low = create_default_config(n_simulations=1000, seed=42)
        config_low.volatility_multiplier = 0.5
        
        config_high = create_default_config(n_simulations=1000, seed=42)
        config_high.volatility_multiplier = 2.0
        
        sampler_low = MonteCarloSampler(config_low)
        sampler_high = MonteCarloSampler(config_high)
        
        results_low = sampler_low.run_simulation(players, games)
        results_high = sampler_high.run_simulation(players, games)
        
        # Calculate standard deviations
        scores_low = [r.player_scores['QB1'] for r in results_low]
        scores_high = [r.player_scores['QB1'] for r in results_high]
        
        std_low = np.std(scores_low)
        std_high = np.std(scores_high)
        
        # High volatility should produce higher standard deviation
        assert std_high > std_low


class TestCorrelationSampling:
    """Test correlation sampling functionality."""
    
    def test_simple_correlation_matrix_properties(self):
        """Test that simple correlation matrix has correct properties."""
        n_players = 5
        base_correlation = 0.1
        
        matrix = create_simple_correlation_matrix(
            n_players, 
            base_correlation, 
            random_state=np.random.RandomState(42)
        )
        
        # Check shape
        assert matrix.shape == (n_players, n_players)
        
        # Check diagonal is 1
        np.testing.assert_array_almost_equal(np.diag(matrix), np.ones(n_players))
        
        # Check symmetry
        np.testing.assert_array_almost_equal(matrix, matrix.T)
        
        # Check positive semi-definite
        eigenvals = np.linalg.eigvals(matrix)
        assert np.all(eigenvals >= -1e-10)  # Allow small numerical errors
    
    def test_correlation_affects_sampling(self):
        """Test that correlations affect sampling results."""
        from src.sim.correlation import CorrelationModel
        
        # Create correlated players (QB and WR on same team)
        players = [
            {
                'player_id': 'QB1',
                'name': 'QB Player',
                'team': 'TEAM1',
                'position': 'QB',
                'salary': 8000
            },
            {
                'player_id': 'WR1',
                'name': 'WR Player',
                'team': 'TEAM1',
                'position': 'WR',
                'salary': 7000
            }
        ]
        
        games = [
            {
                'game_id': 'TEAM2@TEAM1',
                'home_team': 'TEAM1',
                'away_team': 'TEAM2'
            }
        ]
        
        # Test with and without correlations
        config_no_corr = create_default_config(n_simulations=1000, seed=42)
        config_no_corr.include_correlations = False
        
        config_with_corr = create_default_config(n_simulations=1000, seed=42)
        config_with_corr.include_correlations = True
        
        sampler_no_corr = MonteCarloSampler(config_no_corr)
        sampler_with_corr = MonteCarloSampler(config_with_corr)
        
        results_no_corr = sampler_no_corr.run_simulation(players, games)
        results_with_corr = sampler_with_corr.run_simulation(players, games)
        
        # Extract scores
        qb_scores_no_corr = [r.player_scores['QB1'] for r in results_no_corr]
        wr_scores_no_corr = [r.player_scores['WR1'] for r in results_no_corr]
        
        qb_scores_with_corr = [r.player_scores['QB1'] for r in results_with_corr]
        wr_scores_with_corr = [r.player_scores['WR1'] for r in results_with_corr]
        
        # Calculate correlations
        corr_no_corr = np.corrcoef(qb_scores_no_corr, wr_scores_no_corr)[0, 1]
        corr_with_corr = np.corrcoef(qb_scores_with_corr, wr_scores_with_corr)[0, 1]
        
        # With correlation modeling, QB-WR should be more correlated
        assert corr_with_corr > corr_no_corr + 0.05  # At least 5% higher correlation


class TestDistributionSampling:
    """Test that sampling produces reasonable distributions."""
    
    def test_position_specific_distributions(self):
        """Test that different positions have appropriate distributions."""
        # Create players for each position
        players = [
            {
                'player_id': f'{pos}1',
                'name': f'{pos} Player',
                'team': 'TEAM1',
                'position': pos,
                'salary': 7000,
                'site_projection': 15.0
            }
            for pos in ['QB', 'RB', 'WR', 'TE', 'DST']
        ]
        
        games = [
            {
                'game_id': 'TEAM2@TEAM1',
                'home_team': 'TEAM1',
                'away_team': 'TEAM2'
            }
        ]
        
        config = create_default_config(n_simulations=1000, seed=42)
        sampler = MonteCarloSampler(config)
        results = sampler.run_simulation(players, games)
        
        # Generate statistics by position
        summary = sampler.generate_summary_statistics(results, players)
        
        # Check that all positions produce reasonable results
        for position in ['QB', 'RB', 'WR', 'TE', 'DST']:
            pos_data = summary[summary['position'] == position].iloc[0]
            
            # All positions should have positive means
            assert pos_data['sim_mean'] > 0
            
            # Should have reasonable volatility 
            cv = pos_data['sim_std'] / pos_data['sim_mean']
            # Allow higher volatility for skill positions due to boom/bust nature
            max_cv = 2.0 if position in ['WR', 'TE', 'RB'] else 1.0  
            assert 0.1 < cv < max_cv  # Coefficient of variation between 10% and max
            
            # Floor should be at least 0
            assert pos_data['sim_min'] >= 0
    
    def test_zero_floor_constraint(self):
        """Test that fantasy points are never negative."""
        players = [
            {
                'player_id': 'QB1',
                'name': 'QB Player',
                'team': 'TEAM1',
                'position': 'QB',
                'salary': 8000,
                'site_projection': 5.0  # Low projection to increase chance of negative
            }
        ]
        
        games = [
            {
                'game_id': 'TEAM2@TEAM1',
                'home_team': 'TEAM1',
                'away_team': 'TEAM2'
            }
        ]
        
        config = create_default_config(n_simulations=1000, seed=42)
        sampler = MonteCarloSampler(config)
        results = sampler.run_simulation(players, games)
        
        # Check that no scores are negative
        all_scores = [r.player_scores['QB1'] for r in results]
        assert all(score >= 0 for score in all_scores)


if __name__ == "__main__":
    pytest.main([__file__])