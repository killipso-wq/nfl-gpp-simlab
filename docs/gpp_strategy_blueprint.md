# GPP Strategy Blueprint (Stacks, Correlation, Ownership, Uniqueness)

Purpose: Apply AFTER simulation during portfolio construction in the Optimizer.

Stacking
- Always stack QB; Single (QB+1) or Double (QB+2) by contest size.
- Bring-back 0–1 (LF commonly 1).
- Mini-correlations: WR vs opp WR/TE or RB vs opp WR/TE; RB+DST viable.

Ownership/leverage
- Suggested total ownership bands (sum RST%):
  - Small-field: ~80–140%
  - Mid-field: ~60–110%
  - Large-field: ~30–80%
- Limit clustering of chalk; use leverage pivots (teammates/role/salary tier).

Salary/duplication
- Small-field spend near max.
- Mid-field leave 0–800.
- Large-field leave 300–1,500 to reduce dupes.
- Avoid the most common mega-chalk stack combos without leverage.

Simulator-driven thresholds
- Darts: require ≥1 dart_flag (RST% ≤ 5 and boom_score ≥ 70) in LF.
- Boom: aim ≥2 players with boom_score ≥ 70 in LF.
- Value: include ≥1 anchor value (value_per_1k ≥ ~3.0; slate-dependent).

Optimizer constraints (examples)
- Exactly 1 QB; enforce 1–2 same-team WR/TE; bring-back 0–1.
- Ownership band by contest size; cap highly owned players (RST% ≥ 20%) count.
- Avg value_per_1k ≥ 2.4–2.6; total salary ≤ 50,000 with min leftover in LF.
- Max 1 RB per team (unless receiving RB in stack); max 4 per game unless full game-stack mode.

UI — "GPP Presets" (Optimizer tab)
- Preset selector: Small / Mid / Large
- Toggles: bring-back, mini-stacks, salary leftover, require darts
- Sliders: ownership band, boom_score threshold, value_per_1k threshold
- Flow: Apply preset → constraints populate → Optimize → Export
- Presets are editable after applying; defaults tuned over time.

Status
- Planned in Stage 3. The Optimizer will read latest Simulator outputs to apply these constraints in one click.