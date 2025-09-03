# 📄 backend/modules/symbolic/mutation_engine.py
from __future__ import annotations  
from typing import List
from copy import deepcopy
from datetime import datetime
import random

from backend.modules.dna_chain.mutation_scorer import score_mutation
from backend.modules.dna_chain.mutation_checker import check_mutation_against_soul_laws, estimate_entropy_change
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer
from backend.modules.runtime.container_runtime import safe_load_container_by_id, ContainerRuntime
from backend.modules.symbolic.mutation_suggestions import suggest_mutations_for_glyph

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.modules.symbolic_engine.math_logic_kernel import LogicGlyph

MUTATION_VARIANTS = {
    "Think": ["Reflect", "Plan", "Imagine"],
    "Store": ["Remember", "Forget"],
    "Goal": ["Dream", "Desire"],
    "Move": ["Shift", "Redirect"],
    "Memory": ["Recall", "Forget", "Encode"],
    "Code": ["Script", "Function"],
}

def suggest_mutations_for_glyph(glyph: "LogicGlyph") -> List["LogicGlyph"]:
    """
    Generate mutated versions of a LogicGlyph with symbolic tweaks.
    Also logs entropy and SoulLaw check.
    """
    mutations = []

    for _ in range(3):
        mutated = deepcopy(glyph)

        # Mutate label
        if mutated.label in MUTATION_VARIANTS:
            mutated.label = random.choice(MUTATION_VARIANTS[mutated.label])

        # Slight mutation to value if it's a string
        if isinstance(mutated.value, str) and mutated.value:
            if random.random() < 0.3:
                mutated.value = mutated.value[::-1]  # Reverse string

        # Timestamp-based unique ID
        mutated.id = f"{glyph.id}_mut{random.randint(1000,9999)}"

        # Compute entropy delta and SoulLaw violations
        from_str = str(glyph)
        to_str = str(mutated)
        entropy_delta = estimate_entropy_change(from_str, to_str)
        violations = check_mutation_against_soul_laws(f"{from_str} ⟶ {to_str}")

        # Attach metadata
        mutated.metadata["mutation"] = {
            "entropy_delta": entropy_delta,
            "violations": violations,
            "timestamp": datetime.utcnow().isoformat()
        }

        # Score it
        score = score_mutation(mutated.to_dict())
        mutated.metadata["score"] = score

        # Inject into knowledge graph
        writer = get_kg_writer()
        writer.inject_glyph(
            content=f"{from_str} ⟶ {to_str}",
            glyph_type="mutation",
            metadata={
                "source": "mutation_engine",
                "entropy_delta": entropy_delta,
                "score": score,
                "violations": violations
            }
        )

        mutations.append(mutated)

    return mutations

def mutate_container_logic(container_id: str, reason: str) -> None:
    """
    Load a container by ID, apply symbolic mutations to each glyph,
    and save the updated container with metadata.
    """
    print(f"[🧬 MUTATE] Mutating container: {container_id} due to {reason}")

    # Load container
    container = safe_load_container_by_id(container_id)
    if not container:
        print(f"[❌] No container found with ID: {container_id}")
        return

    glyphs = container.get("glyphs", [])
    if not glyphs:
        print(f"[ℹ️] No glyphs found in container: {container_id}")
        return

    mutated_glyphs = []
    for glyph in glyphs:
        try:
            mutations = suggest_mutations_for_glyph(glyph)
            mutated_glyphs.extend(mutations)
        except Exception as e:
            print(f"[⚠️] Failed to mutate glyph {getattr(glyph, 'id', '?')}: {e}")

    if not mutated_glyphs:
        print(f"[🟡] No mutations applied to container {container_id}")
        return

    # Replace old glyphs with mutated ones
    container["glyphs"] = mutated_glyphs

    # Update metadata
    container.setdefault("metadata", {})["last_mutation"] = {
        "reason": reason,
        "timestamp": datetime.utcnow().isoformat(),
        "mutation_count": len(mutated_glyphs),
    }

    # Save container using runtime
    runtime = ContainerRuntime()
    runtime.save_container()

    print(f"[✅] Mutation complete for container {container_id}. Saved with {len(mutated_glyphs)} glyphs.")