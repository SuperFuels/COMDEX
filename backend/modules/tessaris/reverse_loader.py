# File: backend/modules/tessaris/reverse_loader.py

from backend.modules.tessaris.thought_branch import ThoughtBranch
from backend.modules.dna_chain.switchboard import DNA_SWITCH

DNA_SWITCH.register(__file__)  # Track and mutate via DNA Chain

class ReverseLoader:
    @staticmethod
    def load_branch_from_cube(cube: dict) -> ThoughtBranch:
        """
        Convert a compressed glyph cube into a full logic ThoughtBranch.
        This reconstructs meaning for Tessaris analysis or mutation.
        """
        glyphs = cube.get("glyphs", [])
        metadata = cube.get("metadata", {})
        position = cube.get("position", [0, 0, 0, 0])
        cube_id = cube.get("id", "unknown")

        print(f"🔄 Rebuilding ThoughtBranch from cube {cube_id} at {position}...")

        branch = ThoughtBranch(
            origin_id=cube_id,
            glyphs=glyphs,
            metadata=metadata,
            position=position,
            source="reverse_loader"
        )

        return branch