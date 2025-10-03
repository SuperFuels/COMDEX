from __future__ import annotations
import json
import copy
from functools import lru_cache
from typing import Any, Dict, List, Tuple, Union
from backend.photon_algebra.core import EMPTY, TOP, BOTTOM
Expr = Union[str, Dict[str, Any]]
# backend/photon_algebra/rewriter.py
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
        self.idempotence = 0     # a ⊗ a → a, a ⊕ a → a, ¬(¬a) → a
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

# Global memo: structural key -> normalized tree (public cache)
_NORMALIZE_MEMO: Dict[str, Any] = {}
# Global structural key cache (id(expr) -> key)
_STRUCT_CACHE: Dict[int, tuple] = {}

_cache_hits = 0
_cache_misses = 0

def clear_normalize_memo() -> None:
    """
    Clear all normalize-related caches and counters.
    """
    global _cache_hits, _cache_misses
    _NORMALIZE_MEMO.clear()

    # Clear only the caches that actually exist
    for fn in (structural_key, _string_key, _match_pattern_cached):
        try:
            fn.cache_clear()
        except Exception:
            pass

    _cache_hits = 0
    _cache_misses = 0

def clear_normalize_memo() -> None:
    global _cache_hits, _cache_misses
    _NORMALIZE_MEMO.clear()
    _STRUCT_CACHE.clear()   # <--- NEW
    ...

def get_cache_stats() -> dict:
    """Return current cache hit/miss counters."""
    return {"hits": _cache_hits, "misses": _cache_misses}


class _NormCtx:
    """Per-normalize call context with local memo and fast key cache."""
    __slots__ = ("memo", "key_cache")
    def __init__(self) -> None:
        # local memo: structural key of *current* nodes -> normalized
        self.memo: Dict[tuple, Any] = {}
        # cache of id(node) -> structural key, avoids recomputing
        self.key_cache: Dict[int, str] = {}


# -----------------------------------------------------------------------------
# Structural key (optimized: hybrid tuple+hash)
# -----------------------------------------------------------------------------
from functools import lru_cache

def structural_key(expr: Any, cache: dict[int, tuple] | None = None) -> tuple:
    if cache is None:
        cache = {}

    i = id(expr)
    if i in cache:
        return cache[i]

    # Atoms
    if isinstance(expr, str):
        if expr in ("∅", "⊤", "⊥"):
            key = (expr,)
        else:
            key = ("atom", expr)

    elif isinstance(expr, dict):
        op = expr.get("op")
        if "state" in expr:
            child_key = structural_key(expr["state"], cache)
            key = ("op1", op, child_key)
        elif "states" in expr:
            states = expr["states"]
            # recurse to child keys
            if op == "⊕":
                child_keys = [structural_key(s, cache) for s in states]
                child_keys.sort()
            else:
                child_keys = [structural_key(s, cache) for s in states]

            # 🔥 instead of returning giant tuple, return hash
            key = ("opN", op, hash(tuple(child_keys)))
        else:
            key = ("op0", op)

    elif isinstance(expr, list):
        child_keys = [structural_key(x, cache) for x in expr]
        key = ("list", hash(tuple(child_keys)))

    else:
        key = ("atom", expr)

    cache[i] = key
    return key


@lru_cache(maxsize=100_000)
def structural_key_cached(expr_frozen: tuple) -> tuple:
    """Cached version of structural_key."""
    return expr_frozen


def get_structural_key(expr: Any) -> tuple:
    """Public entry point: computes a structural key and memoizes results."""
    return structural_key_cached(structural_key(expr))


def _get_key(s, ctx):
    """Fast structural_key lookup with per-run cache."""
    kid = id(s)
    k = ctx.key_cache.get(kid)
    if k is None:
        k = structural_key(s, ctx.key_cache)
        ctx.key_cache[kid] = k
    return k

# -----------------------------------------------------------------------------
# Pattern variable predicate
# -----------------------------------------------------------------------------
def is_var(token: Any) -> bool:
    """Variables are lowercase ASCII names or tokens starting with '?'."""
    return (
        isinstance(token, str)
        and (token.startswith("?") or (token.isascii() and token.islower()))
    )


