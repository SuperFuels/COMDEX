# File: backend/photon_algebra/tests/test_photon_canonical_ordering.py
import pytest
from hypothesis import given, strategies as st

from backend.photon_algebra.rewriter import normalize
from backend.photon_algebra.renderer import render_photon


def test_commutativity_plus():
    e1 = {"op": "⊕", "states": ["a", "b"]}
    e2 = {"op": "⊕", "states": ["b", "a"]}
    assert normalize(e1) == normalize(e2)


def test_commutativity_times():
    e1 = {"op": "⊗", "states": ["a", "b"]}
    e2 = {"op": "⊗", "states": ["b", "a"]}
    assert normalize(e1) == normalize(e2)


def test_idempotence_plus():
    expr = {"op": "⊕", "states": ["a", "a"]}
    assert normalize(expr) == "a"


@given(st.lists(st.sampled_from(["a", "b", "c", "d"]), min_size=2, max_size=5))
def test_plus_canonicalization_commutativity(xs):
    """
    Any shuffle of xs under ⊕ should normalize to the same canonical form.
    """
    # Build ⊕ expr
    expr = {"op": "⊕", "states": xs}
    shuffled_expr = {"op": "⊕", "states": list(reversed(xs))}

    norm1 = normalize(expr)
    norm2 = normalize(shuffled_expr)

    assert norm1 == norm2


@given(st.lists(st.sampled_from(["p", "q", "r"]), min_size=2, max_size=5))
def test_idempotence_and_sort(xs):
    """
    Duplicates should collapse (idempotence),
    and ordering should be canonicalized (sorted).
    """
    expr = {"op": "⊕", "states": xs}
    norm = normalize(expr)

    if isinstance(norm, dict) and norm.get("op") == "⊕":
        states = norm["states"]
        # No duplicates
        assert len(states) == len(set(map(str, states)))
        # Sorted order
        assert states == sorted(states, key=lambda s: str(s))

@given(st.lists(st.sampled_from(["a", "b", "c", "d"]), min_size=2, max_size=5))
def test_times_canonicalization_commutativity(xs):
    """
    Any shuffle of xs under ⊗ should normalize to the same canonical form.
    """
    expr = {"op": "⊗", "states": xs}
    shuffled_expr = {"op": "⊗", "states": list(reversed(xs))}

    norm1 = normalize(expr)
    norm2 = normalize(shuffled_expr)

    assert norm1 == norm2


@given(st.lists(st.sampled_from(["p", "q", "r"]), min_size=2, max_size=5))
def test_times_idempotence_and_sort(xs):
    """
    Duplicates should collapse (idempotence),
    and ordering should be canonicalized (sorted) for ⊗ as well.
    """
    expr = {"op": "⊗", "states": xs}
    norm = normalize(expr)

    if isinstance(norm, dict) and norm.get("op") == "⊗":
        states = norm["states"]
        # No duplicates
        assert len(states) == len(set(map(str, states)))
        # Sorted order
        assert states == sorted(states, key=lambda s: str(s))