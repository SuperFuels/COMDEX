import uuid
import os
import logging
from typing import List, Dict, Optional, Any

from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.dimensions.containers.hoberman_container import HobermanContainer
from backend.modules.compression.symbolic_compressor import compress_logic_tree  # ✅ Fixed import
from backend.modules.codex.codex_utils import generate_hash
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator  # ✅ Safe accessor

# ✅ Address registry + optional wormhole linker (safe fallbacks)
try:
    from backend.modules.aion.address_book import address_book
except Exception:  # pragma: no cover
    class _NullAB:
        def register_container(self, *_a, **_k): pass
    address_book = _NullAB()

try:
    from backend.modules.dna_chain.container_linker import link_wormhole
except Exception:  # pragma: no cover
    def link_wormhole(*_a, **_k): pass

# ✅ NEW: hub connector (safe fallback)
try:
    from backend.modules.dimensions.container_helpers import connect_container_to_hub
except Exception:  # pragma: no cover
    def connect_container_to_hub(*_a, **_k): pass

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
        self.id = self.container_id  # ✅ explicit .id alias for external engines
        name = f"SEC-{self.container_id}"

        # ✅ parent constructor
        super(SymbolicExpansionContainer, self).__init__(
            name=name,
            runtime=runtime,
            geometry="Symbolic Expansion Sphere"
        )

        self.seed_container = HobermanContainer(container_id=self.container_id, runtime=runtime)
        self.expanded_logic: Optional[Dict[str, Any]] = None
        self.expanded = False
        self.engine = None  # ✅ Attach runtime engine (e.g., QWave SupercontainerEngine)

        # ✅ Ensure this container is discoverable via address book + wormhole graph (idempotent)
        try:
            self._register_address_and_link()
        except Exception as e:
            logger.warning(f"[SEC] address/wormhole setup failed for {self.container_id}: {e}")

        # ✅ NEW: connect into HQ/hub graph (idempotent, safe)
        try:
            doc = {
                "id": self.container_id,
                "name": getattr(self, "name", self.container_id),
                "geometry": getattr(self, "geometry", "Unknown"),
                "type": "container",
                "meta": {"address": f"ucs://local/{self.container_id}#container"},
            }
            connect_container_to_hub(doc)
        except Exception as e:
            logger.debug(f"[SEC] connect_container_to_hub skipped for {self.container_id}: {e}")

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

        # ✅ Re-register to ensure latest meta is in the directory and linked (idempotent)
        try:
            self._register_address_and_link()
        except Exception as e:
            logger.debug(f"[SEC] post-expand address/wormhole setup skipped for {self.container_id}: {e}")

        # ✅ NEW: ensure hub connection after expansion too (idempotent)
        try:
            doc = {
                "id": self.container_id,
                "name": getattr(self, "name", self.container_id),
                "geometry": getattr(self, "geometry", "Unknown"),
                "type": "container",
                "meta": {"address": f"ucs://local/{self.container_id}#container"},
            }
            connect_container_to_hub(doc)
        except Exception as e:
            logger.debug(f"[SEC] post-expand connect_container_to_hub skipped for {self.container_id}: {e}")

        logger.info(f"[SEC] Expansion complete: {self.container_id} | Nodes: {len(logic_tree)}")
        return self.expanded_logic

    def _recursive_layer_unlock(self, logic_tree: List[Dict[str, Any]]):
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

    # ---------------------------------------------------------
    # 🧭 Address + Wormhole helpers (idempotent)
    # ---------------------------------------------------------
    def _register_address_and_link(self, hub_id: str = "ucs_hub") -> None:
        """
        Ensure this container is in the global address book and linked into the wormhole graph.
        Safe to call multiple times.
        """
        record = {
            "id": self.container_id,
            "name": f"SEC-{self.container_id}",
            "type": "symbolic_expansion_container",
            "geometry": self.geometry,
            "meta": {
                "caps": ["inflate", "compress", "symbolic-map"],
                "tags": ["SEC", "symbolic", "expansion"],
            },
        }
        address_book.register_container(record)
        link_wormhole(self.container_id, hub_id)