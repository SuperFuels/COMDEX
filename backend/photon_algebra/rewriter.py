# backend/photon_algebra/rewriter.py
# -*- coding: utf-8 -*-

import copy
from typing import Any, Dict, List, Tuple, Union
from backend.photon_algebra.core import EMPTY  
from .core import EMPTY  # 🔑 shared canonical empty state

Expr = Union[str, Dict[str, Any]]

# =============================================================================
# Variable-based Pattern Matching
# -----------------------------------------------------------------------------
#  - Variables are lowercase ASCII identifiers (e.g., "a", "b", "c") or tokens
#    that start with '?' (e.g., "?x"). They bind to any sub-expression.
#  - Repeated variables must match the same sub-expression (unification).
# =============================================================================

def is_var(token: Any) -> bool:
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
        return copy.deepcopy(env.get(node, node))
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
#   Patterns use variable placeholders like "a", "b", "c".
# =============================================================================

# -------------------------------------------
# Rewrite Rules
# -------------------------------------------
    # --- T14 — Dual Distributivity (DISABLED in rule table) -----------------
    # a ⊕ (b ⊗ c) → (a ⊕ b) ⊗ (a ⊕ c)
    # (b ⊗ c) ⊕ a → (a ⊕ b) ⊗ (a ⊕ c)
    #
    # We handle T14 structurally inside normalize()’s ⊕ branch via a *guarded*
    # fast-path after absorption and other safety checks to avoid ping-pong with
    # the ⊗-distribution logic. Leaving these rules active here would re-introduce
    # the non-terminating rewrite loop.
    #
    # (Handled structurally; no rule entries here.)
    # ------------------------------------------------------------------------
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

    # (REMOVED) P — Distributivity rules for ⊗ over ⊕
    # Distribution is handled structurally in normalize()’s ⊗ branch,
    # after checks for annihilator and dual absorption to avoid premature expansion.

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

    # (STRUCTURAL) ⊗ Idempotence: a ⊗ a → a
    # (REMOVED) T14 — Dual Distributivity:
    # We do NOT keep a factoring rule here (a ⊕ (b ⊗ c) → (a ⊕ b) ⊗ (a ⊕ c)),
    # because normalize()’s ⊗ branch handles distribution structurally.
    # Keeping it here causes ping-pong with ⊗→⊕ distribution.
    # Implemented directly in normalize()’s ⊗ branch (post-commutativity).
    # Implemented as a **guarded fast-path in normalize()** to avoid rewrite loops.
    # Old rules were:
    # a ⊕ (b ⊗ c) → (a ⊕ b) ⊗ (a ⊕ c)
    # (b ⊗ c) ⊕ a → (a ⊕ b) ⊗ (a ⊕ c)

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

# --- normalized form -------------------------------------------------------

