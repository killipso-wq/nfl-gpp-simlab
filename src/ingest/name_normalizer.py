"""
Player name normalization and ID generation utilities.

Implements stable player ID generation: TEAM_POS_NORMALIZEDNAME
where NORMALIZEDNAME = uppercase, punctuation removed, suffixes dropped, spaces collapsed.
"""

import re
from typing import Optional
from slugify import slugify


def normalize_name(name: str) -> str:
    """
    Normalize player name for stable ID generation.
    
    Rules:
    - Uppercase
    - Remove punctuation 
    - Drop suffixes (JR/SR/II/III/IV/V)
    - Collapse spaces
    
    Args:
        name: Raw player name
        
    Returns:
        Normalized name string
    """
    if not name or not isinstance(name, str):
        return ""
    
    # Start with basic normalization
    normalized = name.upper().strip()
    
    # Remove common suffixes
    suffixes = [r'\s+JR\.?$', r'\s+SR\.?$', r'\s+II$', r'\s+III$', r'\s+IV$', r'\s+V$']
    for suffix_pattern in suffixes:
        normalized = re.sub(suffix_pattern, '', normalized)
    
    # Remove punctuation and extra spaces
    normalized = re.sub(r'[^\w\s]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    return normalized


def normalize_position(position: str) -> str:
    """
    Normalize position abbreviations.
    
    Args:
        position: Raw position string
        
    Returns:
        Normalized position (QB/RB/WR/TE/DST/K/UNK)
    """
    if not position or not isinstance(position, str):
        return "UNK"
    
    pos = position.upper().strip()
    
    # Map common variations
    position_map = {
        'D': 'DST',
        'DEF': 'DST', 
        'DEFENSE': 'DST',
        'KICKER': 'K',
        'PK': 'K'
    }
    
    # Return mapped value or original if valid
    if pos in position_map:
        return position_map[pos]
    elif pos in ['QB', 'RB', 'WR', 'TE', 'DST', 'K']:
        return pos
    else:
        return 'UNK'


def build_player_id(name: str, team: str, position: str) -> str:
    """
    Build stable player ID: TEAM_POS_NORMALIZEDNAME
    
    Args:
        name: Player name
        team: Team abbreviation
        position: Position
        
    Returns:
        Player ID string
    """
    if not all([name, team, position]):
        return ""
    
    normalized_name = normalize_name(name)
    normalized_pos = normalize_position(position)
    team_upper = team.upper().strip()
    
    # Handle edge case where name normalization results in empty string
    if not normalized_name:
        normalized_name = "UNKNOWN"
    
    return f"{team_upper}_{normalized_pos}_{normalized_name.replace(' ', '')}"


def build_player_id_from_row(row, name_col='PLAYER', team_col='TEAM', pos_col='POS') -> str:
    """
    Build player ID from a pandas row or dict.
    
    Args:
        row: Pandas Series or dict with player data
        name_col: Column name for player name
        team_col: Column name for team
        pos_col: Column name for position
        
    Returns:
        Player ID string
    """
    try:
        name = row.get(name_col, '') if hasattr(row, 'get') else getattr(row, name_col, '')
        team = row.get(team_col, '') if hasattr(row, 'get') else getattr(row, team_col, '')
        position = row.get(pos_col, '') if hasattr(row, 'get') else getattr(row, pos_col, '')
        
        return build_player_id(name, team, position)
    except (AttributeError, KeyError):
        return ""