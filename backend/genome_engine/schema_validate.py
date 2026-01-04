from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

from jsonschema import Draft202012Validator


def _load_schema(name: str) -> Dict[str, Any]:
    p = Path("/workspaces/COMDEX/schemas") / name
    return json.loads(p.read_text(encoding="utf-8"))


def validate_or_raise(schema_name: str, obj: Dict[str, Any]) -> None:
    schema = _load_schema(schema_name)
    v = Draft202012Validator(schema)
    errors = sorted(v.iter_errors(obj), key=lambda e: e.path)
    if errors:
        msg_lines = [f"Schema validation failed: {schema_name}"]
        for e in errors[:10]:
            path = ".".join(str(x) for x in e.path) if e.path else "<root>"
            msg_lines.append(f"- {path}: {e.message}")
        raise ValueError("\n".join(msg_lines))
