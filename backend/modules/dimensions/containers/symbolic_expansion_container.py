import uuid
import os
import logging
from typing import List, Dict, Optional, Any

from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.dimensions.containers.hoberman_container import HobermanContainer
from backend.modules.compression.symbolic_compressor import compress_logic_tree  # ✅ Fixed import
from backend.modules.codex.codex_utils import generate_hash
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator  # ✅ Safe accessor

logger = logging.getLogger(__name__)
SOUL_LAW_MODE = os.getenv("SOUL_LAW_MODE", "full").lower()


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

    def __init__(self, container_id: Optional[str] = None, runtime: Optional[Any] = None):
        self.container_id = container_id or str(uuid.uuid4())
        name = f"SEC-{self.container_id}"
        super().__init__(name=name, runtime=runtime, geometry="Symbolic Expansion Sphere")

        self.seed_container = HobermanContainer(container_id=self.container_id, runtime=runtime)
        self.expanded_logic: Optional[Dict[str, Any]] = None
        self.expanded = False
        self.engine = None  # ✅ Attach runtime engine (e.g., QWave SupercontainerEngine)

    # ---------------------------------------------------------
    # 🌱 Seed Loading
    # ---------------------------------------------------------
    def load_seed(self, glyph_strings: List[str]):
        logger.info(f"[SEC] Loading {len(glyph_strings)} seed glyphs into Hoberman Sphere.")
        self.seed_container.from_glyphs(glyph_strings)
        self.expanded_logic = None
        self.expanded = False

    # ---------------------------------------------------------
    # 🪬 Expansion Logic (SoulLaw Enforced w/ SAFE MODE bypass)
    # ---------------------------------------------------------
    def expand(
        self,
        avatar_state: Optional[Dict] = None,
        key: Optional[str] = None,
        recursive_unlock: bool = False,
        enforce_morality: bool = True
    ) -> Dict[str, Any]:
        """
        Expand the Symbolic Expansion Container:
            1️⃣ Validate SoulLaw (via Hoberman Sphere)
            2️⃣ Inflate Hoberman Sphere
            3️⃣ Compress inflated logic tree
            4️⃣ Auto-map glyphs into Micro-Grid
            5️⃣ Optionally perform recursive unlock of encrypted subglyphs
        """
        if self.expanded:
            logger.debug(f"[SEC] Already expanded: {self.container_id}")
            return self.expanded_logic

        soul_law = get_soul_law_validator()

        # 🔒 SoulLaw validation (with SAFE MODE bypass)
        if enforce_morality and not soul_law.validate_avatar(avatar_state):
            if SOUL_LAW_MODE == "test":
                logger.warning("[SAFE MODE] Bypassing SoulLaw avatar validation in Symbolic Expansion.")
                avatar_state = {"level": soul_law.MIN_AVATAR_LEVEL}
            else:
                raise PermissionError("Avatar failed SoulLaw validation for Symbolic Expansion.")

        # ✅ Inflate Hoberman Sphere
        inflated = self.seed_container.inflate(avatar_state=avatar_state, key=key)
        logic_tree = inflated["expanded_logic"]

        # 🔑 NEW: Recursive unlock (layer-by-layer)
        if recursive_unlock:
            self._recursive_layer_unlock(logic_tree)

        # ✅ Auto-map glyph nodes into MicroGrid
        if self.micro_grid:
            dims = self.micro_grid.dimensions
            logger.info(f"[SEC] Mapping {len(logic_tree)} glyph nodes into MicroGrid: {dims}")
            self._populate_micro_grid(logic_tree)

        # ✅ Compress expanded logic into symbolic runtime tree
        compressed = compress_logic_tree(logic_tree)
        self.expanded_logic = {
            "container_id": self.container_id,
            "geometry": self.geometry,
            "logic_tree": compressed,
            "expansion_hash": generate_hash(compressed),
            "time_dilation": self.time_dilation,
            "micro_grid": self.micro_grid.serialize() if self.micro_grid else None,
        }
        self.expanded = True
        logger.info(f"[SEC] Expansion complete: {self.container_id} | Nodes: {len(logic_tree)}")
        return self.expanded_logic

    def _recursive_layer_unlock(self, logic_tree: List[Dict[str, Any]]):
        """
        🔑 Unlock encrypted subglyphs layer-by-layer with SoulLaw validation.
        """
        logger.info(f"[SEC] Performing recursive glyph unlock: {len(logic_tree)} nodes")
        soul_law = get_soul_law_validator()
        for node in logic_tree:
            if node.get("encrypted"):
                if soul_law.validate_avatar({"level": soul_law.MIN_AVATAR_LEVEL}):
                    node["unlocked"] = True
                    logger.debug(f"[SEC] Unlocked glyph: {node.get('id', '<unknown>')}")
                else:
                    logger.warning(f"[SEC] Glyph locked by SoulLaw: {node.get('id', '<unknown>')}")

    def _populate_micro_grid(self, logic_tree: List[Dict[str, Any]]):
        x_max, y_max, z_max = self.micro_grid.dimensions
        x = y = z = 0
        for node in logic_tree:
            self.micro_grid.place(node, x, y, z)
            z += 1
            if z >= z_max:
                z = 0; y += 1
            if y >= y_max:
                y = 0; x += 1
            if x >= x_max:
                logger.warning("[SEC] MicroGrid full: Some glyphs not mapped.")
                break

    # ---------------------------------------------------------
    # 🔻 Collapse Logic
    # ---------------------------------------------------------
    def collapse(self):
        logger.info(f"[SEC] Collapsing container: {self.container_id}")
        self.expanded_logic = None
        self.expanded = False
        self.seed_container.collapse()

    # ---------------------------------------------------------
    # 🔄 Runtime Tick (Engine Integration)
    # ---------------------------------------------------------
    def runtime_tick(self):
        if hasattr(self, "engine") and self.engine:
            self.engine.tick()

    # ---------------------------------------------------------
    # 📝 Snapshots & Summaries
    # ---------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        return {
            "container_id": self.container_id,
            "geometry": self.geometry,
            "seed": self.seed_container.get_seed_glyphs(),
            "expanded": self.expanded,
            "time_dilation": self.time_dilation,
            "hash": generate_hash(self.seed_container.get_seed_glyphs()),
            "micro_grid": self.micro_grid.serialize() if self.micro_grid else None,
        }

    def compressed_summary(self) -> Dict[str, Any]:
        return {
            "id": self.container_id,
            "geometry": self.geometry,
            "status": "expanded" if self.expanded else "compressed",
            "glyph_count": len(self.seed_container.get_seed_glyphs()),
        }