# Monte Carlo Methodology Summary

This document summarizes the Monte Carlo methodology from the research PDF ([monte_carlo_football.pdf](monte_carlo_football.pdf)) and maps PDF nomenclature to CLI commands, code implementation, and output formats.

## Methodology Overview from PDF

### Core Estimators

**Sample Statistics** (from T simulation trials):
- **Sample Mean**: x̄ = (1/T) Σ xᵢ 
- **Unbiased Sample Variance**: s² = (1/(T-1)) Σ (xᵢ - x̄)²
- **Sample Standard Deviation**: s = √s²
- **Standard Error of Mean**: SE = s/√T
- **Empirical Quantiles**: p10, p75, p90, p95 from sorted simulation draws

**Confidence Intervals** (when normality assumptions hold):
- Normal-approximation: x̄ ± z_{α/2} × SE
- Bootstrap percentile method for non-normal distributions

### PDF Terminology Mapping to Code

| PDF Term | Code Variable | CLI Parameter | Output Field |
|----------|---------------|---------------|--------------|
| T (trials) | `n_sims` | `--sims` | `metadata.json: sims` |
| Random seed | `random_seed` | `--seed` | `metadata.json: seed` |
| X_i (draw i) | `sim_draws[i]` | N/A | Individual simulation |
| x̄ (sample mean) | `sim_mean` | N/A | `sim_players.csv: sim_mean` |
| Q₁₀ (10th percentile) | `floor_p10` | N/A | `sim_players.csv: floor_p10` |
| Q₇₅ (75th percentile) | `p75` | N/A | `sim_players.csv: p75` |
| Q₉₀ (90th percentile) | `ceiling_p90` | N/A | `sim_players.csv: ceiling_p90` |
| Q₉₅ (95th percentile) | `p95` | N/A | `sim_players.csv: p95` |
| s² (sample variance) | `sim_variance` | N/A | Internal calculation |
| s (sample std dev) | `sim_std` | N/A | `compare.csv: sim_std` |
| SE (standard error) | `std_error` | N/A | Internal/diagnostic use |

## Estimator Implementation

### Mean Estimation
```python
# Unbiased sample mean from T trials
sim_mean = np.mean(simulation_draws, axis=0)
```

### Variance and Standard Deviation
```python
# Unbiased sample variance (Bessel's correction)
sim_variance = np.var(simulation_draws, axis=0, ddof=1)
sim_std = np.sqrt(sim_variance)

# Standard error of the mean
std_error = sim_std / np.sqrt(n_trials)
```

### Quantile Estimation
```python
# Empirical quantiles from simulation draws
quantiles = np.percentile(simulation_draws, [10, 75, 90, 95], axis=0)
floor_p10, p75, ceiling_p90, p95 = quantiles
```

### Exceedance Probabilities
```python
# Boom probability: P(X >= boom_threshold)
boom_prob = np.mean(simulation_draws >= boom_threshold, axis=0)

# Beat site probability: P(X >= site_fpts)  
beat_site_prob = np.mean(simulation_draws >= site_fpts, axis=0)
```

## Reproducibility and Determinism

### Seed Strategy from PDF
The PDF emphasizes reproducible pseudo-random number generation:

1. **Base Seed**: Fixed seed for experiment reproducibility
2. **Child Seeds**: Derived seeds for different random number streams
3. **Generator State**: Consistent RNG state across platforms

### Implementation Mapping

```python
# Base seed from CLI parameter
base_seed = args.seed  # --seed parameter

# Child seed generation for different RNG streams
np.random.seed(base_seed)
team_seed = np.random.randint(0, 2**31)
player_seed = np.random.randint(0, 2**31)
environment_seed = np.random.randint(0, 2**31)

# Individual generator instances
team_rng = np.random.RandomState(team_seed)
player_rng = np.random.RandomState(player_seed)
env_rng = np.random.RandomState(environment_seed)
```

### Cross-Platform Stability Notes

**Data Type Consistency:**
- Use `np.float64` for all intermediate calculations
- Avoid `np.float32` to prevent precision-dependent rounding differences
- Cast final outputs to consistent types before saving

**Numerical Stability:**
- Clamp negative values to zero: `np.maximum(0, simulation_draws)`
- Use stable sorting algorithms for quantile calculation
- Document any OS-specific behavior in metadata.json

**Reproducibility Verification:**
```python
# Test determinism across runs
assert np.allclose(run1_output, run2_output, rtol=1e-14)
```

## Distribution Families

### Supported Distributions (from PDF)

**Continuous Distributions:**
- Normal: `np.random.normal(loc, scale)`
- Log-normal: `np.random.lognormal(mean, sigma)`
- Beta: `np.random.beta(alpha, beta)`
- Gamma: `np.random.gamma(shape, scale)`

**Discrete Distributions:**
- Poisson: `np.random.poisson(lam)`
- Binomial: `np.random.binomial(n, p)`
- Multinomial: `np.random.multinomial(n, pvals)`

**Position-Specific Mappings:**

