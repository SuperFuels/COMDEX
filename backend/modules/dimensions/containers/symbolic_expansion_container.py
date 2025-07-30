import uuid
from typing import List, Dict, Optional, Any

from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.dimensions.containers.hoberman_container import HobermanContainer
from backend.modules.symbolic.symbolic_compressor import compress_logic_tree
from backend.modules.codex.codex_utils import generate_hash


class SymbolicExpansionContainer(UCSBaseContainer):
    """
    🧬 Symbolic Expansion Container
    - Wraps a Hoberman Sphere for inflation
    - Compresses inflated logic trees into symbolic runtime format
    - Inherits UCSBaseContainer features:
        • Micro-grid (for distributed symbolic storage)
        • Time dilation control
        • GHX visualization hooks
        • SQI event emitters
    """
    def __init__(self, container_id: Optional[str] = None):
        super().__init__(container_id=container_id, geometry="Symbolic Expansion Sphere")
        self.seed_container = HobermanContainer(container_id=self.container_id)
        self.expanded_logic: Optional[Dict[str, Any]] = None
        self.expanded = False
        self.engine = None  # ✅ Attach runtime engine (e.g., QWave SupercontainerEngine)

    # ---------------------------------------------------------
    # 🌱 Seed Loading
    # ---------------------------------------------------------
    def load_seed(self, glyph_strings: List[str]):
        """Load glyphs into seed Hoberman container."""
        self.seed_container.from_glyphs(glyph_strings)
        self.expanded_logic = None
        self.expanded = False

    # ---------------------------------------------------------
    # 🪬 Expansion Logic
    # ---------------------------------------------------------
    def expand(self, avatar_state: Optional[Dict] = None, key: Optional[str] = None) -> Dict[str, Any]:
        """
        Expand the Symbolic Expansion Container:
            1️⃣ Inflate underlying Hoberman Sphere (SoulLaw enforced)
            2️⃣ Compress inflated logic tree
            3️⃣ Apply micro-grid and time dilation state from UCSBaseContainer
        """
        if self.expanded:
            return self.expanded_logic

        inflated = self.seed_container.inflate(avatar_state=avatar_state, key=key)
        compressed = compress_logic_tree(inflated["expanded_logic"])

        self.expanded_logic = {
            "container_id": self.container_id,
            "geometry": self.geometry,
            "logic_tree": compressed,
            "expansion_hash": generate_hash(compressed),
            "time_dilation": self.time_dilation,
            "micro_grid": self.micro_grid.serialize(),
        }
        self.expanded = True
        return self.expanded_logic

    # ---------------------------------------------------------
    # 🔻 Collapse Logic
    # ---------------------------------------------------------
    def collapse(self):
        """Collapse symbolic expansion back to compressed seed state."""
        self.expanded_logic = None
        self.expanded = False
        self.seed_container.collapse()

    # ---------------------------------------------------------
    # 🔄 Runtime Tick (Engine Integration)
    # ---------------------------------------------------------
    def runtime_tick(self):
        """
        Called every loop tick:
        - Advances any attached experimental engine (e.g., QWaveEngine)
        - Keeps SEC physics & symbolic state synchronized
        """
        if hasattr(self, "engine") and self.engine:
            self.engine.tick()  # ✅ Advances QWave proton flows & field updates

    # ---------------------------------------------------------
    # 📝 Snapshots & Summaries
    # ---------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """Return a snapshot of current seed and expansion state."""
        return {
            "container_id": self.container_id,
            "geometry": self.geometry,
            "seed": self.seed_container.get_seed_glyphs(),
            "expanded": self.expanded,
            "time_dilation": self.time_dilation,
            "hash": generate_hash(self.seed_container.get_seed_glyphs()),
            "micro_grid": self.micro_grid.serialize(),
        }

    def compressed_summary(self) -> Dict[str, Any]:
        """Compact runtime summary for dashboards and GHXVisualizer."""
        return {
            "id": self.container_id,
            "geometry": self.geometry,
            "status": "expanded" if self.expanded else "compressed",
            "glyph_count": len(self.seed_container.get_seed_glyphs()),
        }