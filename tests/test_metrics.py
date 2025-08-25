"""Tests for summary metrics functionality."""

import numpy as np
import pytest

from nfl_gpp_simlab.metrics import summarize, summarize_simulation_results


def test_summarize_basic():
    """Test basic summarize functionality with default quantiles."""
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = summarize(data)

    # Check all expected keys are present
    expected_keys = {"mean", "median", "std", "q05", "q95"}
    assert set(result.keys()) == expected_keys

    # Check values
    assert result["mean"] == 3.0
    assert result["median"] == 3.0
    assert result["std"] == pytest.approx(np.std([1, 2, 3, 4, 5], ddof=1))
    assert result["q05"] == 1.2  # 5th percentile
    assert result["q95"] == 4.8  # 95th percentile


def test_summarize_custom_quantiles():
    """Test summarize with custom quantiles."""
    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    quantiles = [0.1, 0.25, 0.75, 0.9]
    result = summarize(data, quantiles=quantiles)

    # Check all expected keys are present
    expected_keys = {"mean", "median", "std", "q10", "q25", "q75", "q90"}
    assert set(result.keys()) == expected_keys

    # Check values
    assert result["mean"] == 5.5
    assert result["median"] == 5.5
    assert result["q10"] == 1.9
    assert result["q25"] == 3.25
    assert result["q75"] == 7.75
    assert result["q90"] == 9.1


def test_summarize_empty_data():
    """Test summarize with empty data."""
    result = summarize([])
    assert result == {}


def test_summarize_single_value():
    """Test summarize with single value."""
    result = summarize([5.0])

    assert result["mean"] == 5.0
    assert result["median"] == 5.0
    assert result["std"] == 0.0  # Single value has zero std
    assert result["q05"] == 5.0
    assert result["q95"] == 5.0


def test_summarize_with_numpy_array():
    """Test summarize works with numpy arrays."""
    data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    result = summarize(data)

    assert result["mean"] == 3.0
    assert result["median"] == 3.0


def test_summarize_simulation_results():
    """Test summarize_simulation_results function."""
    simulation_results = {
        "Player1": [10.0, 12.0, 14.0, 16.0, 18.0],
        "Player2": [5.0, 6.0, 7.0, 8.0, 9.0],
    }

    result = summarize_simulation_results(simulation_results)

    assert "Player1" in result
    assert "Player2" in result

    # Check Player1 stats
    p1_stats = result["Player1"]
    assert p1_stats["mean"] == 14.0
    assert p1_stats["median"] == 14.0

    # Check Player2 stats
    p2_stats = result["Player2"]
    assert p2_stats["mean"] == 7.0
    assert p2_stats["median"] == 7.0


def test_summarize_invalid_quantiles():
    """Test that invalid quantiles are ignored."""
    data = [1.0, 2.0, 3.0, 4.0, 5.0]
    quantiles = [-0.1, 0.5, 1.5]  # Invalid quantiles outside [0, 1]
    result = summarize(data, quantiles=quantiles)

    # Only q50 should be present from valid quantiles
    expected_keys = {"mean", "median", "std", "q50"}
    assert set(result.keys()) == expected_keys
    assert result["q50"] == 3.0


def test_summarize_deterministic():
    """Test that summarize produces deterministic results."""
    data = [1.5, 2.7, 3.1, 4.9, 5.2, 6.8, 7.3, 8.6, 9.4, 10.1]

    # Run multiple times and ensure identical results
    result1 = summarize(data)
    result2 = summarize(data)

    assert result1 == result2

    # Test specific values for determinism
    assert result1["mean"] == pytest.approx(5.96)
    assert result1["median"] == pytest.approx(6.0)
    assert result1["q05"] == pytest.approx(2.04)
    assert result1["q95"] == pytest.approx(9.785)
