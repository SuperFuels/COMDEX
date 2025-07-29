import uuid
from typing import List, Dict, Optional, Any

from backend.modules.dimensions.universal_container_system.ucs_base_container import UCSBaseContainer
from backend.modules.glyphos.glyph_parser import parse_glyph_string
from backend.modules.codex.codex_utils import generate_hash
from backend.modules.glyphvault.soul_law_validator import soul_law_validator
from backend.modules.glyphvault.glyph_encryptor import GlyphEncryptor, is_encrypted_block


class HobermanContainer(UCSBaseContainer):
    """
    🌀 Hoberman Container
    Inherits UCSBaseContainer (micro-grid, time dilation, SQI hooks) and adds:
        • Seed glyph inflation logic
        • SoulLaw + recursive unlock gates
        • Morality fallback for blocked glyphs
    """
    def __init__(self, container_id: Optional[str] = None):
        super().__init__(container_id=container_id, geometry="Hoberman Sphere")
        self.seed_glyphs: List[str] = []
        self.expanded_state: Optional[Dict] = None
        self.expanded = False
        self.soul_lock: Optional[str] = None

    # ---------------------------------------------------------
    # 🌱 Seed Glyph Handling
    # ---------------------------------------------------------
    def from_glyphs(self, glyph_strings: List[str], soul_lock: Optional[str] = None):
        """Load initial seed glyphs into this container."""
        self.seed_glyphs = glyph_strings
        self.expanded_state = None
        self.expanded = False
        self.soul_lock = soul_lock

    def get_seed_glyphs(self) -> List[str]:
        """Return the raw glyph seeds (pre-inflation)."""
        return self.seed_glyphs

    # ---------------------------------------------------------
    # 🪬 Inflation Logic (Recursive Unlock + SoulLaw Enforcement)
    # ---------------------------------------------------------
    def inflate(self, avatar_state: Optional[Dict] = None, key: Optional[str] = None) -> Dict:
        """
        Inflate the Hoberman Sphere:
            1️⃣ Validate SoulLaw and identity
            2️⃣ Recursively unlock encrypted glyphs
            3️⃣ Parse glyph strings into executable logic tree
        """
        if self.expanded:
            return self.expanded_state

        # 🔒 SoulLaw validation
        if not soul_law_validator.validate_avatar(avatar_state):
            raise PermissionError("Avatar failed SoulLaw validation.")

        # 🔑 Key-gated expansion
        if self.soul_lock is not None and key != self.soul_lock:
            raise PermissionError("Invalid soul key provided for expansion.")

        logic_tree = []
        encryptor = GlyphEncryptor()

        for glyph in self.seed_glyphs:
            if is_encrypted_block(glyph):
                try:
                    unlocked = encryptor.recursive_unlock(glyph, avatar_state)
                    logic = parse_glyph_string(unlocked)
                except Exception:
                    logic = {
                        "type": "blocked",
                        "reason": "Failed recursive unlock or denied by SoulLaw",
                        "original": glyph,
                    }
            else:
                logic = parse_glyph_string(glyph)

            logic_tree.append(logic)

        # 🧮 Save expanded state
        self.expanded_state = {
            "id": self.container_id,
            "geometry": self.geometry,
            "expanded_logic": logic_tree,
            "inflation_hash": generate_hash(logic_tree),
            "time_dilation": self.time_dilation,
            "micro_grid": self.micro_grid.serialize(),
        }
        self.expanded = True
        return self.expanded_state

    # ---------------------------------------------------------
    # 🔻 Collapse Logic
    # ---------------------------------------------------------
    def collapse(self):
        """Collapse Hoberman Sphere back to seed state."""
        self.expanded_state = None
        self.expanded = False

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
            "micro_grid": self.micro_grid.serialize(),
        }