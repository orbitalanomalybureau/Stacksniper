"""
STACKSNIPER MLB — Base Agent Class
Each agent is a specialist that analyzes one dimension of MLB data
and contributes a weighted opinion to the simulation.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
from sports.mlb.utils.logger import get_logger

@dataclass
class AgentOpinion:
    """An agent's opinion on a player or game outcome."""
    agent_name: str
    agent_type: str
    confidence: float          # 0.0 - 1.0
    weight: float              # How much this agent's opinion matters
    projection: dict           # The actual projection data
    reasoning: str             # Why the agent made this projection
    adjustments: dict = None   # Multiplicative adjustments to baseline

class BaseAgent(ABC):
    """Abstract base class for all simulation agents."""
    def __init__(self, name: str, agent_type: str, weight: float = 1.0):
        self.name = name
        self.agent_type = agent_type
        self.weight = weight
        self.log = get_logger(f"Agent.{name}")

    @abstractmethod
    def analyze(self, context: dict) -> AgentOpinion:
        """
        Analyze the given context and produce an opinion.
        Context contains game data, player data, historical stats, etc.
        """
        pass

    def adjust_confidence(self, data_quality: float, sample_size: int) -> float:
        """Adjust confidence based on data quality and sample size."""
        size_factor = min(1.0, np.log1p(sample_size) / np.log1p(100))
        return round(min(1.0, data_quality * size_factor), 3)
