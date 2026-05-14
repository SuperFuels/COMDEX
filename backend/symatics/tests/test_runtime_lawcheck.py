# backend/symatics/tests/test_runtime_lawcheck.py

from backend.symatics.engine import eval_expr, SymNode
from backend.symatics.signature import Signature
from backend.symatics.context import Context


def test_eval_expr_lawcheck_smoke():
    """
    Smoke test for runtime law validation.
    Verifies that eval_expr runs successfully with ctx.validate_runtime=True.
    """
    ctx = Context(validate_runtime=True, enable_trace=False, debug=True)

    # Create a simple literal node (Signature as leaf)
    sig = Signature(1.0, 1000.0, 0.0, "H")
    node = SymNode(value=sig)

    # Evaluate (this will trigger canonicalization + law check)
    result = eval_expr(node, ctx)

    assert result is not None
    assert isinstance(result, Signature)