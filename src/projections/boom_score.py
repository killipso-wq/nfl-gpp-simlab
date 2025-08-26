"""
Boom score calculations and dart flag logic.

Implements boom_score (1-100) derived from boom_prob and dart_flag heuristics.
"""

import pandas as pd
import numpy as np
from typing import Dict, Union, Optional


def calculate_boom_score(boom_prob: Union[float, pd.Series],
                        beat_site_prob: Union[float, pd.Series] = None,
                        rst_pct: Union[float, pd.Series] = None,
                        value_per_1k: Union[float, pd.Series] = None,
                        position: Union[str, pd.Series] = None) -> Union[float, pd.Series]:
    """
    Calculate boom score (1-100) from boom probability and other factors.
    
    Formula from README:
    - composite = 0.6 × boom_prob + 0.4 × beat_site_prob
    - normalize within position to percentile rank
    - ownership boost: +20% if RST% ≤ 5; +10% if ≤ 10; +5% if ≤ 20; else 0
    - value boost: up to +15% if value_per_1k > position median (linear scale)
    - boom_score = 100 × min(1, norm_pos(composite) × (1 + own_boost) × (1 + value_boost))
    
    Args:
        boom_prob: Boom probability (0-1)
        beat_site_prob: Beat site probability (0-1), optional
        rst_pct: Ownership percentage, optional
        value_per_1k: Value per $1k, optional
        position: Position for within-position normalization, optional
        
    Returns:
        Boom score (1-100)
    """
    # Handle missing beat_site_prob
    if beat_site_prob is None:
        if isinstance(boom_prob, pd.Series):
            beat_site_prob = pd.Series([0.0] * len(boom_prob))
        else:
            beat_site_prob = 0.0
    
    # Base composite score
    composite = 0.6 * boom_prob + 0.4 * beat_site_prob
    
    # For Series, handle position-based normalization
    if isinstance(composite, pd.Series) and position is not None:
        if isinstance(position, pd.Series):
            # Position-wise percentile ranking
            normalized = composite.copy()
            for pos in position.unique():
                if pd.notna(pos):
                    pos_mask = (position == pos)
                    pos_values = composite[pos_mask]
                    if len(pos_values) > 1:
                        normalized[pos_mask] = pos_values.rank(pct=True)
                    else:
                        normalized[pos_mask] = 0.5  # Single player gets median
        else:
            # Single position
            normalized = pd.Series([0.5] * len(composite))
    else:
        # For scalar or no position info, use raw composite
        if isinstance(composite, pd.Series):
            normalized = composite.rank(pct=True)
        else:
            normalized = min(max(composite, 0), 1)  # Clamp to [0,1]
    
    # Ownership boost
    own_boost = 0.0
    if rst_pct is not None:
        if isinstance(rst_pct, pd.Series):
            own_boost = pd.Series([0.0] * len(rst_pct))
            own_boost = own_boost.where(rst_pct > 20, 0.05)  # +5% if ≤ 20
            own_boost = own_boost.where(rst_pct > 10, 0.10)  # +10% if ≤ 10  
            own_boost = own_boost.where(rst_pct > 5, 0.20)   # +20% if ≤ 5
        else:
            if rst_pct <= 5:
                own_boost = 0.20
            elif rst_pct <= 10:
                own_boost = 0.10
            elif rst_pct <= 20:
                own_boost = 0.05
    
    # Value boost (simplified for MVP - up to 15% linear)
    value_boost = 0.0
    if value_per_1k is not None:
        if isinstance(value_per_1k, pd.Series) and position is not None:
            if isinstance(position, pd.Series):
                value_boost = pd.Series([0.0] * len(value_per_1k))
                for pos in position.unique():
                    if pd.notna(pos):
                        pos_mask = (position == pos)
                        pos_values = value_per_1k[pos_mask]
                        if len(pos_values) > 1:
                            pos_median = pos_values.median()
                            excess = (pos_values - pos_median) / pos_median
                            value_boost[pos_mask] = np.clip(excess * 0.15, 0, 0.15)
        else:
            # Simplified scalar case
            if isinstance(value_per_1k, (int, float)) and value_per_1k > 0:
                value_boost = min(0.15, value_per_1k / 10 * 0.15)  # Rough heuristic
    
    # Final boom score
    final_score = 100 * np.minimum(1.0, normalized * (1 + own_boost) * (1 + value_boost))
    
    # Ensure it's in range [1, 100]
    if isinstance(final_score, pd.Series):
        return np.maximum(1.0, final_score)
    else:
        return max(1.0, final_score)


def calculate_dart_flag(boom_score: Union[float, pd.Series],
                       rst_pct: Union[float, pd.Series] = None,
                       boom_threshold: float = 70.0,
                       ownership_threshold: float = 5.0) -> Union[bool, pd.Series]:
    """
    Calculate dart flag based on boom score and ownership.
    
    Dart flag criteria: (RST% ≤ 5) AND (boom_score ≥ 70)
    
    Args:
        boom_score: Boom score (1-100)
        rst_pct: Ownership percentage
        boom_threshold: Minimum boom score for dart flag
        ownership_threshold: Maximum ownership for dart flag
        
    Returns:
        Boolean dart flag(s)
    """
    if rst_pct is None:
        # If no ownership data, can't be a dart
        if isinstance(boom_score, pd.Series):
            return pd.Series([False] * len(boom_score))
        else:
            return False
    
    high_boom = boom_score >= boom_threshold
    low_own = rst_pct <= ownership_threshold
    
    return high_boom & low_own


def calculate_boom_metrics(df: pd.DataFrame,
                          boom_thresholds: Dict[str, float] = None) -> pd.DataFrame:
    """
    Calculate boom score and dart flag for a DataFrame.
    
    Expected columns: boom_prob, beat_site_prob (optional), POS, RST% (optional), value_per_1k (optional)
    
    Args:
        df: DataFrame with boom probability data
        boom_thresholds: Position-specific boom thresholds (not used in score calc)
        
    Returns:
        DataFrame with added boom_score and dart_flag columns
    """
    result_df = df.copy()
    
    # Get optional columns
    beat_site_prob = df.get('beat_site_prob')
    rst_pct = df.get('RST%')  
    value_per_1k = df.get('value_per_1k')
    position = df.get('POS')
    
    # Calculate boom score
    result_df['boom_score'] = calculate_boom_score(
        boom_prob=df['boom_prob'],
        beat_site_prob=beat_site_prob,
        rst_pct=rst_pct,
        value_per_1k=value_per_1k,
        position=position
    )
    
    # Calculate dart flag
    result_df['dart_flag'] = calculate_dart_flag(
        boom_score=result_df['boom_score'],
        rst_pct=rst_pct
    )
    
    return result_df