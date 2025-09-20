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
# Schema (hybrid: external JSON if present, else fallback)
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
                },
                "required": ["symbol"],
            },
        },
    },
    "anyOf": [
        {"required": ["glyphs"]},
        {"required": ["steps"]},
    ],
}


def _load_schema() -> Dict[str, Any]:
    schema_path = Path(__file__).parent / "photon_capsule_schema.json"
    if schema_path.exists():
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[PhotonBridge] Failed to load external schema: {e}")
    return _DEFAULT_SCHEMA


# ──────────────────────────────
# Photon Capsule Loader
# ──────────────────────────────
def load_photon_capsule(path_or_dict: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Load a Photon capsule from path or dict and validate against schema.
    """
    if isinstance(path_or_dict, (str, Path)):
        path = Path(path_or_dict)
        with open(path, "r", encoding="utf-8") as f:
            capsule = json.load(f)
    elif isinstance(path_or_dict, dict):
        capsule = path_or_dict
    else:
        raise TypeError(f"Unsupported capsule input: {type(path_or_dict)}")

    # Schema validation
    try:
        import jsonschema
        schema = _load_schema()
        jsonschema.validate(instance=capsule, schema=schema)
    except ImportError:
        logger.warning("[PhotonBridge] jsonschema not installed, skipping validation.")
    except Exception as e:
        raise ValueError(f"[PhotonBridge] Capsule validation failed: {e}")

    return capsule


# ──────────────────────────────
# Capsule → LogicGlyph Conversion
# ──────────────────────────────
def photon_capsule_to_glyphs(capsule: Dict[str, Any]) -> List[LogicGlyph]:
    """
    Convert Photon capsule JSON into LogicGlyph objects.
    Supports both:
      • new capsules with "glyphs"
      • legacy capsules with "steps"
    """
    raw_items: List[Dict[str, Any]] = []

    if "glyphs" in capsule:
        raw_items = capsule.get("glyphs", [])
    elif "steps" in capsule:
        logger.warning("[PhotonBridge] Legacy capsule format 'steps' detected — auto-upgrading.")
        for step in capsule.get("steps", []):
            raw_items.append({
                "name": step.get("value", "unknown"),
                "logic": step.get("value", ""),
                "operator": step.get("symbol", "⊕"),
                "args": step.get("args", []),
            })

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