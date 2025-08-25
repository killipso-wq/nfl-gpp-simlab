import numpy as np
from nfl_gpp_simlab import MonteCarloConfig, MonteCarloSimulator


def test_simulator_shapes_and_stats():
    cfg = MonteCarloConfig(n_trials=100, random_seed=123)
    sim = MonteCarloSimulator(cfg)

    def sample_fn(rng: np.random.Generator):
        # Example: two metrics per trial drawn from normal distributions
        return np.array([rng.normal(0, 1), rng.normal(10, 2)])

    out = sim.simulate(sample_fn)
    assert out.shape == (cfg.n_trials, 2)

    stats = sim.summarize(out)
    assert set(stats) == {"mean", "std", "q05", "q50", "q95"}
    for arr in stats.values():
        assert arr.shape == (2,)