# backend/photon_algebra/rewriter.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Union

# 🔑 shared canonical empty state (import once)
from backend.photon_algebra.core import EMPTY

Expr = Union[str, Dict[str, Any]]
# --- global normalize cache --------------------------------------------------
# =============================================================================
# Variable-based Pattern Matching (notes)
# -----------------------------------------------------------------------------
# - Variables are lowercase ASCII identifiers (e.g., "a", "b", "c") or tokens
#   that start with '?' (e.g., "?x"). They unify with any sub-expression.
# - Repeated variables must match the same sub-expression (unification).
# =============================================================================

# =============================================================================
# Normalization memoization + structural key caching
# -----------------------------------------------------------------------------
# We keep:
#   1) A process-wide memo (_NORM_MEMO) keyed by a structural key string → normalized expr.
#   2) A per-normalize-run context (_NormCtx) that caches:
#        - memo: local results (can be cleared in tests)
#        - key_cache: id(node) → _string_key(node) to avoid recomputation
# _string_key(node) itself is defined elsewhere in this module.
# =============================================================================

# --- memo + key helpers -----------------------------------------------------
from typing import Any, Dict, Optional

# Global memo: structural key -> normalized tree (public cache)
_NORMALIZE_MEMO: Dict[str, Any] = {}

_cache_hits = 0
_cache_misses = 0

def clear_normalize_memo() -> None:
    global _cache_hits, _cache_misses
    _NORMALIZE_MEMO.clear()
    _structural_key.cache_clear()
    _cache_hits = 0
    _cache_misses = 0

class _NormCtx:
    """Per-normalize call context with local memo and fast key cache."""
    __slots__ = ("memo", "key_cache")
    def __init__(self) -> None:
        # local memo: structural key of *current* nodes -> normalized
        self.memo: Dict[str, Any] = {}
        # cache of id(node) -> structural key, to avoid recomputing _string_key
        self.key_cache: Dict[int, str] = {}

from functools import lru_cache
import json

@lru_cache(maxsize=10_000)
def _structural_key(expr_json: str) -> tuple:
    """
    Compute a stable, hashable structural key for memoization.
    Accepts a JSON string (hashable) instead of raw dicts.
    """
    expr = json.loads(expr_json)
    if not isinstance(expr, dict):
        return ("atom", str(expr))

    op = expr.get("op")
    if op == "∅":
        return ("∅",)

    if "state" in expr:
        return ("op1", op, _structural_key(json.dumps(expr["state"], sort_keys=True)))

    if "states" in expr:
        states = expr["states"]
        if op == "⊕":
            child_keys = tuple(sorted(
                _structural_key(json.dumps(s, sort_keys=True)) for s in states
            ))
        else:
            child_keys = tuple(
                _structural_key(json.dumps(s, sort_keys=True)) for s in states
            )
        return ("opN", op, *child_keys)

    return ("op0", op)

def structural_key(expr: Any) -> tuple:
    """Public wrapper that stringifies expr before passing to _structural_key."""
    import json
    return _structural_key(json.dumps(expr, sort_keys=True))

def _string_key_ctx(node: Any, cache: Dict[int, str]) -> str:
    """
    Like _string_key(node) but caches by id(node) within a single normalize call.
    Safe because we only use it on the normalized-shape nodes of this traversal.
    """
    if not isinstance(node, dict):
        # atoms (strings) — just return themselves
        return str(node)
    i = id(node)
    k = cache.get(i)
    if k is not None:
        return k
    k = _string_key(node)  # uses your existing canonical key function
    cache[i] = k
    return k

def _key_cached(node: Any, cache: Dict[int, str]) -> str:
    """Alias used by the outer quick memo; same semantics as _string_key_ctx."""
    return _string_key_ctx(node, cache)

# Test/CI hook — placeholder until the E5 performance memo lands.
def reset_normalize_memo() -> None:
    """Clear the normalize() memo cache (currently a no-op stub)."""
    return None

