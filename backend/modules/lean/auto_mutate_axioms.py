# backend/modules/lean/auto_mutate_axioms.py

import random
import copy
from typing import Dict, List, Tuple, Optional

def mutate_axiom(logic: str) -> Tuple[str, str]:
    """
    Return a mutated form of the axiom and the strategy used.
    """
    strategies = [
        ("implication_to_equiv", lambda s: s.replace("->", "↔")),
        ("equality_to_inequality", lambda s: s.replace("=", "!=")),
        ("and_to_or", lambda s: s.replace("∧", "∨")),
        ("forall_to_exists", lambda s: s.replace("∀", "∃")),
    ]

    applicable = [(name, fn) for name, fn in strategies if fn(logic) != logic]
    if not applicable:
        return logic, "no_op"

    strategy, func = random.choice(applicable)
    return func(logic), strategy


def mutate_axiom_entries(entries: List[Dict]) -> List[Dict]:
    """
    Given a list of symbolic_logic or axioms entries from a container,
    return a mutated list for symbolic exploration.
    """
    mutated = []
    for e in entries:
        mutated_entry = e.copy()
        logic = e.get("logic", "")
        new_logic, strategy = mutate_axiom(logic)
        mutated_entry["logic"] = new_logic
        mutated_entry["mutated"] = True
        mutated_entry["mutation_strategy"] = strategy
        mutated.append(mutated_entry)
    return mutated


def suggest_axiom_mutation(container: Dict) -> Dict:
    """
    Given a .dc.json container, suggest a single axiom mutation.
    Returns both original and mutated glyphs with metadata.
    """
    glyphs = container.get("glyphs", [])
    for glyph in glyphs:
        if glyph.get("type") != "axiom":
            continue

        original = copy.deepcopy(glyph)
        mutated = copy.deepcopy(glyph)

        logic = original.get("logic", "")
        new_logic, strategy = mutate_axiom(logic)

        if new_logic == logic:
            continue  # No real mutation

        mutated["logic"] = new_logic
        mutated["mutated"] = True
        mutated["mutation_strategy"] = strategy
        mutated["mutation_type"] = "symbolic_logic"
        mutated["name"] = f"{glyph['name']}_mut"
        mutated["mutation_of"] = glyph["name"]
        mutated["tags"] = list(set(mutated.get("tags", []) + ["mutated", "symbolic_exploration"]))

        return {
            "original": original,
            "mutated": mutated,
            "strategy": strategy,
            "reason": f"Applied symbolic mutation strategy: {strategy}"
        }

    return {
        "original": None,
        "mutated": None,
        "reason": "No axiom found or no mutation applied"
    }