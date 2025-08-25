from nfl_gpp_simlab import MonteCarloConfig, MonteCarloSimulator
import numpy as np


def main() -> None:
    cfg = MonteCarloConfig(n_trials=1000, random_seed=123)
    sim = MonteCarloSimulator(cfg)

    # Example: two metrics per trial
    out = sim.simulate(lambda rng: np.array([rng.normal(0, 1), rng.normal(10, 2)]))
    stats = sim.summarize(out)

    print("mean:", stats["mean"])   # array of length 2
    print("q05:", stats["q05"])     # array of length 2
    print("q95:", stats["q95"])     # array of length 2


if __name__ == "__main__":
    main()