import uuid
from typing import List, Dict, Optional
from backend.modules.containers.hoberman_container import HobermanContainer
from backend.modules.symbolic.symbolic_compressor import compress_logic_tree
from backend.modules.codex.codex_utils import generate_hash

class SymbolicExpansionContainer:
    def __init__(self, container_id: Optional[str] = None):
        self.container_id = container_id or str(uuid.uuid4())
        self.seed_container = HobermanContainer(container_id=self.container_id)
        self.expanded_logic: Optional[Dict] = None
        self.expanded = False

    def load_seed(self, glyph_strings: List[str]):
        self.seed_container.from_glyphs(glyph_strings)
        self.expanded_logic = None
        self.expanded = False

    def expand(self, avatar_state: Optional[Dict] = None, key: Optional[str] = None) -> Dict:
        """Expand container into symbolic runtime logic tree."""
        if self.expanded:
            return self.expanded_logic

        # 🔐 Delegate to Hoberman inflation with security
        inflated = self.seed_container.inflate(avatar_state=avatar_state, key=key)
        compressed = compress_logic_tree(inflated["expanded_logic"])

        self.expanded_logic = {
            "container_id": self.container_id,
            "logic_tree": compressed,
            "expansion_hash": generate_hash(compressed),
        }
        self.expanded = True
        return self.expanded_logic

    def collapse(self):
        self.expanded_logic = None
        self.expanded = False
        self.seed_container.collapse()

    def snapshot(self) -> Dict:
        return {
            "container_id": self.container_id,
            "seed": self.seed_container.get_seed_glyphs(),
            "expanded": self.expanded,
            "hash": generate_hash(self.seed_container.get_seed_glyphs()),
        }

    def compressed_summary(self) -> Dict:
        return {
            "id": self.container_id,
            "status": "expanded" if self.expanded else "compressed",
            "glyph_count": len(self.seed_container.get_seed_glyphs()),
        }