| Position | Primary Distribution | Parameters | Output Mapping |
|----------|---------------------|------------|----------------|
| QB | Normal (passing yards) | μ=prior_mean, σ=prior_std | DK points w/ bonuses |
| RB | Log-normal (rushing yards) | μ=log_mean, σ=log_std | DK points w/ receptions |
| WR/TE | Beta-Binomial (targets) | α=usage_alpha, β=usage_beta | DK points w/ bonuses |
| DST | Poisson (sacks/turnovers) | λ=opponent_rate | DK scoring system |

## Error Bounds and Confidence

### Monte Carlo Standard Error

The PDF provides formula for MC standard error:
- **SE_MC** = σ/√T where σ is true population standard deviation
- **Estimated SE**: s/√T using sample standard deviation

### Confidence Interval Construction

**Normal Approximation** (when CLT applies):
```python
# 95% confidence interval for mean
ci_lower = sim_mean - 1.96 * (sim_std / np.sqrt(n_trials))
ci_upper = sim_mean + 1.96 * (sim_std / np.sqrt(n_trials))
```

**Bootstrap Percentile Method** (for non-normal):
```python
# Resample from simulation draws
bootstrap_means = []
for _ in range(1000):
    resample = np.random.choice(simulation_draws, size=len(simulation_draws))
    bootstrap_means.append(np.mean(resample))

# Percentile confidence interval
ci_lower = np.percentile(bootstrap_means, 2.5)
ci_upper = np.percentile(bootstrap_means, 97.5)
```

## Validation and Diagnostics

### Coverage Testing (from PDF)

**Empirical Coverage Rate:**
- Theoretical: For p% confidence interval, coverage should be ~p%
- Implementation: Compare sim predictions to actual outcomes when available

```python
# Coverage diagnostic for [p10, p90] interval
coverage_p10_p90 = np.mean((actual_values >= floor_p10) & 
                           (actual_values <= ceiling_p90))
# Should be approximately 0.80 for proper calibration
```

### Calibration Metrics

**Mean Absolute Error (MAE):**
```python
mae = np.mean(np.abs(sim_mean - actual_values))
```

**Root Mean Square Error (RMSE):**
```python
rmse = np.sqrt(np.mean((sim_mean - actual_values)**2))
```

**Pearson Correlation:**
```python
correlation = np.corrcoef(sim_mean, actual_values)[0, 1]
```

## Output Format Specifications

### CSV Output Schema

**sim_players.csv** (primary Monte Carlo outputs):
```
player_id,PLAYER,POS,TEAM,OPP,sim_mean,floor_p10,p75,ceiling_p90,p95,boom_prob,rookie_fallback,SAL
```

**diagnostics_summary.csv** (validation metrics):
```
position,count,mae,rmse,correlation,coverage_p10_p90,rookie_count
```

**metadata.json** (reproducibility tracking):
```json
{
  "methodology": "monte_carlo_pdf",
  "sims": 10000,
  "seed": 12345,
  "run_id": "uuid-string",
  "git_commit": "abc123...",
  "n_players": 150,
  "n_rookies": 5,
  "coverage_overall": 0.823
}
```

## Integration with Simulation Engine

### Command-Line Interface Mapping

**PDF Algorithm Parameters → CLI:**
```bash
# Number of trials T
--sims 10000

# Random seed for reproducibility  
--seed 12345

# Input data (players and priors)
--players-site players.csv
--team-priors team_priors.csv
--player-priors player_priors.csv

# Output directory
--out data/sim_week
```

### Prior Distribution Parameters

**Team-Level Priors** (from 2023-2024 baseline):
- `pace_mean`, `pace_std`: Plays per game distribution
- `pass_rate_mean`, `pass_rate_std`: Team passing tendency
- `efficiency_alpha`, `efficiency_beta`: Success rate Beta parameters

**Player-Level Priors:**
- `usage_alpha`, `usage_beta`: Target/carry share Beta parameters  
- `efficiency_mean`, `efficiency_std`: Yards per touch Normal parameters
- `td_rate_alpha`, `td_rate_beta`: Touchdown rate Beta parameters

### Environment Adjustments

**Game-Level Factors** (PDF Section 4.2 equivalent):
- Over/Under total: Scales team pace and scoring expectations
- Spread: Adjusts relative team performance and game script
- Moneyline: Additional game script and blowout probability hints
- Team totals: Direct implied scoring when available

## References to PDF Sections

- **Section 2**: Basic Monte Carlo theory → Estimator implementation above
- **Section 3**: Distribution selection → Position-specific mappings
- **Section 4**: Environment factors → Game adjustments in simulator
- **Section 5**: Validation methods → Coverage and calibration diagnostics
- **Appendix A**: Reproducibility → Seed strategy and platform notes
- **Appendix B**: Error bounds → Confidence interval construction

## Implementation Notes

1. **PDF Figure 1** (simulation workflow) maps to `game_simulator.py` main loop
2. **PDF Table 2** (position distributions) implemented in position-specific sampling functions
3. **PDF Algorithm 1** (MC estimation) corresponds to `summarize_simulations()` function
4. **PDF Validation framework** (Section 5) maps to `diagnostics.py` module

This methodology ensures that our implementation follows established Monte Carlo best practices while remaining faithful to the research foundation provided in the PDF.