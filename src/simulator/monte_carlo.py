"""Monte Carlo simulator with parallel execution and deterministic seeding."""

import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Tuple

import numpy as np
from tqdm import tqdm

from .config import MonteCarloConfig


def _run_simulation_batch(
    trial_seeds: List[int],
    simulation_func: Callable,
    simulation_args: Tuple,
    simulation_kwargs: Dict[str, Any]
) -> List[Any]:
    """Run a batch of simulations with specific seeds for each trial.

    This function must be at module level to be picklable for Windows compatibility.

    Args:
        trial_seeds: List of seeds for each trial in this batch
        simulation_func: Function to run for each trial
        simulation_args: Positional arguments for simulation_func
        simulation_kwargs: Keyword arguments for simulation_func

    Returns:
        List of simulation results
    """
    results = []
    for seed in trial_seeds:
        # Create a unique RNG for this specific trial
        rng = np.random.Generator(np.random.PCG64(seed))

        # Pass the trial's RNG to the simulation function
        kwargs = simulation_kwargs.copy()
        kwargs['rng'] = rng
        result = simulation_func(*simulation_args, **kwargs)
        results.append(result)

    return results


class MonteCarloSimulator:
    """Monte Carlo simulator with parallel execution and deterministic seeding."""

    def __init__(self, config: MonteCarloConfig):
        """Initialize the simulator.

        Args:
            config: Configuration for the simulation
        """
        self.config = config

    def run_simulation(
        self,
        simulation_func: Callable,
        *args,
        **kwargs
    ) -> List[Any]:
        """Run Monte Carlo simulation trials.

        Args:
            simulation_func: Function to run for each trial. Must accept 'rng'
                           parameter for the numpy random generator.
            *args: Positional arguments to pass to simulation_func
            **kwargs: Keyword arguments to pass to simulation_func

        Returns:
            List of simulation results in deterministic order
        """
        if self.config.n_jobs == 1:
            return self._run_sequential(simulation_func, args, kwargs)
        else:
            return self._run_parallel(simulation_func, args, kwargs)

    def _run_sequential(
        self,
        simulation_func: Callable,
        args: Tuple,
        kwargs: Dict[str, Any]
    ) -> List[Any]:
        """Run simulations sequentially."""
        # Generate seeds for each trial
        trial_seeds = self._generate_trial_seeds()

        results = []
        iterator = enumerate(trial_seeds)

        if self.config.show_progress:
            iterator = tqdm(iterator, total=len(trial_seeds), desc="Running simulations")

        for i, seed in iterator:
            # Create RNG for this specific trial
            rng = np.random.Generator(np.random.PCG64(seed))
            kwargs_with_rng = kwargs.copy()
            kwargs_with_rng['rng'] = rng
            result = simulation_func(*args, **kwargs_with_rng)
            results.append(result)

        return results

    def _run_parallel(
        self,
        simulation_func: Callable,
        args: Tuple,
        kwargs: Dict[str, Any]
    ) -> List[Any]:
        """Run simulations in parallel with deterministic seeding."""
        # Generate seeds for each trial
        trial_seeds = self._generate_trial_seeds()

        # Split trial seeds into chunks for each worker
        batch_sizes = self._calculate_batch_sizes()
        seed_batches = []
        start_idx = 0

        for batch_size in batch_sizes:
            if batch_size > 0:
                seed_batch = trial_seeds[start_idx:start_idx + batch_size]
                seed_batches.append(seed_batch)
                start_idx += batch_size

        # Prepare tasks for workers
        tasks = []
        for seed_batch in seed_batches:
            if seed_batch:  # Only add non-empty batches
                tasks.append((seed_batch, simulation_func, args, kwargs))

        # Run tasks in parallel
        results = []

        # Use spawn method on all platforms for consistency
        ctx = mp.get_context('spawn')

        with ProcessPoolExecutor(
            max_workers=len(tasks),  # Use actual number of non-empty batches
            mp_context=ctx
        ) as executor:
            # Submit all tasks
            future_to_batch = {}
            for i, task in enumerate(tasks):
                future = executor.submit(_run_simulation_batch, *task)
                future_to_batch[future] = i

            # Collect results in order
            batch_results = [None] * len(tasks)

            for future in as_completed(future_to_batch):
                batch_idx = future_to_batch[future]
                batch_results[batch_idx] = future.result()

        # Flatten results while preserving order
        for batch_result in batch_results:
            if batch_result:
                results.extend(batch_result)

        return results

    def _generate_trial_seeds(self) -> List[int]:
        """Generate deterministic seeds for each trial."""
        if self.config.base_seed is not None:
            seed_seq = np.random.SeedSequence(self.config.base_seed)
        else:
            seed_seq = np.random.SeedSequence()

        # Generate one seed per trial for deterministic results
        trial_seed_sequences = seed_seq.spawn(self.config.n_trials)
        # Generate a unique integer from each sequence
        seeds = []
        for seq in trial_seed_sequences:
            # Use the sequence to generate a random integer as the seed
            temp_rng = np.random.Generator(np.random.PCG64(seq))
            seeds.append(int(temp_rng.integers(0, 2**32)))
        return seeds

    def _calculate_batch_sizes(self) -> List[int]:
        """Calculate batch sizes for workers to ensure near-equal distribution."""
        base_size = self.config.n_trials // self.config.n_jobs
        remainder = self.config.n_trials % self.config.n_jobs

        batch_sizes = [base_size] * self.config.n_jobs

        # Distribute remainder across first workers
        for i in range(remainder):
            batch_sizes[i] += 1

        return batch_sizes


# Example simulation function for testing
def sample_simulation_trial(mean: float = 0.0, std: float = 1.0, rng: np.random.Generator = None) -> float:
    """Example simulation trial function.

    Args:
        mean: Mean of the normal distribution
        std: Standard deviation of the normal distribution
        rng: Random number generator

    Returns:
        Random sample from normal distribution
    """
    if rng is None:
        rng = np.random.default_rng()

    return rng.normal(mean, std)
