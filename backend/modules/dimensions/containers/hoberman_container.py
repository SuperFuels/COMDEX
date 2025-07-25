import uuid
from typing import List, Dict, Optional
from backend.modules.glyphos.glyph_parser import parse_glyph_string
from backend.modules.codex.codex_utils import generate_hash

class HobermanContainer:
    def __init__(self, container_id: Optional[str] = None):
        self.container_id = container_id or str(uuid.uuid4())
        self.seed_glyphs: List[str] = []
        self.expanded_state: Optional[Dict] = None
        self.expanded = False

    def from_glyphs(self, glyph_strings: List[str]):
        """Set seed glyphs from raw CodexLang strings."""
        self.seed_glyphs = glyph_strings
        self.expanded_state = None
        self.expanded = False

    def get_seed_glyphs(self) -> List[str]:
        return self.seed_glyphs

    def inflate(self) -> Dict:
        """Inflate symbolic logic tree from seed glyphs."""
        if self.expanded:
            return self.expanded_state

        logic_tree = []
        for glyph in self.seed_glyphs:
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
        """Collapse to seed-only state."""
        self.expanded_state = None
        self.expanded = False

    def serialize_state(self) -> Dict:
        return {
            "container_id": self.container_id,
            "seed_glyphs": self.seed_glyphs,
            "expanded": self.expanded,
            "inflation_hash": generate_hash(self.seed_glyphs),
        }