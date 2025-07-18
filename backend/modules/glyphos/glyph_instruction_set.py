# backend/modules/glyphos/glyph_instruction_set.py

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


def op_reflect(symbol, memory=None):
    if memory:
        memory.store({
            "label": "reflection",
            "type": "self_reflection",
            "content": f"Reflecting on: {symbol}"
        })
    return f"Reflected on {symbol}"


def op_loop(symbol, count=3):
    return [f"Loop[{i}] → {symbol}" for i in range(count)]


def op_union(set1, set2):
    return list(set(set1) | set(set2))


def op_combine(a, b):
    return f"⊕({a}, {b})"


def op_multiply(a, b):
    return f"⊗({a}, {b})"


def op_condition(condition, then_action, else_action=None):
    if condition:
        return then_action
    return else_action or "No Action"

# Instruction Set Registry
INSTRUCTION_SET: Dict[str, GlyphInstruction] = {
    "→": GlyphInstruction("→", "trigger", op_trigger, "Triggers a symbolic action"),
    "↔": GlyphInstruction("↔", "equivalence", op_equivalence, "Checks bidirectional equivalence"),
    "⟲": GlyphInstruction("⟲", "reflect", op_reflect, "Reflect on a symbol"),
    "⤾": GlyphInstruction("⤾", "loop", op_loop, "Loops over a symbol"),
    "∪": GlyphInstruction("∪", "union", op_union, "Set union of two sets"),
    "⊕": GlyphInstruction("⊕", "combine", op_combine, "Combines two symbolic values"),
    "⊗": GlyphInstruction("⊗", "multiply", op_multiply, "Multiplies symbolic structures"),
    "?": GlyphInstruction("?", "condition", op_condition, "Conditional execution"),
}


def get_instruction(symbol: str) -> GlyphInstruction:
    return INSTRUCTION_SET.get(symbol)