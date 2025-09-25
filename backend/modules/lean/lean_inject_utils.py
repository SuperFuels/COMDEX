# backend/modules/lean/lean_inject_utils.py
from typing import Dict, Any, List


def guess_spec(container: Dict[str, Any]) -> Dict[str, str]:
    """Return field spec (glyph, logic, tree) for this container type."""
    t = (container.get("type") or "dc").lower()
    if t == "dc":
        return {"glyph_field": "glyphs", "logic_field": "logic", "tree_field": "tree"}
    if t == "hoberman":
        return {"glyph_field": "glyphs", "logic_field": "hoberman_logic", "tree_field": "tree"}
    if t == "sec":
        return {"glyph_field": "glyphs", "logic_field": "expanded_logic", "tree_field": "tree"}
    if t == "exotic":
        return {"glyph_field": "glyphs", "logic_field": "exotic_logic", "tree_field": "tree"}
    if t == "symmetry":
        return {"glyph_field": "glyphs", "logic_field": "symmetric_logic", "tree_field": "tree"}
    if t == "atom":
        return {"glyph_field": "glyphs", "logic_field": "axioms", "tree_field": "tree"}
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
    # drop empty arrays commonly ballooning
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
        previews.append(f"{sym} | {name} : {logic_str} → {label} ⟧")
    container["previews"] = previews


def normalize_logic_entry(decl: Dict[str, Any], lean_path: str) -> Dict[str, Any]:
    """
    Normalize a Lean declaration into a standard logic_entry dict.
    Guarantees codexlang/logic/normalized are always set.
    """
    glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")
    name = decl.get("name") or "unnamed"

    # --- codexlang dict (always safe) ---
    codexlang = decl.get("codexlang", {}) or {}

    # legacy shim: preserve codexlang_string if it exists
    if "codexlang_string" in decl and "legacy" not in codexlang:
        codexlang["legacy"] = decl["codexlang_string"]

    # ✅ prefer decl["logic"], then codexlang_string, then codexlang["logic"]
    logic_raw = (
        decl.get("logic")
        or codexlang.get("logic")
        or decl.get("codexlang_string")
        or ""
    )
    if not isinstance(logic_raw, str):
        logic_raw = str(logic_raw)

    # ensure codexlang dict has required keys
    if not codexlang.get("logic") or not isinstance(codexlang["logic"], str):
        codexlang["logic"] = logic_raw
    if not codexlang.get("normalized") or not isinstance(codexlang["normalized"], str):
        codexlang["normalized"] = logic_raw
    if "explanation" not in codexlang:
        codexlang["explanation"] = "Auto-converted from Lean source"

    # simplified / soft form
    try:
        from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
        logic_soft = CodexLangRewriter.simplify(logic_raw, mode="soft") or "True"
    except Exception:
        logic_soft = logic_raw

    return {
        "name": name,
        "symbol": glyph_symbol,
        "logic": logic_soft,
        "logic_raw": logic_raw,
        "codexlang": codexlang,
        "glyph_tree": decl.get("glyph_tree", {}),
        "source": lean_path,
        "body": decl.get("body", ""),
    }