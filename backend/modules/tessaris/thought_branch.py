# File: backend/modules/tessaris/thought_branch.py

import uuid
import json
from typing import List, Optional, Dict, Any, Union

SymbolLike = Union[str, Dict[str, Any], List[Any]]

def _canon_symbol(sym: SymbolLike) -> str:
    """
    Canonicalize any glyph-like object into a stable string key:
    - if dict: prefer 'symbol' or 'logic' or 'value', else json.dumps(sorted)
    - if list: join canonical forms
    - else: str(sym)
    """
    if isinstance(sym, dict):
        # Prefer helpful fields if present
        for k in ("symbol", "logic", "value", "label"):
            if k in sym and isinstance(sym[k], (str, int, float)):
                return str(sym[k])
        try:
            return json.dumps(sym, sort_keys=True, ensure_ascii=False)
        except Exception:
            return str(sym)
    if isinstance(sym, list):
        return "[" + ", ".join(_canon_symbol(s) for s in sym) + "]"
    return str(sym)


class BranchNode:
    def __init__(self, symbol: SymbolLike, source: str = "unknown", metadata: Optional[dict] = None):
        self.id = str(uuid.uuid4())
        self.symbol = symbol                    # keep original
        self.symbol_key = _canon_symbol(symbol) # stable string
        self.source = source
        self.metadata = metadata or {}
        self.children: List['BranchNode'] = []
        self.parent: Optional['BranchNode'] = None  # 🔁 Enables upward reflection

    def generate_branches(self) -> List['BranchNode']:
        """
        Generate child BranchNodes using symbolic logic expansion.
        """
        next_symbols = self._expand_symbol(self.symbol_key)  # always use canonical string
        generated = []
        for s in next_symbols:
            node = BranchNode(symbol=s, source=self.id)
            node.parent = self
            generated.append(node)
        return generated

    def _expand_symbol(self, symbol_key: str) -> List[str]:
        """
        Symbolic expansion map. Replace or enhance with real logic, embeddings, or glyph maps.
        NOTE: symbol_key is always a string (canonicalized).
        """
        return {
            "Δ": ["⊕", "λ"],
            "⊕": ["⇌", "Σ"],
            "λ": ["☼", "ψ"],
            "🎯": ["Δ", "⊕"],
            "🪄": ["λ", "⧖"],
            "⧖": ["ψ", "↔"],
        }.get(symbol_key, [])

    def add_child(self, node: 'BranchNode'):
        node.parent = self
        self.children.append(node)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,           # original (may be dict or str)
            "symbol_key": self.symbol_key,   # canonical string
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
            lines.append("  " * depth + f"{node.symbol_key} ({node.source})")
            for child in node.children:
                recurse(child, depth + 1)

        recurse(self)
        return "\n".join(lines)


class ThoughtBranch:
    def __init__(self, glyphs: List[SymbolLike], origin_id: Optional[str] = None, metadata: Optional[dict] = None):
        self.origin_id = origin_id or str(uuid.uuid4())
        self.glyphs = glyphs
        self.metadata = metadata or {}
        # 👇 CHANGE: position should be a mapping (engine does .get("coord"))
        self.position = {"index": 0, "coord": None}
        self.root: Optional[BranchNode] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin_id": self.origin_id,
            "glyphs": self.glyphs,
            "metadata": self.metadata,
            "position": self.position,  # stays a dict
            "root": self.root.to_dict() if self.root else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThoughtBranch":
        obj = cls(
            origin_id=data.get("origin_id"),
            glyphs=data.get("glyphs", []),
            metadata=data.get("metadata", {}),
        )
        # accept either int or mapping; normalize to mapping
        pos = data.get("position", {"index": 0, "coord": None})
        if isinstance(pos, int):
            pos = {"index": pos, "coord": None}
        obj.position = pos
        if data.get("root"):
            obj.root = ThoughtBranch._rebuild_branch_node(data["root"])
        return obj

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThoughtBranch":
        obj = cls(
            origin_id=data.get("origin_id"),
            glyphs=data.get("glyphs", []),
            metadata=data.get("metadata", {}),
        )
        obj.position = data.get("position", 0)
        if data.get("root"):
            obj.root = ThoughtBranch._rebuild_branch_node(data["root"])
        return obj

    @staticmethod
    def _rebuild_branch_node(data: Dict[str, Any]) -> BranchNode:
        node = BranchNode(
            symbol=data.get("symbol", data.get("symbol_key", "•")),
            source=data.get("source", "unknown"),
            metadata=data.get("metadata", {})
        )
        node.id = data.get("id", str(uuid.uuid4()))
        node.symbol_key = _canon_symbol(node.symbol)
        node.children = [ThoughtBranch._rebuild_branch_node(child) for child in data.get("children", [])]
        for child in node.children:
            child.parent = node
        return node

    def to_glyph_tree(self) -> str:
        return self.root.to_glyph_tree() if self.root else "(no tree)"


# --- Execution entry for THINK glyphs -----------------------------------------
def execute_branch_from_glyph(glyph: SymbolLike, context: dict | None = None) -> dict:
    """
    Create a ThoughtBranch rooted at `glyph` (str or dict), expand one level, optionally log,
    and return a structured result for Tessaris/Codex.
    """
    # Normalize glyph to canonical string for branching; keep original in metadata if needed
    symbol_key = _canon_symbol(glyph)
    tb = ThoughtBranch(
        glyphs=[glyph],
        metadata={"context": context or {}, "source": "glyph_logic.THINK"}
    )
    root = BranchNode(symbol=symbol_key, source="THINK")

    # expand one level using existing symbolic map
    for child in root.generate_branches():
        root.add_child(child)
    tb.root = root

    # optional memory trace (won't crash if missing)
    try:
        from backend.modules.hexcore.memory_engine import MEMORY
        MEMORY.store({
            "label": "THINK",
            "content": {
                "glyph": symbol_key,
                "origin_id": tb.origin_id,
                "children": [c.symbol_key for c in root.children],
            },
        })
    except Exception:
        pass

    out = {
        "status": "ok",
        "origin_id": tb.origin_id,
        "branch": tb.to_dict(),
        "glyph_tree": tb.to_glyph_tree(),
    }
    return out


__all__ = ["BranchNode", "ThoughtBranch", "execute_branch_from_glyph"]