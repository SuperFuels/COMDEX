# backend/modules/lean/lean_exporter.py
# -*- coding: utf-8 -*-
"""
Lean Exporter (real)
──────────────────────────────────────────────────────────────
Exports Lean → container JSON in the Tessaris container formats.

Fixes applied:
- Removed embedded “stub module” (move to lean_exporter_stub.py if you still need it)
- No always-on prints (gated by LEAN_DEBUG=1 or logging)
- Removed duplicate import of normalize_logic_entry
- Safer container id (hash + basename) to avoid collisions
"""

import os
import sys
import json
import argparse
import hashlib
import logging
from typing import Dict, Any

from backend.modules.lean.lean_inject_utils import normalize_logic_entry

# --- Imports with safe fallbacks ---------------------------------------------
try:
    from backend.modules.lean.lean_to_glyph import convert_lean_to_codexlang, emit_codexlang_glyph
except Exception:
    from backend.modules.lean.lean_to_glyph import convert_lean_to_codexlang  # type: ignore

    def emit_codexlang_glyph(node: Dict[str, Any], glyph_label: str = "⟦ Theorem ⟧") -> str:  # type: ignore
        name = node.get("name", "unknown")
        logic = node.get("logic", "???")
        return f"{glyph_label} | {name} : {logic} -> {'Define' if 'Definition' in glyph_label else 'Prove'} ⟧"

try:
    from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
except Exception:
    class CodexLangRewriter:  # type: ignore
        @staticmethod
        def simplify(expr: str, mode: str = "soft") -> str:
            return " ".join((expr or "").split())


logger = logging.getLogger(__name__)

# --- Container layout map -----------------------------------------------------
CONTAINER_MAP = {
    "dc": {
        "type": "dc_container",
        "glyph_field": "glyphs",
        "logic_field": "symbolic_logic",
        "tree_field": "thought_tree",
    },
    "hoberman": {
        "type": "hoberman_container",
        "glyph_field": "hoberman_glyphs",
        "logic_field": "hoberman_logic",
        "tree_field": "hoberman_tree",
    },
    "sec": {
        "type": "symbolic_expansion_container",
        "glyph_field": "expanded_glyphs",
        "logic_field": "expanded_logic",
        "tree_field": "expanded_tree",
    },
    "exotic": {
        "type": "exotic_container",
        "glyph_field": "exotic_glyphs",
        "logic_field": "exotic_logic",
        "tree_field": "exotic_tree",
    },
    "symmetry": {
        "type": "symmetry_container",
        "glyph_field": "symmetric_glyphs",
        "logic_field": "symmetric_logic",
        "tree_field": "symmetric_tree",
    },
    "atom": {
        "type": "atom_container",
        "glyph_field": "atoms",
        "logic_field": "axioms",
        "tree_field": "logic_map",
    },
}


def _debug(msg: str, *args: Any) -> None:
    if os.getenv("LEAN_DEBUG") == "1":
        logger.info(msg, *args)


def _safe_container_id(container_type: str, lean_path: str) -> str:
    h = hashlib.sha1((lean_path or "").encode("utf-8")).hexdigest()[:10]
    base = os.path.basename(lean_path or "in_memory.lean")
    return f"lean::{container_type}::{h}::{base}"


def _emit_preview(decl: Dict[str, Any], glyph_label: str) -> str:
    """
    Call project emit_codexlang_glyph if it supports (decl, label); else fall back.
    """
    try:
        return emit_codexlang_glyph(decl, glyph_label)  # type: ignore[arg-type]
    except TypeError:
        s = emit_codexlang_glyph(decl)  # type: ignore[call-arg]
        if glyph_label != "⟦ Theorem ⟧":
            parts = s.split("|", 1)
            if parts and parts[0].strip().startswith("⟦"):
                s = f"{glyph_label} | {parts[1]}" if len(parts) > 1 else s
        return s


def build_container_from_lean(lean_path: str, container_type: str) -> Dict[str, Any]:
    """
    Build a container dict from a Lean file.
    Uses shared normalize_logic_entry for consistency with injector.
    """
    spec = CONTAINER_MAP.get(container_type.lower(), CONTAINER_MAP["dc"])
    parsed = convert_lean_to_codexlang(lean_path)

    container: Dict[str, Any] = {
        "type": spec["type"],
        "id": _safe_container_id(container_type.lower(), lean_path),
        "metadata": {
            "origin": "lean_import",
            "source_path": parsed.get("source", lean_path),
            "logic_type": parsed.get("logic_type", "unknown"),
        },
        spec["glyph_field"]: [],
        spec["logic_field"]: [],
        spec["tree_field"]: [],
        "previews": [],
        "dependencies": [],
    }

    for decl in parsed.get("parsed_declarations", []):
        glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")

        # glyph list (human-readable)
        container[spec["glyph_field"]].append(_emit_preview(decl, glyph_symbol))

        # normalize into logic entry (shared helper)
        logic_entry = normalize_logic_entry(decl, lean_path)
        container[spec["logic_field"]].append(logic_entry)

        # tree entry
        container[spec["tree_field"]].append(
            {
                "name": logic_entry["name"],
                "glyph": logic_entry["symbol"],
                "node": logic_entry.get("glyph_tree", {}),
            }
        )

        # extras
        container["previews"].append(_emit_preview(decl, glyph_symbol))
        container["dependencies"].append(
            {"theorem": logic_entry["name"], "depends_on": decl.get("depends_on", [])}
        )

    _debug("[lean_exporter] Final container keys: %s", list(container.keys()))
    first_logic = container.get(spec["logic_field"], [])
    if first_logic:
        _debug("[lean_exporter] First logic entry: %s", first_logic[0])

    return container


# --- CLI ---------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export Lean file to glyph container")
    ap.add_argument("lean_file", help="Path to .lean file")
    ap.add_argument(
        "--container-type",
        "-t",
        default="dc",
        choices=list(CONTAINER_MAP.keys()),
        help="Target container layout (default: dc)",
    )
    ap.add_argument("--out", "-o", help="Write output JSON to this path (default: stdout)")
    ap.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    args = ap.parse_args(argv)

    try:
        container = build_container_from_lean(args.lean_file, args.container_type)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(container, f, indent=2 if args.pretty else None, ensure_ascii=False)
            print(f"[✅] Wrote container -> {args.out}")
        else:
            print(json.dumps(container, indent=2 if args.pretty else None, ensure_ascii=False))
        return 0
    except Exception as e:
        print(f"[❌] Failed to export Lean file: {e}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())