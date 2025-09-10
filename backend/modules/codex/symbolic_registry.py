# File: backend/modules/codex/symbolic_registry.py

from typing import Dict, Any, Optional


class SymbolicRegistry:
    """
    Central registry for storing and retrieving symbolic glyph trees or structures.
    Used globally across modules such as CodexCore, PredictionEngine, SQI, etc.
    """

    def __init__(self):
        self.registry: Dict[str, Any] = {}

    def register(self, name: str, glyph_tree: Any) -> None:
        """
        Register a glyph tree or symbolic object by name.
        """
        self.registry[name] = glyph_tree

    def get(self, name: str) -> Optional[Any]:
        """
        Retrieve the registered object by name.
        Returns None if not found.
        """
        return self.registry.get(name)

    def has(self, name: str) -> bool:
        """
        Check if a name is registered.
        """
        return name in self.registry

    def unregister(self, name: str) -> None:
        """
        Remove a name from the registry.
        """
        if name in self.registry:
            del self.registry[name]

    def all(self) -> Dict[str, Any]:
        """
        Return the full registry.
        """
        return self.registry

    def clear(self) -> None:
        """
        Clear the registry.
        """
        self.registry.clear()

    def __repr__(self):
        keys = list(self.registry.keys())
        preview = ", ".join(keys[:5]) + ("..." if len(self.registry) > 5 else "")
        return f"<SymbolicRegistry size={len(self.registry)} keys=[{preview}]>"


# ✅ Singleton instance used across all modules
symbolic_registry = SymbolicRegistry()


def load_symbol_registry() -> SymbolicRegistry:
    """
    Shim for legacy modules to access the global symbolic registry.
    """
    return symbolic_registry