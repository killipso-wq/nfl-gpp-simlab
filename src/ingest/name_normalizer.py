"""
Name normalization utilities for generating stable player IDs.
Implements TEAM_POS_NORMALIZEDNAME format per Master Reference.
"""

import re
from typing import Optional


def normalize_name(name: str) -> str:
    """
    Normalize player name for stable ID generation.
    
    Rules:
    - Uppercase
    - Remove punctuation
    - Drop suffixes (JR, SR, II, III, IV, V)
    - Collapse spaces
    
    Args:
        name: Raw player name
        
    Returns:
        Normalized name string
    """
    if not name:
        return ""
    
    # Convert to uppercase
    normalized = name.upper()
    
    # Remove punctuation
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Remove common suffixes
    suffixes = ['JR', 'SR', 'II', 'III', 'IV', 'V']
    for suffix in suffixes:
        # Remove suffix at end of name (with optional spaces)
        pattern = rf'\s+{suffix}\s*$'
        normalized = re.sub(pattern, '', normalized)
    
    # Collapse multiple spaces to single space and strip
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Replace spaces with underscores for ID format
    normalized = normalized.replace(' ', '_')
    
    return normalized


def normalize_position(position: str) -> str:
    """
    Normalize position designation.
    
    Rules:
    - D → DST (defense/special teams)
    - Uppercase
    
    Args:
        position: Raw position string
        
    Returns:
        Normalized position string
    """
    if not position:
        return ""
    
    pos = position.upper().strip()
    
    # Map D to DST
    if pos == 'D':
        return 'DST'
    
    return pos


def build_player_id(team: str, position: str, name: str) -> str:
    """
    Build stable player_id in TEAM_POS_NORMALIZEDNAME format.
    
    Args:
        team: Team abbreviation
        position: Player position
        name: Player name
        
    Returns:
        Stable player ID string
    """
    if not all([team, position, name]):
        raise ValueError("Team, position, and name are all required for player_id")
    
    team_norm = team.upper().strip()
    pos_norm = normalize_position(position)
    name_norm = normalize_name(name)
    
    if not name_norm:
        raise ValueError(f"Name normalization resulted in empty string for: {name}")
    
    return f"{team_norm}_{pos_norm}_{name_norm}"


def normalize_ownership(ownership: Optional[float]) -> Optional[float]:
    """
    Normalize ownership percentage.
    
    Rules:
    - If ≤ 1: treat as fraction, multiply by 100
    - If > 1: treat as percentage
    
    Args:
        ownership: Raw ownership value
        
    Returns:
        Ownership as percentage (0-100)
    """
    if ownership is None:
        return None
    
    if ownership <= 1.0:
        return ownership * 100.0
    else:
        return ownership