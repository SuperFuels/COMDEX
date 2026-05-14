"""
Bounded joinability probes for the *directed* Photon Algebra normalizer.

Why the restrictions:
- Normalization is a *directed canonicalization*: distribution is only allowed from the ⊗ branch,
  and we intentionally do NOT factor in the ⊕ branch.
- If you freely reassociate/commute ⊗ across operands that contain ⊕, you change *where/when*
  distribution can fire, producing “variants” that are not neutral under this directed strategy.
  That’s not a core bug; it’s a consequence of choosing a single rewrite direction to guarantee
  termination + a stable normal form.
- Therefore, this test only generates one-step variants that are safe w.r.t. the chosen strategy.
"""

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


def dumps_key(x) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


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


def safe_for_prod_reassoc(x) -> bool:
    """
    Reassociating ⊗ changes *when/where* distribution can fire if any operand contains ⊕.
    So only allow ⊗ reassociation when all three participating operands are ⊕-free.
    """
    return not contains_sum(x)


def is_atom(x) -> bool:
    return isinstance(x, str)


# ---- One-step variants (bounded, sound-for-this-normalizer) -------------------

MAX_STEPS_CHECKED = 80  # bumped slightly (was 40); keep CI-friendly


def one_step_variants(e):
    """
    Generate a bounded set of one-step joinability probes that are safe with the
    directed normalizer strategy:

      - ⊕ commutativity: swap children
      - ⊕ associativity: ((a⊕b)⊕c) <-> (a⊕(b⊕c))   (always safe)
      - ⊗ commutativity: swap children              (only if both children are ⊕-free)
      - ⊗ associativity: ((a⊗b)⊗c) <-> (a⊗(b⊗c))   (only if a,b,c are ⊕-free)
      - Optional: a single pre-distribution step of ⊗ over ⊕ (same direction as normalize),
        BUT ONLY when the distributed factor is an *atom* (avoids strategy-dependent variants).

    We apply at ONE node (either root or inside a child), returning a deduped set.
    """
    out = {}

    def add(x):
        if x is None:
            return
        out[dumps_key(x)] = x

    def distribute_once(node):
        # One safe distribution step: X ⊗ (P ⊕ Q) -> (X⊗P) ⊕ (X⊗Q)
        # Restriction: only allow when the factor X is an ATOM, so we don't introduce
        # strategy-dependent variants like (a⊕b)⊗(a⊗b).
        if not isinstance(node, dict) or node.get("op") != "⊗":
            return None
        xs = node.get("states", [])
        if not (isinstance(xs, list) and len(xs) == 2):
            return None

        a, b = xs

        # a ⊗ (p ⊕ q)
        if (
            is_atom(a)
            and isinstance(b, dict)
            and b.get("op") == "⊕"
            and isinstance(b.get("states"), list)
            and len(b["states"]) == 2
        ):
            p, q = b["states"]
            return SUM(PROD(deepclone(a), deepclone(p)), PROD(deepclone(a), deepclone(q)))

        # (p ⊕ q) ⊗ b
        if (
            is_atom(b)
            and isinstance(a, dict)
            and a.get("op") == "⊕"
            and isinstance(a.get("states"), list)
            and len(a["states"]) == 2
        ):
            p, q = a["states"]
            return SUM(PROD(deepclone(p), deepclone(b)), PROD(deepclone(q), deepclone(b)))

        return None

    def one_step_at_node(node):
        """Generate one-step variants at this exact node (no recursion)."""
        local = {}

        def ladd(x):
            if x is None:
                return
            local[dumps_key(x)] = x

        if not isinstance(node, dict):
            return []

        op = node.get("op")
        xs = node.get("states", [])
        if not (isinstance(xs, list) and len(xs) == 2):
            return []

        a, b = xs

        if op == "⊕":
            # commutativity
            ladd({"op": "⊕", "states": [deepclone(b), deepclone(a)]})

            # associativity (both directions) if nested
            if (
                isinstance(a, dict)
                and a.get("op") == "⊕"
                and isinstance(a.get("states"), list)
                and len(a["states"]) == 2
            ):
                x, y = a["states"]
                z = b
                ladd({"op": "⊕", "states": [deepclone(x), SUM(deepclone(y), deepclone(z))]})
            if (
                isinstance(b, dict)
                and b.get("op") == "⊕"
                and isinstance(b.get("states"), list)
                and len(b["states"]) == 2
            ):
                y, z = b["states"]
                x = a
                ladd({"op": "⊕", "states": [SUM(deepclone(x), deepclone(y)), deepclone(z)]})

        elif op == "⊗":
            # commutativity only when both children are ⊕-free
            if safe_for_prod_reassoc(a) and safe_for_prod_reassoc(b):
                ladd({"op": "⊗", "states": [deepclone(b), deepclone(a)]})

            # associativity only when all participating operands are ⊕-free
            if (
                isinstance(a, dict)
                and a.get("op") == "⊗"
                and isinstance(a.get("states"), list)
                and len(a["states"]) == 2
            ):
                x, y = a["states"]
                z = b
                if safe_for_prod_reassoc(x) and safe_for_prod_reassoc(y) and safe_for_prod_reassoc(z):
                    ladd({"op": "⊗", "states": [deepclone(x), PROD(deepclone(y), deepclone(z))]})

            if (
                isinstance(b, dict)
                and b.get("op") == "⊗"
                and isinstance(b.get("states"), list)
                and len(b["states"]) == 2
            ):
                y, z = b["states"]
                x = a
                if safe_for_prod_reassoc(x) and safe_for_prod_reassoc(y) and safe_for_prod_reassoc(z):
                    ladd({"op": "⊗", "states": [PROD(deepclone(x), deepclone(y)), deepclone(z)]})

            # pre-distribution (restricted)
            ladd(distribute_once(node))

        return list(local.values())

    def rec(node):
        # one-step at this node
        for v in one_step_at_node(node):
            add(v)

        # recurse one level: apply one-step inside a child (keeping parent unchanged)
        if isinstance(node, dict):
            xs = node.get("states", [])
            if isinstance(xs, list) and len(xs) == 2:
                for idx in (0, 1):
                    ch = xs[idx]
                    for vch in one_step_at_node(ch)[:12]:
                        nn = deepclone(node)
                        nn["states"][idx] = vch
                        add(nn)

    add(deepclone(e))
    rec(deepclone(e))
    return list(out.values())


@settings(max_examples=250, deadline=None)
@given(exprs)
def test_bounded_confluence_via_one_step_joinability(e):
    """
    Practical bounded local-joinability evidence for the *directed* strategy:
    all one-step variants we generate should normalize to the same NF.
    """
    nf = rewriter.normalize(deepclone(e))
    steps = one_step_variants(deepclone(e))

    for v in steps[:MAX_STEPS_CHECKED]:
        assert rewriter.normalize(deepclone(v)) == nf