from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class PluginInterface(ABC):
    """
    Abstract base class for all cognitive plugins (C1-C5).
    Enforces standard interfaces across the plugin runtime.
    """

    name: str = "UnnamedPlugin"
    description: str = ""
    version: str = "0.1.0"
    enabled: bool = True

    def __init__(self):
        self.internal_state: Dict[str, Any] = {}

    @abstractmethod
    def register_plugin(self) -> None:
        """Called to register the plugin into the plugin manager."""
        pass

    @abstractmethod
    def trigger(self, context: Optional[Dict[str, Any]] = None) -> None:
        """Optional runtime signal trigger."""
        pass

    @abstractmethod
    def mutate(self, logic: str) -> str:
        """Symbolic mutation hook (used in C3)."""
        pass

    @abstractmethod
    def synthesize(self, goal: str) -> str:
        """Scroll/memory -> logic synthesis (used in C5)."""
        pass

    @abstractmethod
    def broadcast_qfc_update(self) -> None:
        """Broadcast changes to the QFC field."""
        pass

    def reset(self) -> None:
        """Optional: Reset internal state (between sessions)."""
        self.internal_state.clear()