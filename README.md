# NFL GPP SimLab

Quick-start for local development.

## Setup

- Python 3.11+ recommended (project supports 3.10–3.12)
- Create and activate a virtual environment, then:

```bash
make dev
```

## Run tests

```bash
make test
```

## Example usage

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

Methodology reference: see docs/research/monte_carlo_football.pdf