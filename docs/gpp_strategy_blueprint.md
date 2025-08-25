# GPP Strategy Blueprint

This document outlines the comprehensive GPP (Guaranteed Prize Pool) strategy framework for the Optimizer tab, including stacking rules, ownership leverage, salary management, and constraint presets. This blueprint will be implemented as one-click presets in the post-simulator MVP phase.

## Overview

The GPP Strategy Blueprint provides tournament-focused constraint templates that apply simulation outputs (boom scores, value metrics, ownership data) to generate differentiated lineups across different contest sizes and formats.

**Contest Size Categories:**
- **Small Field (SF)**: <500 entries - Higher ownership tolerance, focus on ceiling
- **Mid Field (MF)**: 500-5,000 entries - Balanced approach, selective leverage  
- **Large Field (LF)**: 5,000+ entries - Maximum differentiation, dart requirements

## Core Stacking Strategy

### QB Stacking Requirements

**Always Stack QB** (non-negotiable):
- Every lineup must include exactly 1 QB with ≥1 correlating teammate
- Never play QB in isolation due to positive correlation with passing game

**Stack Size by Contest:**
```
Small Field:  QB + 1-2 (flexible based on salary/ownership)
Mid Field:    QB + 1-2 (favor 2 when leverage exists)  
Large Field:  QB + 2-3 (maximum correlation capture)
```

**Primary Stack Compositions:**
1. **QB + WR1** - Most common, reliable correlation
2. **QB + WR2/WR3** - Leverage play when WR1 highly owned
3. **QB + TE** - Lower ownership, good correlation in red zone
4. **QB + WR + TE** - Double stack, higher ceiling potential
5. **QB + 2 WR** - Maximum passing correlation, salary permitting

### Bring-Back Strategy

**Contest Size Guidelines:**
- **Small Field**: Bring-back optional (0-1 players)
- **Mid Field**: Bring-back recommended (1 player)  
- **Large Field**: Bring-back common (1 player, occasionally 0 for max differentiation)

**Bring-Back Player Selection:**
```python
# Optimal bring-back characteristics
bring_back_criteria = {
    'position': ['WR', 'TE', 'RB'],  # Prefer skill positions
    'ownership': 'lower_than_stack_players',  # Leverage opportunity
    'boom_score': '>= 60',  # Upside potential required
    'game_correlation': 'negative_to_stack_team'  # Game script hedge
}
```

**Common Bring-Back Patterns:**
1. **QB/WR stack + Opponent WR** - Most common, game total play
2. **QB/WR stack + Opponent TE** - Lower ownership alternative
3. **QB/WR stack + Opponent RB** - Game script hedge (if RB catches passes)

### Mini-Stack Integration

**Secondary Correlations** (beyond primary QB stack):
- **WR vs Opponent WR/TE**: Same-game shootout potential
- **RB + DST**: Positive correlation when defense creates short fields
- **RB vs Opponent WR**: Negative correlation, game script hedge
- **TE + DST**: Red zone correlation in defensive games

**Implementation in Constraints:**
```python
mini_stack_rules = {
    'same_game_players': {
        'min': 3,  # QB stack + bring-back minimum
        'max': 6,  # Avoid over-concentration
        'preferred': 4  # Sweet spot for most contests
    },
    'correlation_requirements': {
        'QB_passing_game': 'required',  # Always stack QB
        'game_total_exposure': 'preferred',  # Bring-back when possible
        'negative_correlation': 'optional'  # Game script hedges
    }
}
```

## Ownership and Leverage Strategy

### Ownership Bands by Contest Size

