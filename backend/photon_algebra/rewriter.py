from __future__ import annotations
import json
import copy
from functools import lru_cache
from typing import Any, Dict, List, Tuple, Union
from backend.photon_algebra.core import EMPTY, TOP, BOTTOM
Expr = Union[str, Dict[str, Any]]
# backend/photon_algebra/rewriter.py
# =============================================================================
# Numerical Amplitude Extension (Symatics ⊕ with weights + phase)
# =============================================================================
import numpy as np

def superpose(states, weights=None, phases=None):
    """
    Symatics amplitude-level ⊕ operator:
    Combine wave/field arrays with optional weights and phase offsets.
    Returns intensity map (|Σ w*e^{iφ}*ψ|2).
    """
    n = len(states)
    weights = weights or [1/n] * n
    phases = phases or [0] * n
    complex_field = np.sum(
        [w * np.exp(1j * p) * s for s, w, p in zip(states, weights, phases)],
        axis=0
    )
    return np.abs(complex_field)**2
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
#   1) A process-wide memo (_NORM_MEMO) keyed by a structural key string -> normalized expr.
#   2) A per-normalize-run context (_NormCtx) that caches:
#        - memo: local results (can be cleared in tests)
#        - key_cache: id(node) -> _string_key(node) to avoid recomputation
# _string_key(node) itself is defined elsewhere in this module.
# =============================================================================

class PhotonRewriter:
    def __init__(self):
        self.DIAG = []

    def log(self, rule: str, before, after):
        self.DIAG.append({"rule": rule, "before": before, "after": after})

    def normalize(self, expr):
        # Just delegate to the canonical pipeline
        result = normalize(expr)  # <-- use the big one
        return result

# --- Diagnostics counters ------------------------------------------------------
class _DiagCounters:
    """Track normalization and rewrite events for diagnostics."""
    __slots__ = ("rewrites", "absorptions", "idempotence", "distributions")

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.rewrites = 0        # how many times rewrite_fixed changed an expr
        self.absorptions = 0     # times a ⊕ (a ⊗ b) collapsed to a
        self.idempotence = 0     # a ⊗ a -> a, a ⊕ a -> a, ¬(¬a) -> a
        self.distributions = 0   # times ⊗ distributed over ⊕

    def to_dict(self) -> dict:
        """Return a snapshot of current counters as a dict."""
        return {
            "rewrites": self.rewrites,
            "absorptions": self.absorptions,
            "idempotence": self.idempotence,
            "distributions": self.distributions,
        }

    def __repr__(self) -> str:
        return (
            f"<DIAG rewrites={self.rewrites} "
            f"absorptions={self.absorptions} "
            f"idempotence={self.idempotence} "
            f"distributions={self.distributions}>"
        )

# Global shared singleton
DIAG = _DiagCounters()

# --- memo + key helpers -----------------------------------------------------

# =============================================================================
# Global caches
# =============================================================================

# Global memo: structural key -> normalized tree
_NORMALIZE_MEMO: Dict[tuple, Any] = {}
# Global structural key cache: id(expr) -> structural key (per-run)
_STRUCT_CACHE: Dict[int, tuple] = {}

_cache_hits: int = 0
_cache_misses: int = 0

COMMUTATIVE = {"⊕", "⊗", "↔", "≈"}  # ⊖, ⊂, ⊗_M are directional

def _is_commutative(op: str) -> bool:
    return op in COMMUTATIVE
# -----------------------------------------------------------------------------
# Cache maintenance
# -----------------------------------------------------------------------------
def clear_normalize_memo() -> None:
    """
    Clear all normalize-related caches and counters.
    """
    global _cache_hits, _cache_misses
    _NORMALIZE_MEMO.clear()
    _STRUCT_CACHE.clear()

    # clear any decorated caches
    for fn in (structural_key, _string_key, _match_pattern_cached):
        try:
            fn.cache_clear()
        except Exception:
            pass

    _cache_hits = 0
    _cache_misses = 0


def get_cache_stats() -> dict[str, int]:
    """Return current cache hit/miss counters."""
    return {"hits": _cache_hits, "misses": _cache_misses}


class _NormCtx:
    """
    Per-normalize call context with local memo and fast structural-key cache.
    """
    __slots__ = ("memo", "key_cache")

    def __init__(self) -> None:
        # local memo for this normalize call
        self.memo: Dict[tuple, Any] = {}
        # cache of id(node) -> structural key (fast-path for repeated lookups)
        self.key_cache: Dict[int, tuple] = {}


# -----------------------------------------------------------------------------
# Structural key (optimized: hybrid tuple + hash)
# -----------------------------------------------------------------------------
from functools import lru_cache

try:
    from backend.photon_algebra.structural_key_cy import structural_key_cy
    HAVE_CYTHON = True
except ImportError:
    HAVE_CYTHON = False


def structural_key(expr: Any, cache: dict[int, tuple] | None = None) -> tuple:
    """
    Compute a structural key for an expression.

    Behavior:
    - Atoms -> ("atom", value)
    - Dicts -> ("opN", op, tuple(child_keys))
    - Lists -> ("list", tuple(child_keys))
    - For commutative ops (⊕, ⊗, ↔, ≈), child keys are sorted.
      For directional ops (⊖, ⊂), insertion order is preserved.
    - Results are memoized in the given cache.
    """
    if HAVE_CYTHON:
        return structural_key_cy(expr, cache)

    if cache is None:
        cache = {}

    obj_id = id(expr)
    if obj_id in cache:
        return cache[obj_id]

    # --- atoms ---------------------------------------------------------------
    if isinstance(expr, str):
        if expr in ("∅", "⊤", "⊥"):
            key = (expr,)
        else:
            key = ("atom", expr)

    # --- dict expressions ----------------------------------------------------
    elif isinstance(expr, dict):
        op = expr.get("op")

        if "state" in expr:
            child_key = structural_key(expr["state"], cache)
            key = ("op1", op, child_key)

        elif "states" in expr:
            states = expr.get("states", [])
            child_keys = [structural_key(s, cache) for s in states]

            # ✅ Only sort for commutative ops
            if _is_commutative(op):
                child_keys.sort()

            key = ("opN", op, tuple(child_keys))

        else:
            key = ("op0", op)

    # --- list containers -----------------------------------------------------
    elif isinstance(expr, list):
        child_keys = [structural_key(x, cache) for x in expr]
        key = ("list", tuple(child_keys))

    # --- fallback ------------------------------------------------------------
    else:
        key = ("atom", expr)

    cache[obj_id] = key
    return key


