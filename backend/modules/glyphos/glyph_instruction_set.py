# 📁 backend/modules/glyphos/glyph_instruction_set.py

# Symbolic Instruction Definitions for CodexCore
# Each operator is mapped to a runtime behavior

from typing import Any, Callable, Dict

class GlyphInstruction:
    def __init__(self, symbol: str, name: str, func: Callable, description: str = ""):
        self.symbol = symbol
        self.name = name
        self.func = func
        self.description = description

    def execute(self, *args, **kwargs) -> Any:
        return self.func(*args, **kwargs)

# --- Operation Implementations ---

def op_trigger(source, target, memory=None):
    if memory:
        memory.store({
            "label": f"trigger_{source}_to_{target}",
            "type": "glyph_trigger",
            "content": f"{source} triggered {target}"
        })
    return f"{source} → {target}"

def op_equivalence(left, right):
    return left == right

def op_mutate(symbol, memory=None):
    if memory:
        memory.store({
            "label": "mutation",
            "type": "self_mutation",
            "content": f"Mutating on: {symbol}"
        })
    return f"Mutated: {symbol}"

def op_loop(symbol, count=3):
    return [f"Loop[{i}] → {symbol}" for i in range(count)]

def op_union(set1, set2):
    return list(set(set1) | set(set2))

def op_combine(a, b):
    return f"⊕({a}, {b})"

def op_multiply(a, b):
    return f"⊗({a}, {b})"

def op_condition(condition, then_action, else_action=None):
    return then_action if condition else (else_action or "No Action")

def op_delay(symbol, seconds=1):
    import time
    time.sleep(seconds)
    return f"Delayed: {symbol} by {seconds}s"

def op_compress(*symbols):
    return f"∇({', '.join(map(str, symbols))})"

def op_milestone(*args):
    return f"✦ Milestone Reached: {' '.join(map(str, args))}"

# --- Instruction Set Registry ---

INSTRUCTION_SET: Dict[str, GlyphInstruction] = {
    "→": GlyphInstruction("→", "trigger", op_trigger, "Triggers a symbolic action"),
    "↔": GlyphInstruction("↔", "equivalence", op_equivalence, "Checks bidirectional equivalence"),
    "⟲": GlyphInstruction("⟲", "mutate", op_mutate, "Performs self-mutation or update"),
    "⤾": GlyphInstruction("⤾", "loop", op_loop, "Loops over a symbol"),
    "∪": GlyphInstruction("∪", "union", op_union, "Set union of two sets"),
    "⊕": GlyphInstruction("⊕", "combine", op_combine, "Combines two symbolic values"),
    "⊗": GlyphInstruction("⊗", "multiply", op_multiply, "Multiplies symbolic structures"),
    "?": GlyphInstruction("?", "condition", op_condition, "Conditional execution"),
    "⧖": GlyphInstruction("⧖", "delay", op_delay, "Delays execution of a symbol"),
    "∇": GlyphInstruction("∇", "compress", op_compress, "Compresses symbolic values"),
    "✦": GlyphInstruction("✦", "milestone", op_milestone, "Marks a milestone or boot phase"),
}

def get_instruction(symbol: str) -> GlyphInstruction:
    # Direct match first (raw or canonical)
    if symbol in INSTRUCTION_SET:
        return INSTRUCTION_SET[symbol]

    # If canonical form (e.g., "logic:⊕"), strip the domain and retry
    if ":" in symbol:
        _, raw = symbol.split(":", 1)
        if raw in INSTRUCTION_SET:
            return INSTRUCTION_SET[raw]

    return None

def clear_instruction(symbol: str):
    """Remove a registered instruction (cleanup)."""
    if symbol in INSTRUCTION_SET:
        del INSTRUCTION_SET[symbol]

def register_instruction(symbol: str, instr: GlyphInstruction):
    """
    Register or override an instruction dynamically.
    Useful for tests or extensions.
    """
    INSTRUCTION_SET[symbol] = instr