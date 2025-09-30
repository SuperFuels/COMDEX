# backend/photon_algebra/rewriter.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple, Union

# 🔑 shared canonical empty state (import once)
from backend.photon_algebra.core import EMPTY

Expr = Union[str, Dict[str, Any]]

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

# Process-wide memo (optional, safe to clear in tests)
_NORM_MEMO: Dict[str, Any] = {}

def clear_normalize_memo() -> None:
    """Test hook: reset the global normalization memo cache."""
    _NORM_MEMO.clear()

@dataclass
class _NormCtx:
    # Local memo: structural key -> normalized subtree (used within a normalize run)
    memo: Dict[str, Any] = field(default_factory=dict)
    # Per-run cache for structural keys keyed by object identity
    key_cache: Dict[int, str] = field(default_factory=dict)

def _string_key_ctx(node: Any, cache: Dict[int, str]) -> str:
    """
    Cached wrapper around _string_key(node) keyed by id(node).
    Use this inside normalize() to reduce repeated key computation.
    """
    if not isinstance(node, dict):
        # Atoms: stable and cheap
        return str(node)
    oid = id(node)
    hit = cache.get(oid)
    if hit is not None:
        return hit
    k = _string_key(node)  # relies on the module's canonical stringifier
    cache[oid] = k
    return k

