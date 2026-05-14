from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json
from typing import Dict, Tuple

ROOT = Path(__file__).resolve().parent
IR_PATH = ROOT / "operators.json"

@dataclass(frozen=True)
class IRMaps:
    op_to_js: Dict[str, str]
    js_to_op: Dict[str, str]
    punct_to_js: Dict[str, str]
    js_to_punct: Dict[str, str]

def load_ir() -> dict:
    return json.loads(IR_PATH.read_text(encoding="utf-8"))

def build_maps() -> IRMaps:
    ir = load_ir()
    op_to_js = {row["glyph"]: (row["js_emit"] or "") for row in ir["operators"] if row.get("js_emit")}
    punct_to_js = {row["glyph"]: row["js_emit"] for row in ir["punctuation"]}
    js_to_op = {v: k for k, v in op_to_js.items()}
    js_to_punct = {v: k for k, v in punct_to_js.items()}
    return IRMaps(op_to_js, js_to_op, punct_to_js, js_to_punct)