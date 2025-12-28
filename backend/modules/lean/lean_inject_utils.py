# backend/modules/lean/lean_inject_utils.py

from typing import Dict, Any, List


def guess_spec(container: Dict[str, Any]) -> Dict[str, str]:
    """
    Return field spec (glyph_field, logic_field, tree_field) for this container type.

    Supports both short names (dc/sec/...) and your actual exported types
    (dc_container, hoberman_container, symbolic_expansion_container, ...).
    """
    t = (container.get("type") or "dc").lower().strip()

    # accept both short + long type names
    if t in ("dc", "dc_container"):
        return {
            "glyph_field": "glyphs",
            "logic_field": "symbolic_logic",
            "tree_field": "thought_tree",
        }

    if t in ("hoberman", "hoberman_container"):
        return {
            "glyph_field": "hoberman_glyphs",
            "logic_field": "hoberman_logic",
            "tree_field": "hoberman_tree",
        }

    if t in ("sec", "symbolic_expansion_container"):
        return {
            "glyph_field": "expanded_glyphs",
            "logic_field": "expanded_logic",
            "tree_field": "expanded_tree",
        }

    if t in ("exotic", "exotic_container"):
        return {
            "glyph_field": "exotic_glyphs",
            "logic_field": "exotic_logic",
            "tree_field": "exotic_tree",
        }

    if t in ("symmetry", "symmetry_container"):
        return {
            "glyph_field": "symmetric_glyphs",
            "logic_field": "symmetric_logic",
            "tree_field": "symmetric_tree",
        }

    if t in ("atom", "atom_container"):
        return {
            "glyph_field": "atoms",
            "logic_field": "axioms",
            "tree_field": "logic_map",
        }

    raise ValueError(f"Unknown container type: {t}")


def auto_clean(container: Dict[str, Any], spec: Dict[str, str]) -> None:
    """Trim duplicates and empties in glyphs/previews/dependencies."""
    for key in ("glyphs", "previews"):
        if key in container and isinstance(container[key], list):
            seen = set()
            deduped: List[Any] = []
            for x in container[key]:
                if x not in seen:
                    seen.add(x)
                    deduped.append(x)
            container[key] = deduped
    for key in ("dependencies",):
        if key in container and not container[key]:
            del container[key]


def dedupe_by_name(container: Dict[str, Any], spec: Dict[str, str]) -> None:
    """Remove duplicate entries in logic field by name."""
    logic_field = spec["logic_field"]
    if logic_field not in container or not isinstance(container[logic_field], list):
        return
    seen = set()
    unique = []
    for it in container[logic_field]:
        name = it.get("name")
        if name and name not in seen:
            seen.add(name)
            unique.append(it)
    container[logic_field] = unique


def rebuild_previews(container: Dict[str, Any], spec: Dict[str, str], mode: str = "raw") -> None:
    """Rebuild preview strings for logic entries."""
    logic_field = spec["logic_field"]
    items = container.get(logic_field, [])
    previews = []
    for it in items:
        name = it.get("name", "unknown")
        sym = it.get("symbol", "⟦?⟧")
        if mode == "raw":
            logic_str = (
                it.get("logic_raw")
                or it.get("codexlang", {}).get("logic")
                or it.get("logic")
                or "???"
            )
        else:
            logic_str = (
                it.get("logic")
                or it.get("logic_raw")
                or it.get("codexlang", {}).get("logic")
                or "???"
            )
        label = "Define" if "Definition" in sym else "Prove"
        previews.append(f"{sym} | {name} : {logic_str} -> {label} ⟧")
    container["previews"] = previews


def normalize_logic_entry(decl: Dict[str, Any], lean_path: str) -> Dict[str, Any]:
    """
    Normalize a Lean declaration into a standard logic_entry dict.
    Guarantees:
      - logic_raw is truly raw (prefer decl['logic_raw'])
      - logic is normalized/usable (prefer decl['codexlang']['normalized'] or decl['logic'])
      - codexlang['logic'] + codexlang['normalized'] always present
    """
    glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")
    name = decl.get("name") or "unnamed"

    codexlang = (decl.get("codexlang") or {}) if isinstance(decl.get("codexlang"), dict) else {}

    # --- raw vs normalized (IMPORTANT) ---
    logic_raw = (
        decl.get("logic_raw")
        or codexlang.get("logic")
        or decl.get("codexlang_string")
        or decl.get("logic")
        or ""
    )
    if not isinstance(logic_raw, str):
        logic_raw = str(logic_raw)

    logic_norm = (
        codexlang.get("normalized")
        or decl.get("logic")          # in your lean_to_glyph this is already normalized_logic
        or logic_raw
    )
    if not isinstance(logic_norm, str):
        logic_norm = str(logic_norm)

    # legacy shim: preserve codexlang_string if it exists
    if "codexlang_string" in decl and "legacy" not in codexlang:
        codexlang["legacy"] = decl["codexlang_string"]

    # ensure codexlang dict has required keys
    if not isinstance(codexlang.get("logic"), str) or not codexlang.get("logic"):
        codexlang["logic"] = logic_raw
    if not isinstance(codexlang.get("normalized"), str) or not codexlang.get("normalized"):
        codexlang["normalized"] = logic_norm
    if "explanation" not in codexlang:
        codexlang["explanation"] = "Auto-converted from Lean source"

    # simplified / soft form should be based on normalized logic (not raw)
    try:
        from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
        logic_soft = CodexLangRewriter.simplify(logic_norm, mode="soft") or logic_norm or "True"
    except Exception:
        logic_soft = logic_norm or logic_raw

    return {
        "name": name,
        "symbol": glyph_symbol,

        # normalized primary string used by the rest of the stack
        "logic": logic_soft,

        # raw preserved for audit/diffs
        "logic_raw": logic_raw,

        "codexlang": codexlang,
        "glyph_tree": decl.get("glyph_tree", {}),
        "source": lean_path,
        "source_file": decl.get("source_file", lean_path),
        "line": decl.get("line", 0),
        "body": decl.get("body", ""),

        # carry-through fields if present (don’t lose metadata)
        "hash": decl.get("hash"),
        "depends_on": decl.get("depends_on", []),
        "axioms_used": decl.get("axioms_used", []),
    }