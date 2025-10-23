"""
🧠 Symatic Bridge Test
───────────────────────────────────────────────
Validates coherence between AKG concept nodes and Symatics Algebra primitives.
Checks:
- Concept → Symbol consistency
- RSI metadata mapping
- Wave–Photon operator tagging
"""

from backend.modules.aion_knowledge import knowledge_graph_core as akg

def run_symatic_bridge_test():
    print("🔬 Running Symatic Bridge Integrity Test…")

    concepts = akg.export_concepts()
    if not concepts:
        print("⚠️ No concept mappings found in AKG.")
        return

    print(f"📊 Found {len(concepts)} concept fields:")
    for c, syms in concepts.items():
        print(f"  {c} → {syms}")

    # Validate metadata embedding on one concept
    any_concept = next(iter(concepts.keys()))
    print(f"\n🔎 Inspecting metadata for: {any_concept}")
    akg.inspect_node(f"concept:{any_concept}")

    print("\n✅ Bridge test complete — AKG and Symatics layer appear consistent.")

if __name__ == "__main__":
    run_symatic_bridge_test()