# backend/modules/symbolic/symbolic_tree_node.py

import uuid
from dataclasses import dataclass, field
from typing import List, Optional
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import SymbolGlyph


@dataclass
class SymbolicTreeNode:
    """
    A node in the Symbolic Meaning Tree (Holographic Symbol Tree).
    Represents one symbolic glyph with optional children and metadata.
    """
    glyph: SymbolGlyph
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    children: List['SymbolicTreeNode'] = field(default_factory=list)
    parent: Optional['SymbolicTreeNode'] = None

    # Entanglement and origin metadata
    entangled_ids: List[str] = field(default_factory=list)
    replayed_from: Optional[str] = None
    mutation_source: Optional[str] = None

    # Prediction and scoring metadata
    goal_score: Optional[float] = None
    sqi_score: Optional[float] = None

    def add_child(self, child_node: 'SymbolicTreeNode') -> None:
        """
        Add a child node and set its parent reference.
        """
        self.children.append(child_node)
        child_node.parent = self

    def trace_path(self) -> List['SymbolicTreeNode']:
        """
        Return the path from this node to the root.
        """
        path = []
        node = self
        while node:
            path.append(node)
            node = node.parent
        return list(reversed(path))

    def to_dict(self) -> dict:
        """
        Serialize the node and children to a dictionary for export or visualization.
        """
        return {
            "id": self.id,
            "glyph": self.glyph.to_dict() if hasattr(self.glyph, "to_dict") else str(self.glyph),
            "children": [child.to_dict() for child in self.children],
            "entangled_ids": self.entangled_ids,
            "replayed_from": self.replayed_from,
            "mutation_source": self.mutation_source,
            "goal_score": self.goal_score,
            "sqi_score": self.sqi_score
        }