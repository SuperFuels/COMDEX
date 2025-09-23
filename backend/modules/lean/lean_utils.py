# File: backend/modules/lean/lean_utils.py

import json
from typing import Dict, Any, List, Union

# --- LogicGlyph: use your real path (symbolic_engine/symbolic_kernels) ---
from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph

# --- CodexLangRewriter: point to symbolic_engine version, fall back safely ---
try:
    from backend.modules.symbolic_engine.codexlang_rewriter import CodexLangRewriter  # preferred
except Exception:
    # Minimal fallback shim if rewriter isn't available
    class CodexLangRewriter:  # type: ignore
        @staticmethod
        def simplify(text: str) -> str:
            return text

# --- Symbolic registry: prefer codex.symbolic_registry, else fallback to hexcore or local shim ---
symbolic_registry = None
try:
    from backend.modules.codex.symbolic_registry import symbolic_registry as _symreg  # type: ignore
    symbolic_registry = _symreg
except Exception:
    try:
        from backend.modules.hexcore.agent_memory import symbolic_registry as _symreg_hex  # if you have one there
        symbolic_registry = _symreg_hex
    except Exception:
        class _LocalSymbolicRegistry:
            def __init__(self):
                self._store = {}
            def register(self, name: str, payload: Any):
                self._store[name] = payload
            def get(self, name: str):
                return self._store.get(name)
        symbolic_registry = _LocalSymbolicRegistry()


# ----------------------------------------------------
# Lean container + metadata helpers
# ----------------------------------------------------
def is_lean_container(container: Dict[str, Any]) -> bool:
    return container.get("metadata", {}).get("origin") == "lean_import"


def is_lean_universal_container_system(obj: Any) -> bool:
    """
    Detects if the provided object is a Lean-compatible UCS (Universal Container System).
    """
    try:
        if hasattr(obj, "is_lean") and getattr(obj, "is_lean"):
            return True
        if isinstance(obj, dict):
            meta = obj.get("metadata", {})
            if meta.get("origin") == "lean_import" or meta.get("type", "").lower() in {
                "lean_container", "dc_container", "symbolic_expansion_container",
                "hoberman_container", "exotic_container", "symmetry_container", "atom_container"
            }:
                return True
        obj_type = type(obj).__name__.lower()
        return "lean" in obj_type or "ucs" in obj_type
    except Exception:
        return False


