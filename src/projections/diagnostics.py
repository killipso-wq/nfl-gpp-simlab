"""
Diagnostic calculations for projection accuracy.

Implements MAE, RMSE, Pearson correlation, and coverage metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, List


def calculate_mae(actual: pd.Series, predicted: pd.Series) -> float:
    """Calculate Mean Absolute Error."""
    valid_mask = pd.notna(actual) & pd.notna(predicted)
    if valid_mask.sum() == 0:
        return np.nan
    return np.abs(actual[valid_mask] - predicted[valid_mask]).mean()


def calculate_rmse(actual: pd.Series, predicted: pd.Series) -> float:
    """Calculate Root Mean Square Error."""
    valid_mask = pd.notna(actual) & pd.notna(predicted)
    if valid_mask.sum() == 0:
        return np.nan
    return np.sqrt(((actual[valid_mask] - predicted[valid_mask]) ** 2).mean())


def calculate_correlation(actual: pd.Series, predicted: pd.Series) -> float:
    """Calculate Pearson correlation coefficient."""
    valid_mask = pd.notna(actual) & pd.notna(predicted)
    if valid_mask.sum() < 2:
        return np.nan
    return actual[valid_mask].corr(predicted[valid_mask])


def calculate_coverage(actual: pd.Series, p10: pd.Series, p90: pd.Series) -> float:
    """
    Calculate coverage: percentage of actual values within [p10, p90] interval.
    
    Args:
        actual: Actual fantasy points
        p10: 10th percentile projections
        p90: 90th percentile projections
        
    Returns:
        Coverage percentage (0-100)
    """
    valid_mask = pd.notna(actual) & pd.notna(p10) & pd.notna(p90)
    if valid_mask.sum() == 0:
        return np.nan
    
    within_interval = (actual[valid_mask] >= p10[valid_mask]) & (actual[valid_mask] <= p90[valid_mask])
    return (within_interval.sum() / valid_mask.sum()) * 100


def compute_position_diagnostics(df: pd.DataFrame, 
                               exclude_rookies: bool = True) -> pd.DataFrame:
    """
    Compute diagnostic metrics by position.
    
    Expected columns: POS, site_fpts, sim_mean, floor_p10, ceiling_p90, rookie_fallback
    
    Args:
        df: DataFrame with projections and actual results
        exclude_rookies: Whether to exclude rookie_fallback players from metrics
        
    Returns:
        DataFrame with diagnostic metrics by position
    """
    # Filter data
    data = df.copy()
    if exclude_rookies and 'rookie_fallback' in data.columns:
        data = data[~data['rookie_fallback']]
    
    # Only use rows where site_fpts is available
    data = data[pd.notna(data.get('site_fpts', pd.Series([np.nan])))]
    
    if len(data) == 0:
        return pd.DataFrame()
    
    diagnostics = []
    
    # Overall metrics
    overall_metrics = {
        'position': 'Overall',
        'count': len(data),
        'mae': calculate_mae(data['site_fpts'], data['sim_mean']),
        'rmse': calculate_rmse(data['site_fpts'], data['sim_mean']),
        'correlation': calculate_correlation(data['site_fpts'], data['sim_mean']),
        'coverage_p10_p90': calculate_coverage(data['site_fpts'], 
                                              data.get('floor_p10', pd.Series([np.nan] * len(data))),
                                              data.get('ceiling_p90', pd.Series([np.nan] * len(data))))
    }
    diagnostics.append(overall_metrics)
    
    # Position-specific metrics
    if 'POS' in data.columns:
        for position in data['POS'].unique():
            if pd.notna(position):
                pos_data = data[data['POS'] == position]
                
                pos_metrics = {
                    'position': position,
                    'count': len(pos_data),
                    'mae': calculate_mae(pos_data['site_fpts'], pos_data['sim_mean']),
                    'rmse': calculate_rmse(pos_data['site_fpts'], pos_data['sim_mean']),
                    'correlation': calculate_correlation(pos_data['site_fpts'], pos_data['sim_mean']),
                    'coverage_p10_p90': calculate_coverage(pos_data['site_fpts'],
                                                          pos_data.get('floor_p10', pd.Series([np.nan] * len(pos_data))),
                                                          pos_data.get('ceiling_p90', pd.Series([np.nan] * len(pos_data))))
                }
                diagnostics.append(pos_metrics)
    
    return pd.DataFrame(diagnostics)


def compute_rookie_diagnostics(df: pd.DataFrame) -> Dict:
    """
    Compute diagnostics for rookie fallback players.
    
    Args:
        df: DataFrame with projections
        
    Returns:
        Dictionary with rookie counts and basic stats
    """
    if 'rookie_fallback' not in df.columns:
        return {'rookie_count': 0, 'total_count': len(df)}
    
    rookie_count = df['rookie_fallback'].sum()
    total_count = len(df)
    
    return {
        'rookie_count': int(rookie_count),
        'total_count': int(total_count),
        'rookie_percentage': (rookie_count / total_count * 100) if total_count > 0 else 0
    }


def generate_diagnostics_summary(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Generate complete diagnostics summary.
    
    Args:
        df: DataFrame with projections and results
        
    Returns:
        Tuple of (diagnostics_df, summary_dict)
    """
    # Position diagnostics (excluding rookies)
    pos_diagnostics = compute_position_diagnostics(df, exclude_rookies=True)
    
    # Rookie diagnostics
    rookie_stats = compute_rookie_diagnostics(df)
    
    # Summary dictionary for metadata
    summary_dict = {
        'total_players': len(df),
        'players_with_site_fpts': len(df[pd.notna(df.get('site_fpts', pd.Series([np.nan] * len(df))))]),
        'rookie_fallback_count': rookie_stats['rookie_count'],
        'positions_analyzed': list(df.get('POS', pd.Series()).unique()) if 'POS' in df.columns else []
    }
    
    # Add overall metrics to summary if available
    if len(pos_diagnostics) > 0:
        overall_row = pos_diagnostics[pos_diagnostics['position'] == 'Overall']
        if len(overall_row) > 0:
            summary_dict.update({
                'overall_mae': overall_row.iloc[0]['mae'],
                'overall_rmse': overall_row.iloc[0]['rmse'], 
                'overall_correlation': overall_row.iloc[0]['correlation'],
                'overall_coverage': overall_row.iloc[0]['coverage_p10_p90']
            })
    
    return pos_diagnostics, summary_dict


