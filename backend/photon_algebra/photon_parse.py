# backend/photon_algebra/photon_parse.py

"""
Photon Parser
-------------
Strict parser for pretty-printed Photon expressions.

Supports:
    ⊕    superposition (n-ary, commutative)
    ⊗    fusion (binary, commutative)
    ⊗_M  magnetic coupling / composition (binary, directional)
    ⊖    cancellation (binary, non-commutative)
    ↔    entanglement (binary, lowest precedence)
    ≈    similarity (binary, lowest precedence; inert for now)
    ⊂    containment (binary, lowest precedence; inert for now)
    ¬    negation (unary, prefix)
    ★    projection (unary, prefix)
    Φ_B  magnetic-state operator (unary, prefix)
    ∅    empty state
    ⊤    top (constant)
    ⊥    bottom (constant)

Grammar (EBNF):
    expr      := ent
    ent       := sum ( ("↔" | "≈" | "⊂") sum )*
    sum       := prod (("⊕" | "⊖") prod)*
    prod      := factor ( ("⊗" | "⊗_M") factor )*
    factor    := "¬" factor | "★" factor | "Φ_B" factor | atom
    atom      := SYMBOL | "∅" | "⊤" | "⊥" | "(" expr ")"

SYMBOL := string of letters/numbers/underscores (atom identifiers)
"""

from __future__ import annotations
import re
from typing import Any, List


# -------------------------------
# Tokenizer
# -------------------------------
_TOKEN_RE = re.compile(
    r"""
    (⊗_M)             |  # longest operator first
    (Φ_B)             |
    ([⊕⊗⊖↔≈⊂¬★()∅⊤⊥]) |
    ([A-Za-z0-9_?]+)
    """,
    re.VERBOSE,
)


def tokenize(s: str) -> List[str]:
    tokens: List[str] = []
    pos = 0

    for match in _TOKEN_RE.finditer(s):
        start, end = match.span()

        # only allow whitespace between recognized tokens
        if start > pos:
            gap = s[pos:start]
            if gap.strip():
                raise SyntaxError(f"Unexpected token: {gap.strip()}")

        tok = match.group(0)
        tokens.append(tok)
        pos = end

    if pos < len(s):
        tail = s[pos:]
        if tail.strip():
            raise SyntaxError(f"Unexpected token: {tail.strip()}")

    return tokens


# -------------------------------
# Recursive descent parser
# -------------------------------
class Parser:
    def __init__(self, tokens: List[str]):
        self.tokens = tokens
        self.pos = 0

    def peek(self) -> str | None:
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def eat(self, expected: str | None = None) -> str:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("Unexpected end of input")
        if expected is not None and tok != expected:
            raise SyntaxError(f"Expected '{expected}', got '{tok}'")
        self.pos += 1
        return tok

    # expr := ent
    def parse_expr(self) -> Any:
        return self.parse_ent()

    # ent := sum ( ("↔" | "≈" | "⊂") sum )*
    def parse_ent(self):
        node = self.parse_sum()
        while self.peek() in ("↔", "≈", "⊂"):
            op = self.eat()
            rhs = self.parse_sum()
            node = {"op": op, "states": [node, rhs]}
        return node

    # sum := prod (("⊕" | "⊖") prod)*
    def parse_sum(self) -> Any:
        node = self.parse_prod()
        acc = [node]
        while self.peek() in ("⊕", "⊖"):
            op = self.eat()
            rhs = self.parse_prod()
            acc.append(rhs)
            if op != "⊕":  # ⊖ stays binary
                node = {"op": op, "states": [node, rhs]}
            else:
                node = {"op": "⊕", "states": acc}
        return node

    # prod := factor ( ("⊗" | "⊗_M") factor )*
    def parse_prod(self) -> Any:
        node = self.parse_factor()
        while self.peek() in ("⊗", "⊗_M"):
            op = self.eat()
            rhs = self.parse_factor()
            node = {"op": op, "states": [node, rhs]}
        return node

    # factor := "¬" factor | "★" factor | "Φ_B" factor | atom
    def parse_factor(self) -> Any:
        tok = self.peek()
        if tok == "¬":
            self.eat()
            return {"op": "¬", "state": self.parse_factor()}
        if tok == "★":
            self.eat()
            return {"op": "★", "state": self.parse_factor()}
        if tok == "Φ_B":
            self.eat()
            return {"op": "Φ_B", "state": self.parse_factor()}
        return self.parse_atom()

    # atom := SYMBOL | "∅" | "⊤" | "⊥" | "(" expr ")"
    def parse_atom(self) -> Any:
        tok = self.peek()
        if tok is None:
            raise SyntaxError("Unexpected end of input in atom")
        if tok == "(":
            self.eat("(")
            node = self.parse_expr()
            self.eat(")")
            return node
        if tok in ("∅", "⊤", "⊥"):
            self.eat(tok)
            return {"op": tok}
        self.eat()
        return tok


# -------------------------------
# Public API
# -------------------------------
def parse(s: str) -> Any:
    """Parse a pretty-printed Photon expression into an AST dict."""
    tokens = tokenize(s)
    parser = Parser(tokens)
    expr = parser.parse_expr()
    if parser.peek() is not None:
        raise SyntaxError(f"Unexpected token: {parser.peek()}")
    return expr


# -------------------------------
# CLI harness
# -------------------------------
if __name__ == "__main__":
    import sys
    import json
    from backend.photon_algebra.photon_pp import pp
    from backend.photon_algebra.rewriter import normalize

    if len(sys.argv) < 2:
        print("Usage: python -m backend.photon_algebra.photon_parse '<expr-str>'")
        sys.exit(1)

    s = sys.argv[1]
    ast = parse(s)
    norm = normalize(ast)
    print("Input string:", s)
    print("Parsed AST:", json.dumps(ast, ensure_ascii=False, indent=2))
    print("Normalized:", json.dumps(norm, ensure_ascii=False, indent=2))
    print("Pretty again:", pp(norm))