**Total Ownership Targets** (sum of all players' RST%):

| Contest Size | Conservative | Balanced | Aggressive |
|-------------|-------------|----------|------------|
| **Small Field** | 100-140% | 80-120% | 60-100% |
| **Mid Field** | 80-110% | 60-90% | 40-70% |
| **Large Field** | 50-80% | 30-60% | 15-45% |

**Individual Player Ownership Caps:**

| Contest Size | High-Owned Cap | Mid-Owned Cap | Low-Owned Focus |
|-------------|----------------|---------------|-----------------|
| **Small Field** | ≤40% allowed | ≤25% preferred | No requirement |
| **Mid Field** | ≤30% allowed | ≤20% preferred | ≥1 under 15% |
| **Large Field** | ≤20% allowed | ≤15% preferred | ≥2 under 10% |

### Leverage Identification

**High-Leverage Scenarios:**
```python
leverage_opportunities = {
    'teammate_leverage': {
        'description': 'Stack QB with WR2/TE when WR1 highly owned',
        'trigger': 'primary_target_ownership > 25%',
        'action': 'pivot_to_secondary_target'
    },
    'salary_tier_leverage': {
        'description': 'Fade expensive chalk for multiple mid-tier players', 
        'trigger': 'expensive_player_ownership > 30%',
        'action': 'allocate_salary_to_multiple_players'
    },
    'game_script_leverage': {
        'description': 'Target negative correlation when consensus expects blowout',
        'trigger': 'popular_stack_ownership > 40%',
        'action': 'bring_back_opponent_or_fade_game'
    }
}
```

**Ownership Boost Factors** (from simulation):
- **boom_score ≥ 85**: Play regardless of ownership (elite upside)
- **boom_score 70-84**: Prefer ownership ≤ 20%
- **boom_score 50-69**: Require ownership ≤ 15%
- **boom_score < 50**: Only if extreme value or ownership ≤ 5%

## Salary Management and Duplication Avoidance

### Salary Leftover Strategy

**Target Leftover by Contest Size:**
```
Small Field:  $0-200     # Spend near maximum
Mid Field:    $200-800   # Slight inefficiency for differentiation
Large Field:  $300-1500  # Significant leftover to avoid common builds
```

**Salary Allocation Guidelines:**
- **Stars and Scrubs**: 1-2 premium players + value plays to fill roster
- **Balanced**: Spread salary more evenly across roster
- **All-Value**: Focus on value_per_1k, target 6+ players with strong value

### Duplication Avoidance

**Common Build Patterns to Avoid:**
1. **Chalk Stack + Obvious Bring-Back**: Most popular QB stack with most popular opponent player
2. **Price Point Overlap**: Multiple players in same $8,500-$9,000 range
3. **Ownership Clusters**: 4+ players all with 20%+ ownership
4. **Site Darling Stacks**: Stacks heavily promoted by major DFS content creators

**Differentiation Tactics:**
```python
differentiation_strategies = {
    'contrarian_stacking': {
        'method': 'Stack lower-owned QB with higher-owned pass catcher',
        'risk': 'Medium',
        'leverage': 'High when QB outperforms ownership'
    },
    'salary_inefficiency': {
        'method': 'Leave $500+ to avoid most common salary configurations',
        'risk': 'Low',
        'leverage': 'Medium through unique roster construction'
    },
    'position_pivots': {
        'method': 'TE over WR3, RB3 over WR4 when correlation similar',
        'risk': 'Low',
        'leverage': 'Medium through positional uniqueness'
    }
}
```

## Simulation-Driven Constraints

### Boom Score Requirements

**Boom Score Targets by Contest:**
- **Small Field**: ≥1 player with boom_score ≥ 80 (ceiling focus)
- **Mid Field**: ≥2 players with boom_score ≥ 70 (balanced upside)
- **Large Field**: ≥3 players with boom_score ≥ 70, including ≥1 dart (maximum upside)

**Dart Requirements** (dart_flag = True):
- **Small/Mid Field**: Darts optional, focus on value_per_1k
- **Large Field**: ≥1 dart required (RST% ≤ 5% AND boom_score ≥ 70)

### Value Constraints

**Minimum Value Thresholds:**
```python
value_requirements = {
    'team_average_value': {
        'small_field': 2.2,   # Lower bar, focus on ceiling
        'mid_field': 2.4,     # Balanced value requirement
        'large_field': 2.6    # Higher bar for efficiency
    },
    'anchor_value_players': {
        'definition': 'value_per_1k >= 3.0',
        'small_field': 1,     # At least 1 strong value play
        'mid_field': 2,       # 2+ strong value plays
        'large_field': 3      # 3+ strong value plays required
    }
}
```

**Ceiling Value Integration:**
```python
# Prioritize ceiling value in tournament formats
ceiling_value_bonus = {
    'small_field': 0.1,   # 10% bonus for ceil_per_1k in scoring
    'mid_field': 0.15,    # 15% bonus for ceiling value
    'large_field': 0.2    # 20% bonus, significant ceiling focus
}
```

## Position-Specific Constraints

### Quarterback Strategy

**QB Selection Criteria:**
```python
qb_requirements = {
    'boom_score': '>= 65',  # Minimum upside threshold
    'pass_attempts_projected': '>= 35',  # Volume requirement
    'game_total': '>= 44',  # Avoid low-scoring games
    'ceiling_p90': '>= 28'  # Tournament ceiling requirement
}

# Contest-specific QB ownership
qb_ownership_caps = {
    'small_field': 'no_cap',     # Play best QB regardless
    'mid_field': '<= 35%',       # Some differentiation
    'large_field': '<= 25%'      # Significant differentiation
}
```

### Running Back Strategy

**RB Position Constraints:**
```python
rb_strategy = {
    'max_per_team': 1,  # Avoid RB committees from same team
    'stacking_with_qb': {
        'allowed': True,
        'conditions': 'receiving_upside OR red_zone_vulture'
    },
    'bring_back_rb': {
        'conditions': 'pass_catching_role AND ownership <= 15%'
    }
}

# RB boom requirements by contest
rb_boom_requirements = {
    'small_field': 'boom_score >= 50 OR value_per_1k >= 3.2',
    'mid_field': 'boom_score >= 60 OR value_per_1k >= 3.0',  
    'large_field': 'boom_score >= 65 OR dart_flag == True'
}
```

### Wide Receiver Strategy

**WR Stacking Priorities:**
```python
wr_stacking_rules = {
    'primary_stack': {
        'positions': ['WR1', 'WR2'],
        'ownership_consideration': 'high',
        'boom_score_minimum': 60
    },
    'leverage_stacks': {
        'positions': ['WR2', 'WR3', 'TE'],
        'when_to_use': 'WR1_ownership > 30%',
        'boom_score_minimum': 70  # Higher bar for leverage plays
    }
}
```

### Tight End Strategy

**TE Utilization:**
```python
te_strategy = {
    'stack_preference': {
        'with_qb': 'preferred',  # TE stacks often lower owned
        'ceiling_requirement': 'ceiling_p90 >= 18',
        'red_zone_factor': 'boost_if_rz_target_share > 20%'
    },
    'standalone_te': {
        'criteria': 'boom_score >= 75 AND value_per_1k >= 2.8',
        'max_ownership': '20%'  # Only low-owned standalone TEs
    }
}
```

### Defense (DST) Strategy

**DST Selection Framework:**
```python
dst_requirements = {
    'opponent_factors': {
        'turnover_prone_qb': 'strong_positive',
        'poor_offensive_line': 'sack_upside',
        'rookie_qb': 'mistake_potential'
    },
    'correlation_plays': {
        'with_rb': 'short_field_tds',
        'against_popular_qb_stack': 'contrarian_leverage'
    },
    'boom_thresholds': {
        'small_field': 'boom_score >= 45',
        'mid_field': 'boom_score >= 55', 
        'large_field': 'boom_score >= 65 OR dart_flag == True'
    }
}
```

## Preset Configuration Framework

### Preset Selector Options

**Contest Size Presets:**
```python
preset_configurations = {
    'Small_Field_Conservative': {
        'ownership_band': (100, 140),
        'boom_requirements': {'min_players_70_plus': 1},
        'value_requirements': {'team_avg': 2.2, 'anchors': 1},
        'salary_leftover': (0, 200),
        'differentiation': 'low'
    },
    'Small_Field_Aggressive': {
        'ownership_band': (60, 100),
        'boom_requirements': {'min_players_70_plus': 2},
        'value_requirements': {'team_avg': 2.4, 'anchors': 2},
        'salary_leftover': (100, 400),
        'differentiation': 'medium'
    },
    'Mid_Field_Balanced': {
        'ownership_band': (60, 90),
        'boom_requirements': {'min_players_70_plus': 2},
        'value_requirements': {'team_avg': 2.4, 'anchors': 2},
        'salary_leftover': (200, 600),
        'differentiation': 'medium'
    },
    'Large_Field_Max_Leverage': {
        'ownership_band': (15, 45),
        'boom_requirements': {'min_players_70_plus': 3, 'darts_required': 1},
        'value_requirements': {'team_avg': 2.6, 'anchors': 3},
        'salary_leftover': (500, 1500),
        'differentiation': 'high'
    }
}
```

### Toggle Options

**Strategy Toggles:**
```python
strategy_toggles = {
    'enforce_bring_back': {
        'description': 'Require 1 opponent player when stacking',
        'default_by_contest': {'SF': False, 'MF': True, 'LF': True}
    },
    'require_mini_stacks': {
        'description': 'Enforce secondary correlations beyond QB stack',
        'options': [0, 1, 2],  # Number of mini-stacks required
        'default_by_contest': {'SF': 0, 'MF': 1, 'LF': 1}
    },
    'salary_leftover_enforcement': {
        'description': 'Force salary inefficiency for differentiation',
        'default_by_contest': {'SF': False, 'MF': True, 'LF': True}
    },
    'require_darts': {
        'description': 'Force inclusion of dart_flag players',
        'default_by_contest': {'SF': False, 'MF': False, 'LF': True}
    }
}
```

### Slider Controls

**Adjustable Parameters:**
```python
slider_controls = {
    'ownership_band': {
        'label': 'Total Ownership Range (%)',
        'min': 15, 'max': 150, 'step': 5,
        'default_by_preset': 'varies'
    },
    'boom_threshold': {
        'label': 'Minimum Boom Score',
        'min': 40, 'max': 90, 'step': 5,
        'default': 70
    },
    'value_threshold': {
        'label': 'Minimum Value per $1k',
        'min': 2.0, 'max': 4.0, 'step': 0.1,
        'default': 2.4
    },
    'max_salary_leftover': {
        'label': 'Maximum Salary Leftover',
        'min': 0, 'max': 2000, 'step': 100,
        'default_by_contest': {'SF': 200, 'MF': 600, 'LF': 1200}
    }
}
```

## Implementation Workflow

### UI Integration (Planned Post-MVP)

**Optimizer Tab Layout:**
```
┌─────────────────────────────────────────────┐
│ GPP Presets Section                         │
├─────────────────────────────────────────────┤
│ Contest Size: [Small] [Mid] [Large]         │
│ Strategy:     [Conservative] [Balanced]     │
│              [Aggressive] [Custom]          │
├─────────────────────────────────────────────┤
│ ☑ Enforce bring-back                       │
│ ☑ Require mini-stacks (1)                  │
│ ☑ Force salary leftover                    │
│ ☐ Require darts                            │
├─────────────────────────────────────────────┤
│ Ownership Band: [30%] ──●── [80%]          │
│ Boom Threshold: [60]  ──●── [90]           │
│ Value Minimum:  [2.2] ──●── [3.0]          │
├─────────────────────────────────────────────┤
│ [Apply Preset] [Reset] [Optimize]          │
└─────────────────────────────────────────────┘
```

**Apply Preset Workflow:**
1. User selects contest size and strategy style
2. Default toggles and sliders populated
3. User adjusts parameters as needed
4. "Apply Preset" button populates constraint fields
5. Constraints remain editable for fine-tuning
6. "Optimize" button runs lineup generation with applied constraints

### Constraint Translation

**From Preset to Optimizer Constraints:**
```python
def apply_gpp_preset(preset_config, sim_outputs):
    constraints = {}
    
    # Ownership constraints
    constraints['total_ownership_min'] = preset_config['ownership_band'][0]
    constraints['total_ownership_max'] = preset_config['ownership_band'][1]
    
    # Boom score constraints
    boom_players = sim_outputs[sim_outputs['boom_score'] >= preset_config['boom_threshold']]
    constraints['required_players'] = boom_players['player_id'].tolist()
    constraints['min_boom_players'] = preset_config['boom_requirements']['min_players_70_plus']
    
    # Value constraints
    constraints['min_team_value'] = preset_config['value_requirements']['team_avg']
    constraints['min_anchor_value_players'] = preset_config['value_requirements']['anchors']
    
    # Stacking constraints
    constraints['qb_stack_required'] = True
    constraints['min_same_team'] = 2  # QB + 1
    if preset_config.get('enforce_bring_back'):
        constraints['min_opponents'] = 1
    
    # Salary constraints
    constraints['max_salary_leftover'] = preset_config['salary_leftover'][1]
    constraints['min_salary_leftover'] = preset_config['salary_leftover'][0]
    
    return constraints
```

This GPP Strategy Blueprint provides the comprehensive framework for tournament optimization, ensuring that simulation insights translate into actionable lineup construction constraints across different contest types and risk tolerances.