@lru_cache(maxsize=100_000)
def _freeze_key(key: tuple) -> tuple:
    """Cache stable tuples of keys (avoids recomputing)."""
    return key


def get_structural_key(expr: Any) -> tuple:
    """Public entry point: computes a stable structural key with global cache."""
    return _freeze_key(structural_key(expr, _STRUCT_CACHE))


def _get_key(expr: Any, ctx: _NormCtx) -> tuple:
    """Fast structural_key lookup using per-run cache."""
    obj_id = id(expr)
    k = ctx.key_cache.get(obj_id)
    if k is None:
        k = structural_key(expr, ctx.key_cache)
        ctx.key_cache[obj_id] = k
    return k
# -----------------------------------------------------------------------------
# Pattern matching engine
# -----------------------------------------------------------------------------

def is_var(token: Any) -> bool:
    """
    Variables are lowercase ASCII names (e.g., 'a', 'x1')
    or tokens starting with '?' (e.g., '?foo').
    """
    return (
        isinstance(token, str)
        and (token.startswith("?") or (token.isascii() and token.islower()))
    )


@lru_cache(maxsize=200_000)  # 🔼 larger cache for stability/perf
def _match_pattern_cached(pk: tuple, ek: tuple) -> bool:
    """
    Cached structural match guard.
    - Exact structural equality -> True
    - Either side is a variable marker -> True
    """
    if pk == ek:
        return True
    if pk and pk[0] == "var":
        return True
    if ek and ek[0] == "var":
        return True
    return False


def match_pattern(pattern: Expr, expr: Expr, env: Dict[str, Expr] | None = None) -> tuple[bool, Dict[str, Expr]]:
    """
    Attempt to match `pattern` against `expr`.

    Returns:
        (ok, env) where:
        - ok (bool) = match success
        - env (dict) = variable bindings (may be updated)
    """
    if env is None:
        env = {}

    # --- Variable binding ---
    if is_var(pattern):
        bound = env.get(pattern)
        if bound is None:
            env[pattern] = expr
            return True, env
        return (bound == expr), env

    # --- Atom match ---
    if isinstance(pattern, str):
        return (pattern == expr), env

    # --- Structural dict match ---
    if isinstance(pattern, dict) and isinstance(expr, dict):
        if pattern.get("op") != expr.get("op"):
            return False, env

        # quick reject using structural key
        if not _match_pattern_cached(structural_key(pattern), structural_key(expr)):
            return False, env

        # match "state"
        if "state" in pattern:
            ok, env = match_pattern(pattern["state"], expr.get("state"), env)
            if not ok:
                return False, env

        # match "states" (multiset if commutative)
        if "states" in pattern:
            p_states = pattern.get("states", [])
            e_states = expr.get("states", [])

            if len(p_states) != len(e_states):
                return False, env

            if expr.get("op") in COMMUTATIVE:
                unmatched = list(e_states)
                for p in p_states:
                    matched = False
                    for i, e in enumerate(unmatched):
                        ok, new_env = match_pattern(p, e, env.copy())
                        if ok:
                            env = new_env
                            unmatched.pop(i)
                            matched = True
                            break
                    if not matched:
                        return False, env
                return True, env
            else:
                for p, e in zip(p_states, e_states):
                    ok, env = match_pattern(p, e, env)
                    if not ok:
                        return False, env

        return True, env

    # --- Type mismatch ---
    return False, env


def substitute(node: Expr, env: Dict[str, Expr]) -> Expr:
    """
    Substitute variables in `node` using env.
    Performs minimal copying: returns the original node if unchanged.
    """
    if is_var(node):
        return env.get(node, node)

    if isinstance(node, str):
        return node

    if isinstance(node, dict):
        changed = False
        op = node.get("op")
        out: Dict[str, Any] = {"op": op}

        # state
        if "state" in node:
            new_state = substitute(node["state"], env)
            if new_state is not node["state"]:
                changed = True
            out["state"] = new_state

        # states
        if "states" in node:
            new_states = []
            for s in node["states"]:
                new_s = substitute(s, env)
                if new_s is not s:
                    changed = True
                new_states.append(new_s)
            out["states"] = new_states

        return out if changed else node

    return node
# =============================================================================
# Rewrite Rules (axioms + derived theorems)
#
# Notes:
# * T14 (Dual Distributivity) is intentionally NOT in this table. Distribution
#   is handled structurally in normalize(): ⊗ distributes over ⊕; ⊕ does not factor.
#   Keeping a T14 factoring rule here can ping-pong with ⊗->⊕ distribution.
# * ⊗ idempotence (a ⊗ a -> a) is enforced locally in normalize()'s ⊗ branch
#   (post-commutativity) to keep normal forms stable.
# =============================================================================

