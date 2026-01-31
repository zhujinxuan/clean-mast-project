"""Base classes and registry for recommend strategies."""

from abc import ABC, abstractmethod
from typing import Protocol

from ..config import ExtrapolateConfiguration
from ...models.reconstruct_meso import ReconstructMesoConfiguration


class RecommendStrategy(ABC):
    """Base class for extrapolation recommendation strategies."""

    name: str

    @abstractmethod
    def recommend(
        self,
        reconstruct_config: ReconstructMesoConfiguration,
        base_dir: str,
        extrapolate_heights: list[float],
    ) -> ExtrapolateConfiguration:
        """Generate extrapolation configuration.

        Args:
            reconstruct_config: ReconstructMeso configuration (provides mast outputs)
            base_dir: Base directory for resolving relative paths
            extrapolate_heights: Target heights for extrapolation (m)

        Returns:
            ExtrapolateConfiguration ready to execute
        """
        pass


# Strategy registry
_strategies: dict[str, type[RecommendStrategy]] = {}


def register_strategy(strategy_class: type[RecommendStrategy]) -> type[RecommendStrategy]:
    """Register a strategy class."""
    _strategies[strategy_class.name] = strategy_class
    return strategy_class


def get_strategy(name: str) -> type[RecommendStrategy]:
    """Get a strategy class by name.

    Args:
        name: Strategy name (e.g., "top3-constant-shear")

    Returns:
        Strategy class

    Raises:
        ValueError: If strategy not found
    """
    if name not in _strategies:
        available = ", ".join(_strategies.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return _strategies[name]


def list_strategies() -> list[str]:
    """List available strategy names."""
    return list(_strategies.keys())