# --- Public entrypoint with global memo -------------------------------------

def normalize(expr: Any) -> Any:
    """
    Normalize Photon expressions under axioms + calculus rules:
      - Apply rewrite rules to a fixed point (T8–T15, etc.)
      - Canonicalize ⊕: flatten, drop ∅, absorption, idempotence, commutativity
      - Distribute ⊗ over ⊕ (both sides)  [⊗ handles distribution; ⊕ does NOT factor]
      - Cancellation: a ⊖ a = ∅ ; a ⊖ ∅ = a ; ∅ ⊖ a = a
      - Double negation: ¬(¬a) = a
    """
    # atoms (strings) fast-path
    if not isinstance(expr, dict):
        return expr

    # global memo by *input* structural key
    k0 = _string_key(expr)
    cached = _NORM_MEMO.get(k0)
    if cached is not None:
        return cached

    out = _normalize_inner(expr, _NormCtx())
    _NORM_MEMO[k0] = out
    return out

# -----------------------------------------------------------------------------
# Pattern variable predicate
# -----------------------------------------------------------------------------
def is_var(token: Any) -> bool:
    """Variables are lowercase ASCII names or tokens starting with '?'."""
    if not isinstance(token, str):
        return False
    return token.startswith("?") or (len(token) > 0 and token.isascii() and token.islower())

def match_pattern(pattern: Expr, expr: Expr, env: Dict[str, Expr] | None = None):
    """
    Try to match `pattern` against `expr`. Returns (ok, env) where env contains
    variable bindings. Variables are strings recognized by `is_var`.
    """
    if env is None:
        env = {}

    # Variable: bind or check consistency
    if is_var(pattern):
        bound = env.get(pattern, None)
        if bound is None:
            env[pattern] = expr
            return True, env
        return (bound == expr), env

    # Atomic strings: must be equal
    if isinstance(pattern, str):
        return (pattern == expr), env

    # Dicts: op + (state|states)
    if isinstance(pattern, dict) and isinstance(expr, dict):
        if pattern.get("op") != expr.get("op"):
            return False, env

        # state
        if "state" in pattern:
            ok, env = match_pattern(pattern["state"], expr.get("state"), env)
            if not ok:
                return False, env

        # states
        if "states" in pattern:
            p_states = pattern.get("states", [])
            e_states = expr.get("states", [])

            if len(p_states) != len(e_states):
                return False, env

            if expr.get("op") in COMMUTATIVE:
                # Order-insensitive: try all permutations
                import itertools
                for perm in itertools.permutations(e_states, len(p_states)):
                    env_try = env.copy()
                    ok = True
                    for p, e in zip(p_states, perm):
                        ok2, env_try = match_pattern(p, e, env_try)
                        if not ok2:
                            ok = False
                            break
                    if ok:
                        return True, env_try
                return False, env
            else:
                # Positional match
                for p, e in zip(p_states, e_states):
                    ok, env = match_pattern(p, e, env)
                    if not ok:
                        return False, env

        return True, env

    # Type mismatch
    return False, env


def substitute(node: Expr, env: Dict[str, Expr]) -> Expr:
    """Substitute variables in `node` using env. Deep-copies dicts."""
    if is_var(node):
        return env.get(node, node)
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        out = {"op": node.get("op")}
        if "state" in node:
            out["state"] = substitute(node["state"], env)
        if "states" in node:
            out["states"] = [substitute(s, env) for s in node["states"]]
        return out
    return copy.deepcopy(node)


# =============================================================================
# Rewrite Rules (axioms + derived theorems)
#
# Notes:
# • T14 (Dual Distributivity) is intentionally NOT in this table. Distribution
#   is handled structurally in normalize(): ⊗ distributes over ⊕; ⊕ does not factor.
#   Keeping a T14 factoring rule here can ping-pong with ⊗→⊕ distribution.
# • ⊗ idempotence (a ⊗ a → a) is enforced locally in normalize()’s ⊗ branch
#   (post-commutativity) to keep normal forms stable.
# =============================================================================

