# File: codex_core/virtual/symbolic_instruction_set.py

"""
Symbolic Instruction Set for CodexCore

Defines the complete symbolic instruction set used by the virtual Codex CPU.
Includes: logic ops, memory ops, runtime triggers, quantum/symbolic extensions.
"""

from enum import Enum

class SymbolicOpCode(Enum):
    ADD = "⊕"                # Add/Combine symbols
    SEQUENCE = "→"           # Sequential step
    BIDIRECTIONAL = "↔"      # Two-way link (entanglement)
    LOOP = "⟲"               # Recursion/loop
    DELAY = "⧖"              # Delay/wait
    STORE = "≡"              # Memory store
    RECALL = "⧉"             # Memory fetch
    MUTATE = "⬁"             # Request mutation
    BOOT = "⚛"               # Boot trigger
    DREAM = "✦"              # Dream generation
    REFLECT = "🧽"            # Self-reflection
    TELEPORT = "🧭"           # Container jump
    Q_SUPERPOSE = "⧜"        # Quantum superposition (symbolic)
    Q_COLLAPSE = "⧝"         # Collapse superposition
    Q_ENTANGLE = "⧠"         # Entangle logic state
    COMPRESS = "⋰"           # Compress instruction tree
    EXPAND = "⋱"             # Expand latent tree

# Each instruction maps to logic handlers in the emulator or executor
OPCODE_HANDLER_MAP = {
    SymbolicOpCode.ADD: "handle_add",
    SymbolicOpCode.SEQUENCE: "handle_sequence",
    SymbolicOpCode.BIDIRECTIONAL: "handle_bidir",
    SymbolicOpCode.LOOP: "handle_loop",
    SymbolicOpCode.DELAY: "handle_delay",
    SymbolicOpCode.STORE: "handle_store",
    SymbolicOpCode.RECALL: "handle_recall",
    SymbolicOpCode.MUTATE: "handle_mutate",
    SymbolicOpCode.BOOT: "handle_boot",
    SymbolicOpCode.DREAM: "handle_dream",
    SymbolicOpCode.REFLECT: "handle_reflect",
    SymbolicOpCode.TELEPORT: "handle_teleport",
    SymbolicOpCode.Q_SUPERPOSE: "handle_q_superpose",
    SymbolicOpCode.Q_COLLAPSE: "handle_q_collapse",
    SymbolicOpCode.Q_ENTANGLE: "handle_q_entangle",
    SymbolicOpCode.COMPRESS: "handle_compress",
    SymbolicOpCode.EXPAND: "handle_expand",
}

def is_valid_opcode(symbol: str) -> bool:
    return any(op.value == symbol for op in SymbolicOpCode)

def get_opcode(symbol: str) -> SymbolicOpCode:
    for op in SymbolicOpCode:
        if op.value == symbol:
            return op
    raise ValueError(f"Unknown symbolic opcode: {symbol}")