"""
Photon -> Codex Bridge
─────────────────────────────────────────────
Converts Photon Capsules (.phn JSON) into Codex structures:
- LogicGlyph objects
- Symbolic Registry entries
- Optional Codex scroll strings (for GHX/QFC replay)

This makes Photon capsules first-class citizens inside CodexCore.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

from backend.modules.codex.logic_tree import LogicGlyph
from backend.modules.codex.symbolic_registry import symbolic_registry
# ✅ Canonical validator (kept old schema machinery as fallback, but prefer this)
from backend.modules.photon.validation import validate_photon_capsule

logger = logging.getLogger(__name__)

# ──────────────────────────────
# Default inline schema (fallback)
# ──────────────────────────────
_DEFAULT_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "glyphs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "logic": {"type": "string"},
                    "operator": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "meta": {"type": "object"},
                },
                "required": ["operator"],
            },
        },
        "steps": {  # legacy support
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "value": {"type": "string"},
                    "args": {"type": "array", "items": {"type": "string"}},
                    "meta": {"type": "object"},
                },
                "required": ["symbol"],
            },
        },
        "engine": {"type": "string"},
    },
    "anyOf": [
        {"required": ["glyphs"]},
        {"required": ["steps"]},
    ],
}

# ──────────────────────────────
# Schema loading / validation
# ──────────────────────────────
try:
    import jsonschema  # type: ignore
    _HAS_JSONSCHEMA = True
except Exception:
    jsonschema = None  # type: ignore
    _HAS_JSONSCHEMA = False

_SCHEMA_PATH = Path(__file__).parent / "photon_capsule_schema.json"
if _SCHEMA_PATH.exists():
    try:
        _CAPSULE_SCHEMA: Dict[str, Any] = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"[PhotonBridge] Failed to load external schema: {e}")
        _CAPSULE_SCHEMA = _DEFAULT_SCHEMA
else:
    _CAPSULE_SCHEMA = _DEFAULT_SCHEMA


def _validate_capsule(data: Dict[str, Any]) -> None:
    """
    Validate capsule JSON.
    Prefer canonical validator; fall back to local jsonschema if needed.
    """
    # First try canonical validator (raises jsonschema.ValidationError on failure)
    try:
        validate_photon_capsule(data)
        return
    except Exception as e:
        # If the canonical path fails because jsonschema is not available, we still try local fallback.
        if not _HAS_JSONSCHEMA:
            # Repackage as standardized error
            raise ValueError({
                "validation_errors": [{"code": "E001", "message": str(e)}],
                "validation_errors_version": "v1",
            })

    # Fallback to local jsonschema validation
    if not _HAS_JSONSCHEMA:
        logger.debug("[PhotonBridge] jsonschema not installed; skipping fallback validation")
        return

    try:
        jsonschema.validate(instance=data, schema=_CAPSULE_SCHEMA)  # type: ignore
    except Exception as e:
        # Standardized validation error format (v1)
        errors = [{
            "code": "E001",  # could later map specific codes
            "message": str(e)
        }]
        raise ValueError({
            "validation_errors": errors,
            "validation_errors_version": "v1"
        })


# ──────────────────────────────
# Photon Capsule Loader
# ──────────────────────────────
def load_photon_capsule(path_or_dict: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Load a Photon capsule from path or dict and validate against schema.
    Handles:
      • new 'glyph_stream' → normalized into 'glyphs' (keeps glyph_stream)
      • legacy 'steps' → converted to 'glyphs'
      • legacy 'body'  → converted to 'glyphs'
    Always validates after migration.
    """
    if isinstance(path_or_dict, (str, Path)):
        path = Path(path_or_dict)
        with open(path, "r", encoding="utf-8") as f:
            capsule = json.load(f)
    elif isinstance(path_or_dict, dict):
        capsule = path_or_dict.copy()
    else:
        raise TypeError(f"Unsupported capsule input: {type(path_or_dict)}")

    # ──────────────────────────────
    # New canonical stream -> glyphs (but keep glyph_stream for tooling)
    # ──────────────────────────────
    if "glyphs" not in capsule and "glyph_stream" in capsule:
        gs = capsule.get("glyph_stream") or []
        capsule["glyphs"] = gs

    # ──────────────────────────────
    # Legacy upgrade: steps -> glyphs (structured)
    # ──────────────────────────────
    if "steps" in capsule and "glyphs" not in capsule:
        logger.warning("Legacy capsule format detected: field 'steps' -> auto-converted to 'glyphs'.")
        converted: List[Dict[str, Any]] = []
        for step in capsule.get("steps", []):
            converted.append({
                "name": step.get("value", "unknown"),
                "logic": step.get("value", ""),
                "operator": step.get("symbol", "⊕"),
                "args": step.get("args", []),
                "meta": step.get("meta", {}),
            })
        capsule["glyphs"] = converted

    # ──────────────────────────────
    # Legacy upgrade: body -> glyphs (structured)
    # ──────────────────────────────
    if "body" in capsule and "glyphs" not in capsule:
        logger.warning("Legacy capsule format detected: field 'body' -> migrated to 'glyphs'.")
        converted: List[Dict[str, Any]] = []
        for g in capsule.get("body", []):
            converted.append({
                "name": g.get("name", "unknown"),
                "logic": g.get("logic", ""),
                "operator": g.get("operator", "⊕"),
                "args": g.get("args", []),
                "meta": g.get("meta", {}),
            })
        capsule["glyphs"] = converted

    # Drop legacy keys (schemas often use additionalProperties=false)
    for legacy_key in ("steps", "body"):
        if legacy_key in capsule:
            capsule.pop(legacy_key, None)

    # ✅ Schema validation (after migration)
    _validate_capsule(capsule)

    return capsule


