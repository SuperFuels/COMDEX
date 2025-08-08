# backend/modules/lean/lean_exporter.py

import sys
import json
import argparse
from typing import Dict, Any

# --- Imports with safe fallbacks ---------------------------------------------
try:
    from backend.modules.lean.lean_to_glyph import convert_lean_to_codexlang, emit_codexlang_glyph
except Exception:
    # Minimal fallback if emit/import paths shift; convert_lean_to_codexlang must exist though.
    from backend.modules.lean.lean_to_glyph import convert_lean_to_codexlang  # type: ignore

    def emit_codexlang_glyph(node: Dict[str, Any], glyph_label: str = "⟦ Theorem ⟧") -> str:  # type: ignore
        name = node.get("name", "unknown")
        logic = node.get("logic", "???")
        # Match the project’s preview conventions with explicit label
        return f"{glyph_label} | {name} : {logic} → {'Define' if 'Definition' in glyph_label else 'Prove'} ⟧"

try:
    from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
except Exception:
    # Soft shim if rewriter module isn’t present; preserves interface
    class CodexLangRewriter:  # type: ignore
        @staticmethod
        def simplify(expr: str, mode: str = "soft") -> str:
            # very soft: trim whitespace only
            return " ".join((expr or "").split())


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


# --- Helpers -----------------------------------------------------------------
def _emit_preview(node: Dict[str, Any], glyph_label: str) -> str:
    """
    Call project emit_codexlang_glyph if it supports (node, label); else fall back.
    """
    try:
        # Preferred: new signature (node, glyph_label)
        return emit_codexlang_glyph(node, glyph_label)  # type: ignore[arg-type]
    except TypeError:
        # Legacy: emit(node) without label
        # If legacy returns "⟦ Theorem | name : logic → Prove ⟧", we rewrite the label if needed.
        s = emit_codexlang_glyph(node)  # type: ignore[call-arg]
        if glyph_label != "⟦ Theorem ⟧":
            # replace leading label only
            parts = s.split("|", 1)
            if parts and parts[0].strip().startswith("⟦"):
                s = f"{glyph_label} | {parts[1]}" if len(parts) > 1 else s
        return s


def build_container_from_lean(lean_path: str, container_type: str) -> Dict[str, Any]:
    spec = CONTAINER_MAP.get(container_type.lower(), CONTAINER_MAP["dc"])
    parsed = convert_lean_to_codexlang(lean_path)

    container: Dict[str, Any] = {
        "type": spec["type"],
        "id": f"lean::{container_type}::{lean_path.split('/')[-1]}",
        "metadata": {
            "origin": "lean_import",
            "source_path": parsed["source"],
            "logic_type": parsed["logic_type"],
        },
        spec["glyph_field"]: [],
        spec["logic_field"]: [],
        spec["tree_field"]: [],
        "previews": [],
        "dependencies": [],
    }

    for decl in parsed["parsed_declarations"]:
        glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")

        # glyph list (human-readable)
        container[spec["glyph_field"]].append(_emit_preview(decl["codexlang"], glyph_symbol))

        # logic entries (keep both raw & normalized for UI choice)
        logic_raw = decl["codexlang"]["logic"]
        logic_soft = CodexLangRewriter.simplify(logic_raw, mode="soft")

        container[spec["logic_field"]].append({
            "name": decl["name"],
            "symbol": glyph_symbol,
            "logic": logic_soft,           # normalized/soft view
            "logic_raw": logic_raw,        # raw original, no info loss
            "codexlang": decl["codexlang"],
            "glyph_tree": decl["glyph_tree"],
            "source": lean_path,
            "body": decl.get("body", ""),
        })

        # tree
        container[spec["tree_field"]].append({
            "name": decl["name"],
            "glyph": glyph_symbol,
            "node": decl["glyph_tree"],
        })

        # extras
        container["previews"].append(_emit_preview(decl["codexlang"], glyph_symbol))
        container["dependencies"].append({
            "theorem": decl["name"],
            "depends_on": decl["depends_on"],
        })

    return container


# --- CLI ---------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Export Lean file to glyph container")
    ap.add_argument("lean_file", help="Path to .lean file")
    ap.add_argument(
        "--container-type",
        "-t",
        default="dc",
        choices=list(CONTAINER_MAP.keys()),
        help="Target container layout (default: dc)",
    )
    args = ap.parse_args()

    try:
        container = build_container_from_lean(args.lean_file, args.container_type)
        print(json.dumps(container, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[❌] Failed to convert Lean file: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()