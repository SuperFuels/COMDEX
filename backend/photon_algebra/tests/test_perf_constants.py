import time
import pytest
from backend.photon_algebra.rewriter import normalize
from hypothesis import given, strategies as st

@pytest.mark.parametrize("expr", [
    {"op": "∅"},
    {"op": "⊤"},
    {"op": "⊥"},
])
def test_constants_fastpath(expr):
    """
    Ensure canonical constants are returned immediately
    without unnecessary recursive normalization.
    """
    start = time.perf_counter()
    out = normalize(expr)
    elapsed = time.perf_counter() - start

    # Structural equality
    assert out == expr

    # Guardrail: must be very fast (< 1ms)
    assert elapsed < 0.001, f"Slow constant normalization: {elapsed:.6f}s"


def test_constants_idempotent():
    """
    Normalizing constants multiple times should be stable and identical.
    """
    constants = [
        {"op": "∅"},
        {"op": "⊤"},
        {"op": "⊥"},
    ]
    for c in constants:
        n1 = normalize(c)
        n2 = normalize(normalize(c))
        assert n1 == n2
        assert n1 is n2 or n1 == c

atoms = st.sampled_from(["a", "b", "c"])


def photon_exprs(depth=3):
    if depth == 0:
        # Atoms or constants
        return st.one_of(
            atoms,
            st.just({"op": "∅"}),
            st.just({"op": "⊤"}),
            st.just({"op": "⊥"}),
        )

    return st.one_of(
        atoms,
        st.just({"op": "∅"}),
        st.just({"op": "⊤"}),
        st.just({"op": "⊥"}),

        st.builds(lambda s: {"op": "⊕", "states": s},
                  st.lists(photon_exprs(depth-1), min_size=2, max_size=3)),
        st.builds(lambda a, b: {"op": "⊗", "states": [a, b]},
                  photon_exprs(depth-1), photon_exprs(depth-1)),
        st.builds(lambda a, b: {"op": "⊖", "states": [a, b]},
                  photon_exprs(depth-1), photon_exprs(depth-1)),
        st.builds(lambda a, b: {"op": "↔", "states": [a, b]},
                  photon_exprs(depth-1), photon_exprs(depth-1)),
        st.builds(lambda s: {"op": "¬", "state": s}, photon_exprs(depth-1)),
        st.builds(lambda s: {"op": "★", "state": s}, photon_exprs(depth-1)),
    )


@given(photon_exprs())
def test_normalize_constants_embedded(expr):
    """
    Property: normalize() must be stable when constants ⊤, ⊥, ∅
    appear inside larger expressions.
    """
    n1 = normalize(expr)
    n2 = normalize(normalize(expr))
    assert n1 == n2