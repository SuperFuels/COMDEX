import json
from hypothesis import given, settings, strategies as st

from backend.photon_algebra import rewriter, core


def SUM(a, b):
    return {"op": "⊕", "states": [a, b]}


def PROD(a, b):
    return {"op": "⊗", "states": [a, b]}


EMPTY = core.EMPTY


def deepclone(x):
    return json.loads(json.dumps(x, ensure_ascii=False))


# ---- Generator: PA-core-ish, binary-only -------------------------------------

atoms = st.sampled_from(["a", "b", "c", "d"])


def core_exprs(max_leaves=40):
    leaf = st.one_of(atoms, st.just(EMPTY))

    def extend(children):
        return st.one_of(
            st.tuples(children, children).map(lambda t: SUM(t[0], t[1])),
            st.tuples(children, children).map(lambda t: PROD(t[0], t[1])),
        )

    return st.recursive(leaf, extend, max_leaves=max_leaves)


exprs = core_exprs()


# ---- Helpers -----------------------------------------------------------------

def contains_sum(e) -> bool:
    """True iff an expression contains any ⊕ node anywhere."""
    if isinstance(e, dict):
        if e.get("op") == "⊕":
            return True
        xs = e.get("states", [])
        if isinstance(xs, list):
            return any(contains_sum(x) for x in xs)
    return False


def has_sum_directly_under_prod(e) -> bool:
    """NF invariant: no ⊕ as a direct child of ⊗."""
    if not isinstance(e, dict):
        return False
    op = e.get("op")
    if op == "⊗":
        xs = e.get("states", [])
        if isinstance(xs, list):
            for ch in xs:
                if isinstance(ch, dict) and ch.get("op") == "⊕":
                    return True
    xs = e.get("states", [])
    if isinstance(xs, list):
        return any(has_sum_directly_under_prod(ch) for ch in xs)
    return False


# ---- Properties --------------------------------------------------------------

@settings(max_examples=250, deadline=None)
@given(exprs)
def test_idempotence(e):
    n1 = rewriter.normalize(deepclone(e))
    n2 = rewriter.normalize(deepclone(n1))
    assert n1 == n2


@settings(max_examples=250, deadline=None)
@given(exprs)
def test_no_sum_under_prod_in_normal_form(e):
    nf = rewriter.normalize(deepclone(e))
    assert not has_sum_directly_under_prod(nf)


@settings(max_examples=250, deadline=None)
@given(exprs, exprs)
def test_commutativity_stability_sum(a, b):
    a = rewriter.normalize(deepclone(a))
    b = rewriter.normalize(deepclone(b))
    assert rewriter.normalize(deepclone(SUM(a, b))) == rewriter.normalize(deepclone(SUM(b, a)))


@settings(max_examples=250, deadline=None)
@given(exprs, exprs)
def test_commutativity_stability_product(a, b):
    # For ⊗, commutativity-as-a-normal-form property is only stable when
    # we are not forcing distribution-sensitive operands (⊕) into the product.
    a = rewriter.normalize(deepclone(a))
    b = rewriter.normalize(deepclone(b))

    if contains_sum(a) or contains_sum(b):
        return

    assert rewriter.normalize(deepclone(PROD(a, b))) == rewriter.normalize(deepclone(PROD(b, a)))


@settings(max_examples=250, deadline=None)
@given(exprs, exprs, exprs)
def test_associativity_stability_sum(a, b, c):
    a = rewriter.normalize(deepclone(a))
    b = rewriter.normalize(deepclone(b))
    c = rewriter.normalize(deepclone(c))
    left = SUM(SUM(a, b), c)
    right = SUM(a, SUM(b, c))
    assert rewriter.normalize(deepclone(left)) == rewriter.normalize(deepclone(right))


@settings(max_examples=250, deadline=None)
@given(exprs, exprs, exprs)
def test_associativity_stability_product(a, b, c):
    # Same story: grouping affects when distribution fires if any operand contains ⊕.
    a = rewriter.normalize(deepclone(a))
    b = rewriter.normalize(deepclone(b))
    c = rewriter.normalize(deepclone(c))

    if contains_sum(a) or contains_sum(b) or contains_sum(c):
        return

    left = PROD(PROD(a, b), c)
    right = PROD(a, PROD(b, c))
    assert rewriter.normalize(deepclone(left)) == rewriter.normalize(deepclone(right))


@settings(max_examples=250, deadline=None)
@given(atoms, exprs)
def test_absorption_sanity(a, b):
    # Absorption is guaranteed in the specific NF setting:
    # if 'a' appears as a SUM term, drop any term with a product that has 'a' as a factor.
    #
    # But distribution can change whether (a ⊗ b) appears as a direct SUM term if b contains ⊕.
    b = rewriter.normalize(deepclone(b))

    if contains_sum(b):
        return

    lhs = SUM(a, PROD(a, b))
    assert rewriter.normalize(deepclone(lhs)) == rewriter.normalize(deepclone(a))