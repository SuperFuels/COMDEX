# File: backend/modules/codexcore_virtual/instruction_registry.py

"""
Instruction Registry for Virtual CodexCore

Maps CodexLang symbolic operators to runtime function handlers.
Supports runtime extension, mutation, and execution tracking.
"""

from typing import Callable, Dict, Any

class InstructionRegistry:
    def __init__(self):
        self.registry: Dict[str, Callable[[Any], Any]] = {}

    def register(self, symbol: str, handler: Callable[[Any], Any]):
        if symbol in self.registry:
            raise ValueError(f"Instruction '{symbol}' already registered.")
        self.registry[symbol] = handler

    def execute(self, symbol: str, operand: Any) -> Any:
        if symbol not in self.registry:
            raise KeyError(f"Unknown instruction symbol: {symbol}")
        return self.registry[symbol](operand)

    def list_instructions(self) -> Dict[str, str]:
        return {symbol: func.__name__ for symbol, func in self.registry.items()}

    def override(self, symbol: str, handler: Callable[[Any], Any]):
        """Force override for mutation or hot patching."""
        self.registry[symbol] = handler

# Example default runtime registry
registry = InstructionRegistry()

# Built-in instruction handlers (minimal examples)
def handle_reflect(data):
    return f"[REFLECT] {data}"

def handle_store(data):
    return f"[STORE] {data}"

def handle_recall(data):
    return f"[RECALL] {data}"

# Register default instructions
registry.register("⟲", handle_reflect)
registry.register("⊕", handle_store)
registry.register("↺", handle_recall)

# This file will be imported into codex_emulator.py to power symbolic dispatch