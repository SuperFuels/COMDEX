"""
🧠 AION Brain Knowledge Sphere
──────────────────────────────────────────────────────────────
Inflates AION's semantic core from atomized WikiGraph data into
a live HobermanContainer - the "Knowledge Sphere" of the brain.

Inputs:
    data/knowledge/atoms/wikigraph_atoms.qkg.json
Output:
    Live HobermanContainer instance registered with UCS

Runtime:
    Can be imported or executed standalone:
        python -m backend.modules.aion_knowledge.brain_knowledge_sphere
"""

import json
import logging
from pathlib import Path
from backend.modules.dimensions.containers.hoberman_container import HobermanContainer

# ✅ FIXED IMPORTS
from backend.modules.aion_core.avatar_state import AVATAR_STATE
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator

logger = logging.getLogger(__name__)
ATOMIZED_PATH = Path("data/knowledge/atoms/wikigraph_atoms.qkg.json")

# Initialize the validator and verify the avatar
validator = get_soul_law_validator()
if validator.validate_avatar(AVATAR_STATE):
    print("✅ [SoulLaw] Avatar validation successful.")
else:
    raise ValueError("❌ [SoulLaw] Avatar validation failed.")

class BrainKnowledgeSphere:
    """
    🧩 BrainKnowledgeSphere
    Initializes and inflates AION's Hoberman Knowledge Sphere from atomized data.
    """

    def __init__(self, container_id: str = "hoberman_knowledge_sphere"):
        self.container_id = container_id
        self.hoberman = None
        self.seed_glyphs = []
        self.state = {}

    # ─────────────────────────────────────────
    def load_atomized_knowledge(self):
        """Load atomized knowledge graph from JSON."""
        if not ATOMIZED_PATH.exists():
            raise FileNotFoundError(f"Missing atom data: {ATOMIZED_PATH}")

        with open(ATOMIZED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.seed_glyphs = [a["id"] for a in data.get("atoms", []) if isinstance(a, dict)]
        logger.info(f"[BrainSphere] Loaded {len(self.seed_glyphs)} atom glyphs.")
        return self.seed_glyphs

    # ─────────────────────────────────────────
    def instantiate_container(self):
        """Create Hoberman container and load glyph seeds."""
        self.hoberman = HobermanContainer(container_id=self.container_id)
        self.hoberman.from_glyphs(self.seed_glyphs)
        logger.info(f"[BrainSphere] HobermanContainer instantiated ({self.container_id}).")
        return self.hoberman

    # ─────────────────────────────────────────
    def inflate(self, avatar_level: int = 3):
        """
        Inflate the knowledge sphere:
          - Enforces SoulLaw (bypassed in SAFE MODE)
          - Maps glyphs into micro-grid
          - Registers with UCS + GHX
        """
        if not self.hoberman:
            self.instantiate_container()

        avatar_state = {"level": avatar_level}
        self.state = self.hoberman.inflate(avatar_state=avatar_state)
        logger.info(
            f"[BrainSphere] Inflation complete for {self.container_id} "
            f"({len(self.seed_glyphs)} glyphs -> {len(self.state.get('expanded_logic', []))} logic nodes)"
        )
        return self.state

    # ─────────────────────────────────────────
    def collapse(self):
        """Collapse back to seed state."""
        if self.hoberman:
            self.hoberman.collapse()
            logger.info(f"[BrainSphere] Collapsed: {self.container_id}")
        else:
            logger.warning("[BrainSphere] No active Hoberman container to collapse.")

    # ─────────────────────────────────────────
    def status(self):
        """Return serialized state summary."""
        if not self.hoberman:
            return {"status": "uninitialized"}
        return self.hoberman.serialize_state()


# ─────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────
if __name__ == "__main__":
    print("🧠 Bootstrapping AION Brain Knowledge Sphere...")
    try:
        sphere = BrainKnowledgeSphere()
        sphere.load_atomized_knowledge()
        sphere.instantiate_container()
        state = sphere.inflate(avatar_level=3)
        print("✅ Brain Knowledge Sphere inflated successfully.")
        print(f"🌐 Total Glyphs: {len(sphere.seed_glyphs)}")
        print(f"🪐 Logic Nodes:  {len(state.get('expanded_logic', []))}")
    except Exception as e:
        print(f"❌ Failed to bootstrap Brain Knowledge Sphere: {e}")