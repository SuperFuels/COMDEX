"""
Symbolic Instruction Set (Shim)

⚠️ Deprecated: Thin wrapper over
`backend/modules/codexcore_virtual/instruction_registry`.

Use `instruction_registry.registry` directly for canonical ops.

- Provides `is_valid_opcode()` and `get_opcode()` wrappers.
- Auto-aliases legacy raw symbols (⊕, ⟲, →) to domain-tagged keys.
"""

import warnings
from typing import Dict
from backend.codexcore_virtual import instruction_registry as ir

# -----------------------------------------------------------------------------
# Legacy alias overrides (ensure canonical domain mapping)
# -----------------------------------------------------------------------------
LEGACY_ALIASES = {
    "⊕": "logic:⊕",       # addition / combine
    "⟲": "control:⟲",     # loop / iteration
    "→": "logic:→",       # sequence / trigger
}

# -----------------------------------------------------------------------------
# Backwards compatibility shim
# -----------------------------------------------------------------------------
def is_valid_opcode(symbol: str) -> bool:
    """Check if a symbol (raw or domain-tagged) is registered or aliased."""
    if symbol in ir.registry.registry:
        return True
    if symbol in LEGACY_ALIASES:
        return True
    if symbol in ir.registry.aliases:
        return True
    return False


def get_opcode(symbol: str) -> str:
    """
    Return the canonical domain-tagged key for a symbol.
    - Raw glyphs first checked against LEGACY_ALIASES
    - Then against registry aliases
    - Otherwise returns canonical if already registered
    """
    if symbol in ir.registry.registry:
        return symbol
    if symbol in LEGACY_ALIASES:
        canonical = LEGACY_ALIASES[symbol]
        warnings.warn(
            f"[compat] Symbol '{symbol}' resolved to '{canonical}' via hardcoded legacy shim.",
            DeprecationWarning,
        )
        return canonical
    if symbol in ir.registry.aliases:
        canonical = ir.registry.aliases[symbol]
        warnings.warn(
            f"[compat] Symbol '{symbol}' resolved to '{canonical}' via registry alias shim.",
            DeprecationWarning,
        )
        return canonical
    raise ValueError(f"Unknown symbolic opcode: {symbol}")


def list_symbolic_opcodes() -> Dict[str, str]:
    """Return all registered ops from the canonical registry."""
    return ir.registry.list_instructions()