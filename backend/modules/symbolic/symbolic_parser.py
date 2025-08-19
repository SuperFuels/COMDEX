# File: backend/modules/symbolic/symbolic_parser.py

from typing import Union, Dict, Any
from dataclasses import dataclass, field


@dataclass
class CodexAST:
    """Unified AST structure for symbolic ingestion."""
    root: str
    args: list = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self):
        return f"CodexAST(root={self.root}, args={self.args}, meta={self.meta})"


def parse_raw_input_to_ast(raw: Union[str, Dict[str, Any]]) -> CodexAST:
    """
    Normalize raw symbolic input into a CodexAST.
    
    Supports:
    - Raw CodexLang strings: "add(x, y)"
    - Dict-based glyph trees:
      {
          "root": "add",
          "args": ["x", "y"],
          "meta": {"domain": "math"}
      }
    """
    if isinstance(raw, str):
        # Simple parser for CodexLang-like syntax: e.g., "add(x, y)"
        try:
            fn_name = raw.split('(')[0].strip()
            arg_str = raw.split('(', 1)[1].rsplit(')', 1)[0]
            args = [a.strip() for a in arg_str.split(',')] if arg_str else []
            return CodexAST(root=fn_name, args=args)
        except Exception as e:
            raise ValueError(f"Invalid CodexLang string: {raw}") from e

    elif isinstance(raw, dict):
        if "root" not in raw:
            raise ValueError("Dict input must include a 'root' field.")
        args = raw.get("args", [])
        meta = raw.get("meta", {})
        return CodexAST(root=raw["root"], args=args, meta=meta)

    else:
        raise TypeError(f"Unsupported input type: {type(raw)}")