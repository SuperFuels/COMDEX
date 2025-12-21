# 📁 backend/modules/glyphos/glyph_instruction_set.py

from __future__ import annotations

from typing import Any, Callable, Dict, Optional
import os
import asyncio
import logging

log = logging.getLogger("glyphos.instructions")

# ================================================================
# 🔄 Glyph Registry (OPT-IN, non-blocking, idempotent)
# ================================================================
import threading
from typing import Optional

def _truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "on"}

_GLYPHOS_LOCK = threading.Lock()
_GLYPHOS_STARTED = False

def maybe_update_glyph_registry(*, force: bool = False) -> bool:
    """
    Start glyph registry rebuild in the background.

    - Never runs at import time (only when you call it).
    - Non-blocking (runs in a daemon thread).
    - Idempotent per-process (won't start twice unless force=True).

    Enable in server:
      GLYPHOS_REBUILD_ON_STARTUP=1

    Testing defaults:
      Skips automatically when PYTEST_CURRENT_TEST is set, unless force=True.
    """
    global _GLYPHOS_STARTED

    if not force:
        # Skip during pytest unless explicitly forced
        if os.getenv("PYTEST_CURRENT_TEST"):
            return False
        if not _truthy("GLYPHOS_REBUILD_ON_STARTUP", False):
            return False

    with _GLYPHOS_LOCK:
        if _GLYPHOS_STARTED and not force:
            return False
        _GLYPHOS_STARTED = True

    def _run() -> None:
        try:
            from backend.modules.glyphos.glyph_registry_updater import update_glyph_registry
        except Exception as e:
            log.warning("[GlyphOS] glyph_registry_updater import failed (skipping): %s", e)
            return

        try:
            update_glyph_registry()
        except Exception as e:
            log.warning("[GlyphOS] update_glyph_registry failed: %s", e)

    threading.Thread(target=_run, name="glyphos-registry-rebuild", daemon=True).start()
    return True


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
    return f"{source} -> {target}"


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
    return [f"Loop[{i}] -> {symbol}" for i in range(count)]


def op_union(set1, set2):
    return list(set(set1) | set(set2))


def op_combine(*args, **kwargs):
    """
    Legacy ⊕ operator.
    Behaviors:
      * ⊕(value) -> "[STORE] value"
      * ⊕(context, value) -> "[STORE] value"
      * ⊕(a, b) -> "⊕(a, b)"
      * ⊕(context, a, b) -> "⊕(a, b)"
    """
    if len(args) == 1:
        (a,) = args
        return f"[STORE] {a}"

    elif len(args) == 2:
        first, second = args
        if not isinstance(first, str) or first == "context":
            return f"[STORE] {second}"
        return f"⊕({first}, {second})"

    elif len(args) == 3:
        _, a, b = args
        return f"⊕({a}, {b})"

    else:
        raise TypeError(f"op_combine expected 1-3 args, got {args}")


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


def op_teleport(*, target: str, context=None, **kwargs):
    kwargs = dict(kwargs)  # copy
    kwargs.setdefault("target", target)
    return {
        "glyph_action": "teleport",
        "target": target,
        "ok": True,
        "kwargs": kwargs,
        "context": context,
    }


# --- Instruction Set Registry ---

INSTRUCTION_SET: Dict[str, GlyphInstruction] = {
    "->": GlyphInstruction("->", "trigger", op_trigger, "Triggers a symbolic action"),
    "↔": GlyphInstruction("↔", "equivalence", op_equivalence, "Checks bidirectional equivalence"),
    "⟲": GlyphInstruction("⟲", "mutate", op_mutate, "Performs self-mutation or update"),
    "⤾": GlyphInstruction("⤾", "loop", op_loop, "Loops over a symbol"),
    "∪": GlyphInstruction("∪", "union", op_union, "Set union of two sets"),
    "⊕": GlyphInstruction("⊕", "combine", op_combine, "Combines or stores symbolic values"),
    "⊗": GlyphInstruction("⊗", "multiply", op_multiply, "Multiplies symbolic structures"),
    "?": GlyphInstruction("?", "condition", op_condition, "Conditional execution"),
    "⧖": GlyphInstruction("⧖", "delay", op_delay, "Delays execution of a symbol"),
    "∇": GlyphInstruction("∇", "compress", op_compress, "Compresses symbolic values"),
    "✦": GlyphInstruction("✦", "milestone", op_milestone, "Marks a milestone or boot phase"),
    "teleport": GlyphInstruction("teleport", "teleport", op_teleport, "Teleport a target to destination"),
}


def get_instruction(symbol: str) -> Optional[GlyphInstruction]:
    # Direct match first (raw or canonical)
    if symbol in INSTRUCTION_SET:
        return INSTRUCTION_SET[symbol]

    # If canonical form (e.g., "logic:⊕"), strip the domain and retry
    if ":" in symbol:
        _, raw = symbol.split(":", 1)
        if raw in INSTRUCTION_SET:
            return INSTRUCTION_SET[raw]

    return None


def clear_instruction(symbol: str) -> None:
    """Remove a registered instruction (cleanup)."""
    if symbol in INSTRUCTION_SET:
        del INSTRUCTION_SET[symbol]


def register_instruction(symbol: str, instr: GlyphInstruction) -> None:
    """
    Register or override an instruction dynamically.
    Useful for tests or extensions.
    """
    INSTRUCTION_SET[symbol] = instr