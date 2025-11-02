# backend/modules/photonlang/ops/registry.py
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Dict, List, Literal, Optional

@dataclass
class OpLaws:
    commutative: bool = False
    associative: bool = False
    idempotent: bool = False

@dataclass
class OpSpec:
    glyph: str
    name: str
    arity: Literal["1","2","n"]
    precedence: int
    associativity: Literal["left","right","none"]
    laws: OpLaws
    lowering_call: str
    hover: Optional[str] = None
    examples: Optional[List[str]] = None

def load_specs() -> Dict[str, OpSpec]:
    p = Path(__file__).with_name("operators.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    out: Dict[str,OpSpec] = {}
    for row in data["operators"]:
        laws = OpLaws(**row.get("laws", {}))
        spec = OpSpec(
            glyph=row["glyph"],
            name=row["name"],
            arity=row["arity"],
            precedence=row.get("precedence", 50),
            associativity=row.get("associativity","none"),
            laws=laws,
            lowering_call=row.get("lowering",{}).get("call", row["name"]),
            hover=row.get("hover"),
            examples=row.get("examples", []),
        )
        out[spec.glyph] = spec
    return out