def extract_theorems(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    return container.get("symbolic_logic", [])


def extract_lean_metadata(container: Dict[str, Any]) -> Dict[str, Any]:
    meta = container.get("metadata", {})
    return {
        "origin": meta.get("origin"),
        "logic_type": meta.get("logic_type"),
        "source_path": meta.get("source_path")
    }


# ----------------------------------------------------
# Name + summary helpers
# ----------------------------------------------------
def get_theorem_names(container: Dict[str, Any]) -> List[str]:
    logic = extract_theorems(container)
    return [entry.get("name") for entry in logic if entry.get("symbol") == "⟦ Theorem ⟧"]


def summarize_lean_container(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a compact summary of a Lean container's logic structure.
    Includes per-kind counts (theorem/lemma/def/axiom/constant).
    """
    logic = extract_theorems(container)
    counts = {"theorems": 0, "lemmas": 0, "defs": 0, "axioms": 0, "constants": 0}
    names = {"theorems": [], "lemmas": [], "defs": [], "axioms": [], "constants": []}

    for e in logic:
        sym = e.get("symbol", "")
        nm = e.get("name", "?")
        if sym == "⟦ Theorem ⟧":
            counts["theorems"] += 1
            names["theorems"].append(nm)
        elif sym == "⟦ Lemma ⟧":
            counts["lemmas"] += 1
            names["lemmas"].append(nm)
        elif sym == "⟦ Definition ⟧":
            counts["defs"] += 1
            names["defs"].append(nm)
        elif sym == "⟦ Axiom ⟧":
            counts["axioms"] += 1
            names["axioms"].append(nm)
        elif sym == "⟦ Constant ⟧":
            counts["constants"] += 1
            names["constants"].append(nm)

    return {
        "is_lean": is_lean_container(container),
        "source_path": container.get("metadata", {}).get("source_path"),
        "counts": counts,
        "names": names,
    }


def pretty_print_lean_summary(container: Dict[str, Any]) -> None:
    summary = summarize_lean_container(container)
    print("\n📦 Lean Container Summary:")
    print(json.dumps(summary, indent=2))


# ----------------------------------------------------
# Validation + normalization
# ----------------------------------------------------
def validate_logic_trees(container: Dict[str, Any]) -> List[str]:
    errors = []
    logic_entries = container.get("symbolic_logic", [])

    allowed_types = {
        "ImplicationGlyph", "AndGlyph", "OrGlyph", "NotGlyph",
        "TrueGlyph", "FalseGlyph", "ProvableGlyph", "EntailmentGlyph",
        "SequentGlyph", "ProofStepGlyph", "SymbolGlyph"
    }

    for entry in logic_entries:
        name = entry.get("name", "???")
        node = entry.get("glyph_tree") or entry
        try:
            if isinstance(node, dict) and node.get("type") in allowed_types:
                _ = LogicGlyph.from_dict(node)  # smoke test
            else:
                logic = entry.get("logic") or entry.get("codexlang", {}).get("logic")
                if not isinstance(logic, str) or not logic.strip():
                    raise ValueError("missing or non-string 'logic'")
        except Exception as e:
            errors.append(f"❌ Theorem `{name}`: {e}")

    return errors


def normalize_codexlang(container: Dict[str, Any]) -> None:
    for entry in container.get("symbolic_logic", []):
        logic = entry.get("logic", "") or ""
        codex = entry.get("codexlang", {}) or {}
        try:
            simplify = getattr(CodexLangRewriter, "simplify", None)
            simplified = simplify(logic) if callable(simplify) else CodexLangRewriter().simplify(logic)  # type: ignore
            entry["logic"] = simplified
            if isinstance(codex, dict):
                codex["logic"] = simplified
                entry["codexlang"] = codex
        except Exception:
            pass


def inject_preview_and_links(container: Dict[str, Any]) -> None:
    logic_list = container.get("symbolic_logic", [])
    name_map = {entry.get("name"): entry for entry in logic_list}

    for entry in logic_list:
        try:
            codex = entry.get("codexlang", {}) or {}
            glyph_symbol = codex.get("symbol") or entry.get("symbol") or "⟦ Theorem ⟧"
            entry["symbol"] = glyph_symbol

            logic = codex.get("logic") or entry.get("logic", "")
            name = entry.get("name", "")

            # label mapping
            if glyph_symbol == "⟦ Definition ⟧":
                label = "Define"
            elif glyph_symbol in ("⟦ Axiom ⟧", "⟦ Constant ⟧"):
                label = "Assume"
            else:
                label = "Prove"

            entry["preview"] = f"{glyph_symbol} | {name} : {logic} ⟧"
            if not entry.get("glyph_string"):
                entry["glyph_string"] = f"{glyph_symbol} | {name} : {logic} → {label} ⟧"

            # depends_on backlinks (body + logic)
            deps: List[str] = []
            for text in [entry.get("body", ""), logic]:
                for other_name in name_map:
                    if other_name and other_name != name and other_name in (text or ""):
                        deps.append(other_name)
            entry["depends_on"] = list(sorted(set(deps)))

            # adjust args type in codexlang
            args = codex.get("args")
            if isinstance(args, list) and len(args) >= 2 and isinstance(args[1], dict):
                if glyph_symbol == "⟦ Definition ⟧":
                    args[1]["type"] = "Definition"
                elif glyph_symbol in ("⟦ Axiom ⟧", "⟦ Constant ⟧"):
                    args[1]["type"] = "Assumption"
                else:
                    args[1]["type"] = "Proof"

            entry["logic"] = logic
        except Exception:
            continue


def harmonize_symbols_and_trees(container: Dict[str, Any]) -> None:
    logic_list = container.get("symbolic_logic", [])
    glyph_by_name: Dict[str, Any] = {}
    for e in logic_list:
        try:
            name = e.get("name", "")
            gsym = (e.get("codexlang", {}) or {}).get("symbol") or e.get("symbol") or "⟦ Theorem ⟧"
            logic = (e.get("codexlang", {}) or {}).get("logic") or e.get("logic", "")
            if name:
                glyph_by_name[name] = (gsym, logic)
        except Exception:
            continue

    tree = container.get("thought_tree", [])
    fixed: List[Dict[str, Any]] = []
    seen = set()
    for node_entry in tree:
        try:
            name = node_entry.get("name", "")
            node = node_entry.get("node")
            glyph = node_entry.get("glyph") or "⟦ Theorem ⟧"

            gsym, logic = glyph_by_name.get(name, (glyph, None))
            node_entry["glyph"] = gsym

            if isinstance(node, dict):
                args = node.get("args")
                if isinstance(args, list) and len(args) >= 2 and isinstance(args[1], dict):
                    if gsym == "⟦ Definition ⟧":
                        args[1]["type"] = "Definition"
                    elif gsym in ("⟦ Axiom ⟧", "⟦ Constant ⟧"):
                        args[1]["type"] = "Assumption"
                    else:
                        args[1]["type"] = "Proof"

            sig = (name, node_entry["glyph"], logic or "")
            if sig in seen:
                continue
            seen.add(sig)
            fixed.append(node_entry)
        except Exception:
            fixed.append(node_entry)

    container["thought_tree"] = fixed


def register_theorems(container: Dict[str, Any]) -> None:
    for entry in container.get("symbolic_logic", []):
        try:
            name = entry.get("name")
            if name:
                symbolic_registry.register(name, {
                    "entry": entry,
                    "kind": entry.get("symbol")
                })
        except Exception:
            continue

from typing import Dict, Any
try:
    from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
except Exception:
    class CodexLangRewriter:  # soft shim
        @staticmethod
        def simplify(expr: str, mode: str = "soft") -> str:
            return " ".join((expr or "").split())


def _normalize_logic_entry(decl: Dict[str, Any], lean_path: str) -> Dict[str, Any]:
    """
    Normalize a Lean declaration into a logic entry with safe codexlang dict.
    Ensures:
      - codexlang is always a dict
      - codexlang['logic'] and codexlang['normalized'] are set
      - logic_raw always falls back to a non-empty string
    """
    glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")
    name = decl.get("name") or "unnamed"

    # --- codexlang dict (always safe) ---
    codexlang = decl.get("codexlang", {}) or {}

    # legacy shim
    if "codexlang_string" in decl and "legacy" not in codexlang:
        codexlang["legacy"] = decl["codexlang_string"]

    # logic_raw with full fallback chain
    logic_raw = (
        codexlang.get("logic")
        or decl.get("codexlang_string")
        or decl.get("logic", "")
    )
    if not logic_raw or not isinstance(logic_raw, str):
        logic_raw = "True"

    # ensure codexlang dict has required keys
    if not codexlang.get("logic") or not isinstance(codexlang["logic"], str):
        codexlang["logic"] = logic_raw
    if not codexlang.get("normalized") or not isinstance(codexlang["normalized"], str):
        codexlang["normalized"] = logic_raw
    if "explanation" not in codexlang:
        codexlang["explanation"] = "Auto-converted from Lean source"

    # soft-normalized version
    logic_soft = CodexLangRewriter.simplify(logic_raw, mode="soft") or "True"

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