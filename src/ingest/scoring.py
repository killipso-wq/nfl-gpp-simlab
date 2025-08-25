"""
DraftKings scoring helper for NFL fantasy points calculation.
"""
import pandas as pd


def dk_points(row: pd.Series) -> float:
    """
    Calculate DraftKings fantasy points for a player's weekly performance.
    
    Args:
        row: pandas Series containing weekly stats from nfl_data_py
        
    Returns:
        float: DraftKings fantasy points for the week, clamped at 0
        
    DK Scoring Rules:
    - 1 pt per reception (PPR)
    - 0.1 per yard rushing/receiving
    - 6 per rush/rec TD
    - 3-pt 300-yard pass bonus
    - 3-pt 100-yard rush/rec bonus (apply both for WR/RB if both conditions met)
    - 4 per passing TD
    - -1 per interception
    - 0.04 per passing yard
    - -1 per fumble lost
    - Clamp negatives at 0 after summing
    """
    points = 0.0
    
    # Reception points (PPR)
    points += row.get('receptions', 0) * 1.0
    
    # Rushing yards (0.1 per yard)
    rush_yards = row.get('rushing_yards', 0)
    points += rush_yards * 0.1
    
    # Receiving yards (0.1 per yard)
    rec_yards = row.get('receiving_yards', 0)
    points += rec_yards * 0.1
    
    # Rushing TDs (6 points each)
    points += row.get('rushing_tds', 0) * 6.0
    
    # Receiving TDs (6 points each)
    points += row.get('receiving_tds', 0) * 6.0
    
    # Passing yards (0.04 per yard)
    pass_yards = row.get('passing_yards', 0)
    points += pass_yards * 0.04
    
    # Passing TDs (4 points each)
    points += row.get('passing_tds', 0) * 4.0
    
    # Interceptions (-1 point each)
    points -= row.get('interceptions', 0) * 1.0
    
    # Fumbles lost (-1 point each)
    points -= row.get('fumbles_lost', 0) * 1.0
    
    # Bonuses
    # 300-yard passing bonus
    if pass_yards >= 300:
        points += 3.0
    
    # 100-yard rushing bonus
    if rush_yards >= 100:
        points += 3.0
        
    # 100-yard receiving bonus
    if rec_yards >= 100:
        points += 3.0
    
    # Clamp at 0 (no negative scores)
    return max(0.0, points)