def identify_flags(df: pd.DataFrame, 
                  abs_delta_threshold: float = 5.0,
                  pct_delta_threshold: float = 0.25) -> pd.DataFrame:
    """
    Identify flagged players based on large discrepancies or data issues.
    
    Args:
        df: DataFrame with projections
        abs_delta_threshold: Threshold for absolute delta flagging
        pct_delta_threshold: Threshold for percentage delta flagging  
        
    Returns:
        DataFrame with flagged players and reasons
    """
    flags = []
    
    for idx, row in df.iterrows():
        reasons = []
        
        # Check for large absolute delta
        if pd.notna(row.get('delta_mean')) and abs(row['delta_mean']) > abs_delta_threshold:
            reasons.append(f"Large absolute delta: {row['delta_mean']:.1f}")
        
        # Check for large percentage delta  
        if pd.notna(row.get('pct_delta')) and abs(row['pct_delta']) > pct_delta_threshold:
            reasons.append(f"Large percentage delta: {row['pct_delta']:.1%}")
        
        # Check for missing salary when needed
        if pd.isna(row.get('SAL')) and 'value_per_1k' in df.columns:
            reasons.append("Missing salary")
            
        # Check for missing ownership when needed
        if pd.isna(row.get('RST%')) and 'dart_flag' in df.columns:
            reasons.append("Missing ownership")
        
        # Check for extreme values
        if pd.notna(row.get('sim_mean')) and (row['sim_mean'] < 0 or row['sim_mean'] > 100):
            reasons.append(f"Extreme projection: {row['sim_mean']:.1f}")
        
        if reasons:
            flags.append({
                'player_id': row.get('player_id', ''),
                'PLAYER': row.get('PLAYER', ''),
                'POS': row.get('POS', ''),
                'TEAM': row.get('TEAM', ''),
                'reasons': '; '.join(reasons),
                'delta_mean': row.get('delta_mean'),
                'pct_delta': row.get('pct_delta'),
                'sim_mean': row.get('sim_mean'),
                'site_fpts': row.get('site_fpts')
            })
    
    return pd.DataFrame(flags)