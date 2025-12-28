# backend/modules/lean/auto_mutate_axioms.py

from __future__ import annotations

import random
import copy
import re
from typing import Dict, List, Tuple, Optional, Any


# ----------------------------
# Safer rewrite helpers
# ----------------------------

def _token_replace(s: str, pattern: str, repl: str) -> str:
    """
    Regex-based replacement to avoid accidental substring mangling.
    pattern is a regex.
    """
    return re.sub(pattern, repl, s)


def mutate_axiom(logic: str, *, rng: Optional[random.Random] = None) -> Tuple[str, str]:
    """
    Return a mutated form of the axiom and the strategy used.
    Mutations are intentionally "symbolic exploration" (may break provability).
    """
    rng = rng or random

    logic = logic or ""
    logic_in = logic

    strategies = [
        # ->  ↔  (token-ish)
        ("implication_to_equiv", lambda s: _token_replace(s, r"\s*->\s*", " ↔ ")),
        # =   ≠  (Lean uses ≠)
        ("equality_to_neq", lambda s: _token_replace(s, r"\s*=\s*", " ≠ ")),
        # ∧   ∨
        ("and_to_or", lambda s: _token_replace(s, r"\s*∧\s*", " ∨ ")),
        # ∀   ∃
        ("forall_to_exists", lambda s: _token_replace(s, r"\b∀\b", "∃")),
    ]

    applicable = []
    for name, fn in strategies:
        out = fn(logic)
        if out != logic:
            applicable.append((name, fn))

    if not applicable:
        return logic_in, "no_op"

    strategy, func = rng.choice(applicable)
    return func(logic_in), strategy


def mutate_axiom_entries(
    entries: List[Dict[str, Any]],
    *,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Given a list of symbolic_logic/axioms entries from a container,
    return a mutated list for symbolic exploration.
    """
    rng = random.Random(seed) if seed is not None else None

    mutated: List[Dict[str, Any]] = []
    for e in entries:
        if not isinstance(e, dict):
            continue

        mutated_entry = e.copy()

        logic_raw = e.get("logic_raw") or e.get("logic") or ""
        new_logic, strategy = mutate_axiom(str(logic_raw), rng=rng)

        # Keep both
        mutated_entry["logic_raw"] = str(logic_raw)
        mutated_entry["logic"] = new_logic

        # Update codexlang if present
        codex = mutated_entry.get("codexlang")
        if isinstance(codex, dict):
            codex = codex.copy()
            codex["logic"] = new_logic
            codex["normalized"] = new_logic
            mutated_entry["codexlang"] = codex

        mutated_entry["mutated"] = True
        mutated_entry["mutation_strategy"] = strategy
        mutated.append(mutated_entry)

    return mutated


def suggest_axiom_mutation(
    container: Dict[str, Any],
    *,
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Suggest a single axiom mutation from a container.

    Supports:
      - container["axioms"] (list[dict])
      - container["symbolic_logic"] entries where symbol == "⟦ Axiom ⟧"

    Returns:
      { original, mutated, strategy, reason }
    """
    rng = random.Random(seed) if seed is not None else None

    # Prefer explicit axioms field
    candidates: List[Dict[str, Any]] = []
    ax = container.get("axioms")
    if isinstance(ax, list):
        candidates.extend([x for x in ax if isinstance(x, dict)])

    # Also accept symbolic_logic axioms
    sym = container.get("symbolic_logic")
    if isinstance(sym, list):
        for x in sym:
            if isinstance(x, dict) and (x.get("symbol") == "⟦ Axiom ⟧" or x.get("kind") == "axiom"):
                candidates.append(x)

    for entry in candidates:
        original = copy.deepcopy(entry)
        mutated = copy.deepcopy(entry)

        logic_raw = original.get("logic_raw") or original.get("logic") or ""
        new_logic, strategy = mutate_axiom(str(logic_raw), rng=rng)

        if new_logic == str(logic_raw):
            continue

        mutated["logic_raw"] = str(logic_raw)
        mutated["logic"] = new_logic
        mutated["mutated"] = True
        mutated["mutation_strategy"] = strategy
        mutated["mutation_type"] = "symbolic_logic"

        nm = mutated.get("name") or "axiom"
        mutated["name"] = f"{nm}_mut"
        mutated["mutation_of"] = nm

        tags = mutated.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        mutated["tags"] = sorted(set(tags + ["mutated", "symbolic_exploration"]))

        codex = mutated.get("codexlang")
        if isinstance(codex, dict):
            codex = codex.copy()
            codex["logic"] = new_logic
            codex["normalized"] = new_logic
            mutated["codexlang"] = codex

        return {
            "original": original,
            "mutated": mutated,
            "strategy": strategy,
            "reason": f"Applied symbolic mutation strategy: {strategy}",
        }

    return {
        "original": None,
        "mutated": None,
        "reason": "No axiom candidates found or no mutation applied",
    }