@lru_cache(maxsize=100_000)  # ⬅️ bump up
def _match_pattern_cached(pk: tuple, ek: tuple) -> bool:
    """
    Fast cached check: either equal, or one side is a variable.
    pk, ek are structural_key tuples (NOT strings).
    """
    # Exact structural match
    if pk == ek:
        return True

    # Variable detection: structural_key marks vars as ("var", name)
    if pk[0] == "var" or ek[0] == "var":
        return True

    return False

def match_pattern(pattern: Expr, expr: Expr, env: Dict[str, Expr] | None = None):
    """
    Try to match `pattern` against `expr`. Returns (ok, env) where env contains
    variable bindings. Variables are strings recognized by `is_var`.
    """
    if env is None:
        env = {}

    # Variable: bind or check consistency
    if is_var(pattern):
        bound = env.get(pattern)
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

        # --- quick reject using cached key ---
        if not _match_pattern_cached(structural_key(pattern), structural_key(expr)):
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
                # Multiset (order-insensitive) matching
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
                # Positional match
                for p, e in zip(p_states, e_states):
                    ok, env = match_pattern(p, e, env)
                    if not ok:
                        return False, env

        return True, env

    # Type mismatch
    return False, env

def substitute(node: Expr, env: Dict[str, Expr]) -> Expr:
    """Substitute variables in node using env. Avoids unnecessary copies."""
    if is_var(node):
        return env.get(node, node)
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        changed = False
        out = {"op": node.get("op")}
        if "state" in node:
            new_state = substitute(node["state"], env)
            if new_state is not node.get("state"):
                changed = True
            out["state"] = new_state
        if "states" in node:
            new_states = []
            for s in node["states"]:
                new_s = substitute(s, env)
                new_states.append(new_s)
                if new_s is not s:
                    changed = True
            out["states"] = new_states
        return out if changed else node
    return node
    
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

    # (REMOVED) T14 — Dual Distributivity
    # Handled structurally in normalize().

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
        {"op": "⊖", "states": ["a", EMPTY]},
        "a",
    ),
    # T15 (swapped): ∅ ⊖ a → a
    (
        {"op": "⊖", "states": [EMPTY, "a"]},
        "a",
    ),
]

# =============================================================================
# Rewrite Rules (axioms + derived theorems)
# =============================================================================

REWRITE_RULES: List[Tuple[Expr, Expr]] = [
    # ... all your rules ...
]

# -----------------------------------------------------------------------------
# Build fast index for rules by operator
# -----------------------------------------------------------------------------
from collections import defaultdict

RULES_BY_OP: Dict[str, List[Tuple[Expr, Expr]]] = defaultdict(list)
for pat, repl in REWRITE_RULES:
    if isinstance(pat, dict):
        RULES_BY_OP[pat.get("op", None)].append((pat, repl))
    else:
        RULES_BY_OP[None].append((pat, repl))


# =============================================================================
# Rewrite Engine
# =============================================================================

COMMUTATIVE = {"⊕"}  # etc.

def rewrite_once(expr: Expr) -> Expr:
    # now uses RULES_BY_OP instead of scanning REWRITE_RULES
    ...

# =============================================================================
# Rewrite Engine
# =============================================================================

COMMUTATIVE = {"⊕"}  # if you later add commutativity for other ops, extend this set

