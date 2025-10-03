# distutils: language = c
# cython: boundscheck=False, wraparound=False, cdivision=True

from cpython.dict cimport PyDict_GetItem
from cpython.unicode cimport PyUnicode_Check
from libc.stdlib cimport malloc, free

cdef inline bint is_special_str(object expr):
    # Avoids Python set lookup
    return expr == "∅" or expr == "⊤" or expr == "⊥"


def structural_key_cy(expr, dict cache=None):
    """
    Python entry point: structural_key in Cython.
    Falls back to cache dict if provided.
    """
    if cache is None:
        cache = {}
    return _structural_key(expr, cache)


cdef object _structural_key(object expr, dict cache):
    cdef long i = id(expr)
    cdef object cached = cache.get(i)
    if cached is not None:
        return cached

    cdef object key
    if PyUnicode_Check(expr):
        if is_special_str(expr):
            key = (expr,)
        else:
            key = ("atom", expr)

    elif isinstance(expr, dict):
        op = expr.get("op")   # keep as plain Python call
        if "state" in expr:
            child_key = _structural_key(expr["state"], cache)
            key = ("op1", op, child_key)
        elif "states" in expr:
            states = expr["states"]
            if op == "⊕":
                child_keys = [_structural_key(s, cache) for s in states]
                child_keys.sort()
            else:
                child_keys = [_structural_key(s, cache) for s in states]
            key = ("opN", op, tuple(child_keys))
        else:
            key = ("op0", op)

    elif isinstance(expr, list):
        child_keys = [_structural_key(x, cache) for x in expr]
        key = ("list", tuple(child_keys))

    else:
        # Fallback for ints, bools, etc.
        key = ("atom", expr)

    cache[i] = key
    return key