REWRITE_RULES: List[Tuple[Expr, Expr]] = [
    # P - Associativity: (a ⊕ b) ⊕ c -> a ⊕ (b ⊕ c)
    (
        {"op": "⊕", "states": [{"op": "⊕", "states": ["a", "b"]}, "c"]},
        {"op": "⊕", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
    ),

    # P - Commutativity: a ⊕ b -> b ⊕ a
    (
        {"op": "⊕", "states": ["a", "b"]},
        {"op": "⊕", "states": ["b", "a"]},
    ),

    # P - Idempotence: a ⊕ a -> a
    (
        {"op": "⊕", "states": ["a", "a"]},
        "a",
    ),

    # (REMOVED) T14 - Dual Distributivity
    # Handled structurally in normalize().

    # P - Cancellation: a ⊖ a -> ∅
    (
        {"op": "⊖", "states": ["a", "a"]},
        EMPTY,
    ),

    # P - Double Negation: ¬(¬a) -> a
    (
        {"op": "¬", "state": {"op": "¬", "state": "a"}},
        "a",
    ),

    # T10 - Entanglement distributivity: (a↔b) ⊕ (a↔c) -> a ↔ (b ⊕ c)
    (
        {"op": "⊕", "states": [
            {"op": "↔", "states": ["a", "b"]},
            {"op": "↔", "states": ["a", "c"]},
        ]},
        {"op": "↔", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
    ),
    # T10 (commuted): (a↔c) ⊕ (a↔b) -> a ↔ (b ⊕ c)
    (
        {"op": "⊕", "states": [
            {"op": "↔", "states": ["a", "c"]},
            {"op": "↔", "states": ["a", "b"]},
        ]},
        {"op": "↔", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]},
    ),

    # T11 - Entanglement idempotence: a ↔ a -> a
    (
        {"op": "↔", "states": ["a", "a"]},
        "a",
    ),

    # T12 - Projection fidelity: ★(a↔b) -> (★a) ⊕ (★b)
    (
        {"op": "★", "state": {"op": "↔", "states": ["a", "b"]}},
        {"op": "⊕", "states": [
            {"op": "★", "state": "a"},
            {"op": "★", "state": "b"},
        ]},
    ),

    # T13 - Absorption: a ⊕ (a ⊗ b) -> a
    (
        {"op": "⊕", "states": ["a", {"op": "⊗", "states": ["a", "b"]}]},
        "a",
    ),
    # T13 (commuted): (a ⊗ b) ⊕ a -> a
    (
        {"op": "⊕", "states": [{"op": "⊗", "states": ["a", "b"]}, "a"]},
        "a",
    ),

    # T15 - Falsification: a ⊖ ∅ -> a
    (
        {"op": "⊖", "states": ["a", EMPTY]},
        "a",
    ),
    # T15 (swapped): ∅ ⊖ a -> a
    (
        {"op": "⊖", "states": [EMPTY, "a"]},
        "a",
    ),
]

# -----------------------------------------------------------------------------
# Index rewrite rules by operator for faster matching
# -----------------------------------------------------------------------------
from collections import defaultdict

RULES_BY_OP: Dict[str, List[Tuple[Expr, Expr]]] = defaultdict(list)
for pat, repl in REWRITE_RULES:
    if isinstance(pat, dict):
        RULES_BY_OP[pat.get("op")] .append((pat, repl))
    else:
        RULES_BY_OP[None].append((pat, repl))  # atom/constant patterns


# =============================================================================
# Rewrite Engine
# =============================================================================


def rewrite_once(expr: Expr) -> Expr:
    """
    Try to apply exactly one rewrite rule to `expr`.
    Checks RULES_BY_OP index for candidates, tries both orderings if commutative.
    Returns rewritten expression if a rule applies, else returns expr unchanged.
    """
    op = expr.get("op") if isinstance(expr, dict) else None
    candidates = RULES_BY_OP.get(op, []) + RULES_BY_OP.get(None, [])

    # direct attempt
    for pattern, replacement in candidates:
        env = match(expr, pattern)
        if env is not None:
            DIAG.rewrites += 1
            return substitute(replacement, env)

    # commutative flip (only when exactly 2 operands)
    if isinstance(expr, dict) and op in COMMUTATIVE:
        states = expr.get("states", [])
        if len(states) == 2:
            flipped = {"op": op, "states": [states[1], states[0]]}
            for pattern, replacement in candidates:
                env = match(flipped, pattern)
                if env is not None:
                    DIAG.rewrites += 1
                    return substitute(replacement, env)

    return expr


def rewrite_fixpoint(expr: Expr, max_iters: int = 64) -> Expr:
    """
    Repeatedly apply `rewrite_once` until reaching a fixed point
    or until max_iters is hit.
    """
    current = expr
    for _ in range(max_iters):
        nxt = rewrite_once(current)
        if nxt == current:
            break
        current = nxt
    return current


# =============================================================================
# Structural Normalization Helpers
# =============================================================================

def _string_key(x, ctx=None) -> tuple:
    """
    Canonical sort/deduplication key.
    Uses structural_key/_get_key when available for stability.
    """
    return _get_key(x, ctx) if ctx is not None else structural_key(x)

def _normalize_shallow(expr: Expr, ctx: _NormCtx, skey=None) -> Expr:
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")
    states = expr.get("states", [])

    # Normalize children first
    norm_state = expr.get("state")
    if norm_state is not None:
        norm_state = _normalize_inner(norm_state, ctx)
    norm_states = [_normalize_inner(s, ctx) for s in states]

    # --- ⊕ (sum) -----------------------------------------------------------
    if op == "⊕":
        flat: List[Expr] = []
        for s in norm_states:
            if isinstance(s, dict) and s.get("op") == "⊕":
                flat.extend(s.get("states", []))
            else:
                flat.append(s)

        # Remove ∅ (identity)
        flat = [s for s in flat if not (isinstance(s, dict) and s.get("op") == "∅")]

        # Absorption: drop (a⊗...) if any factor is already present
        atoms = {structural_key(s) for s in flat if not (isinstance(s, dict) and s.get("op") == "⊗")}
        pruned = []
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "⊗":
                if any(structural_key(f) in atoms for f in s["states"]):
                    DIAG.absorptions += 1
                    continue
            pruned.append(s)
        flat = pruned

        # Deduplication (idempotence) + commutativity
        seen, dedup = set(), []
        for s in flat:
            k = _string_key(s, ctx)
            if k not in seen:
                seen.add(k)
                dedup.append(s)
        dedup_sorted = sorted(dedup, key=lambda s: _string_key(s, ctx))

        if not dedup_sorted:
            return EMPTY
        if len(dedup_sorted) == 1:
            return dedup_sorted[0]
        return {"op": "⊕", "states": dedup_sorted}

    # --- ⊗ (product) -------------------------------------------------------
    elif op == "⊗":
        flat: List[Expr] = []
        for s in norm_states:
            if isinstance(s, dict) and s.get("op") == "⊗":
                flat.extend(s.get("states", []))
            else:
                flat.append(s)

        # Annihilators
        if any(isinstance(s, dict) and s.get("op") == "⊥" for s in flat):
            return {"op": "⊥"}
        if any(isinstance(s, dict) and s.get("op") == "∅" for s in flat):
            return EMPTY

        if len(flat) == 2:
            a, b = flat
            if _string_key(a, ctx) > _string_key(b, ctx):
                a, b = b, a
            if isinstance(a, dict) and a.get("op") == "⊕":
                DIAG.distributions += 1
                return _normalize_inner({"op": "⊕", "states": [{"op": "⊗", "states": [ai, b]} for ai in a["states"]]}, ctx)
            if isinstance(b, dict) and b.get("op") == "⊕":
                DIAG.distributions += 1
                return _normalize_inner({"op": "⊕", "states": [{"op": "⊗", "states": [a, bi]} for bi in b["states"]]}, ctx)
            return {"op": "⊗", "states": [a, b]}

        if len(flat) > 2:
            flat = sorted(flat, key=lambda s: _string_key(s, ctx))
            for i, s in enumerate(flat):
                if isinstance(s, dict) and s.get("op") == "⊕":
                    others = flat[:i] + flat[i+1:]
                    DIAG.distributions += 1
                    return _normalize_inner(
                        {"op": "⊕", "states": [{"op": "⊗", "states": others + [t]} for t in s["states"]]},
                        ctx,
                    )
            return {"op": "⊗", "states": flat}

        return {"op": "⊗", "states": flat}

    # --- ⊖ (difference) ----------------------------------------------------
    elif op == "⊖":
        if len(norm_states) == 2:
            x, y = norm_states
            if structural_key(x) == structural_key(y):
                return EMPTY
            if isinstance(y, dict) and y.get("op") == "∅":
                return x
            if isinstance(x, dict) and x.get("op") == "∅":
                return y
        return {"op": "⊖", "states": norm_states}

    # --- ¬ (negation) ------------------------------------------------------
    elif op == "¬":
        inner = norm_state or (norm_states[0] if norm_states else None)
        if isinstance(inner, dict) and inner.get("op") == "¬":
            return _normalize_inner(inner.get("state"), ctx)
        return {"op": "¬", "state": inner}

    # --- ≈ / ⊂ (meta-ops) --------------------------------------------------
    elif op in {"≈", "⊂"} and len(norm_states) == 2:
        a, b = norm_states
        if structural_key(a) == structural_key(b):
            return TOP
        if op == "⊂":
            if a == BOTTOM or (isinstance(a, dict) and a.get("op") == "⊥"):
                return TOP
            if b == TOP or (isinstance(b, dict) and b.get("op") == "⊤"):
                return TOP
        return {"op": op, "states": [a, b]}

    # --- trivial ops -------------------------------------------------------
    elif op in {"⊤", "⊥"}:
        return {"op": op}
    elif op == "∅":
        return EMPTY

    # --- ↔ (equivalence) ---------------------------------------------------
    elif op == "↔":
        flat = []
        for s in norm_states:
            if isinstance(s, dict) and s.get("op") == "↔":
                flat.extend(s.get("states", []))
            else:
                flat.append(s)
        if len(flat) == 1:
            return flat[0]
        return {"op": "↔", "states": flat}

    # --- fallback ----------------------------------------------------------
    out = {"op": op}
    if norm_states:
        out["states"] = norm_states
    if norm_state is not None:
        out["state"] = norm_state
    return out


# --- helpers ---------------------------------------------------------------

def _flatten_plus(states):
    """Recursively flatten nested ⊕ expressions."""
    out = []
    for s in states:
        if isinstance(s, dict) and s.get("op") == "⊕":
            out.extend(_flatten_plus(s.get("states", [])))
        else:
            out.append(s)
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
            print(f"[rewrite_fixed] Iter {i}: {cur} -> {nxt}")
        cur = nxt
    return cur

# --- Fast-guarded rewrite ----------------------------------------------------
def _maybe_rewrite(expr: Expr) -> Expr:
    """
    Call rewrite_fixed(expr) only if there are candidate rules for this op
    (or generic None-op rules). This avoids the rewrite loop when it can't fire.
    Also bumps DIAG.rewrites only when a change happens.
    """
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")
    has_op_rules = bool(RULES_BY_OP.get(op))
    has_generic_rules = bool(RULES_BY_OP.get(None))

    if not (has_op_rules or has_generic_rules):
        return expr  # fast reject: no rules can apply

    nxt = rewrite_fixed(expr)
    if nxt != expr:
        DIAG.rewrites += 1
    return nxt

# --- normalized form -------------------------------------------------------
# --- Public entrypoint ------------------------------------------------------

def normalize(expr: Any, strict: bool = False) -> Any:
    """
    Normalize Photon expressions under axioms + calculus rules:
        - Apply rewrite rules to a fixed point (T8-T15, etc.)
        - Canonicalize ⊕: flatten, drop ∅, absorption, idempotence, commutativity
        - Distribute ⊗ over ⊕ (both sides)
        - Cancellation: a ⊖ a = ∅ ; a ⊖ ∅ = a ; ∅ ⊖ a = a
        - Double negation: ¬(¬a) = a

    If strict=True, perform *structural normalization only* (no simplifications).
    This preserves full tree shape for JSON↔SymPy roundtrips.
    """

    # Constants fast-path
    if isinstance(expr, dict) and expr.get("op") in {"∅", "⊤", "⊥"}:
        return expr

    if not isinstance(expr, dict):
        return expr

    k0 = structural_key(expr)
    if not strict:
        cached = _NORMALIZE_MEMO.get(k0)
        if cached is not None:
            return cached

    ctx = _NormCtx()
    out = _normalize_inner(expr, ctx, strict=strict)

    # For strict mode, do *not* iterate or simplify further.
    if not strict:
        while True:
            nxt = _normalize_inner(out, ctx, strict=strict)
            if nxt == out:
                break
            out = nxt
        _NORMALIZE_MEMO[k0] = out

    return out


def _normalize_inner(expr: Any, ctx: _NormCtx, strict: bool = False) -> Any:
    if not isinstance(expr, dict):
        return expr

    skey = structural_key(expr, ctx.key_cache)

    # 🔍 Check global cache first
    cached = _NORMALIZE_MEMO.get(skey)
    if cached is not None:
        return cached

    # Check per-call memo
    if skey in ctx.memo:
        return ctx.memo[skey]

    op = expr.get("op")
    states = expr.get("states", [])

    # ✅ handle meta-ops first
    if op in {"≈", "⊂", "↔"} and len(states) == 2:
        a, b = states
        a = _normalize_inner(a, ctx, strict=strict)
        b = _normalize_inner(b, ctx, strict=strict)

        if not strict and structural_key(a) == structural_key(b):
            ctx.memo[skey] = TOP
            _NORMALIZE_MEMO[skey] = TOP
            return TOP

        if op == "⊂":
            if a == BOTTOM or (isinstance(a, dict) and a.get("op") == "⊥"):
                ctx.memo[skey] = TOP
                _NORMALIZE_MEMO[skey] = TOP
                return TOP
            if b == TOP or (isinstance(b, dict) and b.get("op") == "⊤"):
                ctx.memo[skey] = TOP
                _NORMALIZE_MEMO[skey] = TOP
                return TOP

        out = {"op": op, "states": [a, b]}
        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    # 👇 only if not a meta-op, continue with child-normalization & rewrite
    if "states" in expr:
        expr = {**expr, "states": [_normalize_inner(s, ctx) for s in states]}
    if "state" in expr:
        expr = {**expr, "state": _normalize_inner(expr.get("state"), ctx)}

    expr = _maybe_rewrite(expr)
    # Might have simplified to an atom
    if not isinstance(expr, dict):
        ctx.memo[skey] = expr
        _NORMALIZE_MEMO[skey] = expr
        return expr

    op = expr.get("op")
    states = expr.get("states", [])

    # --- Absorption / annihilation: a ⊗ ¬a -> ⊥ ---
    if op == "⊗" and len(states) == 2:
        s1, s2 = states
        if (
            isinstance(s1, dict)
            and s1.get("op") == "¬"
            and _get_key(s1.get("state"), ctx) == _get_key(s2, ctx)
        ) or (
            isinstance(s2, dict)
            and s2.get("op") == "¬"
            and _get_key(s2.get("state"), ctx) == _get_key(s1, ctx)
        ):
            ctx.memo[skey] = {"op": "⊥"}
            return {"op": "⊥"}

    # Duality: a ⊕ ¬a -> ⊤
    if op == "⊕" and len(states) == 2:
        s1, s2 = states
        if s1 == {"op": "¬", "state": s2} or s2 == {"op": "¬", "state": s1}:
            ctx.memo[skey] = TOP
            return TOP

    # De Morgan's Laws (with ★ handling)
    if op == "¬" and isinstance(expr.get("state"), dict):
        inner = expr["state"]

        if inner.get("op") == "⊕":
            states = inner.get("states", [])

            # Collapse if any ★x is present -> whole sum = ★x
            for s in states:
                if isinstance(s, dict) and s.get("op") == "★":
                    t = s.get("state")
                    if not isinstance(t, dict):
                        return {"op": "¬", "state": {"op": "★", "state": t}}

            # Standard De Morgan if multi-term
            if len(states) > 1:
                return {"op": "⊗", "states": [{"op": "¬", "state": s} for s in states]}
            elif len(states) == 1:
                return {"op": "¬", "state": states[0]}
            else:
                return EMPTY

        if inner.get("op") == "⊗":
            states = inner.get("states", [])
            if len(states) > 1:
                return {"op": "⊕", "states": [{"op": "¬", "state": s} for s in states]}
            elif len(states) == 1:
                return {"op": "¬", "state": states[0]}
            else:
                return EMPTY

    if op == "⊕":
        flat = _flatten_plus(states)

        if strict:
            # Structural-only: flatten and sort, but skip absorption/idempotence
            dedup = []
            seen = set()
            for s in flat:
                k = _get_key(s, ctx)
                if k not in seen:
                    seen.add(k)
                    dedup.append(s)

            dedup_sorted = sorted(dedup, key=lambda s: _get_key(s, ctx))

            if not dedup_sorted:
                out = EMPTY
            elif len(dedup_sorted) == 1:
                out = {"op": "⊕", "states": dedup_sorted}
            else:
                out = {"op": "⊕", "states": dedup_sorted}

            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # Drop ∅ (identity)
        flat = [
            s for s in flat
            if not ((isinstance(s, dict) and s.get("op") == "∅") or s == "∅")
        ]

        # Absorption: drop (a ⊗ b) if any factor already present
        # --- Absorption: drop (a ⊗ b) if any factor already present ---
        normalized_flat = [_normalize_inner(s, ctx) for s in flat]

        present = {
            _get_key(s, ctx)
            for s in normalized_flat
            if not (isinstance(s, dict) and s.get("op") == "⊗")
        }

        pruned = []
        for s in normalized_flat:
            if isinstance(s, dict) and s.get("op") == "⊗":
                factors = [_normalize_inner(f, ctx) for f in s.get("states", [])]
                if any(_get_key(f, ctx) in present for f in factors):
                    DIAG.absorptions += 1
                    continue
            pruned.append(s)

        flat = pruned
        # --- Explicit absorption collapse: a ⊕ (a ⊗ b) -> a ---
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "⊗":
                factors = s.get("states", [])
                for f in factors:
                    for other in flat:
                        if not (isinstance(other, dict) and other.get("op") == "⊗"):
                            if _get_key(f, ctx) == _get_key(other, ctx):
                                DIAG.absorptions += 1
                                out = other
                                ctx.memo[skey] = out
                                _NORMALIZE_MEMO[skey] = out
                                return out

        # --- Collapse absorbed singleton ---
        # If ⊕ now contains only one surviving state, collapse to it directly
        if len(flat) == 1:
            DIAG.absorptions += 1
            out = flat[0]
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # Absorbing top
        if any(isinstance(s, dict) and s.get("op") == "⊤" for s in flat):
            out = TOP
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- Duality inside sums (a ⊕ ¬a = ⊤) ---
        key_map = {_get_key(s, ctx): s for s in flat}
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "¬":
                st_key = _get_key(s["state"], ctx)
                if st_key in key_map:
                    out = TOP
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out
            else:
                neg_key = ("op1", "¬", _get_key(s, ctx))
                if neg_key in key_map:
                    out = TOP
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out

        # --- Absorption: x ⊕ ★x -> ★x (collapse entire sum) ---
        atom_keys = {
            _get_key(s, ctx): s for s in flat if not isinstance(s, dict)
        }
        star_keys = {}
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "★":
                t = s.get("state")
                if not isinstance(t, dict):
                    star_keys[_get_key(t, ctx)] = t
        common = set(atom_keys) & set(star_keys)
        if common:
            k = sorted(common)[0]
            out = {"op": "★", "state": star_keys[k]}
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- T10 Distributivity (↔ over ⊕) ---
        if len(flat) == 2:
            s1, s2 = flat
            if (
                isinstance(s1, dict) and s1.get("op") == "↔"
                and isinstance(s2, dict) and s2.get("op") == "↔"
            ):
                states1 = s1.get("states", [])
                states2 = s2.get("states", [])

                # Only process if both ↔ have exactly two states
                if len(states1) == 2 and len(states2) == 2:
                    a1, b1 = states1
                    a2, b2 = states2
                else:
                    # Skip malformed ↔ expressions
                    out = {"op": "⊕", "states": flat}
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out

                # Case 1: shared left side -> (a ↔ b1) ⊕ (a ↔ b2) = a ↔ (b1 ⊕ b2)
                if a1 == a2:
                    combined = {"op": "⊕", "states": [b1, b2]}
                    out = {"op": "↔", "states": [a1, combined]}
                    out = _normalize_inner(out, ctx)
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out

                # Case 2: shared right side -> (a1 ↔ b) ⊕ (a2 ↔ b) = b ↔ (a1 ⊕ a2)
                if b1 == b2:
                    combined = {"op": "⊕", "states": [a1, a2]}
                    out = {"op": "↔", "states": [b1, combined]}
                    out = _normalize_inner(out, ctx)
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out

                # Case 2: shared right side -> (a1 ↔ b) ⊕ (a2 ↔ b) = b ↔ (a1 ⊕ a2)
                if b1 == b2:
                    combined = {"op": "⊕", "states": [a1, a2]}
                    out = {"op": "↔", "states": [b1, combined]}
                    out = _normalize_inner(out, ctx)
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out

                # Case 3: symmetric match (↔ is commutative)
                if a1 == b2:
                    combined = {"op": "⊕", "states": [b1, a2]}
                    out = {"op": "↔", "states": [a1, combined]}
                    out = _normalize_inner(out, ctx)
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out

                if b1 == a2:
                    combined = {"op": "⊕", "states": [a1, b2]}
                    out = {"op": "↔", "states": [b1, combined]}
                    out = _normalize_inner(out, ctx)
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out

        # --- Idempotence + commutativity (⊕, ⊗, etc.) ---
        normalized = [_normalize_inner(s, ctx) for s in flat]

        uniq = {}
        for s in normalized:
            k = _get_key(s, ctx)
            if k not in uniq:
                uniq[k] = (s, k)
            else:
                DIAG.idempotence += 1

        # --- Canonicalization: sort only for commutative operators ---
        COMMUTATIVE = {"⊕", "⊗", "↔", "≈"}  # ⊖, ⊂ are *not* commutative
        if op in COMMUTATIVE:
            items = sorted(uniq.values(), key=lambda x: x[1])
            uniq_sorted = [s for s, _ in items]
        else:
            # Preserve insertion order for non-commutative operators (⊖, ⊂)
            uniq_sorted = [s for s, _ in uniq.values()]

        # --- Collapse or wrap ---
        if not uniq_sorted:
            out = EMPTY
        elif len(uniq_sorted) == 1:
            if strict:
                out = {"op": op, "states": uniq_sorted}  # preserve op in strict mode
            else:
                out = uniq_sorted[0]
        else:
            out = {"op": op, "states": uniq_sorted}

        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "⊗_M":
        flat = []
        for s in states:
            if isinstance(s, dict) and s.get("op") == "⊗_M":
                flat.extend(s.get("states", []))
            else:
                flat.append(s)

        # annihilator: magnetic composition with ∅ collapses to ∅
        if any(s == "∅" or (isinstance(s, dict) and s.get("op") == "∅") for s in flat):
            out = EMPTY
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # preserve order; directional operator
        flat = [_normalize_inner(s, ctx) for s in flat]

        if len(flat) == 1:
            out = flat[0]
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        out = {"op": "⊗_M", "states": flat}
        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "⊗":
        # --- Flatten nested ⊗ (associativity) ---
        flat = []
        for s in states:
            if isinstance(s, dict) and s.get("op") == "⊗":
                flat.extend(s.get("states", []))
            else:
                flat.append(s)

        # --- Annihilator: if any ∅ -> whole expr ∅ ---
        if any(s == "∅" or (isinstance(s, dict) and s.get("op") == "∅") for s in flat):
            out = EMPTY
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- Absorption: a ⊗ (a ⊕ b) -> a ---
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "⊕":
                options = s["states"]
                for opt in options:
                    if any(_get_key(opt, ctx) == _get_key(t, ctx) for t in flat):
                        DIAG.absorptions += 1
                        out = opt
                        ctx.memo[skey] = out
                        _NORMALIZE_MEMO[skey] = out
                        return out

        # --- Deduplication (idempotence: a ⊗ a -> a) ---
        uniq = {}
        for s in flat:
            k = _get_key(s, ctx)
            if k not in uniq:
                uniq[k] = (s, k)
            else:
                DIAG.idempotence += 1

        # Canonical order by structural key
        items = sorted(uniq.values(), key=lambda x: x[1])
        unique_sorted = [s for s, _ in items]

        # --- Collapse singleton: ⊗[a] -> a ---
        if len(unique_sorted) == 1:
            out = unique_sorted[0]
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- Absorption: a ⊗ ¬a -> ⊥ ---
        normal_keys = set()
        neg_inner_keys = set()
        for s in unique_sorted:
            if isinstance(s, dict) and s.get("op") == "¬":
                neg_inner_keys.add(_get_key(s["state"], ctx))
            else:
                normal_keys.add(_get_key(s, ctx))
        if normal_keys & neg_inner_keys:
            out = {"op": "⊥"}
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- Distribution: a ⊗ (b ⊕ c) -> (a ⊗ b) ⊕ (a ⊗ c) ---
        for i, s in enumerate(unique_sorted):
            if isinstance(s, dict) and s.get("op") == "⊕":
                others = unique_sorted[:i] + unique_sorted[i + 1 :]
                expanded = {
                    "op": "⊕",
                    "states": [
                        {"op": "⊗", "states": others + [branch]}
                        for branch in s["states"]
                    ],
                }
                DIAG.distributions += 1
                out = _normalize_inner(expanded, ctx)
                ctx.memo[skey] = out
                _NORMALIZE_MEMO[skey] = out
                return out

        # --- Otherwise: keep as ⊗ ---
        out = {"op": "⊗", "states": unique_sorted}
        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    # --- ⊖ (difference) ----------------------------------------------------
    elif op == "⊖":
        if len(states) == 2:
            x, y = states

            # --- Basic rules ---
            if structural_key(x) == structural_key(y):
                out = EMPTY  # a ⊖ a -> ∅

            elif (isinstance(y, dict) and y.get("op") == "∅") or y == "∅":
                out = x  # a ⊖ ∅ -> a

            elif (isinstance(x, dict) and x.get("op") == "∅") or x == "∅":
                out = y  # ∅ ⊖ a -> a

            # --- Nested cancellation forms ---
            elif isinstance(y, dict) and y.get("op") == "⊖":
                y1, y2 = y["states"]
                if structural_key(x) == structural_key(y1):
                    out = y2  # a ⊖ (a ⊖ b) -> b
                elif structural_key(x) == structural_key(y2):
                    out = {"op": "⊖", "states": [x, y1]}  # a ⊖ (b ⊖ a) -> a ⊖ b
                else:
                    out = {"op": "⊖", "states": [x, y]}

            # --- Chained cancellation: (a ⊖ b) ⊖ a -> b
            elif isinstance(x, dict) and x.get("op") == "⊖":
                x1, x2 = x["states"]
                if structural_key(x2) == structural_key(y):
                    out = x1
                else:
                    out = {"op": "⊖", "states": [x, y]}

            else:
                out = {"op": "⊖", "states": [x, y]}

            # --- Special collapse: (a ⊖ (a ⊖ b)) ⊖ (a ⊗ a) -> b
            if (
                isinstance(out, dict)
                and out.get("op") == "⊖"
                and isinstance(out["states"][0], dict)
                and out["states"][0].get("op") == "⊖"
                and isinstance(out["states"][1], dict)
                and out["states"][1].get("op") == "⊗"
            ):
                left = out["states"][0]
                right = out["states"][1]
                if (
                    isinstance(left["states"][1], dict)
                    and left["states"][1].get("op") == "⊖"
                    and _get_key(left["states"][0], ctx) == _get_key(right["states"][0], ctx)
                ):
                    out = left["states"][1]["states"][1]

        else:
            # fold left: (((s1 ⊖ s2) ⊖ s3) ...)
            cur = states[0]
            for nxt in states[1:]:
                cur = {"op": "⊖", "states": [cur, nxt]}
            out = cur

        # --- Canonicalization ---
        out = _maybe_rewrite(out)

        # 🔧 Preserve operand order for non-commutative ops (⊖, ⊂)
        if isinstance(out, dict) and out.get("op") in {"⊖", "⊂"}:
            out["states"] = list(out.get("states", []))

        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "¬":
        inner = _normalize_inner(expr.get("state"), ctx)

        # ¬∅ -> ∅
        if inner == "∅" or (isinstance(inner, dict) and inner.get("op") == "∅"):
            out = EMPTY
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # ¬(¬a) -> a
        if isinstance(inner, dict) and inner.get("op") == "¬":
            DIAG.idempotence += 1
            out = _normalize_inner(inner.get("state"), ctx)
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- De Morgan's Laws (guarded) ---
        if isinstance(inner, dict):
            if inner.get("op") == "⊕":
                flat = _flatten_plus(inner.get("states", []))

                # Collapse with ★ if present
                for s in flat:
                    if isinstance(s, dict) and s.get("op") == "★" and not isinstance(s.get("state"), dict):
                        out = {"op": "¬", "state": {"op": "★", "state": s["state"]}}
                        ctx.memo[skey] = out
                        _NORMALIZE_MEMO[skey] = out
                        return out

                if len(flat) > 1:
                    out = {"op": "⊗", "states": [{"op": "¬", "state": s} for s in flat]}
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out
                elif len(flat) == 1:
                    inner = flat[0]
                else:
                    inner = EMPTY

            elif inner.get("op") == "⊗":
                flat = inner.get("states", [])
                if len(flat) > 1:
                    out = {"op": "⊕", "states": [{"op": "¬", "state": s} for s in flat]}
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out
                elif len(flat) == 1:
                    inner = flat[0]
                else:
                    inner = EMPTY

        # Default: keep ¬
        out = {"op": "¬", "state": inner}
        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "Φ_B":
        inner = _normalize_inner(expr.get("state"), ctx, strict=strict)

        # Φ_B(∅) -> ∅
        if inner == EMPTY or (isinstance(inner, dict) and inner.get("op") == "∅"):
            out = EMPTY
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # idempotence: Φ_B(Φ_B(a)) -> Φ_B(a)
        if isinstance(inner, dict) and inner.get("op") == "Φ_B":
            out = inner
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        out = {"op": "Φ_B", "state": inner}
        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "★":
        raw_inner = expr.get("state")

        # --- Normalize inner first ---
        inner = _normalize_inner(raw_inner, ctx)

        # --- Deeply flatten all nested ⊕ (associative collapse) ---
        def deep_flatten_plus(node):
            if isinstance(node, dict) and node.get("op") == "⊕":
                out = []
                for s in node.get("states", []):
                    out.extend(deep_flatten_plus(s))
                return out
            return [node]

        flat_raw = deep_flatten_plus(inner)

        # --- Collapse rule: ★(a ⊕ ★a ⊕ b) -> ★a ---
        atom_keys = set()
        star_for_key = {}
        for s in flat_raw:
            if isinstance(s, dict) and s.get("op") == "★":
                t = s.get("state")
                if not isinstance(t, dict):  # ★ on atomic state
                    star_for_key[_get_key(t, ctx)] = t
            elif not isinstance(s, dict):
                atom_keys.add(_get_key(s, ctx))

        # If both a and ★a appear -> collapse to ★a
        common = atom_keys & set(star_for_key.keys())
        if common:
            k = sorted(common)[0]
            out = {"op": "★", "state": star_for_key[k]}
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- Canonicalize flattened ⊕ back into AST form ---
        uniq = {}
        for s in flat_raw:
            k = _get_key(s, ctx)
            if k not in uniq:
                uniq[k] = s
        uniq_sorted = [v for _, v in sorted(uniq.items(), key=lambda kv: kv[0])]

        if not uniq_sorted:
            inner_norm = EMPTY
        elif len(uniq_sorted) == 1:
            inner_norm = uniq_sorted[0]
        else:
            inner_norm = {"op": "⊕", "states": uniq_sorted}

        # --- Simplify recursively ---
        # If inner is a sum, first deep-flatten ⊕ and try the collapse ★(a ⊕ ★a ⊕ ...) -> ★a
        if isinstance(inner_norm, dict) and inner_norm.get("op") == "⊕":
            def _deep_flatten_plus(node):
                if isinstance(node, dict) and node.get("op") == "⊕":
                    acc = []
                    for s in node.get("states", []):
                        acc.extend(_deep_flatten_plus(s))
                    return acc
                return [node]

            flat = _deep_flatten_plus(inner_norm)

            # Collapse rule: if both atom a and ★a are present -> ★a
            atom_keys = set()
            star_for = {}
            for s in flat:
                if isinstance(s, dict) and s.get("op") == "★":
                    t = s.get("state")
                    if not isinstance(t, dict):  # only atomic ★t collapses
                        star_for[_get_key(t, ctx)] = t
                elif not isinstance(s, dict):
                    atom_keys.add(_get_key(s, ctx))

            common = atom_keys & set(star_for.keys())
            if common:
                k = sorted(common)[0]  # deterministic pick
                out = {"op": "★", "state": star_for[k]}
                ctx.memo[skey] = out
                _NORMALIZE_MEMO[skey] = out
                return out

            # Otherwise rebuild inner ⊕ canonically (drop ∅, dedup, sort)
            flat = [
                s for s in flat
                if not (isinstance(s, dict) and s.get("op") == "∅")
                   and s != "∅"
            ]
            uniq = {}
            for s in flat:
                k = _get_key(s, ctx)
                if k not in uniq:
                    uniq[k] = s
            items = sorted(uniq.values(), key=lambda x: _get_key(x, ctx))
            inner_norm = items[0] if len(items) == 1 else {"op": "⊕", "states": items}

        # Final shape cases after any ⊕ handling above
        if inner_norm == EMPTY or (
            isinstance(inner_norm, dict) and inner_norm.get("op") == "∅"
        ):
            out = EMPTY
        elif isinstance(inner_norm, dict) and inner_norm.get("op") == "★":
            out = inner_norm  # ★★a -> ★a
        elif isinstance(inner_norm, dict) and inner_norm.get("op") == "↔":
            states = inner_norm.get("states", [])
            if len(states) == 2:  # T12: ★(a↔b) -> (★a) ⊕ (★b)
                a, b = states
                out = {
                    "op": "⊕",
                    "states": [
                        {"op": "★", "state": a},
                        {"op": "★", "state": b},
                    ],
                }
            else:
                out = {"op": "★", "state": inner_norm}
        else:
            out = {"op": "★", "state": inner_norm}

        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "∅":
        ctx.memo[skey] = EMPTY
        _NORMALIZE_MEMO[skey] = EMPTY
        return EMPTY

    else:
        # Passthrough (operators not specially handled)
        out = {k: v for k, v in expr.items()}

        op = out.get("op")
        if RULES_BY_OP.get(op) or RULES_BY_OP.get(None):
            out2 = rewrite_fixed(out)
            if out2 != out:
                DIAG.rewrites += 1
            out = out2

        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
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
            k = structural_key(expr)
        else:
            k = ("atom", str(expr))

        cached = _NORMALIZE_MEMO.get(k)
        if cached is not None:
            _cache_hits += 1
            return cached

        # Count miss now (root-level only)
        _cache_misses += 1

        out = normalize(expr)
        _NORMALIZE_MEMO.setdefault(k, out)
        return _NORMALIZE_MEMO[k]


rewriter = _RewriterWrapper()

def test_star_sum_collapse():
    """
    Regression test:
    a ⊕ ★a ⊕ b should collapse to ★a under normalization,
    ensuring roundtrip stability.
    """
    expr = {"op": "★", "state": {"op": "⊕", "states": ["a", {"op": "★", "state": "a"}, "b"]}}
    assert normalize(expr) == {"op": "★", "state": "a"}

if __name__ == "__main__":
    import sys
    import json

    # Allow input as either JSON or shorthand string
    if len(sys.argv) < 2:
        print("Usage: python -m backend.photon_algebra.rewriter '<expr>'")
        print("Example: python -m backend.photon_algebra.rewriter '{\"op\":\"⊕\",\"states\":[{\"op\":\"↔\",\"states\":[\"a\",\"b\"]},{\"op\":\"↔\",\"states\":[\"a\",\"c\"]}]}'")
        sys.exit(1)

    raw = sys.argv[1]

    try:
        # Try parsing JSON first
        expr = json.loads(raw)
    except json.JSONDecodeError:
        # Fallback: treat as raw string atom
        expr = raw

    print("Input expression:", expr)
    print("=" * 60)

    # Reset diagnostics before running
    DIAG.reset()

    # Normalize with debug tracing
    result = rewrite_fixed(expr, debug=True)
    result = normalize(result)

    print("=" * 60)
    print("Normalized result:", json.dumps(result, ensure_ascii=False, indent=2))
    print("Diagnostics:", DIAG.to_dict())
    print("Cache stats:", get_cache_stats())

reset_normalize_memo = clear_normalize_memo