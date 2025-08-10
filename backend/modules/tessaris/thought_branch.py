# File: backend/modules/tessaris/thought_branch.py

import uuid
from typing import List, Optional, Dict, Any


class BranchNode:
    def __init__(self, symbol: str, source: str = "unknown", metadata: Optional[dict] = None):
        self.id = str(uuid.uuid4())
        self.symbol = symbol
        self.source = source
        self.metadata = metadata or {}
        self.children: List['BranchNode'] = []
        self.parent: Optional['BranchNode'] = None  # 🔁 Enables upward reflection

    def generate_branches(self) -> List['BranchNode']:
        """
        Generate child BranchNodes using symbolic logic expansion.
        Placeholder logic for now; override with advanced symbolic growth.
        """
        next_symbols = self._expand_symbol(self.symbol)
        generated = []
        for s in next_symbols:
            node = BranchNode(symbol=s, source=self.id)
            node.parent = self
            generated.append(node)
        return generated

    def _expand_symbol(self, symbol: str) -> List[str]:
        """
        Symbolic expansion map. Replace or enhance with real logic, embeddings, or glyph maps.
        """
        return {
            "Δ": ["⊕", "λ"],
            "⊕": ["⇌", "Σ"],
            "λ": ["☼", "ψ"],
            "🎯": ["Δ", "⊕"],
            "🪄": ["λ", "⧖"],
            "⧖": ["ψ", "↔"],
        }.get(symbol, [])

    def add_child(self, node: 'BranchNode'):
        node.parent = self
        self.children.append(node)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "source": self.source,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
        }

    def to_glyph_tree(self) -> str:
        """
        Convert the node and its children into an indented glyph tree string for scroll rendering.
        """
        lines = []

        def recurse(node: 'BranchNode', depth: int = 0):
            lines.append("  " * depth + f"{node.symbol} ({node.source})")
            for child in node.children:
                recurse(child, depth + 1)

        recurse(self)
        return "\n".join(lines)


class ThoughtBranch:
    def __init__(self, glyphs: List[str], origin_id: Optional[str] = None, metadata: Optional[dict] = None):
        self.origin_id = origin_id or str(uuid.uuid4())
        self.glyphs = glyphs
        self.metadata = metadata or {}
        self.position = 0  # Runtime execution tracker
        self.root: Optional[BranchNode] = None  # 🌱 Optional root node for glyph tree

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin_id": self.origin_id,
            "glyphs": self.glyphs,
            "metadata": self.metadata,
            "position": self.position,
            "root": self.root.to_dict() if self.root else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThoughtBranch":
        obj = cls(
            origin_id=data.get("origin_id"),
            glyphs=data.get("glyphs", []),
            metadata=data.get("metadata", {}),
        )
        obj.position = data.get("position", 0)
        if "root" in data and data["root"]:
            obj.root = ThoughtBranch._rebuild_branch_node(data["root"])
        return obj

    @staticmethod
    def _rebuild_branch_node(data: Dict[str, Any]) -> BranchNode:
        node = BranchNode(
            symbol=data.get("symbol"),
            source=data.get("source"),
            metadata=data.get("metadata", {})
        )
        node.id = data.get("id", str(uuid.uuid4()))
        node.children = [ThoughtBranch._rebuild_branch_node(child) for child in data.get("children", [])]
        for child in node.children:
            child.parent = node
        return node

    def to_glyph_tree(self) -> str:
        """
        Returns stringified glyph tree from root node (Codex-ready scroll).
        """
        return self.root.to_glyph_tree() if self.root else "(no tree)"

    # --- Execution entry for THINK glyphs -----------------------------------------

# --- Execution entry for THINK glyphs -----------------------------------------
def execute_branch_from_glyph(glyph: str, context: dict | None = None) -> dict:
        """
        Create a ThoughtBranch rooted at `glyph`, expand one level, optionally log,
        and return a structured result for Tessaris/Codex.
        """
        tb = ThoughtBranch(glyphs=[glyph], metadata={"context": context or {}, "source": "glyph_logic.THINK"})
        root = BranchNode(symbol=glyph, source="THINK")

        # expand one level using existing symbolic map in BranchNode._expand_symbol
        for child in root.generate_branches():
            root.add_child(child)
        tb.root = root

        # optional memory trace (won't crash if missing)
        try:
            from backend.modules.hexcore.memory_engine import MEMORY
            MEMORY.store({
                "role": "glyph",
                "label": "THINK",
                "content": f"THINK:{glyph}",
                "metadata": {
                    "origin_id": tb.origin_id,
                    "children": [c.symbol for c in root.children],
                },
            })
        except Exception:
            pass

        return {
            "status": "ok",
            "origin_id": tb.origin_id,
            "branch": tb.to_dict(),
            "glyph_tree": tb.to_glyph_tree(),
        }

    # ensure it’s exported
        try:
            __all__  # may not exist yet
        except NameError:
            __all__ = []
        __all__ += ["execute_branch_from_glyph"]