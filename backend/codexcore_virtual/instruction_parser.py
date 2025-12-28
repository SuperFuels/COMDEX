# ===============================
# 📁 backend/codexcore_virtual/instruction_parser.py
# ===============================
"""
CodexCore Virtual Instruction Parser (compat layer)

This module produces the legacy *instruction list* shape:
    [{"opcode": "...", "args": [...], "meta": {...}}, ...]

It MUST NOT domain-force via metadata first (that breaks your canonical/collision stack).
Instead it:
  - uses backend.modules.codex.virtual.instruction_parser.parse_codexlang as the
    single source of truth for parsing + opcode resolution
  - converts the unified AST into the legacy instruction list shape
  - supports "=>” as top-level program sequencing (depth-safe)
  - avoids heavyweight imports at module import time (lazy import parse_codexlang)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def _infer_mode_from_opcode(opcode: Optional[str], fallback: Optional[str]) -> str:
    """
    Prefer the opcode's namespace (photon:/symatics:) over the caller's fallback.
    Keeps legacy meta consistent even when parsing in mode=None.
    """
    if isinstance(opcode, str):
        if opcode.startswith("photon:"):
            return "photon"
        if opcode.startswith("symatics:"):
            return "symatics"
    return fallback or "logic"


def _split_top_level_sequence(code: str) -> List[str]:
    """
    Split on top-level '=>' while respecting parentheses nesting.
    Example: "A => ⟲((B => C) -> D) => E" splits into ["A", "⟲((B => C) -> D)", "E"].
    """
    s = (code or "").strip()
    if not s:
        return []

    out: List[str] = []
    buf: List[str] = []
    depth = 0
    i = 0

    while i < len(s):
        ch = s[i]

        if ch == "(":
            depth += 1
            buf.append(ch)
            i += 1
            continue
        if ch == ")":
            depth = max(0, depth - 1)
            buf.append(ch)
            i += 1
            continue

        # top-level =>
        if depth == 0 and s.startswith("=>", i):
            seg = "".join(buf).strip()
            if seg:
                out.append(seg)
            buf = []
            i += 2
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        out.append(tail)
    return out


def _flatten_program(tree: Any) -> List[Dict[str, Any]]:
    """
    Normalize unified parse tree into a list of top-level nodes.
    Accepts:
      - {"op":"program","children":[...]}
      - single node dict
      - list of node dicts
    """
    if tree is None:
        return []
    if isinstance(tree, dict) and tree.get("op") == "program":
        children = tree.get("children", [])
        return [c for c in children if isinstance(c, dict)]
    if isinstance(tree, dict):
        return [tree]
    if isinstance(tree, list):
        return [x for x in tree if isinstance(x, dict)]
    return []


def _ast_to_legacy_instr(node: Any, *, mode: Optional[str]) -> Dict[str, Any]:
    """
    Convert unified AST node:
        {"op": <opcode>, "args": [...]}
      or {"op":"lit","value": "..."}
    into legacy instruction dict:
        {"opcode": <opcode>, "args":[...], "meta": {...}}

    IMPORTANT:
      - Child nodes inherit the *inferred* mode of their parent opcode.
        This prevents e.g. symatics:⟲(lit) from producing lit meta as "logic".
    """
    # If we get a list here (e.g. token stream fallback), wrap as a tiny program-ish list.
    if isinstance(node, list):
        inferred = _infer_mode_from_opcode(None, mode)
        converted = [
            _ast_to_legacy_instr(x, mode=inferred) if isinstance(x, (dict, list)) else x
            for x in node
        ]
        return {
            "opcode": "program",
            "args": converted,
            "meta": {"mode": inferred, "pattern": "program"},
        }

    if not isinstance(node, dict):
        return {
            "opcode": "unknown:∅",
            "args": [node],
            "meta": {"mode": mode or "logic", "pattern": "unknown"},
        }

    op = node.get("op")

    # literal node
    if op == "lit":
        value = node.get("value")
        inferred = _infer_mode_from_opcode(None, mode)
        return {
            "opcode": "lit",
            "args": [value] if value is not None else [],
            "meta": {"mode": inferred, "pattern": "literal"},
        }

    inferred = _infer_mode_from_opcode(op, mode)

    args = node.get("args", [])
    out_args: List[Any] = []

    if isinstance(args, list):
        for a in args:
            if isinstance(a, (dict, list)):
                # ✅ propagate inferred mode to children
                out_args.append(_ast_to_legacy_instr(a, mode=inferred))
            else:
                out_args.append(a)
    elif args is None:
        out_args = []
    else:
        out_args = [args]

    # classify pattern for legacy meta
    pattern = "unary" if len(out_args) == 1 else "binary" if len(out_args) == 2 else "nary"

    return {
        "opcode": op or "unknown:∅",
        "args": out_args,
        "meta": {"mode": inferred, "pattern": pattern},
    }


def parse_codex_instructions(codex_str: str, mode: str = None) -> List[Dict[str, Any]]:
    """
    Parses a CodexLang string into a list of legacy symbolic CPU instructions.

    Supports:
      - nested parentheses, function-style ops, no-space operators
      - top-level sequencing via "=>"

    mode:
      - "photon" / "symatics" / None
      - mode is passed through to the unified parser (which already resolves opcodes correctly)
    """
    codex_str = (codex_str or "").strip()
    if not codex_str:
        return []

    # normalize common ascii variants
    codex_str = codex_str.replace("<->", "↔")

    # ✅ Lazy import to avoid heavy side-effects / circular imports at module load time
    from backend.modules.codex.virtual.instruction_parser import parse_codexlang

    instructions: List[Dict[str, Any]] = []

    for segment in _split_top_level_sequence(codex_str):
        segment = (segment or "").strip()
        if not segment:
            continue

        logger.debug(f"[codexcore_virtual.parser] segment='{segment}' mode={mode}")

        tree = parse_codexlang(segment, mode=mode)
        nodes = _flatten_program(tree)

        # If parser returned something odd but dict-like, still try to convert it.
        if not nodes and isinstance(tree, dict):
            nodes = [tree]

        for n in nodes:
            instructions.append(_ast_to_legacy_instr(n, mode=mode))

    # Optional SoulLaw validation hook (non-blocking)
    try:
        from backend.modules.glyphvault.soul_law_validator import soul_law_validator

        if not soul_law_validator.validate_container({"instructions": instructions}):
            logger.warning("[SoulLaw] Validation failed: instruction sequence may violate SoulLaw")
    except Exception:
        pass

    return instructions


# 🧪 CLI Debug Harness
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    samples = [
        "A ⊕ B",
        "X -> Y",
        "⟲(Reflect)",
        "A ⊕ B -> C",
        "A ⊕ B -> C => ⟲(Loop)",
        "⟲(A ⊕ B)",
        "(A ⊕ B) -> C",
        "⟲((A ⊕ B) -> C)",
        "A ⊖ ∅",
        "A⊕B->C",
        "(A) -> (B)",
        "NoteThisLiteral",
        "A => ⟲((B => C) -> D) => E",
    ]

    for s in samples:
        print(f"\nInput: {s}")
        print("Photon:", parse_codex_instructions(s, mode="photon"))
        print("Symatics:", parse_codex_instructions(s, mode="symatics"))
        print("Raw:", parse_codex_instructions(s))