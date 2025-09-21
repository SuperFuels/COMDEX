"""
Photon → Codex Bridge
─────────────────────────────────────────────
Converts Photon Capsules (.phn JSON) into Codex structures:
- LogicGlyph objects
- Symbolic Registry entries
- Optional Codex scroll strings (for GHX/QFC replay)

This makes Photon capsules first-class citizens inside CodexCore.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Union

from backend.modules.codex.logic_tree import LogicGlyph
from backend.modules.codex.symbolic_registry import symbolic_registry

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
    """Validate capsule JSON with jsonschema if available."""
    if not _HAS_JSONSCHEMA:
        logger.debug("[PhotonBridge] jsonschema not installed; skipping validation")
        return
    try:
        jsonschema.validate(instance=data, schema=_CAPSULE_SCHEMA)  # type: ignore
    except Exception as e:
        raise ValueError(f"[PhotonBridge] Capsule validation failed: {e}") from e


# ──────────────────────────────
# Photon Capsule Loader
# ──────────────────────────────
def load_photon_capsule(path_or_dict: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Load a Photon capsule from path or dict and validate against schema.
    Handles legacy 'steps' and 'body' fields with auto-upgrade + warnings.
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
    # Legacy upgrade paths
    # ──────────────────────────────
    if "body" in capsule and "glyphs" not in capsule:
        logger.warning("[PhotonBridge] Legacy capsule with 'body' → migrated to 'glyphs'.")
        capsule["glyphs"] = capsule.pop("body")

    if "steps" in capsule and "glyphs" not in capsule:
        logger.warning("[PhotonBridge] Legacy capsule with 'steps' → auto-converted to 'glyphs'.")
        converted: List[Dict[str, Any]] = []
        for step in capsule.get("steps", []):
            converted.append({
                "name": step.get("value", "unknown"),
                "logic": step.get("value", ""),
                "operator": step.get("symbol", "⊕"),
                "args": step.get("args", []),
            })
        capsule["glyphs"] = converted
        capsule.pop("steps")

    # ✅ Schema validation (after migration)
    _validate_capsule(capsule)

    return capsule
    
    # ──────────────────────────────
    # Legacy compatibility upgrades
    # ──────────────────────────────
    if "steps" in capsule and "glyphs" not in capsule:
        logger.warning("[PhotonBridge] Legacy capsule with 'steps' → auto-converted to 'glyphs'.")
        capsule["glyphs"] = [
            {
                "name": s.get("value", "unknown"),
                "logic": s.get("value", ""),
                "operator": s.get("symbol"),
                "args": s.get("args", []),
                "meta": s.get("meta", {}),
            }
            for s in capsule.pop("steps", [])
        ]

    if "body" in capsule and "glyphs" not in capsule:
        logger.warning("[PhotonBridge] Non-schema field 'body' → migrated to 'glyphs'.")
        capsule["glyphs"] = [
            {
                "name": g.get("name", "unknown"),
                "logic": g.get("logic", ""),
                "operator": g.get("operator"),
                "args": g.get("args", []),
                "meta": g.get("meta", {}),
            }
            for g in capsule.pop("body", [])
        ]

    # ──────────────────────────────
    # Schema validation
    # ──────────────────────────────
    _validate_capsule(capsule)

    return capsule


# ──────────────────────────────
# Capsule → LogicGlyph Conversion
# ──────────────────────────────
def photon_capsule_to_glyphs(capsule: Dict[str, Any]) -> List[LogicGlyph]:
    """
    Convert Photon capsule JSON into LogicGlyph objects.
    Supports:
      • new capsules with "glyphs"
      • legacy capsules with "steps"/"body"
    """
    raw_items: List[Dict[str, Any]] = capsule.get("glyphs", [])

    glyphs: List[LogicGlyph] = []
    for item in raw_items:
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
    glyphs = photon_capsule_to_glyphs(capsule)

    if register:
        register_photon_glyphs(glyphs, capsule_id=capsule_id)

    scroll = render_photon_scroll(glyphs) if render_scroll else None

    return {
        "glyphs": glyphs,
        "scroll": scroll,
        "engine": capsule.get("engine", "codex"),
        "name": capsule.get("name", "unnamed"),
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python photon_to_codex.py <capsule.phn>")
        sys.exit(1)

    capsule_path = sys.argv[1]
    result = photon_to_codex(capsule_path, capsule_id="cli_test")

    print("=== Photon → Codex Bridge ===")
    print("Glyphs:")
    for g in result["glyphs"]:
        print(" ", g)
    print("\nScroll:")
    print(result["scroll"])