# File: backend/modules/tessaris/thought_branch.py

import uuid
from typing import List, Optional, Dict


class BranchNode:
    def __init__(self, symbol: str, source: str = "unknown", metadata: dict = {}):
        self.id = str(uuid.uuid4())
        self.symbol = symbol
        self.source = source
        self.metadata = metadata
        self.children: List['BranchNode'] = []

    def generate_branches(self) -> List['BranchNode']:
        """
        Generate new branches based on symbolic rules.
        In v1 this is placeholder logic; future versions can use:
        - Contextual dreaming
        - Bootloader state
        - Goal memory
        - Glyph mutation triggers
        """
        next_symbols = self._expand_symbol(self.symbol)
        return [BranchNode(symbol=s, source=self.id) for s in next_symbols]

    def _expand_symbol(self, symbol: str) -> List[str]:
        """
        Map known symbols to potential next branches.
        This can later be replaced by dynamic graph logic.
        """
        return {
            "Δ": ["⊕", "λ"],
            "⊕": ["⇌", "Σ"],
            "λ": ["☼", "ψ"],
        }.get(symbol, [])

    def add_child(self, node: 'BranchNode'):
        self.children.append(node)

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "source": self.source,
            "metadata": self.metadata,
            "children": [child.to_dict() for child in self.children],
        }


class ThoughtBranch:
    def __init__(self, glyphs: List[str], origin_id: Optional[str] = None, metadata: dict = {}):
        self.origin_id = origin_id or str(uuid.uuid4())
        self.glyphs = glyphs
        self.metadata = metadata
        self.position = 0  # Used by glyph executor to track logic flow

    def to_dict(self) -> Dict:
        return {
            "origin_id": self.origin_id,
            "glyphs": self.glyphs,
            "metadata": self.metadata,
            "position": self.position
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ThoughtBranch":
        return cls(
            origin_id=data.get("origin_id"),
            glyphs=data.get("glyphs", []),
            metadata=data.get("metadata", {}),
        )