import math
import pytest
from hypothesis import given, strategies as st

from backend.symatics import rewriter as R


# -----------------
# Strategies
# -----------------

atoms = st.sampled_from(["A", "B", "C", "D"])

phases = st.one_of(
    st.floats(min_value=-10.0, max_value=10.0, allow_nan=False, allow_infinity=False),  # arbitrary φ
    st.just(0.0),                                # special φ=0
    st.just(math.pi),                            # special φ=π
)


@st.composite
def exprs(draw, depth=0):
    """Recursive generator for Symatics expressions."""
    if depth > 2 or draw(st.booleans()):
        # terminal: atom or ⊥
        if draw(st.booleans()):
            return R.Bot()
        else:
            return R.Atom(draw(atoms))
    else:
        φ = draw(phases)
        left = draw(exprs(depth=depth + 1))
        right = draw(exprs(depth=depth + 1))
        return R.Interf(R.norm_phase(φ), left, right)


# -----------------
# Properties
# -----------------

@given(exprs())
def test_normalize_idempotent(e):
    """normalize(e) is idempotent."""
    n1 = R.normalize(e)
    n2 = R.normalize(n1)
    assert n1 == n2


@given(exprs())
def test_structural_equiv_reflexive(e):
    """symatics_structural_equiv(e, e) always holds."""
    assert R.symatics_structural_equiv(e, e)


@given(atoms)
def test_special_cases(atom):
    """Special phases reduce correctly for self-interference."""
    A = R.Atom(atom)

    # φ=0: (A ⋈[0] A) → A
    e0 = R.Interf(0.0, A, A)
    assert R.normalize(e0) == A

    # φ=π: (A ⋈[π] A) → ⊥
    epi = R.Interf(math.pi, A, A)
    assert isinstance(R.normalize(epi), R.Bot)

    # φ=nontrivial: stays neither A nor ⊥
    ephi = R.Interf(0.7, A, A)
    norm = R.normalize(ephi)
    assert norm != A
    assert not isinstance(norm, R.Bot)


@given(exprs())
def test_normalize_terminates_quickly(e):
    """
    normalize should converge within 200 steps (guard against runaway rewrites).
    For realistic expressions, it should finish well under this budget.
    """
    try:
        norm = R.normalize(e, max_steps=200)
    except RuntimeError:
        pytest.fail("normalize did not converge within 200 steps")

    # Sanity check: idempotence after normalization
    assert R.normalize(norm) == norm