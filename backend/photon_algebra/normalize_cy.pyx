# distutils: language = c
# cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True

from cpython.dict cimport PyDict_GetItem
from cpython.object cimport PyObject
from cpython.list cimport PyList_New, PyList_SET_ITEM

# Use our faster structural_key
from backend.photon_algebra.structural_key_cy import structural_key_cy

# Import DIAG counters and constants from Python side
from backend.photon_algebra.rewriter import DIAG, EMPTY, TOP, BOTTOM


def normalize_cy(expr, ctx):
    """Entry point: normalize expression with Cython inner loop."""
    return _normalize_inner_cy(expr, ctx)


cdef object _normalize_inner_cy(object expr, object ctx):
    cdef object op, states, key
    cdef list norm_states
    cdef list unique
    cdef dict seen
    cdef object s, out

    if isinstance(expr, str):
        return expr

    elif isinstance(expr, dict):
        op = expr.get("op")

        # ------------------------------------------------------------------
        # OR (⊕) — commutative + idempotent
        # ------------------------------------------------------------------
        if op == "⊕":
            states = expr.get("states", [])
            norm_states = [_normalize_inner_cy(s, ctx) for s in states]

            # Deduplicate via structural_key_cy
            seen = {}
            unique = []
            for s in norm_states:
                key = structural_key_cy(s, ctx.key_cache)
                if key not in seen:
                    seen[key] = 1
                    unique.append(s)
                else:
                    DIAG.idempotence += 1

            if not unique:
                return EMPTY
            if len(unique) == 1:
                return unique[0]

            # Canonicalize order
            unique.sort(key=lambda x: structural_key_cy(x, ctx.key_cache))
            return {"op": "⊕", "states": unique}

        # ------------------------------------------------------------------
        # AND (⊗) — commutative, absorption, distribution
        # ------------------------------------------------------------------
        elif op == "⊗":
            states = expr.get("states", [])
            norm_states = [_normalize_inner_cy(s, ctx) for s in states]

            # Absorption: annihilation if any operand is ∅
            for s in norm_states:
                if isinstance(s, dict) and s.get("op") == "∅":
                    return EMPTY

            # Deduplicate
            seen = {}
            unique = []
            for s in norm_states:
                key = structural_key_cy(s, ctx.key_cache)
                if key not in seen:
                    seen[key] = 1
                    unique.append(s)
                else:
                    DIAG.idempotence += 1

            if not unique:
                return EMPTY
            if len(unique) == 1:
                return unique[0]

            # Canonicalize commutativity
            unique.sort(key=lambda x: structural_key_cy(x, ctx.key_cache))

            # Distribution: a ⊗ (b ⊕ c) → (a⊗b) ⊕ (a⊗c)
            for s in unique:
                if isinstance(s, dict) and s.get("op") == "⊕":
                    others = [x for x in unique if x is not s]
                    DIAG.distributions += 1
                    return _normalize_inner_cy(
                        {"op": "⊕", "states": [
                            {"op": "⊗", "states": others + [sub]}
                            for sub in s["states"]
                        ]},
                        ctx
                    )

            return {"op": "⊗", "states": unique}

        # ------------------------------------------------------------------
        # NOT (¬)
        # ------------------------------------------------------------------
        elif op == "¬":
            inner = _normalize_inner_cy(expr.get("state"), ctx)
            return {"op": "¬", "state": inner}

        # ------------------------------------------------------------------
        # STAR (★)
        # ------------------------------------------------------------------
        elif op == "★":
            inner = _normalize_inner_cy(expr.get("state"), ctx)
            return {"op": "★", "state": inner}

        # ------------------------------------------------------------------
        # Constants / trivial cases
        # ------------------------------------------------------------------
        elif op in ("∅", "⊤", "⊥"):
            return {"op": op}

        # ------------------------------------------------------------------
        # Fallback to Python for rare ops (⊖, ≈, ↔, etc.)
        # ------------------------------------------------------------------
        from backend.photon_algebra.rewriter import _normalize_inner
        return _normalize_inner(expr, ctx)

    else:
        return expr