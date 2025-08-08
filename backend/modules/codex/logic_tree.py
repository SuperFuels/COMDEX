# File: backend/modules/codex/logic_tree.py

from typing import Any, Dict, List


class LogicGlyph:
    def __init__(self, name: str, logic: str, operator: str, args: List[Any]):
        self.name = name
        self.logic = logic
        self.operator = operator
        self.args = args

    @classmethod
    def from_codexlang(cls, codexlang: Dict[str, Any]) -> "LogicGlyph":
        return cls(
            name=codexlang.get("name", "unknown"),
            logic=codexlang.get("logic", ""),
            operator=codexlang.get("operator", "⊕"),
            args=codexlang.get("args", [])
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "LogicGlyph",
            "name": self.name,
            "logic": self.logic,
            "operator": self.operator,
            "args": self.args
        }

    def __repr__(self) -> str:
        return f"<LogicGlyph name={self.name} logic={self.logic} operator={self.operator}>"