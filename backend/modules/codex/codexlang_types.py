# File: backend/modules/codex/codexlang_types.py

from typing import List, Dict, Optional, Union


class CodexAST:
    def __init__(
        self,
        type: str,
        value: Optional[str] = None,
        children: Optional[List["CodexAST"]] = None,
        metadata: Optional[Dict[str, Union[str, float, int]]] = None,
    ):
        self.type = type  # e.g., "logic", "math", "vector"
        self.value = value  # Optional string value (e.g. variable name, operator)
        self.children = children or []  # Sub-AST nodes
        self.metadata = metadata or {}  # Optional metadata like source, confidence

    def to_dict(self) -> Dict:
        """Serialize CodexAST to dict for storage or JSON export."""
        return {
            "type": self.type,
            "value": self.value,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict) -> "CodexAST":
        """Deserialize dict into CodexAST."""
        return CodexAST(
            type=data["type"],
            value=data.get("value"),
            children=[CodexAST.from_dict(c) for c in data.get("children", [])],
            metadata=data.get("metadata", {}),
        )

    def __repr__(self):
        return f"CodexAST(type={self.type}, value={self.value}, children={len(self.children)})"