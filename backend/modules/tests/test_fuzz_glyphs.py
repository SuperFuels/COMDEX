import pytest
from hypothesis import given, strategies as st

from backend.modules.glyphos.codexlang_translator import parse_action_expr, translate_node
from backend.modules.codex.canonical_ops import CANONICAL_OPS, OP_METADATA
from backend.modules.codex.collision_resolver import COLLISIONS, ALIASES

# Collect all possible raw symbols (from canonical ops, aliases, collisions)
ALL_SYMBOLS = list(CANONICAL_OPS.keys()) + list(ALIASES.keys()) + list(COLLISIONS.keys())


# ────────────────────────────────────────────────
# Hypothesis strategy: generate random glyph expressions
# ────────────────────────────────────────────────
@st.composite
def glyph_exprs(draw, depth=0):
    sym = draw(st.sampled_from(ALL_SYMBOLS))
    if depth > 2:  # stop recursion
        return sym
    # With some probability, generate an operator with args
    if draw(st.booleans()):
        arg_count = draw(st.integers(min_value=1, max_value=3))
        args = [draw(glyph_exprs(depth + 1)) for _ in range(arg_count)]
        arg_strs = [a if isinstance(a, str) else str(a) for a in args]
        return f"{sym}({', '.join(arg_strs)})"
    return sym


# ────────────────────────────────────────────────
# Property-based fuzz test
# ────────────────────────────────────────────────
@given(glyph_exprs())
def test_fuzz_translate_never_crashes(expr):
    """Fuzz: Random glyph expressions across all domains should never crash."""
    parsed = parse_action_expr(expr)
    translated = translate_node(parsed)

    # Either a raw string (leaf) or a dict with canonical op
    if isinstance(translated, dict):
        op = translated["op"]
        assert isinstance(op, str)
        # Must be resolvable somewhere in our metadata space
        assert (
            op in OP_METADATA
            or op in CANONICAL_OPS.values()
            or any(op in opts for opts in COLLISIONS.values())
        )
    else:
        # Leaf nodes are just plain strings like "A" or "ψ⟩"
        assert isinstance(translated, str)