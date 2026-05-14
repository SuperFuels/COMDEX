# backend/modules/dimensions/containers/hoberman_container.py

import uuid
import os
import logging
from typing import List, Dict, Optional, Any

from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.glyphos.glyph_parser import parse_glyph_string
from backend.modules.codex.codex_utils import generate_hash
from backend.modules.glyphvault.soul_law_validator import get_soul_law_validator
from backend.modules.glyphvault.glyph_encryptor import GlyphEncryptor, is_encrypted_block

# ✅ Centralized address/wormhole hookup (idempotent + safe)
from backend.modules.dimensions.container_helpers import connect_container_to_hub

logger = logging.getLogger(__name__)
SOUL_LAW_MODE = os.getenv("SOUL_LAW_MODE", "full").lower()


class HobermanContainer(UCSBaseContainer):
    """
    🌀 Hoberman Container
    Inherits UCSBaseContainer (micro-grid, time dilation, SQI hooks) and adds:
        * Seed glyph inflation logic
        * SoulLaw + recursive unlock gates
        * Morality fallback for blocked glyphs
    """

    def __init__(self, container_id: Optional[str] = None, runtime: Optional[Any] = None):
        """
        Initialize a Hoberman Container.

        Args:
            container_id (Optional[str]): Unique identifier for the container.
            runtime (Optional[Any]): Attached runtime reference (e.g., UCS runtime manager).
        """
        self.container_id = container_id or str(uuid.uuid4())
        name = f"HOB-{self.container_id}"

        # ✅ Call UCSBaseContainer with required args
        super().__init__(name=name, runtime=runtime, geometry="Hoberman Sphere")

        # ✅ Ensure inherited fields exist (important for SAFE MODE runs or custom runtime skips)
        if not hasattr(self, "time_dilation"):
            self.time_dilation = 1.0  # Default to neutral time scaling

        if self.micro_grid is None:
            self.init_micro_grid()  # Auto-init if missing

        self.seed_glyphs: List[str] = []
        self.expanded_state: Optional[Dict] = None
        self.expanded = False
        self.soul_lock: Optional[str] = None

        # ✅ Address registration + default wormhole link via helper (idempotent)
        try:
            doc = {
                "id": self.container_id,
                "name": name,
                "geometry": self.geometry,
                "type": "container",  # keep generic type; subtype in meta
                "meta": {
                    "address": f"ucs://local/{self.container_id}#container",
                    "kind": "hoberman",
                },
            }
            connect_container_to_hub(doc)  # safe no-op if already linked/registered
        except Exception as e:
            logger.warning(f"[Hoberman] Address/Wormhole setup failed for {self.container_id}: {e}")

    # ---------------------------------------------------------
    # 🌱 Seed Glyph Handling
    # ---------------------------------------------------------
    def from_glyphs(self, glyph_strings: List[str], soul_lock: Optional[str] = None):
        """Load initial seed glyphs into this container."""
        self.seed_glyphs = glyph_strings
        self.expanded_state = None
        self.expanded = False
        self.soul_lock = soul_lock
        logger.info(f"[Hoberman] Loaded {len(glyph_strings)} glyph seeds.")

    def get_seed_glyphs(self) -> List[str]:
        """Return the raw glyph seeds (pre-inflation)."""
        return self.seed_glyphs

    # ---------------------------------------------------------
    # 🪬 Inflation Logic (Recursive Unlock + SoulLaw Enforcement w/ SAFE MODE bypass)
    # ---------------------------------------------------------
    def inflate(self, avatar_state: Optional[Dict] = None, key: Optional[str] = None) -> Dict:
        """
        Inflate the Hoberman Sphere:
            1️⃣ Validate SoulLaw and identity
            2️⃣ Recursively unlock encrypted glyphs
            3️⃣ Parse glyph strings into executable logic tree
            4️⃣ Auto-map glyph nodes into MicroGrid
        """
        if self.expanded:
            logger.debug(f"[Hoberman] Already expanded: {self.container_id}")
            return self.expanded_state

        # 🔒 SoulLaw validation (lazy-loaded accessor)
        soul_law = get_soul_law_validator()
        if not soul_law.validate_avatar(avatar_state):
            if SOUL_LAW_MODE == "test":
                logger.warning("[SAFE MODE] Bypassing SoulLaw validation in HobermanContainer.inflate()")
                avatar_state = {"level": soul_law.MIN_AVATAR_LEVEL}
            else:
                raise PermissionError("Avatar failed SoulLaw validation.")

        # 🔑 Key-gated expansion
        if self.soul_lock is not None and key != self.soul_lock:
            raise PermissionError("Invalid soul key provided for expansion.")

        logic_tree = []
        encryptor = GlyphEncryptor(key=b'0' * 32)  # ✅ Default AES-GCM key

        # 🔓 Recursive glyph unlock and parsing
        for glyph in self.seed_glyphs:
            if is_encrypted_block(glyph):
                try:
                    unlocked = encryptor.recursive_unlock(
                        ciphertext=glyph,
                        associated_data=None,
                        avatar_state=avatar_state
                    )
                    if unlocked:
                        logger.debug(f"[Hoberman] Successfully unlocked glyph: {glyph[:12]}...")
                        logic = parse_glyph_string(unlocked)
                    else:
                        raise ValueError("Recursive unlock returned None")
                except Exception as e:
                    logger.error(f"[Hoberman] Failed to unlock glyph: {glyph} ({e})")
                    logic = {
                        "type": "blocked",
                        "reason": "Failed recursive unlock or denied by SoulLaw",
                        "original": glyph
                    }
            else:
                logic = parse_glyph_string(glyph)

            logic_tree.append(logic)

        # 🧠 Auto-map glyphs into micro-grid
        self._populate_micro_grid(logic_tree)

        # 🧮 Save expanded state
        self.expanded_state = {
            "id": self.container_id,
            "geometry": self.geometry,
            "expanded_logic": logic_tree,
            "inflation_hash": generate_hash(logic_tree),
            "time_dilation": self.time_dilation,
            "micro_grid": self.micro_grid.serialize() if self.micro_grid else None,
        }
        self.expanded = True
        logger.info(f"[Hoberman] Inflation complete: {self.container_id} (logic nodes: {len(logic_tree)})")

        # ✅ Ensure address + wormhole link exist after inflation too (idempotent)
        try:
            doc = {
                "id": self.container_id,
                "name": f"HOB-{self.container_id}",
                "geometry": self.geometry,
                "type": "container",
                "meta": {
                    "address": f"ucs://local/{self.container_id}#container",
                    "kind": "hoberman",
                },
            }
            connect_container_to_hub(doc)  # safe re-run
        except Exception as e:
            logger.warning(f"[Hoberman] Post-inflate address/wormhole setup failed for {self.container_id}: {e}")

        return self.expanded_state

    def _populate_micro_grid(self, logic_tree: List[Dict[str, Any]]):
        """Round-robin place glyph nodes into MicroGrid."""
        if not self.micro_grid:
            logger.warning("[Hoberman] MicroGrid unavailable; skipping glyph placement.")
            return
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
                logger.warning("[Hoberman] MicroGrid full: remaining glyphs not mapped.")
                break

    # ---------------------------------------------------------
    # 🔻 Collapse Logic
    # ---------------------------------------------------------
    def collapse(self):
        """Collapse Hoberman Sphere back to seed state."""
        self.expanded_state = None
        self.expanded = False
        if self.micro_grid:
            self.init_micro_grid()  # Reset grid for fresh expansion
        logger.info(f"[Hoberman] Collapsed: {self.container_id}")

    # ---------------------------------------------------------
    # 📝 Serialization
    # ---------------------------------------------------------
    def serialize_state(self) -> Dict[str, Any]:
        return {
            "container_id": self.container_id,
            "geometry": self.geometry,
            "seed_glyphs": self.seed_glyphs,
            "expanded": self.expanded,
            "soul_lock": self.soul_lock,
            "time_dilation": self.time_dilation,
            "inflation_hash": generate_hash(self.seed_glyphs),
            "micro_grid": self.micro_grid.serialize() if self.micro_grid else None,
        }