REWRITE_RULES: List[Tuple[Expr, Expr]] = [
    # P — Associativity: (a ⊕ b) ⊕ c → a ⊕ (b ⊕ c)
    (
        {"op": "⊕", "states": [{"op": "⊕", "states": ["a", "b"]}, "c"]},
        {"op": "⊕", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
    ),

    # P — Commutativity: a ⊕ b → b ⊕ a
    (
        {"op": "⊕", "states": ["a", "b"]},
        {"op": "⊕", "states": ["b", "a"]},
    ),

    # P — Idempotence: a ⊕ a → a
    (
        {"op": "⊕", "states": ["a", "a"]},
        "a",
    ),

    # (REMOVED) T14 — Dual Distributivity:
    # We intentionally do NOT keep a factoring rule here:
    #     a ⊕ (b ⊗ c) → (a ⊕ b) ⊗ (a ⊕ c)
    # normalize()’s ⊗ branch handles distribution; a table rule would ping-pong.

    # P — Cancellation: a ⊖ a → ∅
    (
        {"op": "⊖", "states": ["a", "a"]},
        EMPTY,
    ),

    # P — Double Negation: ¬(¬a) → a
    (
        {"op": "¬", "state": {"op": "¬", "state": "a"}},
        "a",
    ),

    # T10 — Entanglement distributivity: (a↔b) ⊕ (a↔c) → a ↔ (b ⊕ c)
    (
        {"op": "⊕", "states": [
            {"op": "↔", "states": ["a", "b"]},
            {"op": "↔", "states": ["a", "c"]},
        ]},
        {"op": "↔", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
    ),
    # T10 (commuted): (a↔c) ⊕ (a↔b) → a ↔ (b ⊕ c)
    (
        {"op": "⊕", "states": [
            {"op": "↔", "states": ["a", "c"]},
            {"op": "↔", "states": ["a", "b"]},
        ]},
        {"op": "↔", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
    ),

    # T11 — Entanglement idempotence: a ↔ a → a
    (
        {"op": "↔", "states": ["a", "a"]},
        "a",
    ),

    # T12 — Projection fidelity: ★(a↔b) → (★a) ⊕ (★b)
    (
        {"op": "★", "state": {"op": "↔", "states": ["a", "b"]}},
        {"op": "⊕", "states": [
            {"op": "★", "state": "a"},
            {"op": "★", "state": "b"},
        ]},
    ),

    # T13 — Absorption: a ⊕ (a ⊗ b) → a
    (
        {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["a", "b"]}]},
        "a",
    ),
    # T13 (commuted): (a ⊗ b) ⊕ a → a
    (
        {"op": "⊕", "states": [{"op": "⊗", "states": ["a", "b"]}, "a"]},
        "a",
    ),

    # T15 — Falsification: a ⊖ ∅ → a
    (
        {"op": "⊖", "states": ["a", {"op": "∅"}]},
        "a",
    ),
    # T15 (swapped): ∅ ⊖ a → a
    (
        {"op": "⊖", "states": [{"op": "∅"}, "a"]},
        "a",
    ),
]

# =============================================================================
# Rewrite Engine
# =============================================================================

COMMUTATIVE = {"⊕"}  # if you later add commutativity for other ops, extend this set

def rewrite_once(expr: Expr) -> Expr:
    """Apply at most one rewrite rule to expr (top-level), considering commutative flips."""
    # try direct order
    for pattern, replacement in REWRITE_RULES:
        env = match(expr, pattern)
        if env is not None:
            return substitute(replacement, env)

    # if op is commutative, also try swapped operands for matching
    if isinstance(expr, dict) and expr.get("op") in COMMUTATIVE:
        st = expr.get("states", [])
        if len(st) == 2:
            flipped = {"op": expr["op"], "states": [st[1], st[0]]}
            for pattern, replacement in REWRITE_RULES:
                env = match(flipped, pattern)
                if env is not None:
                    # apply replacement to flipped env, then keep result (no need to unflip)
                    return substitute(replacement, env)

    return expr


def rewrite_fixpoint(expr: Expr, max_iters: int = 64) -> Expr:
    """Apply rewrite_once until no change (or iteration cap)."""
    current = expr
    for _ in range(max_iters):
        nxt = rewrite_once(current)
        if nxt == current:
            break
        current = nxt
    return current


# =============================================================================
# Structural Normalization (canonical form)
#  - flatten / sort / dedupe for ⊕
#  - distribute ⊗ over ⊕
#  - handle ⊖, ¬, ∅
#  Then run rewrite_fixpoint to catch theorem-based rewrites.
# =============================================================================

# helper used for stable sorting/canonicalization
def _string_key(x) -> str:
    return str(x)

def _normalize_shallow(expr: Expr) -> Expr:
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")
    states = expr.get("states", [])

    # Normalize children first
    norm_state = expr.get("state")
    if norm_state is not None:
        norm_state = normalize(norm_state)
    norm_states = [normalize(s) for s in states]

    if op == "⊕":
        # Flatten nested ⊕
        flat: List[Expr] = []
        for s in norm_states:
            if isinstance(s, dict) and s.get("op") == "⊕":
                flat.extend(s.get("states", []))
            else:
                flat.append(s)

        # Remove ∅ (identity for ⊕)
        flat = [s for s in flat if not (isinstance(s, dict) and s.get("op") == "∅")]

        # Absorption: drop (a ⊗ b) if 'a' (or 'b') present as a standalone in the sum
        present_atoms = {_string_key(s) for s in flat
                         if not (isinstance(s, dict) and s.get("op") == "⊗")}
        pruned: List[Expr] = []
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "⊗":
                a, b = s.get("states", [None, None])
                if _string_key(a) in present_atoms or _string_key(b) in present_atoms:
                    # absorbed by an existing atom in the sum
                    continue
            pruned.append(s)
        flat = pruned

        # Deduplicate (idempotence) + commutativity (sorted)
        dedup: List[Expr] = []
        seen = set()
        for s in flat:
            k = _string_key(s)
            if k in seen:
                continue
            seen.add(k)
            dedup.append(s)
        dedup_sorted = sorted(dedup, key=_string_key)

        if len(dedup_sorted) == 0:
            return EMPTY
        if len(dedup_sorted) == 1:
            return dedup_sorted[0]
        return {"op": "⊕", "states": dedup_sorted}

    elif op == "⊗":
        # Work with normalized children we computed above
        states = norm_states

        # First, canonicalize commutativity: sort the two operands
        if len(states) == 2:
            a, b = states
            # ensure a ⊗ b == b ⊗ a by stable key
            if _string_key(a) > _string_key(b):
                a, b = b, a

            # Distribute over ⊕ on either side (then recurse through normalize)
            if isinstance(b, dict) and b.get("op") == "⊕":
                return normalize({
                    "op": "⊕",
                    "states": [{"op": "⊗", "states": [a, bi]} for bi in b["states"]]
                })
            if isinstance(a, dict) and a.get("op") == "⊕":
                return normalize({
                    "op": "⊕",
                    "states": [{"op": "⊗", "states": [ai, b]} for ai in a["states"]]
                })
            return {"op": "⊗", "states": [a, b]}

        # Fallback for non-binary or already-normalized cases
        return {"op": "⊗", "states": states}

    elif op == "⊖":
        if len(norm_states) == 2:
            x, y = norm_states
            # a ⊖ a = ∅
            if x == y:
                return EMPTY
            # a ⊖ ∅ = a ; ∅ ⊖ a = a
            if isinstance(y, dict) and y.get("op") == "∅":
                return x
            if isinstance(x, dict) and x.get("op") == "∅":
                return y
        return {"op": "⊖", "states": norm_states}

    elif op == "¬":
        inner = norm_state if norm_state is not None else (norm_states[0] if norm_states else None)
        # ¬(¬a) → a
        if isinstance(inner, dict) and inner.get("op") == "¬":
            inner2 = inner.get("state") if "state" in inner else (inner.get("states", [None])[0])
            return normalize(inner2)
        return {"op": "¬", "state": inner}

    elif op == "∅":
        return EMPTY

    # Generic pass-through op
    out = {"op": op}
    if norm_states:
        out["states"] = norm_states
    if norm_state is not None:
        out["state"] = norm_state
    return out


# --- helpers ---------------------------------------------------------------

def _flatten_plus(seq):
    """
    Flatten ⊕ nodes out of a list of states until no ⊕ remains directly inside.
    Ensures we never keep a nested ⊕ node itself alongside its children.
    """
    out = list(seq)
    changed = True
    while changed:
        changed = False
        new = []
        for s in out:
            if isinstance(s, dict) and s.get("op") == "⊕" and isinstance(s.get("states"), list):
                new.extend(s["states"])   # keep only the children, never the ⊕ node itself
                changed = True
            else:
                new.append(s)
        out = new
    return out

def rewrite_fixed(expr: Expr, max_iter: int = 64, debug: bool = False) -> Expr:
    """
    Iteratively apply rewrite_once until a fixed point.
    If debug=True, prints the expression at each iteration.
    """
    cur = expr
    for i in range(max_iter):
        nxt = rewrite_once(cur)
        if nxt == cur:
            break
        if debug:
            print(f"[rewrite_fixed] Iter {i}: {cur}  →  {nxt}")
        cur = nxt
    return cur


# --- global normalize cache --------------------------------------------------
from typing import Dict, Any

# cache: structural-key -> normalized tree
_NORMALIZE_MEMO: Dict[Any, Any] = {}
_cache_hits = 0
_cache_misses = 0


def clear_normalize_memo() -> None:
    """Clear global normalize() memoization cache and reset hit/miss stats."""
    global _cache_hits, _cache_misses
    _NORMALIZE_MEMO.clear()
    _structural_key.cache_clear()
    _cache_hits = 0
    _cache_misses = 0


# --- normalized form -------------------------------------------------------
# --- Public entrypoint ------------------------------------------------------

def normalize(expr: Any) -> Any:
    """
    Normalize Photon expressions under axioms + calculus rules:
        - Apply rewrite rules to a fixed point (T8–T15, etc.)
        - Canonicalize ⊕: flatten, drop ∅, absorption, idempotence, commutativity
        - Distribute ⊗ over ⊕ (both sides) [⊗ handles distribution; ⊕ does NOT factor]
        - Cancellation: a ⊖ a = ∅ ; a ⊖ ∅ = a ; ∅ ⊖ a = a
        - Double negation: ¬(¬a) = a
    """
    # Atoms (strings) fast-path
    if not isinstance(expr, dict):
        return expr

    k0 = structural_key(expr)
    cached = _NORMALIZE_MEMO.get(k0)
    if cached is not None:
        return cached

    # --- run until stable ---
    ctx = _NormCtx()
    out = _normalize_inner(expr, ctx)
    while True:
        nxt = _normalize_inner(out, ctx)
        if nxt == out:
            break
        out = nxt

    _NORMALIZE_MEMO[k0] = out
    return out


def _normalize_inner(expr: Any, ctx: _NormCtx) -> Any:
    # Atoms pass through
    if not isinstance(expr, dict):
        return expr

    # Local memo by structural key of the *current* node
    skey = structural_key(expr)
    if skey in ctx.memo:
        return ctx.memo[skey]

    # 1) Normalize children first
    if "states" in expr:
        expr = {**expr, "states": [_normalize_inner(s, ctx) for s in expr.get("states", [])]}
    if "state" in expr:
        expr = {**expr, "state": _normalize_inner(expr.get("state"), ctx)}

    # 2) Single-step rewrite until stable
    expr = rewrite_fixed(expr)

    # Might have simplified to an atom
    if not isinstance(expr, dict):
        ctx.memo[skey] = expr
        return expr

    op = expr.get("op")
    states = expr.get("states", [])

    if op == "⊕":
        # 🚫 No T14 factoring here (⊗ distributes; prevents ping-pong).
        # Order for ⊕:
        #   flatten → drop ∅ → absorption → idempotence + commutativity
        flat = _flatten_plus(states)

        # Drop ∅ (identity)
        flat = [s for s in flat if not (isinstance(s, dict) and s.get("op") == "∅")]

        # Absorption: remove products that contain an already-present atomic term
        present = {structural_key(s) for s in flat if not (isinstance(s, dict) and s.get("op") == "⊗")}
        pruned = []
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "⊗":
                a_, b_ = s.get("states", [None, None])
                if structural_key(a_) in present or structural_key(b_) in present:
                    continue  # absorbed
            pruned.append(s)
        flat = pruned

        # ✅ Try T10 distributivity before dedup/sort
        if len(flat) == 2:
            s1, s2 = flat
            if (
                isinstance(s1, dict) and s1.get("op") == "↔" and
                isinstance(s2, dict) and s2.get("op") == "↔"
            ):
                a1, b1 = s1["states"]
                a2, b2 = s2["states"]
                if a1 == a2:
                    out = {"op": "↔", "states": [a1, {"op": "⊕", "states": [b1, b2]}]}
                    out = _normalize_inner(out, ctx)
                    ctx.memo[skey] = out
                    return out
                if b1 == b2:
                    out = {"op": "↔", "states": [b1, {"op": "⊕", "states": [a1, a2]}]}
                    out = _normalize_inner(out, ctx)
                    ctx.memo[skey] = out
                    return out

        # Idempotence + commutativity (dedupe + sort by structural key)
        seen = {}
        for s in flat:
            k = structural_key(s)
            if k not in seen:
                seen[k] = s
        uniq_sorted = [seen[k] for k in sorted(seen.keys())]

        # ✅ Run deep normalize on children to stabilize nested rewrites
        uniq_sorted = [_normalize_inner(s, ctx) for s in uniq_sorted]

        if not uniq_sorted:
            out = EMPTY
        elif len(uniq_sorted) == 1:
            out = uniq_sorted[0]
        else:
            out = {"op": "⊕", "states": uniq_sorted}

        ctx.memo[skey] = out
        return out

    elif op == "⊗":
        if len(states) == 2:
            a, b = states

            # Annihilator
            if isinstance(a, dict) and a.get("op") == "∅":
                out = EMPTY
                ctx.memo[skey] = out
                return out
            if isinstance(b, dict) and b.get("op") == "∅":
                out = EMPTY
                ctx.memo[skey] = out
                return out

            # Canonicalize commutativity
            if structural_key(a) > structural_key(b):
                a, b = b, a

            # Local ⊗ idempotence: a ⊗ a → a
            if structural_key(a) == structural_key(b):
                out = _normalize_inner(a, ctx)
                ctx.memo[skey] = out
                return out

            def _is_plus(x):
                return isinstance(x, dict) and x.get("op") == "⊕" and isinstance(x.get("states"), list)

            # Dual absorption
            if _is_plus(b) and any(structural_key(s) == structural_key(a) for s in b["states"]):
                out = _normalize_inner(a, ctx)
                ctx.memo[skey] = out
                return out
            if _is_plus(a) and any(structural_key(s) == structural_key(b) for s in a["states"]):
                out = _normalize_inner(b, ctx)
                ctx.memo[skey] = out
                return out

            # Distribute over ⊕
            if _is_plus(b):
                out = _normalize_inner(
                    {"op": "⊕", "states": [{"op": "⊗", "states": [a, bi]} for bi in b["states"]]},
                    ctx,
                )
                ctx.memo[skey] = out
                return out
            if _is_plus(a):
                out = _normalize_inner(
                    {"op": "⊕", "states": [{"op": "⊗", "states": [ai, b]} for ai in a["states"]]},
                    ctx,
                )
                ctx.memo[skey] = out
                return out

            out = {"op": "⊗", "states": [a, b]}
        else:
            # Fallback for non-binary arity
            out = {"op": "⊗", "states": states}

        # ✅ Final rewrite pass
        out = rewrite_fixed(out)

        ctx.memo[skey] = out
        return out

    elif op == "⊖":
        if len(states) == 2:
            x, y = states
            if structural_key(x) == structural_key(y):
                out = EMPTY
            elif isinstance(y, dict) and y.get("op") == "∅":
                out = x
            elif isinstance(x, dict) and x.get("op") == "∅":
                out = y
            else:
                out = {"op": "⊖", "states": states}
        else:
            out = {"op": "⊖", "states": states}

        out = rewrite_fixed(out)
        ctx.memo[skey] = out
        return out

    elif op == "¬":
        inner = _normalize_inner(expr.get("state"), ctx)
        if isinstance(inner, dict) and inner.get("op") == "¬":
            out = _normalize_inner(inner.get("state"), ctx)
        else:
            out = {"op": "¬", "state": inner}
        out = rewrite_fixed(out)
        ctx.memo[skey] = out
        return out

    elif op == "★":
        inner = _normalize_inner(expr.get("state"), ctx)

        if isinstance(inner, dict) and inner.get("op") == "★":
            out = inner
        elif isinstance(inner, dict) and inner.get("op") == "↔":
            a, b = inner["states"]
            expanded = {"op": "⊕", "states": [
                {"op": "★", "state": a},
                {"op": "★", "state": b},
            ]}
            # ✅ Fully normalize right now
            out = _normalize_inner(expanded, ctx)
            out = rewrite_fixed(out)
        else:
            out = {"op": "★", "state": inner}

        ctx.memo[skey] = out
        return out

    elif op == "∅":
        ctx.memo[skey] = EMPTY
        return EMPTY

    else:
        # Passthrough (↔, etc.)
        out = {k: v for k, v in expr.items()}
        out = rewrite_fixed(out)
        ctx.memo[skey] = out
        return out

# --- Backward-compat shims (temporary; remove after migration) ----------------
def match(expr, pattern, env=None):
    """
    Legacy API shim:
    - old: match(expr, pattern, env) -> env | None
    - new: match_pattern(pattern, expr, env) -> (ok, env)
    """
    ok, out = match_pattern(pattern, expr, env or {})
    return out if ok else None


def apply_rules(expr):
    """
    Legacy API shim:
    - old: apply_rules(expr) -> single-step rewrite
    - new: rewrite_once(expr) -> single-step rewrite
    """
    return rewrite_once(expr)

# --- Cache statistics ------------------------------------------------------

def get_cache_stats() -> dict[str, int]:
    """Return current cache hit/miss counts."""
    return {"hits": _cache_hits, "misses": _cache_misses}

class _RewriterWrapper:
    def normalize(self, expr):
        global _cache_hits, _cache_misses
        if isinstance(expr, dict):
            import json
            k = _structural_key(json.dumps(expr, sort_keys=True))
        else:
            k = ("atom", str(expr))

        if k in _NORMALIZE_MEMO:
            _cache_hits += 1
            return _NORMALIZE_MEMO[k]

        _cache_misses += 1
        out = normalize(expr)
        _NORMALIZE_MEMO[k] = out
        return out

rewriter = _RewriterWrapper()
