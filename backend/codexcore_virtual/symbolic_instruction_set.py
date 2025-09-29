"""
Symbolic Instruction Set (Shim)

⚠️ Deprecated: This file is now a thin wrapper over
`backend/modules/codexcore_virtual/instruction_registry`.

Use `instruction_registry.registry` directly for canonical ops.

We keep this file to preserve backwards compatibility with older
Codex/GlyphOS code that imports `symbolic_instruction_set`.

- Provides `is_valid_opcode()` and `get_opcode()` wrappers.
- Auto-aliases legacy raw symbols (⊕, ⟲, etc.) to domain-tagged keys.
"""

import warnings
from typing import Dict
from backend.codexcore_virtual import instruction_registry as ir

# -----------------------------------------------------------------------------
# Backwards compatibility shim
# -----------------------------------------------------------------------------

def is_valid_opcode(symbol: str) -> bool:
    """Check if a symbol (raw or domain-tagged) is registered."""
    if symbol in ir.registry.registry:
        return True
    if symbol in ir.registry.aliases:
        return True
    return False


def get_opcode(symbol: str) -> str:
    """
    Return the canonical domain-tagged key for a symbol.
    If raw, resolves through alias table.
    """
    if symbol in ir.registry.registry:
        return symbol
    if symbol in ir.registry.aliases:
        canonical = ir.registry.aliases[symbol]
        warnings.warn(
            f"[compat] Symbol '{symbol}' resolved to '{canonical}' via alias shim.",
            DeprecationWarning,
        )
        return canonical
    raise ValueError(f"Unknown symbolic opcode: {symbol}")


# -----------------------------------------------------------------------------
# Legacy handler map compatibility
# -----------------------------------------------------------------------------

def list_symbolic_opcodes() -> Dict[str, str]:
    """
    Return all registered ops from the canonical registry.
    Mirrors old OPCODE_HANDLER_MAP but with domain-tagged keys.
    """
    return ir.registry.list_instructions()


# -----------------------------------------------------------------------------
# Notes:
# - Prefer `instruction_registry.registry` in new code.
# - This file will be fully removed after CodexCore vNext.
# -----------------------------------------------------------------------------