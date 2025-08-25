"""
Name normalization utilities for consistent player IDs.
"""
import re


def normalize_name(name: str) -> str:
    """
    Normalize a player name according to README specifications.
    
    Args:
        name: Raw player name
        
    Returns:
        Normalized name (uppercase, punctuation removed, suffixes dropped, spaces collapsed)
        
    Normalization rules per README §5:
    - NORMALIZEDNAME = uppercase, punctuation removed, suffixes (JR/SR/II/III/IV/V) dropped, spaces collapsed
    """
    if not name:
        return ""
    
    # Convert to uppercase
    normalized = name.upper()
    
    # Remove suffixes (JR, SR, II, III, IV, V)
    suffixes = [r'\s+JR\.?$', r'\s+SR\.?$', r'\s+II$', r'\s+III$', r'\s+IV$', r'\s+V$']
    for suffix_pattern in suffixes:
        normalized = re.sub(suffix_pattern, '', normalized)
    
    # Remove punctuation (keep letters, numbers, and spaces for now)
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Collapse multiple spaces into single spaces and strip
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Replace remaining spaces with empty string to create single token
    normalized = normalized.replace(' ', '')
    
    return normalized


def build_player_id(team: str, position: str, name: str) -> str:
    """
    Build a player ID in the format TEAM_POS_NORMALIZEDNAME.
    
    Args:
        team: Team abbreviation
        position: Player position
        name: Player name
        
    Returns:
        Player ID string in format "TEAM_POS_NORMALIZEDNAME"
    """
    team = team.upper() if team else "UNK"
    position = position.upper() if position else "UNK"
    normalized_name = normalize_name(name)
    
    return f"{team}_{position}_{normalized_name}"