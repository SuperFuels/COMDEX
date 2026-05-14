# backend/tests/test_black_hole_container.py
# ──────────────────────────────────────────────
#  Quick runtime test for Tessaris BlackHoleContainer
# ──────────────────────────────────────────────

from backend.modules.dimensions.containers.black_hole_container import BlackHoleContainer

if __name__ == "__main__":
    bh = BlackHoleContainer()
    logic_tree = {"expr": ["⊕", "↔", "μ"], "depth": 3}

    # Compress symbolic structure
    bh.compress_ast(logic_tree)

    # Trigger collapse simulation (emits ψ-κ-T gravity event)
    bh.collapse()

    print("\n✅ BlackHoleContainer test completed.")