def normalize(expr: Any) -> Any:
    """
    Normalize Photon expressions under axioms + calculus rules:
      - Apply rewrite rules to a fixed point (T8–T15, etc.)
      - Canonicalize ⊕: flatten, drop ∅, absorption, idempotence, commutativity
      - Distribute ⊗ over ⊕ (both sides)  [⊗ handles distribution; ⊕ does NOT factor]
      - Cancellation: a ⊖ a = ∅ ; a ⊖ ∅ = a ; ∅ ⊖ a = a
      - Double negation: ¬(¬a) = a
    """
    # atoms (strings) pass through
    if not isinstance(expr, dict):
        return expr

    # 1) normalize children first
    if "states" in expr:
        expr = {**expr, "states": [normalize(s) for s in expr.get("states", [])]}
    if "state" in expr:
        expr = {**expr, "state": normalize(expr.get("state"))}

    # 2) single-step rewrite until stable (covers T10–T15 patterns)
    expr = rewrite_fixed(expr)

    # might have simplified to an atom
    if not isinstance(expr, dict):
        return expr

    op = expr.get("op")
    states = expr.get("states", [])

    if op == "⊕":
        # IMPORTANT: We do NOT "factor" T14 here.
        # Doing  a ⊕ (b ⊗ c) → (a ⊕ b) ⊗ (a ⊕ c)  in the ⊕ branch
        # can ping-pong with ⊗ distributing over ⊕. Distribution is handled
        # structurally in the ⊗ case below; here we only clean up the sum.

        # flatten nested ⊕
        flat = _flatten_plus(states)

        # drop ∅ (identity)
        flat = [s for s in flat if not (isinstance(s, dict) and s.get("op") == "∅")]

        # --- Absorption FIRST ------------------------------------------------
        # If a sum contains 'a' and also (a ⊗ b) or (b ⊗ a), drop that product.
        present_keys = {
            _string_key(s)
            for s in flat
            if not (isinstance(s, dict) and s.get("op") == "⊗")
        }
        pruned: List[Expr] = []
        for s in flat:
            if isinstance(s, dict) and s.get("op") == "⊗":
                a_, b_ = s.get("states", [None, None])
                if _string_key(a_) in present_keys or _string_key(b_) in present_keys:
                    continue  # absorbed by existing term
            pruned.append(s)
        flat = pruned
        # --------------------------------------------------------------------

        # --- Special collapse so that a ⊗ (a ⊕ b) and (a ⊗ a) ⊕ (a ⊗ b) agree ---
        # (a⊗a) ⊕ (a⊗b)  →  a     (and all commuted orders)
        if len(flat) == 2:
            u, v = flat

            def _is_times(e):
                return (
                    isinstance(e, dict)
                    and e.get("op") == "⊗"
                    and isinstance(e.get("states"), list)
                    and len(e["states"]) == 2
                )

            if _is_times(u) and _is_times(v):
                ua, ub = u["states"]
                va, vb = v["states"]

                def eq(x, y) -> bool:
                    return _string_key(x) == _string_key(y)

                # Try all pairings to detect one square term and one sharing its factor.
                candidates = [
                    (ua, ub, va, vb),
                    (ua, ub, vb, va),
                    (va, vb, ua, ub),
                    (vb, va, ua, ub),
                ]
                for A1, A2, B1, B2 in candidates:
                    if eq(A1, A2) and (eq(B1, A1) or eq(B2, A1)):
                        # (A1⊗A1) ⊕ (A1⊗B)  →  A1
                        return normalize(A1)
        # --------------------------------------------------------------------

        # idempotence + commutativity on the cleaned list
        uniq: List[Expr] = []
        seen = set()
        for s in flat:
            k = _string_key(s)
            if k in seen:
                continue
            seen.add(k)
            uniq.append(s)
        uniq_sorted = sorted(uniq, key=_string_key)

        if not uniq_sorted:
            return EMPTY
        if len(uniq_sorted) == 1:
            return uniq_sorted[0]
        return {"op": "⊕", "states": uniq_sorted}

    elif op == "⊗":
        # annihilator: ∅
        if len(states) == 2:
            a, b = states

            # if either side is ∅, whole product is ∅
            if isinstance(a, dict) and a.get("op") == "∅":
                return EMPTY
            if isinstance(b, dict) and b.get("op") == "∅":
                return EMPTY

            # canonicalize commutativity: stable order
            if _string_key(a) > _string_key(b):
                a, b = b, a

            # idempotence for ⊗: a ⊗ a → a
            # Ensures a ⊗ (a ⊕ a) → a matches the distributed/right-hand form.
            if _string_key(a) == _string_key(b):
                return normalize(a)

            # --- dual absorption for product -------------------------
            # a ⊗ (a ⊕ b) = a   and   (a ⊕ b) ⊗ a = a
            def _is_plus(x):
                return (
                    isinstance(x, dict)
                    and x.get("op") == "⊕"
                    and isinstance(x.get("states"), list)
                )

            if _is_plus(b):
                b_states = b["states"]
                if any(_string_key(s) == _string_key(a) for s in b_states):
                    return normalize(a)

            if _is_plus(a):
                a_states = a["states"]
                if any(_string_key(s) == _string_key(b) for s in a_states):
                    return normalize(b)
            # --------------------------------------------------------

            # distribute over ⊕ on either side
            if isinstance(b, dict) and b.get("op") == "⊕":
                return normalize({
                    "op": "⊕",
                    "states": [{"op": "⊗", "states": [a, bi]} for bi in b["states"]],
                })
            if isinstance(a, dict) and a.get("op") == "⊕":
                return normalize({
                    "op": "⊕",
                    "states": [{"op": "⊗", "states": [ai, b]} for ai in a["states"]],
                })

            return {"op": "⊗", "states": [a, b]}

        # Fallback for non-binary or already-normalized cases
        return {"op": "⊗", "states": states}

    elif op == "⊖":  # cancellation + falsification shims
        if len(states) == 2:
            x, y = states
            if x == y:
                return EMPTY
            if isinstance(y, dict) and y.get("op") == "∅":
                return x
            if isinstance(x, dict) and x.get("op") == "∅":
                return y
        return {"op": "⊖", "states": states}

    elif op == "¬":  # double negation elimination
        inner = expr.get("state")
        if isinstance(inner, dict) and inner.get("op") == "¬":
            return normalize(inner.get("state"))
        return {"op": "¬", "state": inner}

    elif op == "∅":
        return EMPTY  # canonical

    # passthrough for any other ops (★, ↔, etc.) with normalized children
    return {k: v for k, v in expr.items()}


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