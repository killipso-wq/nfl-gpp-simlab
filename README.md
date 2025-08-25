# NFL GPP SimLab

This repository contains the simulation lab for exploring NFL GPP strategies.

## How to use

Import the package in Python and run simulations programmatically. Example:

```python
from nfl_gpp_simlab import MonteCarloConfig, MonteCarloSimulator
import numpy as np

cfg = MonteCarloConfig(n_trials=1000, random_seed=123)
sim = MonteCarloSimulator(cfg)

# Example: two metrics per trial
out = sim.simulate(lambda rng: np.array([rng.normal(0, 1), rng.normal(10, 2)]))
stats = sim.summarize(out)
print(stats["mean"], stats["q05"], stats["q95"])  # arrays of length 2
```

## Continuous Integration

CI runs automatically on pull requests and on pushes to main to lint, type-check, and test the package. No local CLI is required.

Methodology reference: see docs/research/monte_carlo_football.pdf