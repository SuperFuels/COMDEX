# backend/modules/lean/lean_injector.py
import os
import sys
import json
from typing import Any, Dict, List

from backend.modules.lean.lean_inject_utils import normalize_logic_entry, guess_spec
from backend.modules.lean.lean_to_glyph import convert_lean_to_codexlang
from backend.modules.lean.lean_utils import (
    validate_logic_trees,
    inject_preview_and_links,
    normalize_codexlang,
    register_theorems,
)


def _rebuild_from_logic(
    container: Dict[str, Any],
    glyph_field: str,
    logic_field: str,
    tree_field: str,
) -> None:
    """Rebuild human-readable glyphs + tree from the canonical logic list."""
    glyphs: List[str] = []
    tree: List[Dict[str, Any]] = []

    for e in container.get(logic_field, []):
        sym = e.get("symbol", "⟦ Theorem ⟧")
        name = e.get("name", "?")

        # Use normalized logic for UI glyph line (raw still stored separately)
        logic_norm = (
            e.get("logic")
            or e.get("codexlang", {}).get("normalized")
            or e.get("logic_raw")
            or "True"
        )

        label = "Define" if "Definition" in sym else "Prove"
        glyphs.append(f"{sym} | {name} : {logic_norm} -> {label} ⟧")

        tree.append(
            {
                "name": name,
                "glyph": sym,
                "node": e.get("glyph_tree", {}) or {},
            }
        )

    container[glyph_field] = glyphs
    container[tree_field] = tree


def inject_theorems_into_container(
    container: Dict[str, Any],
    lean_path: str,
    *,
    overwrite: bool = True,
    auto_clean: bool = False,
    normalize: bool = False,
) -> Dict[str, Any]:
    """
    Inject Lean theorems into a symbolic container.
    - Uses guess_spec() to select correct glyph/logic/tree fields.
    - Preserves raw vs normalized correctly:
        logic_raw = decl.logic_raw (or codexlang.logic)
        logic     = decl.logic     (or codexlang.normalized)
    - normalize=True uses normalize_logic_entry() (CodexLang soft simplify)
    """
    parsed = convert_lean_to_codexlang(lean_path)

    # ✅ use unified spec resolver (fixed in lean_inject_utils.py)
    try:
        spec = guess_spec(container)
    except Exception:
        # safe fallback if container has weird/missing type
        spec = guess_spec({"type": "dc_container"})

    glyph_field = spec["glyph_field"]
    logic_field = spec["logic_field"]
    tree_field = spec["tree_field"]

    container.setdefault(glyph_field, [])
    container.setdefault(logic_field, [])
    container.setdefault(tree_field, [])

    # Build name -> index map for overwrite semantics
    name_to_idx = {
        e.get("name"): i
        for i, e in enumerate(container.get(logic_field, []))
        if isinstance(e, dict) and e.get("name")
    }

    for decl in parsed.get("parsed_declarations", []):
        if normalize:
            # ✅ normalized entry (raw+norm handled correctly by normalize_logic_entry after our fix)
            logic_entry = normalize_logic_entry(decl, lean_path)
        else:
            # ✅ raw/pure mode: STILL preserve raw vs normalized correctly
            glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")
            name = decl.get("name") or "unnamed"

            codex = decl.get("codexlang", {}) or {}

            logic_raw = (
                decl.get("logic_raw")
                or codex.get("logic")
                or decl.get("codexlang_string")
                or decl.get("logic")
                or "True"
            )
            if not isinstance(logic_raw, str):
                logic_raw = str(logic_raw)

            logic_norm = (
                decl.get("logic")  # in your converter this is normalized_logic
                or codex.get("normalized")
                or logic_raw
            )
            if not isinstance(logic_norm, str):
                logic_norm = str(logic_norm)

            # ensure codexlang always has both keys
            if not isinstance(codex.get("logic"), str) or not codex.get("logic"):
                codex["logic"] = logic_raw
            if not isinstance(codex.get("normalized"), str) or not codex.get("normalized"):
                codex["normalized"] = logic_norm
            if "explanation" not in codex:
                codex["explanation"] = "Auto-converted from Lean source"

            logic_entry = {
                "name": name,
                "symbol": glyph_symbol,
                "logic": logic_norm,  # ✅ normalized
                "logic_raw": logic_raw,  # ✅ raw
                "codexlang": codex,
                "glyph_tree": decl.get("glyph_tree", {}) or {},
                "source": lean_path,
                "source_file": decl.get("source_file", lean_path),
                "line": decl.get("line", 0),
                "body": decl.get("body", ""),
                "hash": decl.get("hash"),
                "depends_on": decl.get("depends_on", []),
                "axioms_used": decl.get("axioms_used", []),
            }

        # --- injector-only extras (don’t overwrite raw/norm fields) ---
        lean_proof_snippet = (decl.get("body") or "").strip()
        logic_entry.update(
            {
                "leanProof": lean_proof_snippet,
                "symbolicProof": logic_entry.get("logic"),
                "proofExplanation": (logic_entry.get("codexlang") or {}).get("explanation"),
                "replay_tags": ["📜 Lean Theorem", f"🧠 {logic_entry.get('symbol','⟦ Theorem ⟧')}"],
            }
        )

        # --- overwrite vs append ---
        nm = logic_entry.get("name")
        if overwrite and nm in name_to_idx:
            container[logic_field][name_to_idx[nm]] = logic_entry
        else:
            container[logic_field].append(logic_entry)
            name_to_idx[nm] = len(container[logic_field]) - 1

    # Keep glyphs/tree in sync with logic
    _rebuild_from_logic(container, glyph_field, logic_field, tree_field)

    # Optional integrated post-processing / cleanup
    if auto_clean:
        # ✅ do NOT wipe previews/dependencies after generating them
        normalize_codexlang(container)
        inject_preview_and_links(container)
        register_theorems(container)

    # Validation (non-fatal) + attach to container
    errors = validate_logic_trees(container)
    container["validation_errors"] = errors or []
    container["validation_errors_version"] = "v1"

    if errors:
        print("⚠️  Logic validation errors:")
        for e in errors:
            print("  *", e)

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
        injected = inject_theorems_into_container(
            container,
            lean_path,
            overwrite=True,
            auto_clean=True,
            normalize=False,
        )
        save_container(injected, container_path)
        print(f"[✅] Injected Lean theorems into {container_path}")
    except Exception as e:
        print(f"[❌] Error: {e}", file=sys.stderr)
        sys.exit(1)