def _key_cached(node: Any, key_cache: Dict[int, str]) -> str:
    """Alias used in hot paths; identical to _string_key_ctx."""
    return _string_key_ctx(node, key_cache)

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

        # states (positional)
        if "states" in pattern:
            p_states = pattern.get("states", [])
            e_states = expr.get("states", [])
            if len(p_states) != len(e_states):
                return False, env
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

    # T10 — Entanglement distributivity: (a↔b) ⊕ (a↔c) → a↔(b⊕c)
    (
        {"op": "⊕", "states": [
            {"op": "↔", "states": ["a", "b"]},
            {"op": "↔", "states": ["a", "c"]},
        ]},
        {"op": "↔", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
    ),
    # T10 (commuted): (a↔c) ⊕ (a↔b) → a↔(b⊕c)
    (
        {"op": "⊕", "states": [
            {"op": "↔", "states": ["a", "c"]},
            {"op": "↔", "states": ["a", "b"]},
        ]},
        {"op": "↔", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
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

def rewrite_fixed(expr: Expr, max_iter: int = 64) -> Expr:
    """Iteratively apply rewrite_once until a fixed point."""
    prev = None
    cur = expr
    for _ in range(max_iter):
        nxt = rewrite_once(cur)
        if nxt == cur:
            break
        cur = nxt
    return cur

# --- add near the other module-level globals ---
from typing import Dict, Any

# cache: structural-key -> normalized tree
_NORM_MEMO: Dict[str, Any] = {}

def clear_normalize_memo() -> None:
    """Optional: test hook to reset normalize() memoization cache."""
    _NORM_MEMO.clear()

# --- normalized form -------------------------------------------------------
# --- Public entrypoint ------------------------------------------------------

def _normalize_impl(expr: Any, _memo: Dict[str, Any] = None, _key_cache: Dict[int, str] = None) -> Any:
    """
    Normalize Photon expressions under axioms + calculus rules:
      - Apply rewrite rules to a fixed point (T8–T15, etc.)
      - Canonicalize ⊕: flatten, drop ∅, absorption, idempotence, commutativity
      - Distribute ⊗ over ⊕ (both sides)  [⊗ handles distribution; ⊕ does NOT factor]
      - Cancellation: a ⊖ a = ∅ ; a ⊖ ∅ = a ; ∅ ⊖ a = a
      - Double negation: ¬(¬a) = a
    """
    if _memo is None:
        _memo = {}
    if _key_cache is None:
        _key_cache = {}

    # atoms (strings) pass through
    if not isinstance(expr, dict):
        return expr

    # quick memo by structural key
    k0 = _key_cached(expr, _key_cache)
    if k0 in _memo:
        return _memo[k0]
# --- Inner worker with memoization -----------------------------------------

# Public entrypoint with a tiny global memo keyed by the input shape.
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

    # global memo by input structural key
    k0 = _string_key(expr)
    cached = _NORM_MEMO.get(k0)
    if cached is not None:
        return cached

    out = _normalize_inner(expr, _NormCtx())
    _NORM_MEMO[k0] = out
    return out

def _normalize_inner(expr: Any, ctx: _NormCtx) -> Any:
    # atoms pass through
    if not isinstance(expr, dict):
        return expr

    # local memo by structural key of the *current* node
    skey = _string_key_ctx(expr, ctx.key_cache)
    if skey in ctx.memo:
        return ctx.memo[skey]

    # 1) normalize children first
    if "states" in expr:
        expr = {**expr, "states": [_normalize_inner(s, ctx) for s in expr.get("states", [])]}
    if "state" in expr:
        expr = {**expr, "state": _normalize_inner(expr.get("state"), ctx)}

    # 2) single-step rewrite until stable (covers T10–T15 patterns you keep enabled)
    expr = rewrite_fixed(expr)

    # might have simplified to an atom
    if not isinstance(expr, dict):
        ctx.memo[skey] = expr
        return expr

    op = expr.get("op")
    states = expr.get("states", [])

    if op == "⊕":
        # 🚫 No T14 factoring here (⊗ branch distributes; prevents ping-pong).
        # Order for ⊕:
        #   flatten → drop ∅ → absorption → idempotence + commutativity
        flat = _flatten_plus(states)

        # drop ∅ (identity)
        flat = [s for s in flat if not (isinstance(s, dict) and s.get("op") == "∅")]

        # Absorption: remove products that contain an already-present atomic term
        present = {
            _string_key_ctx(s, ctx.key_cache)
            for s in flat
            if not (isinstance(s, dict) and s.get("op") == "⊗")
        }
        pruned = []
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "⊗":
                a_, b_ = s.get("states", [None, None])
                if _string_key_ctx(a_, ctx.key_cache) in present or \
                   _string_key_ctx(b_, ctx.key_cache) in present:
                    continue  # absorbed
            pruned.append(s)
        flat = pruned

        # Special collapse for agreement with ⊗-distribution:
        # (a⊗a) ⊕ (a⊗b)  →  a   (and commuted variants)
        if len(flat) == 2:
            u, v = flat

            def _is_times(e):
                return isinstance(e, dict) and e.get("op") == "⊗" and isinstance(e.get("states"), list) and len(e["states"]) == 2

            if _is_times(u) and _is_times(v):
                ua, ub = u["states"]; va, vb = v["states"]

                def eq(x, y): return _string_key_ctx(x, ctx.key_cache) == _string_key_ctx(y, ctx.key_cache)

                for A1, A2, B1, B2 in [
                    (ua, ub, va, vb),
                    (ua, ub, vb, va),
                    (va, vb, ua, ub),
                    (vb, va, ua, ub),
                ]:
                    if eq(A1, A2) and (eq(B1, A1) or eq(B2, A1)):
                        out = _normalize_inner(A1, ctx)
                        ctx.memo[skey] = out
                        return out

        # Idempotence + commutativity (dedupe + sort by key)
        uniq, seen = [], set()
        for s in flat:
            k = _string_key_ctx(s, ctx.key_cache)
            if k in seen:
                continue
            seen.add(k)
            uniq.append(s)
        uniq_sorted = sorted(uniq, key=lambda x: _string_key_ctx(x, ctx.key_cache))

        if not uniq_sorted:
            ctx.memo[skey] = EMPTY
            return EMPTY
        if len(uniq_sorted) == 1:
            ctx.memo[skey] = uniq_sorted[0]
            return uniq_sorted[0]
        out = {"op": "⊕", "states": uniq_sorted}
        ctx.memo[skey] = out
        return out

    elif op == "⊗":
        if len(states) == 2:
            a, b = states

            # annihilator
            if isinstance(a, dict) and a.get("op") == "∅":
                ctx.memo[skey] = EMPTY; return EMPTY
            if isinstance(b, dict) and b.get("op") == "∅":
                ctx.memo[skey] = EMPTY; return EMPTY

            # canonicalize commutativity
            if _string_key_ctx(a, ctx.key_cache) > _string_key_ctx(b, ctx.key_cache):
                a, b = b, a

            # local ⊗ idempotence: a ⊗ a → a
            if _string_key_ctx(a, ctx.key_cache) == _string_key_ctx(b, ctx.key_cache):
                out = _normalize_inner(a, ctx)
                ctx.memo[skey] = out
                return out

            def _is_plus(x):
                return isinstance(x, dict) and x.get("op") == "⊕" and isinstance(x.get("states"), list)

            # dual absorption
            if _is_plus(b):
                if any(_string_key_ctx(s, ctx.key_cache) == _string_key_ctx(a, ctx.key_cache) for s in b["states"]):
                    out = _normalize_inner(a, ctx)
                    ctx.memo[skey] = out
                    return out
            if _is_plus(a):
                if any(_string_key_ctx(s, ctx.key_cache) == _string_key_ctx(b, ctx.key_cache) for s in a["states"]):
                    out = _normalize_inner(b, ctx)
                    ctx.memo[skey] = out
                    return out

            # distribute over ⊕
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
            ctx.memo[skey] = out
            return out

        # Fallback for non-binary arity
        out = {"op": "⊗", "states": states}
        ctx.memo[skey] = out
        return out

    elif op == "⊖":
        if len(states) == 2:
            x, y = states
            if x == y:
                ctx.memo[skey] = EMPTY; return EMPTY
            if isinstance(y, dict) and y.get("op") == "∅":
                ctx.memo[skey] = x; return x
            if isinstance(x, dict) and x.get("op") == "∅":
                ctx.memo[skey] = y; return y
        out = {"op": "⊖", "states": states}
        ctx.memo[skey] = out
        return out

    elif op == "¬":
        inner = expr.get("state")
        if isinstance(inner, dict) and inner.get("op") == "¬":
            out = _normalize_inner(inner.get("state"), ctx)
            ctx.memo[skey] = out
            return out
        out = {"op": "¬", "state": inner}
        ctx.memo[skey] = out
        return out

    elif op == "∅":
        ctx.memo[skey] = EMPTY
        return EMPTY

    # passthrough (★, ↔, etc.) with already-normalized children
    out = {k: v for k, v in expr.items()}
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