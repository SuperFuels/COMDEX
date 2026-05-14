# 📁 backend/modules/codex/virtual/symbolic_instruction_set.py
# ===============================
"""
Codex Virtual Instruction Set

Maps symbolic ops (->, ↔, ⟲, ⧖, ⊕, 🚨) to execution logic.
Operates on virtual registers and runtime context.
"""

from typing import Any, Dict, List
from backend.modules.codex.virtual.virtual_registers import VirtualRegisters
from backend.modules.codex.ops.op_trigger import op_trigger


def op_chain(args: List[str], registers: VirtualRegisters, context: Dict[str, Any]) -> str:
    """Symbolic -> Chain: Pass values through sequentially."""
    if not args:
        return "[ChainEmpty]"
    result = args[-1]
    registers.store("last_chain", result)
    return f"[Chain -> {result}]"


def op_reflect(args: List[str], registers: VirtualRegisters, context: Dict[str, Any]) -> str:
    """Symbolic ⟲ Reflection: Re-evaluate last instruction or mutate it."""
    last = registers.get("last_result") or "[None]"
    return f"[Reflect({last})]"


def op_combine(args: List[str], registers: VirtualRegisters, context: Dict[str, Any]) -> str:
    """Symbolic ⊕ Combine: Merge multiple ideas into one."""
    merged = " + ".join(args)
    return f"[Combined({merged})]"


def op_bond(args: List[str], registers: VirtualRegisters, context: Dict[str, Any]) -> str:
    """Symbolic ↔ Entangle: Link symbolic values."""
    if len(args) < 2:
        return "[BondError: Need 2+ symbols]"
    pair = (args[0], args[1])
    registers.store("entangled", pair)
    return f"[Bonded {pair[0]} ↔ {pair[1]}]"


def op_delay(args: List[str], registers: VirtualRegisters, context: Dict[str, Any]) -> str:
    """Symbolic ⧖ Delay: Intent to defer logic or simulate lag."""
    registers.store("delayed_intent", args)
    return f"[⧖ DeferredIntent: {args}]"


# Symbolic Operator Map
SYMBOLIC_OPS = {
    "->": op_chain,
    "⟲": op_reflect,
    "⊕": op_combine,
    "↔": op_bond,
    "⧖": op_delay,
    "🚨": op_trigger  # new op for symbolic triggers
}
