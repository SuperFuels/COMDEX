# File: backend/modules/codex/symbolic_registry.py

from typing import Dict, Any


class SymbolicRegistry:
    def __init__(self):
        self.registry: Dict[str, Any] = {}

    def register(self, name: str, glyph_tree: Any):
        self.registry[name] = glyph_tree

    def get(self, name: str) -> Any:
        return self.registry.get(name)

    def all(self) -> Dict[str, Any]:
        return self.registry

    def clear(self):
        self.registry.clear()

    def __repr__(self):
        return f"<SymbolicRegistry size={len(self.registry)}>"


# Singleton instance used across modules
symbolic_registry = SymbolicRegistry()