def rewrite_once(expr: Expr) -> Expr:
    """Apply at most one rewrite rule to expr (top-level)."""
    op = expr.get("op") if isinstance(expr, dict) else None
    candidates = RULES_BY_OP.get(op, []) + RULES_BY_OP.get(None, [])

    # try direct order
    for pattern, replacement in candidates:
        env = match(expr, pattern)
        if env is not None:
            DIAG.rewrites += 1
            return substitute(replacement, env)

    # commutative flip (only if 2 operands)
    if isinstance(expr, dict) and op in COMMUTATIVE:
        st = expr.get("states", [])
        if len(st) == 2:
            flipped = {"op": op, "states": [st[1], st[0]]}
            for pattern, replacement in candidates:
                env = match(flipped, pattern)
                if env is not None:
                    DIAG.rewrites += 1
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
def _string_key(x, ctx=None) -> tuple:
    """
    Cheap canonical key for sorting/deduplication.
    Uses structural_key/_get_key instead of str().
    """
    if ctx is not None:
        return _get_key(x, ctx)  # cached lookup
    return structural_key(x)  

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

        # Absorption: drop (a ⊗ b ⊗ …) if ANY factor is present as a standalone in the sum
        # Collect all standalone atoms in the sum (not ⊗ products)
        present_atoms = {
            structural_key(s) for s in flat
            if not (isinstance(s, dict) and s.get("op") == "⊗")
        }

        pruned = []
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "⊗":
                factors = s.get("states", [])
                # If ANY factor of the product is already present as a standalone summand → absorb
                if any(structural_key(f) in present_atoms for f in factors):
                    DIAG.absorptions += 1  # 🔍 absorption fired
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
        dedup_sorted = sorted(dedup, key=lambda s: _string_key(s, ctx))

        if len(dedup_sorted) == 0:
            return EMPTY
        if len(dedup_sorted) == 1:
            return dedup_sorted[0]
        return {"op": "⊕", "states": dedup_sorted}

    elif op == "⊗":
        # Work with normalized children computed above
        states = norm_states

        # --- Flatten nested ⊗ (associativity) ---
        flat: List[Expr] = []
        for s in states:
            if isinstance(s, dict) and s.get("op") == "⊗":
                flat.extend(s.get("states", []))
            else:
                flat.append(s)
        states = flat

        # --- Annihilators ---
        # If any ⊥ present → whole product is ⊥
        if any(isinstance(s, dict) and s.get("op") == "⊥" for s in states):
            return {"op": "⊥"}
        # If any ∅ present → whole product is ∅
        if any(isinstance(s, dict) and s.get("op") == "∅" for s in states):
            return EMPTY

        # --- Binary fast-path ---
        if len(states) == 2:
            a, b = states

            # Canonicalize commutativity by a cheap stable key
            if _string_key(a) > _string_key(b):
                a, b = b, a

            # Distribute over ⊕ on either side
            if isinstance(a, dict) and a.get("op") == "⊕":
                DIAG.distributions += 1
                return normalize({
                    "op": "⊕",
                    "states": [{"op": "⊗", "states": [ai, b]} for ai in a["states"]],
                })
            if isinstance(b, dict) and b.get("op") == "⊕":
                DIAG.distributions += 1
                return normalize({
                    "op": "⊕",
                    "states": [{"op": "⊗", "states": [a, bi]} for bi in b["states"]],
                })

            # Otherwise keep ⊗ in canonical order
            return {"op": "⊗", "states": [a, b]}

        # --- N-ary or other cases ---
        if len(states) > 2:
            # Canonicalize commutativity for stability
            states = sorted(states, key=_string_key)

            # Try one distribution if any factor is a sum
            for i, s in enumerate(states):
                if isinstance(s, dict) and s.get("op") == "⊕":
                    others = [x for j, x in enumerate(states) if j != i]
                    DIAG.distributions += 1
                    return normalize({
                        "op": "⊕",
                        "states": [{"op": "⊗", "states": others + [t]} for t in s["states"]],
                    })

            # No distribution opportunity; keep as ⊗
            return {"op": "⊗", "states": states}

        # Fallback (0/1-ary)
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

    elif op == "¬":
        inner = norm_state if norm_state is not None else (norm_states[0] if norm_states else None)
        if isinstance(inner, dict) and inner.get("op") == "¬":
            inner2 = inner.get("state") if "state" in inner else (inner.get("states", [None])[0])
            return normalize(inner2)
        return {"op": "¬", "state": inner}

    elif op in {"≈", "⊂"}:
        a, b = states

        # trivial reflexivity: a ≈ a → ⊤
        if structural_key(a) == structural_key(b):
            ctx.memo[skey] = TOP
            return TOP

        if op == "⊂":
            # ⊥ ⊂ X → ⊤
            if a == BOTTOM or (isinstance(a, dict) and a.get("op") == "⊥"):
                ctx.memo[skey] = TOP
                return TOP
            # X ⊂ ⊤ → ⊤
            if b == TOP or (isinstance(b, dict) and b.get("op") == "⊤"):
                ctx.memo[skey] = TOP
                return TOP

        # default inert
        out = {"op": op, "states": [a, b]}
        ctx.memo[skey] = out
        return out

    elif op in {"⊤", "⊥"}:
        out = {"op": op}
        ctx.memo[skey] = out
        return out

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

    elif op == "∅":
        return EMPTY

    # fallback
    out = {"op": op}
    if norm_states:
        out["states"] = norm_states
    if norm_state is not None:
        out["state"] = norm_state
    ctx.memo[skey] = out
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
            print(f"[rewrite_fixed] Iter {i}: {cur} → {nxt}")
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

