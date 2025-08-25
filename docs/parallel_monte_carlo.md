# Parallel Monte Carlo Simulation

This implementation provides high-performance, deterministic Monte Carlo simulations with parallel execution support.

## Features

### Parallel Execution
- **CPU-bound parallelism** using `ProcessPoolExecutor`
- **Deterministic results** regardless of `n_jobs` setting
- **Cross-platform compatibility** (Ubuntu, macOS, Windows)
- **Automatic CPU detection** and limiting

### Configuration

```python
from src.simulator.config import MonteCarloConfig
from src.simulator.monte_carlo import MonteCarloSimulator

# Basic configuration
config = MonteCarloConfig(
    n_trials=10000,        # Number of simulation trials
    n_jobs=4,              # Parallel workers (default: 1)
    base_seed=42,          # Reproducible seed (optional)
    show_progress=True     # Progress bar (auto-disabled for n_jobs > 1)
)

simulator = MonteCarloSimulator(config)
results = simulator.run_simulation(your_simulation_function)
```

### Environment Variables

Set the number of parallel workers via environment variable:

```bash
export NFL_GPP_SIMLAB_N_JOBS=4
python your_script.py  # Will use 4 workers by default
```

### Deterministic Seeding

The simulator ensures **identical results** across execution modes:

- `n_jobs=1` vs `n_jobs=4` with same `base_seed` → identical outputs
- Repeated runs with same configuration → identical outputs  
- Different `base_seed` values → different outputs

This is achieved through per-trial seeding using `numpy.random.SeedSequence`.

## Performance Considerations

### When to Use Parallel Execution

✅ **Good candidates:**
- Large trial counts (1000+ trials)
- CPU-intensive simulation functions
- Multi-core systems available

❌ **Poor candidates:**
- Small trial counts (< 100 trials) 
- I/O-bound operations
- Simple calculations with high overhead

### Scaling Behavior

- **n_jobs** is automatically clamped to available CPU count
- **Work distribution** is near-equal across workers
- **Memory usage** scales with number of workers
- **Progress bars** are disabled automatically for clean output

## Example Usage

```python
# Run example
python example.py
```

This demonstrates:
- Sequential vs parallel execution comparison
- Determinism verification
- Environment variable configuration
- Performance measurement

## Testing

Run the comprehensive test suite:

```bash
pip install pytest
python -m pytest tests/ -v
```

Tests cover:
- Determinism across execution modes
- Environment variable handling
- Edge cases and error conditions
- Cross-platform compatibility