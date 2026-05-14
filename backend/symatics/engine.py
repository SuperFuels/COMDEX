# symatics/engine.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Optional

from .signature import Signature
from .operators import OPS, Operator
from .normalize import canonical_signature  # modularized canonicalization


# ---------------------------------------------------------------------------
# AST Nodes
# ---------------------------------------------------------------------------

@dataclass
class SymNode:
    op: Optional[str] = None
    args: List["SymNode"] = None
    value: Optional[Signature] = None  # Leaf = raw wave signature

    def is_leaf(self) -> bool:
        return self.value is not None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def literal_signature(value: float) -> Signature:
    """Map a bare number into a default Wave Signature."""
    return Signature(
        amplitude=value,
        frequency=1.0,        # default base frequency
        phase=0.0,            # default phase
        polarization="H",     # default polarization
        mode=None,
        oam_l=None,
        envelope=None,
        meta={"literal": True}
    )


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------

from backend.symatics.core.validators.law_check import run_law_checks

def eval_expr(node: SymNode, ctx: Optional["Context"] = None) -> Any:
    """
    Evaluate a Symatics AST node into a Signature (or entangled dict).

    Now integrates runtime law validation via run_law_checks()
    when ctx.validate_runtime=True.
    """
    # --- Leaf Node ---------------------------------------------------------
    if node.is_leaf():
        result = (
            canonical_signature(node.value)
            if ctx is None
            else ctx.canonical_signature(node.value)
        )

        # Optional per-leaf validation
        if getattr(ctx, "validate_runtime", False):
            run_law_checks(result, ctx)
        return result

    # --- Operator Node -----------------------------------------------------
    if node.op not in OPS:
        raise ValueError(f"Unknown operator: {node.op}")

    op: Operator = OPS[node.op]
    args = [eval_expr(arg, ctx) for arg in node.args]

    # --- Execute Operator Implementation ----------------------------------
    impl = op.impl
    try:
        result = impl(*args, ctx=ctx)  # modern API
    except TypeError:
        result = impl(*args)  # fallback for older ops

    # --- Runtime Validation + Telemetry -----------------------------------
    if getattr(ctx, "validate_runtime", False):
        try:
            law_results = run_law_checks(result, ctx)

            if getattr(ctx, "debug", False) and law_results:
                passed = sum(1 for r in law_results.values() if r.get("passed"))
                total = len(law_results)
                print(f"[LawCheck] {passed}/{total} passed for op {node.op}")
        except Exception as e:
            if getattr(ctx, "debug", False):
                print(f"[LawCheck] Skipped ({e})")

    return result

# ---------------------------------------------------------------------------
# Parser (S-Expression v0.1)
# ---------------------------------------------------------------------------

def parse(tokens: List[str]) -> SymNode:
    """
    Parse a simple S-expression into a SymNode tree.
    Example: ["(", "⊕", "a", "b", ")"]
    """
    if not tokens:
        raise ValueError("Unexpected EOF")

    token = tokens.pop(0)
    if token == "(":
        op = tokens.pop(0)
        args = []
        while tokens[0] != ")":
            args.append(parse(tokens))
        tokens.pop(0)  # consume ")"
        return SymNode(op=op, args=args)
    elif token.replace(".", "", 1).isdigit():
        # Treat as amplitude-only Signature (quick literal)
        return SymNode(value=literal_signature(float(token)))
    else:
        raise ValueError(f"Unexpected token: {token}")


def tokenize(expr: str) -> List[str]:
    return expr.replace("(", " ( ").replace(")", " ) ").split()


def parse_expr(expr: str) -> SymNode:
    return parse(tokenize(expr))


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Example: (μ (⊕ 1.0 2.0))
    expr = "(μ (⊕ 1.0 2.0))"
    ast = parse_expr(expr)
    result = eval_expr(ast)
    print(f"Expr: {expr}")
    print(f"AST: {ast}")
    print(f"Result: {result}")

    # Import law checks from laws.py for consistency
    from .laws import law_associativity
    print("Associativity check (⊕):", "PASS" if law_associativity() else "FAIL")

# ---------------------------------------------------------------------------
# Roadmap (Engine v0.2+)
# ---------------------------------------------------------------------------
# Parser:
#   - Extend S-expression parser with symbolic identifiers (variables).
#   - Add nested expressions with arbitrary depth.
#
# Evaluator:
#   - Context propagation through all operator calls (uniform API).
#   - Add support for probabilistic branching (for measurement).
#
# AST:
#   - Track source metadata for better debugging/tracing.
#   - Add pretty-printer for symbolic expressions.
#
# Integration:
#   - CodexCore execution binding via run_symatics_expr().
#   - SCI IDE integration: live AST + evaluation trace overlay.