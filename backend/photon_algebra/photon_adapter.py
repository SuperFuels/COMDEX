# backend/photon_algebra/photon_adapter.py
import json
from typing import Any, Dict, Tuple
from pathlib import Path
import fastjsonschema
from backend.photon_algebra import rewriter
from backend.photon_algebra.rewriter import _string_key  # ⚡️ no DIAG import here
from backend.photon_algebra.core import PhotonState
"""
Photon Adapter
--------------
Thin wrapper around `rewriter.normalize` with:
- JSON Schema validation for Photon AST
- Diagnostics counters (rewrite, absorption, distribution events)
- Stable normalize API for external callers
"""
# ---------------------------
# JSON Schema
# ---------------------------
_SCHEMA_PATH = Path(__file__).with_name("photon_schema.json")

_SCHEMA_DEF = {
    "type": "object",
    "required": ["op"],
    "properties": {
        "op": {"type": "string"},
        "states": {
            "type": "array",
            "items": {
                "oneOf": [
                    {"$ref": "#"},           # nested Photon AST
                    {"type": "string"}       # atomic symbol
                ]
            },
        },
        "state": {
            "oneOf": [
                {"$ref": "#"},
                {"type": "string"}
            ]
        },
    },
    "additionalProperties": True,
}
VALIDATE = fastjsonschema.compile(_SCHEMA_DEF)


# ---------------------------
# Public API
# ---------------------------
def normalize_expr(expr: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    VALIDATE(expr)
    rewriter.DIAG.reset()

    # Clear cache so DIAG increments reflect this call
    rewriter.clear_normalize_memo()

    norm = rewriter.normalize(expr)
    meta = {
        "normalized_key": _string_key(norm),
        "invariants": {"no_plus_under_times": not _has_plus_under_times(norm)},
        **rewriter.DIAG.to_dict(),
    }
    return norm, meta

# ---------------------------
# Helpers
# ---------------------------
def _has_plus_under_times(expr: Any) -> bool:
    """Check if a ⊕ node exists directly under a ⊗ (invariant check)."""
    if isinstance(expr, dict) and expr.get("op") == "⊗":
        for s in expr.get("states", []):
            if isinstance(s, dict) and s.get("op") == "⊕":
                return True
    if isinstance(expr, dict):
        return any(_has_plus_under_times(s) for s in expr.get("states", []) if isinstance(s, dict))
    return False


def to_json(expr: PhotonState, indent: int = 2) -> str:
    """Serialize a Photon expression to JSON string."""
    return json.dumps(expr, indent=indent, ensure_ascii=False)

def from_json(data: str) -> PhotonState:
    """Deserialize a Photon expression from JSON string."""
    return json.loads(data)

# ---------------------------
# CLI harness
# ---------------------------
if __name__ == "__main__":
    # Example input
    expr = {"op": "⊗", "states": ["a", {"op": "⊕", "states": ["b", "c"]}]}
    norm, meta = normalize_expr(expr)
    print("Input:", expr)
    print("Normalized:", json.dumps(norm, ensure_ascii=False, indent=2))
    print("Metadata:", json.dumps(meta, ensure_ascii=False, indent=2))