# ──────────────────────────────
# Capsule -> LogicGlyph Conversion
# ──────────────────────────────
def photon_capsule_to_glyphs(capsule: Dict[str, Any]) -> List[LogicGlyph]:
    """
    Convert Photon capsule JSON into LogicGlyph objects.
    Supports:
      * new capsules with "glyphs" (preferred)
      * fallback to "glyph_stream" if present
    """
    raw_items: List[Dict[str, Any]] = (
        capsule.get("glyphs")
        or capsule.get("glyph_stream")
        or []
    )

    glyphs: List[LogicGlyph] = []
    for item in raw_items:
        # Defensive: ensure dict shape
        if not isinstance(item, dict):
            glyphs.append(LogicGlyph(name=str(item), logic=str(item), operator="⊕", args=[]))
            continue

        g = LogicGlyph(
            name=item.get("name", "unknown"),
            logic=item.get("logic", ""),
            operator=item.get("operator", "⊕"),
            args=item.get("args", []),
        )
        glyphs.append(g)

    return glyphs


# ──────────────────────────────
# Registry + Scroll Integration
# ──────────────────────────────
def register_photon_glyphs(
    glyphs: List[LogicGlyph],
    capsule_id: str = "photon_capsule"
) -> None:
    symbolic_registry.register(capsule_id, [g.to_dict() for g in glyphs])


def render_photon_scroll(glyphs: List[LogicGlyph]) -> str:
    lines: List[str] = []
    for g in glyphs:
        args = g.args or []
        if len(args) == 2:
            lines.append(f"{g.operator}({args[0]}, {args[1]})")
        elif len(args) == 1:
            lines.append(f"{g.operator}({args[0]})")
        elif args:
            lines.append(f"{g.operator}({', '.join(args)})")
        else:
            lines.append(f"{g.operator}()")
    return " ; ".join(lines)


# ──────────────────────────────
# Convenience Entry Point
# ──────────────────────────────
def photon_to_codex(
    path_or_dict: Union[str, Path, Dict[str, Any]],
    capsule_id: str = "photon_capsule",
    register: bool = True,
    render_scroll: bool = True,
) -> Dict[str, Any]:
    capsule = load_photon_capsule(path_or_dict)

    # Extract validation errors if schema had issues (kept for back-compat callers)
    validation_errors = capsule.pop("validation_errors", [])
    if validation_errors:
        # Normalize to v1 format if they aren't already
        if validation_errors and isinstance(validation_errors[0], str):
            validation_errors = [
                {"code": f"E{str(i+1).zfill(3)}", "message": msg}
                for i, msg in enumerate(validation_errors)
            ]

    glyphs = photon_capsule_to_glyphs(capsule)

    if register:
        register_photon_glyphs(glyphs, capsule_id=capsule_id)

    scroll = render_photon_scroll(glyphs) if render_scroll else None

    return {
        "glyphs": glyphs,
        "scroll": scroll,
        "engine": capsule.get("engine", "codex"),
        "name": capsule.get("name", "unnamed"),
        "validation_errors": validation_errors,
        "validation_errors_version": "v1",
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python photon_to_codex.py <capsule.phn>")
        sys.exit(1)

    capsule_path = sys.argv[1]
    result = photon_to_codex(capsule_path, capsule_id="cli_test")

    print("=== Photon -> Codex Bridge ===")
    print("Glyphs:")
    for g in result["glyphs"]:
        print(" ", g)
    print("\nScroll:")
    print(result["scroll"])
    if result["validation_errors"]:
        print("\nValidation Errors:")
        for err in result["validation_errors"]:
            print(f" - {err['code']}: {err['message']}")