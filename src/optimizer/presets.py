"""
GPP strategy presets for different contest sizes and strategies
"""

from typing import Dict, Any


def get_gpp_presets() -> Dict[str, Dict[str, Any]]:
    """
    Returns predefined GPP preset configurations
    """
    presets = {
        "Solo Entry": {
            "description": "Conservative settings for single-entry contests",
            "num_lineups": 1,
            "salary_min_spend": 49500,
            "qb_stack_min": 1,
            "qb_stack_max": 2,
            "bring_back_count": 1,
            "max_players_per_team": 4,
            "max_total_ownership": 600,
            "max_player_exposure": 100,
            "projection_variance": 0.05,
            "min_unique_players": 9,  # N/A for single lineup
            "strategy_notes": "Low variance, high floor plays"
        },
        
        "20-max": {
            "description": "Moderate diversification for 20-max contests",
            "num_lineups": 20,
            "salary_min_spend": 49000,
            "qb_stack_min": 1,
            "qb_stack_max": 2,
            "bring_back_count": 1,
            "max_players_per_team": 4,
            "max_total_ownership": 400,
            "max_player_exposure": 30,
            "projection_variance": 0.15,
            "min_unique_players": 3,
            "strategy_notes": "Balanced approach with moderate correlation"
        },
        
        "150-max": {
            "description": "High diversification for large-field contests",
            "num_lineups": 150,
            "salary_min_spend": 48500,
            "qb_stack_min": 1,
            "qb_stack_max": 3,
            "bring_back_count": 0,  # Less bring-back for more variety
            "max_players_per_team": 5,
            "max_total_ownership": 350,
            "max_player_exposure": 15,
            "projection_variance": 0.20,
            "min_unique_players": 4,
            "strategy_notes": "High ceiling plays, aggressive stacking"
        }
    }
    
    return presets


def get_preset_by_name(preset_name: str) -> Dict[str, Any]:
    """
    Get a specific preset configuration by name
    """
    presets = get_gpp_presets()
    return presets.get(preset_name, presets["20-max"])  # Default to 20-max


def get_site_specific_adjustments(site: str) -> Dict[str, Any]:
    """
    Get site-specific adjustments to apply to presets
    """
    adjustments = {
        "DraftKings": {
            "salary_cap": 50000,
            "roster_template": {
                "QB": 1, "RB": 2, "WR": 3, "TE": 1, "FLEX": 1, "DST": 1
            },
            "total_players": 9,
            "ppr_scoring": True,
            "strategy_notes": "Full PPR scoring, emphasis on target share"
        },
        
        "FanDuel": {
            "salary_cap": 60000,
            "roster_template": {
                "QB": 1, "RB": 2, "WR": 3, "TE": 1, "FLEX": 1, "K": 1, "DST": 1
            },
            "total_players": 9,
            "ppr_scoring": False,
            "strategy_notes": "No PPR, kicker variance, target rushing upside"
        }
    }
    
    return adjustments.get(site, adjustments["DraftKings"])


def apply_preset_to_constraints(
    preset_name: str,
    site: str = "DraftKings",
    custom_overrides: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Apply a preset configuration and return complete constraints dictionary
    """
    # Get base preset
    preset = get_preset_by_name(preset_name)
    
    # Get site adjustments
    site_adjustments = get_site_specific_adjustments(site)
    
    # Build constraints dictionary
    constraints = {
        # Basic settings
        "num_lineups": preset["num_lineups"],
        "salary_cap": site_adjustments["salary_cap"],
        "min_salary": preset["salary_min_spend"],
        
        # Position settings (from site)
        "roster_template": site_adjustments["roster_template"],
        "total_players": site_adjustments["total_players"],
        
        # Stacking rules
        "qb_stack_min": preset["qb_stack_min"],
        "qb_stack_max": preset["qb_stack_max"],
        "bring_back_count": preset["bring_back_count"],
        "max_players_per_team": preset["max_players_per_team"],
        
        # Ownership limits
        "max_total_ownership": preset["max_total_ownership"],
        "max_player_exposure": preset["max_player_exposure"],
        
        # Randomness/diversity
        "projection_variance": preset["projection_variance"],
        "min_unique_players": preset["min_unique_players"],
        
        # Metadata
        "preset_name": preset_name,
        "site": site,
        "strategy_notes": preset["strategy_notes"],
        "site_notes": site_adjustments["strategy_notes"]
    }
    
    # Apply custom overrides if provided
    if custom_overrides:
        constraints.update(custom_overrides)
    
    return constraints


def get_preset_descriptions() -> Dict[str, str]:
    """
    Get user-friendly descriptions of each preset
    """
    presets = get_gpp_presets()
    return {
        name: config["description"] 
        for name, config in presets.items()
    }


def validate_constraints(constraints: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate constraint settings and return (is_valid, error_messages)
    """
    errors = []
    
    # Check required fields
    required_fields = [
        "salary_cap", "min_salary", "qb_stack_min", "qb_stack_max",
        "max_players_per_team", "projection_variance"
    ]
    
    for field in required_fields:
        if field not in constraints:
            errors.append(f"Missing required constraint: {field}")
    
    # Validate ranges
    if "salary_cap" in constraints and "min_salary" in constraints:
        if constraints["min_salary"] >= constraints["salary_cap"]:
            errors.append("Minimum salary must be less than salary cap")
    
    if "qb_stack_min" in constraints and "qb_stack_max" in constraints:
        if constraints["qb_stack_min"] > constraints["qb_stack_max"]:
            errors.append("QB stack minimum cannot exceed maximum")
    
    if "projection_variance" in constraints:
        if constraints["projection_variance"] < 0 or constraints["projection_variance"] > 1:
            errors.append("Projection variance must be between 0 and 1")
    
    if "max_player_exposure" in constraints:
        if constraints["max_player_exposure"] < 1 or constraints["max_player_exposure"] > 100:
            errors.append("Max player exposure must be between 1 and 100")
    
    return len(errors) == 0, errors


def get_strategy_tips(preset_name: str, site: str) -> Dict[str, str]:
    """
    Get strategy tips for a specific preset and site combination
    """
    preset = get_preset_by_name(preset_name)
    site_info = get_site_specific_adjustments(site)
    
    tips = {
        "general": preset["strategy_notes"],
        "site_specific": site_info["strategy_notes"],
        "stacking": f"Target {preset['qb_stack_min']}-{preset['qb_stack_max']} stack with bring-back: {preset['bring_back_count']}",
        "ownership": f"Max total ownership: {preset['max_total_ownership']}%, individual exposure: {preset['max_player_exposure']}%",
        "variance": f"Projection randomness: {preset['projection_variance']:.0%} to create lineup diversity"
    }
    
    # Add preset-specific tips
    if preset_name == "Solo Entry":
        tips["focus"] = "Prioritize high floor players with solid target share and usage"
    elif preset_name == "20-max":
        tips["focus"] = "Balance floor and ceiling with moderate correlation plays"
    elif preset_name == "150-max":
        tips["focus"] = "Target high ceiling, low-owned players with leverage spots"
    
    return tips