def normalize(expr: Any) -> Any:
    """
    Normalize Photon expressions under axioms + calculus rules:
        - Apply rewrite rules to a fixed point (T8–T15, etc.)
        - Canonicalize ⊕: flatten, drop ∅, absorption, idempotence, commutativity
        - Distribute ⊗ over ⊕ (both sides) [⊗ handles distribution; ⊕ does NOT factor]
        - Cancellation: a ⊖ a = ∅ ; a ⊖ ∅ = a ; ∅ ⊖ a = a
        - Double negation: ¬(¬a) = a

    NOTE: Cache hit/miss counters are handled here.
    The global cache `_NORMALIZE_MEMO` stores normalized trees keyed
    by their structural form.
    """

    # --- Perf fast-paths for canonical constants ---
    if isinstance(expr, dict) and expr.get("op") in {"∅", "⊤", "⊥"}:
        return expr

    # Atoms (strings) fast-path
    if not isinstance(expr, dict):
        return expr

    k0 = structural_key(expr)

    # --- Global cache check ---
    global _cache_hits, _cache_misses
    cached = _NORMALIZE_MEMO.get(k0)
    if cached is not None:
        _cache_hits += 1   # ✅ record hit
        return cached
    _cache_misses += 1      # ✅ record miss

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
    if not isinstance(expr, dict):
        return expr

    skey = structural_key(expr, ctx.key_cache)

    # 🔍 Check global cache first
    cached = _NORMALIZE_MEMO.get(skey)
    if cached is not None:
        global _cache_hits
        _cache_hits += 1
        return cached
    else:
        global _cache_misses
        _cache_misses += 1

    # Check per-call memo
    if skey in ctx.memo:
        return ctx.memo[skey]

    op = expr.get("op")
    states = expr.get("states", [])

    # ✅ handle meta-ops first
    if op in {"≈", "⊂"} and len(states) == 2:
        a, b = states

        a = _normalize_inner(a, ctx)
        b = _normalize_inner(b, ctx)

        if structural_key(a) == structural_key(b):
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

    # --- Absorption / annihilation: a ⊗ ¬a → ⊥ ---
    if op == "⊗" and len(states) == 2:
        s1, s2 = states
        if (isinstance(s1, dict) and s1.get("op") == "¬" and _get_key(s1.get("state"), ctx) == _get_key(s2, ctx)) \
            or (isinstance(s2, dict) and s2.get("op") == "¬" and _get_key(s2.get("state"), ctx) == _get_key(s1, ctx)):
            ctx.memo[skey] = {"op": "⊥"}
            return {"op": "⊥"}

    # Duality: a ⊕ ¬a → ⊤
    if op == "⊕" and len(states) == 2:
        s1, s2 = states
        if s1 == {"op": "¬", "state": s2} or s2 == {"op": "¬", "state": s1}:
            ctx.memo[skey] = TOP
            return TOP

    # De Morgan's Laws
    if op == "¬" and isinstance(expr.get("state"), dict):
        inner = expr["state"]
        if inner.get("op") == "⊕":
            # ¬(a ⊕ b) → (¬a ⊗ ¬b)
            states = inner.get("states", [])
            return {"op": "⊗", "states": [{"op": "¬", "state": s} for s in states]}
        if inner.get("op") == "⊗":
            # ¬(a ⊗ b) → (¬a ⊕ ¬b)
            states = inner.get("states", [])
            return {"op": "⊕", "states": [{"op": "¬", "state": s} for s in states]}

    if op == "⊕":
        flat = _flatten_plus(states)

        # Drop ∅ (identity)
        flat = [
            s for s in flat
            if not ((isinstance(s, dict) and s.get("op") == "∅") or s == "∅")
        ]

        # Absorption: drop (a ⊗ b) if any factor already present
        present = {_get_key(s, ctx) for s in flat if not (isinstance(s, dict) and s.get("op") == "⊗")}
        pruned = []
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "⊗":
                factors = s.get("states", [])
                if any(_get_key(f, ctx) in present for f in factors):
                    DIAG.absorptions += 1
                    continue
            pruned.append(s)
        flat = pruned

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
                # Case: s = {"op": "¬", "state": t}, check if t is present
                st_key = _get_key(s["state"], ctx)
                if st_key in key_map:
                    out = TOP
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out
            else:
                # Case: s = t, check if {"op": "¬", "state": t} is present
                neg_key = ("op1", "¬", _get_key(s, ctx))
                if neg_key in key_map:
                    out = TOP
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out

        # Try T10 distributivity
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
                    _NORMALIZE_MEMO[skey] = out
                    return out

                if b1 == b2:
                    out = {"op": "↔", "states": [b1, {"op": "⊕", "states": [a1, a2]}]}
                    out = _normalize_inner(out, ctx)
                    ctx.memo[skey] = out
                    _NORMALIZE_MEMO[skey] = out
                    return out

        # --- Idempotence + commutativity (⊕) ---
        # normalize children up front
        normalized = [_normalize_inner(s, ctx) for s in flat]

        # dedup with structural keys
        uniq = {}
        for s in normalized:
            k = _get_key(s, ctx)
            if k not in uniq:
                uniq[k] = (s, k)
            else:
                DIAG.idempotence += 1

        # sort once by cached keys
        items = sorted(uniq.values(), key=lambda x: x[1])
        uniq_sorted = [s for s, _ in items]

        if not uniq_sorted:
            out = EMPTY
        elif len(uniq_sorted) == 1:
            out = uniq_sorted[0]
        else:
            out = {"op": "⊕", "states": uniq_sorted}

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

        # --- Annihilator: if any ⊥ → whole expr ⊥ ---
        if any(isinstance(s, dict) and s.get("op") == "⊥" for s in flat):
            out = {"op": "⊥"}
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- If any ∅ present, the whole product collapses to ∅ (absorbing) ---
        if any((isinstance(s, dict) and s.get("op") == "∅") or s == "∅" for s in flat):
            out = EMPTY
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- Deduplicate (idempotence, with cached keys) ---
        uniq = {}
        for s in flat:
            k = _get_key(s, ctx)  # ⚡ fast structural key lookup
            if k not in uniq:
                uniq[k] = (s, k)  # store (expr, key)
            else:
                DIAG.idempotence += 1  # 🔍 idempotence fired

        items = list(uniq.values())  # [(expr, key), ...]

        if not items:
            out = EMPTY  # identity
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        if len(items) == 1:
            out = items[0][0]
            ctx.memo[skey] = out
            _NORMALIZE_MEMO[skey] = out
            return out

        # --- Canonicalize commutativity using cached keys ---
        items.sort(key=lambda pair: pair[1])  # sort by key directly
        unique_sorted = [s for s, _ in items]

        # --- Normalize children after dedupe/sort ---
        unique_sorted = [_normalize_inner(s, ctx) for s in unique_sorted]

        out = {"op": "⊕", "states": unique_sorted}
        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

        # --- Normalize children after dedupe/sort ---
        unique_sorted = [_normalize_inner(s, ctx) for s in unique_sorted]

        # --- Canonicalize commutativity ---
        if len(items) > 2:
            items.sort(key=lambda x: x[1])  # sort by cached key

        unique_sorted = [s for s, _ in items]

        # --- Absorption: a ⊗ ¬a → ⊥ ---
        # Build sets of factor keys and negated-factor inner keys, then intersect.
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

        # --- Distribution: a ⊗ (b ⊕ c) → (a ⊗ b) ⊕ (a ⊗ c) ---
        for s in unique_sorted:
            if isinstance(s, dict) and s.get("op") == "⊕":
                others = [x for x in unique_sorted if x is not s]
                DIAG.distributions += 1  # 🔍 distribution fired
                expanded = {
                    "op": "⊕",
                    "states": [{"op": "⊗", "states": others + [sub]} for sub in s["states"]],
                }
                out = _normalize_inner(expanded, ctx)
                ctx.memo[skey] = out
                _NORMALIZE_MEMO[skey] = out
                return out

        # --- Otherwise: keep as ⊗ ---
        out = {"op": "⊗", "states": unique_sorted}
        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "⊖":
        if len(states) == 2:
            x, y = states

            # --- Basic rules ---
            if structural_key(x) == structural_key(y):
                out = EMPTY  # a ⊖ a → ∅

            elif (isinstance(y, dict) and y.get("op") == "∅") or y == "∅":
                out = x  # a ⊖ ∅ → a

            elif (isinstance(x, dict) and x.get("op") == "∅") or x == "∅":
                out = y  # ∅ ⊖ a → a

            # --- Nested cancellation forms ---
            elif isinstance(y, dict) and y.get("op") == "⊖":
                y1, y2 = y["states"]
                # a ⊖ (a ⊖ b) → b
                if structural_key(x) == structural_key(y1):
                    out = y2
                # a ⊖ (b ⊖ a) → a ⊖ b
                elif structural_key(x) == structural_key(y2):
                    out = {"op": "⊖", "states": [x, y1]}
                else:
                    out = {"op": "⊖", "states": [x, y]}

            # --- Chained cancellation: (a ⊖ b) ⊖ a → b
            elif isinstance(x, dict) and x.get("op") == "⊖":
                x1, x2 = x["states"]
                if structural_key(x2) == structural_key(y):
                    out = x1
                else:
                    out = {"op": "⊖", "states": [x, y]}

            else:
                out = {"op": "⊖", "states": [x, y]}

            # --- Special collapse: (a ⊖ (a ⊖ b)) ⊖ (a ⊗ a) → b
            if (
                isinstance(out, dict) and out.get("op") == "⊖"
                and isinstance(out["states"][0], dict) and out["states"][0].get("op") == "⊖"
                and isinstance(out["states"][1], dict) and out["states"][1].get("op") == "⊗"
            ):
                left = out["states"][0]
                right = out["states"][1]
                if (
                    isinstance(left["states"][1], dict)
                    and left["states"][1].get("op") == "⊖"
                    and _get_key(left["states"][0], ctx) == _get_key(right["states"][0], ctx)
                ):
                    # reduce to just the inner right branch (b)
                    out = left["states"][1]["states"][1]

        else:
            # fold left: (((s1 ⊖ s2) ⊖ s3) ...)
            cur = states[0]
            for nxt in states[1:]:
                cur = {"op": "⊖", "states": [cur, nxt]}
            out = cur

        # --- Canonicalization ---
        out = _maybe_rewrite(out)

        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "¬":
        inner = _normalize_inner(expr.get("state"), ctx)

        # ¬∅ → ∅
        if inner == "∅" or (isinstance(inner, dict) and inner.get("op") == "∅"):
            out = EMPTY  
            ctx.memo[skey] = EMPTY
            return out

        # ¬(¬a) → a
        if isinstance(inner, dict) and inner.get("op") == "¬":
            DIAG.idempotence += 1
            out = _normalize_inner(inner.get("state"), ctx)
        else:
            out = {"op": "¬", "state": inner}

        out = _maybe_rewrite(out)
        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "★":
        inner = _normalize_inner(expr.get("state"), ctx)

        if isinstance(inner, dict) and inner.get("op") == "★":
            out = inner
        elif isinstance(inner, dict) and inner.get("op") == "↔":
            a, b = inner["states"]
            expanded = {
                "op": "⊕",
                "states": [
                    {"op": "★", "state": a},
                    {"op": "★", "state": b},
                ],
            }
            # ✅ Fully normalize right now
            out = _normalize_inner(expanded, ctx)
            out = _maybe_rewrite(out)
        else:
            out = {"op": "★", "state": inner}

        ctx.memo[skey] = out
        _NORMALIZE_MEMO[skey] = out
        return out

    elif op == "∅":
        ctx.memo[skey] = EMPTY
        return EMPTY

    else:
        # Passthrough (↔, etc.)
        out = {k: v for k, v in expr.items()}
        out2 = rewrite_fixed(out)   # <-- define out2 properly
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