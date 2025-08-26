"""
Value metrics calculations for fantasy football projections.

Implements value_per_1k, ceil_per_1k, delta_mean, pct_delta with safe math.
"""

import pandas as pd
import numpy as np
from typing import Union, Optional


def safe_divide(numerator: Union[float, pd.Series], 
                denominator: Union[float, pd.Series], 
                default: float = 0.0) -> Union[float, pd.Series]:
    """
    Safe division with zero guard.
    
    Args:
        numerator: Numerator value(s)
        denominator: Denominator value(s) 
        default: Default value when denominator is zero
        
    Returns:
        Result of division or default value
    """
    if isinstance(denominator, pd.Series):
        result = numerator / denominator.replace(0, np.nan)
        return result.fillna(default)
    else:
        return numerator / denominator if denominator != 0 else default


def value_per_1k(sim_mean: Union[float, pd.Series], 
                salary: Union[float, pd.Series]) -> Union[float, pd.Series]:
    """
    Calculate value per $1k salary.
    
    Args:
        sim_mean: Simulated mean projection
        salary: Player salary
        
    Returns:
        Value per $1k (sim_mean / (salary/1000))
    """
    return safe_divide(sim_mean, salary / 1000, default=0.0)


def ceil_per_1k(ceiling_p90: Union[float, pd.Series], 
                salary: Union[float, pd.Series]) -> Union[float, pd.Series]:
    """
    Calculate ceiling value per $1k salary.
    
    Args:
        ceiling_p90: 90th percentile projection
        salary: Player salary
        
    Returns:
        Ceiling value per $1k (p90 / (salary/1000))
    """
    return safe_divide(ceiling_p90, salary / 1000, default=0.0)


def delta_mean(sim_mean: Union[float, pd.Series], 
               site_fpts: Union[float, pd.Series]) -> Union[float, pd.Series]:
    """
    Calculate difference between our projection and site projection.
    
    Args:
        sim_mean: Our simulated mean projection
        site_fpts: Site fantasy points projection
        
    Returns:
        Delta (sim_mean - site_fpts)
    """
    return sim_mean - site_fpts


def pct_delta(sim_mean: Union[float, pd.Series], 
              site_fpts: Union[float, pd.Series]) -> Union[float, pd.Series]:
    """
    Calculate percentage difference vs site projection.
    
    Args:
        sim_mean: Our simulated mean projection
        site_fpts: Site fantasy points projection
        
    Returns:
        Percentage delta (delta_mean / max(1, |site_fpts|))
    """
    delta = delta_mean(sim_mean, site_fpts)
    
    if isinstance(site_fpts, pd.Series):
        abs_site = site_fpts.abs()
        denominator = pd.concat([abs_site, pd.Series([1] * len(abs_site))], axis=1).max(axis=1)
    else:
        denominator = max(1, abs(site_fpts))
    
    return safe_divide(delta, denominator, default=0.0)


def calculate_value_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all value metrics for a DataFrame.
    
    Expected columns: sim_mean, ceiling_p90, SAL (optional), site_fpts (optional)
    
    Args:
        df: DataFrame with projection data
        
    Returns:
        DataFrame with added value metric columns
    """
    result_df = df.copy()
    
    # Value metrics (only if salary present)
    if 'SAL' in df.columns:
        result_df['value_per_1k'] = value_per_1k(df['sim_mean'], df['SAL'])
        if 'ceiling_p90' in df.columns:
            result_df['ceil_per_1k'] = ceil_per_1k(df['ceiling_p90'], df['SAL'])
        else:
            result_df['ceil_per_1k'] = np.nan
    else:
        result_df['value_per_1k'] = np.nan
        result_df['ceil_per_1k'] = np.nan
    
    # Comparison metrics (only if site projections present)
    if 'site_fpts' in df.columns:
        result_df['delta_mean'] = delta_mean(df['sim_mean'], df['site_fpts'])
        result_df['pct_delta'] = pct_delta(df['sim_mean'], df['site_fpts'])
    else:
        result_df['delta_mean'] = np.nan
        result_df['pct_delta'] = np.nan
    
    return result_df