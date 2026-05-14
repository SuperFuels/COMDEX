"""
Symatics -> CodexLang Rewriter
─────────────────────────────
Transforms symbolic "Symatics" ops (experimental operators and glyphs) 
into canonical CodexLang equivalents.

- This module acts as the bridge layer between Symatics expressions 
  and Codex symbolic execution.
- Keeps the shape of instruction trees consistent with CodexLang 
  (dicts with "op" and "args").
- Lightweight and deterministic, safe to monkeypatch in tests.
"""

from typing import Dict, Any


# 🔑 Mapping table: extend as Symatics operators are defined
SYMATIC_OPS_MAP = {
    "⊕": "logic:⊕",        # XOR -> canonical logic XOR
    "⋈": "interf:⋈",       # Join/Merge operator
    "⟁": "barrier:⟁",      # Dimension lock
    "⌬": "mod:⌬",          # Compression lens
    # Add more as language expands...
}


def rewrite_symatics_to_codex(tree: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively rewrite Symatics ops into canonical CodexLang form.

    Args:
        tree: Instruction tree in dict form. Example:
              {"op": "⊕", "args": ["A", "B"]}

    Returns:
        Canonicalized tree (dict).
    """
    if not isinstance(tree, dict):
        return tree

    op = tree.get("op")
    if op in SYMATIC_OPS_MAP:
        tree = dict(tree)  # copy shallow to avoid mutating external refs
        tree["op"] = SYMATIC_OPS_MAP[op]

    # Recurse into arguments
    args = tree.get("args")
    if isinstance(args, list):
        tree["args"] = [rewrite_symatics_to_codex(a) for a in args]

    return tree


def is_symatic_op(op: str) -> bool:
    """
    Quick check: is the operator a known Symatics glyph?
    """
    return op in SYMATIC_OPS_MAP


def list_supported_symatics() -> Dict[str, str]:
    """
    Return mapping of supported Symatics ops -> Codex equivalents.
    Useful for debugging or exposing through APIs.
    """
    return dict(SYMATIC_OPS_MAP)