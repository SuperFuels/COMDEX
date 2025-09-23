# backend/modules/lean/lean_exporter.py

import sys
import json
import argparse
from typing import Dict, Any
from backend.modules.lean.lean_inject_utils import normalize_logic_entry
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
def _emit_preview(decl: Dict[str, Any], glyph_label: str) -> str:
    """
    Call project emit_codexlang_glyph if it supports (decl, label); else fall back.
    """
    try:
        # Preferred: new signature (decl, glyph_label)
        return emit_codexlang_glyph(decl, glyph_label)  # type: ignore[arg-type]
    except TypeError:
        # Legacy: emit(decl) without label
        s = emit_codexlang_glyph(decl)  # type: ignore[call-arg]
        if glyph_label != "⟦ Theorem ⟧":
            # replace leading label only
            parts = s.split("|", 1)
            if parts and parts[0].strip().startswith("⟦"):
                s = f"{glyph_label} | {parts[1]}" if len(parts) > 1 else s
        return s


import traceback

from backend.modules.lean.lean_inject_utils import normalize_logic_entry


def build_container_from_lean(lean_path: str, container_type: str) -> Dict[str, Any]:
    """
    Build a container dict from a Lean file.
    Ensures all logic/name fields are valid non-empty strings.
    Adds backwards-compatibility for legacy `codexlang_string`.
    Guarantees codexlang['logic'] and codexlang['normalized'] are always set.
    Uses shared _normalize_logic_entry for consistency with injector.
    """
    spec = CONTAINER_MAP.get(container_type.lower(), CONTAINER_MAP["dc"])
    parsed = convert_lean_to_codexlang(lean_path)

    try:
        container: Dict[str, Any] = {
            "type": spec["type"],
            "id": f"lean::{container_type}::{lean_path.split('/')[-1]}",
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
            container[spec["tree_field"]].append({
                "name": logic_entry["name"],
                "glyph": logic_entry["symbol"],
                "node": logic_entry.get("glyph_tree", {}),
            })

            # extras
            container["previews"].append(_emit_preview(decl, glyph_symbol))
            container["dependencies"].append({
                "theorem": logic_entry["name"],
                "depends_on": decl.get("depends_on", []),
            })

        # 🔎 Debug output for smoke test failures
        print("[DEBUG] Final container keys:", list(container.keys()))
        first_logic = container.get(spec["logic_field"], [None])
        if first_logic:
            print("[DEBUG] First logic entry:", first_logic[0])

        return container

    except Exception as e:
        print("[DEBUG] build_container_from_lean failed:", e)
        traceback.print_exc()
        raise


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
    ap.add_argument(
        "--out", "-o",
        help="Write output JSON to this path (default: print to stdout)",
    )
    args = ap.parse_args()

    try:
        container = build_container_from_lean(args.lean_file, args.container_type)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(container, f, indent=2, ensure_ascii=False)
            print(f"[✅] Wrote container → {args.out}")
        else:
            print(json.dumps(container, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[❌] Failed to convert Lean file: {e}")
        sys.exit(2)


if __name__ == "__main__":
    main()