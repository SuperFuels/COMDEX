# backend/modules/lean/lean_injector.py
import os
import sys
import json
from typing import Any, Dict, List
from backend.modules.lean.lean_inject_utils import normalize_logic_entry
from backend.modules.lean.lean_to_glyph import convert_lean_to_codexlang, emit_codexlang_glyph
from backend.modules.lean.lean_utils import (
    validate_logic_trees,
    inject_preview_and_links,
    normalize_codexlang,
    register_theorems,
    is_lean_universal_container_system,
)

def _rebuild_from_logic(container: Dict[str, Any], glyph_field: str, logic_field: str, tree_field: str) -> None:
    """Rebuild human-readable glyphs and thought_tree from symbolic_logic for consistency."""
    glyphs: List[str] = []
    thought_tree: List[Dict[str, Any]] = []

    for e in container.get(logic_field, []):
        sym = e.get("symbol", "⟦ Theorem ⟧")
        name = e.get("name", "?")
        logic = e.get("logic", "?")
        label = "Define" if "Definition" in sym else "Prove"
        glyphs.append(f"{sym} | {name} : {logic} → {label} ⟧")
        thought_tree.append({
            "name": name,
            "glyph": sym,
            "node": e.get("glyph_tree")
        })

    container[glyph_field] = glyphs
    container[tree_field] = thought_tree

def inject_theorems_into_container(
    container: Dict[str, Any],
    lean_path: str,
    *,
    overwrite: bool = True,
    auto_clean: bool = False,
    normalize: bool = False,   # 👈 new
) -> Dict[str, Any]:
    """
    Inject Lean theorems into a symbolic container (dc, SEC, Hoberman, Atom, Exotic, Symmetry, etc.).
    Supports overwrite-by-name to avoid duplicates. Optionally auto-cleans previews/links.
    Ensures logic fields are always valid non-empty strings.
    """
    parsed = convert_lean_to_codexlang(lean_path)

    # Choose insertion fields based on container type
    container_type = container.get("type", "unknown").lower()
    glyph_field = "glyphs"
    logic_field = "symbolic_logic"
    tree_field = "thought_tree"

    if "hoberman" in container_type:
        glyph_field = "hoberman_glyphs"
        logic_field = "hoberman_logic"
        tree_field = "hoberman_tree"
    elif "sec" in container_type or "expansion" in container_type:
        glyph_field = "expanded_glyphs"
        logic_field = "expanded_logic"
        tree_field = "expanded_tree"
    elif "atom" in container_type:
        glyph_field = "atoms"
        logic_field = "axioms"
        tree_field = "logic_map"
    elif "symmetry" in container_type:
        glyph_field = "symmetric_glyphs"
        logic_field = "symmetric_logic"
        tree_field = "symmetric_tree"
    elif "exotic" in container_type:
        glyph_field = "exotic_glyphs"
        logic_field = "exotic_logic"
        tree_field = "exotic_tree"

    container.setdefault(glyph_field, [])
    container.setdefault(logic_field, [])
    container.setdefault(tree_field, [])

    # Build name → index map for overwrite semantics
    name_to_idx = {
        e.get("name"): i
        for i, e in enumerate(container.get(logic_field, []))
        if e.get("name")
    }

    for decl in parsed.get("parsed_declarations", []):
        if normalize:
            # --- full CodexLang normalization ---
            logic_entry = normalize_logic_entry(decl, lean_path)
        else:
            # --- raw/pure mode: prefer CodexLang logic ---
            glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")
            name = decl.get("name") or "unnamed"

            codex = decl.get("codexlang", {}) or {}
            logic_str = decl.get("logic") or codex.get("logic") or "True"

            logic_entry = {
                "name": name,
                "symbol": glyph_symbol,
                "logic": logic_str,
                "logic_raw": logic_str,
                "codexlang": codex,
                "glyph_tree": decl.get("glyph_tree", {}),
                "source": lean_path,
                "body": decl.get("body", ""),
            }

        # --- injector-only extras ---
        lean_proof_snippet = (decl.get("body") or "").strip()
        logic_entry.update({
            "leanProof": lean_proof_snippet,
            "symbolicProof": logic_entry.get("logic"),
            "proofExplanation": logic_entry.get("codexlang", {}).get("explanation"),
            "replay_tags": ["📜 Lean Theorem", f"🧠 {logic_entry['symbol']}"],
        })

        # --- overwrite vs append ---
        if overwrite and logic_entry["name"] in name_to_idx:
            container[logic_field][name_to_idx[logic_entry["name"]]] = logic_entry
        else:
            container[logic_field].append(logic_entry)
            name_to_idx[logic_entry["name"]] = len(container[logic_field]) - 1

    # Keep glyphs/tree in sync with logic
    _rebuild_from_logic(container, glyph_field, logic_field, tree_field)

    # Optional logic post-processing / cleanup
    if auto_clean:
        normalize_codexlang(container)
        inject_preview_and_links(container)
        register_theorems(container)
        container["previews"] = []
        container["dependencies"] = []

    # Validation (non-fatal)
    errors = validate_logic_trees(container)
    if errors:
        print("⚠️  Logic validation errors:")
        for e in errors:
            print("  •", e)

    return container

def load_container(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Container not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_container(container: Dict[str, Any], path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(container, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # legacy direct usage still supported
    if len(sys.argv) < 3:
        print("Usage: python lean_injector.py <container.json> <theorems.lean>")
        sys.exit(1)
    container_path = sys.argv[1]
    lean_path = sys.argv[2]
    try:
        container = load_container(container_path)
        injected = inject_theorems_into_container(container, lean_path, overwrite=True, auto_clean=True)
        save_container(injected, container_path)
        print(f"[✅] Injected Lean theorems into {container_path}")
    except Exception as e:
        print(f"[❌] Error: {e}", file=sys.stderr)
        sys.exit(1)