#!/usr/bin/env python3
"""
Add new symbols or fusion outputs to an existing concept in the Aion Knowledge Graph (AKG).

Usage:
    PYTHONPATH=. python -m backend.modules.aion_knowledge.tools.add_to_concept concept_field_1 Φ λ Ω

Features:
    • Adds each symbol to the specified concept via "is_a" triplets.
    • Automatically links lineage with "derived_from" and "subclass_of" relations.
    • Reinforces existing connections if symbols already exist.
    • Displays updated membership after modification.
"""

import sys
import time
from backend.modules.aion_knowledge import knowledge_graph_core as akg

# Optional global lineage anchor
DEFAULT_SUPERCONCEPT = "superconcept_1761236835"

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m backend.modules.aion_knowledge.tools.add_to_concept <concept_name> [symbol1 symbol2 ...]")
        sys.exit(1)

    concept_name = sys.argv[1]
    symbols = sys.argv[2:] if len(sys.argv) > 2 else []

    if not symbols:
        print(f"⚠️  No symbols provided. Will list current members of concept:{concept_name}")
        concepts = akg.export_concepts()
        members = concepts.get(concept_name, [])
        print(f"Current members of {concept_name}: {members}")
        sys.exit(0)

    print(f"🧩 Adding symbols {symbols} to concept:{concept_name}")

    for sym in symbols:
        try:
            # Base association
            akg.add_triplet(f"symbol:{sym}", "is_a", f"concept:{concept_name}", strength=1.0)
            # Lineage reinforcement
            akg.add_triplet(f"symbol:{sym}", "derived_from", f"concept:{concept_name}", strength=0.8)
            # Hierarchical binding to superconcept (if defined)
            akg.add_triplet(f"concept:{concept_name}", "subclass_of", f"concept:{DEFAULT_SUPERCONCEPT}", strength=1.0)

            # Metadata note
            akg.add_triplet(
                f"concept:{concept_name}",
                "reinforced_at",
                f"timestamp:{int(time.time())}",
                strength=0.1
            )

            print(f"  ✅ Linked symbol:{sym} → concept:{concept_name} (+lineage)")

        except Exception as e:
            print(f"  ⚠️  Failed to add {sym} to {concept_name}: {e}")

    # Summary
    updated_members = akg.export_concepts().get(concept_name, [])
    print("\n🔎 Updated concept members:")
    print(updated_members)

    # Optional superconcept integrity check
    if DEFAULT_SUPERCONCEPT in akg.export_concepts():
        print(f"\n🌐 Superconcept lineage maintained under {DEFAULT_SUPERCONCEPT}")
    else:
        print(f"⚠️  Superconcept node {DEFAULT_SUPERCONCEPT} not found — lineage links created but may be latent.")

    print("\n✅ Operation complete.")

if __name__ == "__main__":
    main()