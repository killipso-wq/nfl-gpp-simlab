"""NFL GPP SimLab - Monte Carlo simulation for NFL DFS optimization."""

__version__ = "0.1.0"

from .config import MonteCarloConfig
from .metrics import summarize
from .simulator import MonteCarloSimulator

__all__ = ["MonteCarloConfig", "MonteCarloSimulator", "summarize"]
