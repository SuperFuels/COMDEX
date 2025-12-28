# ===============================
# 📁 backend/modules/codex/virtual/instruction_parser.py
# ===============================
"""
CodexLang Instruction Parser

Parses symbolic glyph strings into executable nested instruction trees.
Handles operators, grouping, and implicit structure.

Key rules (to avoid breaking cross-stack symbols):
  - NEVER domain-force via metadata first.
  - Prefer: already-canonical -> mode override -> collision_resolver -> CANONICAL_OPS
            -> symbolic_instruction_set legacy aliases -> metadata LAST.
  - Correctly unwrap ONLY truly-wrapping parentheses (fixes "(A) -> (B)" bug).
  - Tokenizes operators even without spaces (A⊕B, (A⊕B)->C, etc).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.codexcore_virtual.instruction_metadata_bridge import get_instruction_metadata
from backend.modules.codex.canonical_ops import CANONICAL_OPS

logger = logging.getLogger(__name__)

_PHOTON_OPS = {"⊕", "⊗", "↔", "⊖", "¬", "★", "∅", "≈", "⊂"}
_SYMATICS_OPS = {"⊕", "⊗", "↔", "⊖", "⟲", "μ", "π", "⋈", "↺"}

# Recognized symbolic operators (token-level)
_OPERATORS = ["->", "↔", "⟲", "⊕", "⧖", "⊖"]


def resolve_opcode(symbol: str, mode: Optional[str] = None) -> str:
    """
    Resolve a raw symbol into a canonical opcode with the correct precedence:

      1) already-canonical (contains ':')
      2) explicit mode override (photon:/symatics:) for known operators
      3) collision_resolver (authoritative if present)
      4) CANONICAL_OPS table
      5) symbolic_instruction_set legacy aliases
      6) instruction_metadata_bridge domain (LAST resort)
      7) unknown:<symbol>
    """
    if not symbol:
        return "unknown:∅"

    if ":" in symbol:
        return symbol

    if mode == "photon" and symbol in _PHOTON_OPS:
        return f"photon:{symbol}"
    if mode == "symatics" and symbol in _SYMATICS_OPS:
        return f"symatics:{symbol}"

    # Prefer collision resolver (global priority rules)
    try:
        from backend.modules.codex.collision_resolver import resolve_op

        try:
            r = resolve_op(symbol, mode=mode)
        except TypeError:
            r = resolve_op(symbol)

        if isinstance(r, str) and r:
            return r
    except Exception:
        pass

    # Canonical ops table
    r = CANONICAL_OPS.get(symbol)
    if isinstance(r, str) and r:
        return r

    # Legacy shim (hard aliases)
    try:
        from backend.codexcore_virtual import symbolic_instruction_set as sis
        return sis.get_opcode(symbol)
    except Exception:
        pass

    # Metadata LAST (informational, not authoritative)
    meta = get_instruction_metadata(symbol)
    if meta:
        return f"{meta.get('domain', 'unknown')}:{symbol}"

    return f"unknown:{symbol}"


class InstructionParser:
    def __init__(self):
        # Recognized symbolic operators
        self.operators = list(_OPERATORS)

        # Operator precedence (low -> high)
        self.precedence = {
            "->": 1,
            "⧖": 1,
            "↔": 2,
            "⟲": 2,  # primarily unary-function style, but kept for compatibility
            "⊕": 3,
            "⊖": 3,
        }

    # ─── Public Entrypoint ───────────────────────────────────────────
    def parse_codexlang_string(self, code: str, mode: str = None) -> Dict[str, Any]:
        code = (code or "").strip()
        if not code:
            return {"op": None, "args": []}

        # normalize common ascii variants
        code = code.replace("<->", "↔")

        tokens = self.tokenize(code)
        if not tokens:
            return {"op": None, "args": []}

        tree = self.build_tree(tokens, mode=mode)

        if isinstance(tree, list):
            if len(tree) == 1:
                return tree[0]
            return {"op": "program", "children": tree}
        return tree

    # ─── Tokenizer ──────────────────────────────────────────────────
    def tokenize(self, code: str) -> List[str]:
        """
        Tokenize while respecting parentheses AND extracting operators even without spaces.
        Example:
          "⟲(A⊕B)->C" -> ["⟲","(","A","⊕","B",")","->","C"]
        """
        tokens: List[str] = []
        i = 0
        n = len(code)

        # operators in descending length order
        two_char_ops = {"->"}  # keep tiny on purpose
        one_char_ops = set(["↔", "⟲", "⊕", "⧖", "⊖", "¬", "⊗", "∅", "★", "≈", "⊂"])
        parens = {"(", ")"}

        def flush(buf: List[str]) -> None:
            if buf:
                s = "".join(buf)
                if s:
                    tokens.append(s)
                buf.clear()

        buf: List[str] = []

        while i < n:
            ch = code[i]

            # whitespace
            if ch.isspace():
                flush(buf)
                i += 1
                continue

            # parentheses
            if ch in parens:
                flush(buf)
                tokens.append(ch)
                i += 1
                continue

            # 2-char operator (->)
            if i + 1 < n:
                pair = code[i : i + 2]
                if pair in two_char_ops:
                    flush(buf)
                    tokens.append(pair)
                    i += 2
                    continue

            # 1-char operator
            if ch in one_char_ops:
                flush(buf)
                tokens.append(ch)
                i += 1
                continue

            # accumulate literal token
            buf.append(ch)
            i += 1

        flush(buf)
        return tokens

    # ─── Paren unwrap guard ─────────────────────────────────────────
    @staticmethod
    def _is_wrapped_by_outer_parens(tokens: List[str]) -> bool:
        """
        True only if the first '(' pairs with the last ')' at depth 0.
        Fixes the bug where "(A) -> (B)" was incorrectly unwrapped.
        """
        if len(tokens) < 2 or tokens[0] != "(" or tokens[-1] != ")":
            return False

        depth = 0
        for idx, tok in enumerate(tokens):
            if tok == "(":
                depth += 1
            elif tok == ")":
                depth -= 1
                if depth == 0 and idx != len(tokens) - 1:
                    return False
            if depth < 0:
                return False

        return depth == 0

    # ─── Tree Builder ───────────────────────────────────────────────
    def build_tree(self, tokens: List[str], mode: str = None) -> Any:
        """
        Convert tokens into AST using precedence + parentheses.
        Output shape:
          {"op": <opcode>, "args": [ ... ]} or {"op":"lit","value":...}
        """
        if not tokens:
            return None

        # unwrap only if truly wrapping
        if self._is_wrapped_by_outer_parens(tokens):
            return self.build_tree(tokens[1:-1], mode=mode)

        # function-style unary op like ⟲( ... )
        if (
            len(tokens) >= 4
            and tokens[1] == "("
            and tokens[-1] == ")"
            and tokens[0] in self.operators
            and self._is_wrapped_by_outer_parens(tokens[1:])
        ):
            op = tokens[0]
            inner = self.build_tree(tokens[2:-1], mode=mode)
            return {"op": resolve_opcode(op, mode=mode), "args": [inner]}

        # operator precedence: low -> high (so low binds last; becomes top-level)
        for prec in sorted(set(self.precedence.values())):
            depth = 0
            for i, tok in enumerate(tokens):
                if tok == "(":
                    depth += 1
                    continue
                if tok == ")":
                    depth -= 1
                    continue
                if depth != 0:
                    continue

                if tok in self.operators and self.precedence.get(tok) == prec:
                    left_tokens = tokens[:i]
                    right_tokens = tokens[i + 1 :]

                    # if operator appears but missing side, treat as literal op
                    if not left_tokens or not right_tokens:
                        break

                    left = self.build_tree(left_tokens, mode=mode)
                    right = self.build_tree(right_tokens, mode=mode)

                    return {
                        "op": resolve_opcode(tok, mode=mode),
                        "args": [x for x in [left, right] if x is not None],
                    }

        # base case -> literal(s)
        if len(tokens) == 1:
            v = tokens[0]
            # If the literal itself is an operator symbol, resolve it (rare but happens)
            if v in self.operators:
                return {"op": resolve_opcode(v, mode=mode), "args": []}
            return {"op": "lit", "value": v}

        # fallback: sequence of literals
        return [{"op": "lit", "value": t} for t in tokens if t not in {"(", ")"}]


# ✅ Public wrapper
_parser = InstructionParser()


def parse_codexlang(code: str, mode: str = None) -> Dict[str, Any]:
    return _parser.parse_codexlang_string(code, mode=mode)


# 🧪 CLI Debug Harness
if __name__ == "__main__":
    samples = [
        "⚛ -> ✦ ⟲ 🧠",
        "A ⊕ B -> C",
        "(A) -> (B)",
        "X ↔ Y",
        "⟲(A ⊕ B)",
        "⟲((A ⊕ B) -> C)",
        "A⊕B->C",
        "A ⊖ ∅",
    ]
    for s in samples:
        print(f"\nInput: {s}")
        print(parse_codexlang(s, mode="photon"))