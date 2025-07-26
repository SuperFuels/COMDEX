import uuid
from typing import List, Dict, Optional, Any
from backend.modules.glyphos.glyph_parser import parse_glyph_string
from backend.modules.codex.codex_utils import generate_hash
from backend.modules.glyphvault.soul_law_validator import soul_law_validator
from backend.modules.glyphvault.glyph_encryptor import GlyphEncryptor, is_encrypted_block

class HobermanContainer:
    def __init__(self, container_id: Optional[str] = None):
        self.container_id = container_id or str(uuid.uuid4())
        self.seed_glyphs: List[str] = []
        self.expanded_state: Optional[Dict] = None
        self.expanded = False
        self.soul_lock: Optional[str] = None

    def from_glyphs(self, glyph_strings: List[str], soul_lock: Optional[str] = None):
        self.seed_glyphs = glyph_strings
        self.expanded_state = None
        self.expanded = False
        self.soul_lock = soul_lock

    def get_seed_glyphs(self) -> List[str]:
        return self.seed_glyphs

    def inflate(self, avatar_state: Optional[Dict] = None, key: Optional[str] = None) -> Dict:
        if self.expanded:
            return self.expanded_state

        if not soul_law_validator.validate_avatar(avatar_state):
            raise PermissionError("Avatar failed SoulLaw validation.")

        if self.soul_lock is not None and key != self.soul_lock:
            raise PermissionError("Invalid soul key provided for expansion.")

        logic_tree = []
        encryptor = GlyphEncryptor()

        for glyph in self.seed_glyphs:
            # 🔐 Step 1: Check if glyph is encrypted
            if is_encrypted_block(glyph):
                try:
                    # 🔁 Step 2: Attempt recursive unlock
                    unlocked = encryptor.recursive_unlock(glyph, avatar_state)
                    logic = parse_glyph_string(unlocked)
                except Exception:
                    # 🧠 Step 3: Morality block fallback
                    logic = {
                        "type": "blocked",
                        "reason": "Failed recursive unlock or access denied by SoulLaw",
                        "original": glyph,
                    }
            else:
                logic = parse_glyph_string(glyph)

            logic_tree.append(logic)

        self.expanded_state = {
            "id": self.container_id,
            "expanded_logic": logic_tree,
            "inflation_hash": generate_hash(logic_tree),
        }
        self.expanded = True
        return self.expanded_state

    def collapse(self):
        self.expanded_state = None
        self.expanded = False

    def serialize_state(self) -> Dict:
        return {
            "container_id": self.container_id,
            "seed_glyphs": self.seed_glyphs,
            "expanded": self.expanded,
            "soul_lock": self.soul_lock,
            "inflation_hash": generate_hash(self.seed_glyphs),
        }