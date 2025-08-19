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


def is_lean_container(container: Dict[str, Any]) -> bool:
    """
    Returns True if the container was imported from a Lean .lean file.
    """
    return container.get("metadata", {}).get("origin") == "lean_import"


def is_lean_universal_container_system(obj: Any) -> bool:
    """
    Detects if the provided object is a Lean-compatible UCS (Universal Container System).
    Supports:
      • UCS runtime/state objects
      • dict containers (with Lean origin metadata)
      • Types marked with Lean-related attributes
    """
    try:
        # Attribute-based detection
        if hasattr(obj, "is_lean") and getattr(obj, "is_lean"):
            return True

        # Check dict metadata (for loaded containers)
        if isinstance(obj, dict):
            meta = obj.get("metadata", {})
            if meta.get("origin") == "lean_import" or meta.get("type", "").lower() in {
                "lean_container", "dc_container", "symbolic_expansion_container",
                "hoberman_container", "exotic_container", "symmetry_container", "atom_container"
            }:
                return True

        # Type name heuristic
        obj_type = type(obj).__name__.lower()
        return "lean" in obj_type or "ucs" in obj_type

    except Exception:
        return False


def extract_theorems(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns a list of all symbolic theorems from the container.
    """
    return container.get("symbolic_logic", [])


def extract_lean_metadata(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns Lean-specific metadata fields from the container, if present.
    """
    meta = container.get("metadata", {})
    return {
        "origin": meta.get("origin"),
        "logic_type": meta.get("logic_type"),
        "source_path": meta.get("source_path")
    }


def get_theorem_names(container: Dict[str, Any]) -> List[str]:
    """
    Returns a list of theorem names in the container.
    """
    logic = extract_theorems(container)
    return [entry.get("name") for entry in logic if entry.get("symbol") == "⟦ Theorem ⟧"]


def summarize_lean_container(container: Dict[str, Any]) -> Dict[str, Any]:
    """
    Returns a compact summary of a Lean container's logic structure.
    """
    return {
        "is_lean": is_lean_container(container),
        "source_path": container.get("metadata", {}).get("source_path"),
        "num_theorems": len(get_theorem_names(container)),
        "theorems": get_theorem_names(container)
    }


def pretty_print_lean_summary(container: Dict[str, Any]) -> None:
    """
    Prints a human-readable summary of Lean container contents.
    """
    summary = summarize_lean_container(container)
    print("\n📦 Lean Container Summary:")
    print(json.dumps(summary, indent=2))


def validate_logic_trees(container: Dict[str, Any]) -> List[str]:
    """
    Validates symbolic_logic entries. If glyph_tree is a fallback (type=='LogicGlyph'),
    don't try to reconstruct; just check basic structure.
    """
    errors = []
    logic_entries = container.get("symbolic_logic", [])

    # Allowed concrete glyph class names your from_dict understands:
    allowed_types = {
        "ImplicationGlyph", "AndGlyph", "OrGlyph", "NotGlyph",
        "TrueGlyph", "FalseGlyph", "ProvableGlyph", "EntailmentGlyph",
        "SequentGlyph", "ProofStepGlyph", "SymbolGlyph"
    }

    for entry in logic_entries:
        name = entry.get("name", "???")
        node = entry.get("glyph_tree") or entry  # prefer glyph_tree if present

        try:
            # If it's a real glyph dict and has a known type, reconstruct.
            if isinstance(node, dict) and node.get("type") in allowed_types:
                # Safe to try reconstruct
                _ = LogicGlyph.from_dict(node)  # smoke test
            else:
                # Fallback path: just ensure 'logic' exists and is a string
                logic = entry.get("logic") or entry.get("codexlang", {}).get("logic")
                if not isinstance(logic, str) or not logic.strip():
                    raise ValueError("missing or non-string 'logic'")
        except Exception as e:
            errors.append(f"❌ Theorem `{name}`: {e}")

    return errors


def normalize_codexlang(container: Dict[str, Any]) -> None:
    """
    Normalize all logic entries using CodexLangRewriter.
    In-place updates `logic` and `codexlang.logic` fields of each theorem.
    """
    for entry in container.get("symbolic_logic", []):
        logic = entry.get("logic", "") or ""
        codex = entry.get("codexlang", {}) or {}

        try:
            simplify = getattr(CodexLangRewriter, "simplify", None)
            if callable(simplify):
                simplified = simplify(logic)
            else:
                simplified = CodexLangRewriter().simplify(logic)  # type: ignore

            # Update both `logic` and `codexlang.logic`
            entry["logic"] = simplified
            if isinstance(codex, dict):
                codex["logic"] = simplified
                entry["codexlang"] = codex
        except Exception:
            # Best-effort; leave original logic if normalization fails
            pass


def inject_preview_and_links(container: Dict[str, Any]) -> None:
    """
    Adds CodexLang preview strings, glyph_string fallback, cross-linking, and
    harmonizes symbol vs codexlang.symbol across entries.
    """
    logic_list = container.get("symbolic_logic", [])
    name_map = {entry.get("name"): entry for entry in logic_list}

    for entry in logic_list:
        try:
            codex = entry.get("codexlang", {}) or {}
            # prefer codexlang.symbol; fall back to entry.symbol; default Theorem
            glyph_symbol = codex.get("symbol") or entry.get("symbol") or "⟦ Theorem ⟧"
            entry["symbol"] = glyph_symbol  # sync outer symbol

            logic = codex.get("logic") or entry.get("logic", "")
            name = entry.get("name", "")

            # label: Define for definitions, Prove otherwise
            label = "Define" if glyph_symbol == "⟦ Definition ⟧" else "Prove"

            # preview (short; no arrow tail)
            entry["preview"] = f"{glyph_symbol} | {name} : {logic} ⟧"

            # glyph_string (verbose; with arrow tail)
            if not entry.get("glyph_string"):
                entry["glyph_string"] = f"{glyph_symbol} | {name} : {logic} → {label} ⟧"

            # depends_on backlinks based on body mentions
            deps: List[str] = []
            body_text = entry.get("body", "") or ""
            for other_name in name_map:
                if other_name and other_name != name and other_name in body_text:
                    deps.append(other_name)
            entry["depends_on"] = deps

            # ensure codexlang.args[1].type matches glyph (Proof vs Definition)
            args = codex.get("args")
            if isinstance(args, list) and len(args) >= 2 and isinstance(args[1], dict):
                args[1]["type"] = "Definition" if glyph_symbol == "⟦ Definition ⟧" else "Proof"

            # keep a plain 'logic' mirror for convenience/legacy
            entry["logic"] = logic

        except Exception:
            continue


def harmonize_symbols_and_trees(container: Dict[str, Any]) -> None:
    """
    Keep symbol, codexlang.symbol, preview/glyph_string, and tree glyphs consistent.
    Also de-duplicate thought_tree entries by (name, glyph, logic) signature.
    """
    logic_list = container.get("symbolic_logic", [])
    # Build lookup by name → (glyph_symbol, logic)
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

    # Fix thought_tree glyphs + arg[1] type; remove duplicates
    tree = container.get("thought_tree", [])
    fixed: List[Dict[str, Any]] = []
    seen = set()
    for node_entry in tree:
        try:
            name = node_entry.get("name", "")
            node = node_entry.get("node")
            glyph = node_entry.get("glyph") or "⟦ Theorem ⟧"

            gsym, logic = glyph_by_name.get(name, (glyph, None))
            node_entry["glyph"] = gsym  # sync glyph to symbols from logic_list

            # Adjust the node's second arg type for Definition glyphs; Proof otherwise
            if isinstance(node, dict):
                args = node.get("args")
                if isinstance(args, list) and len(args) >= 2 and isinstance(args[1], dict):
                    args[1]["type"] = "Definition" if gsym == "⟦ Definition ⟧" else "Proof"

            sig = (name, node_entry["glyph"], logic or "")
            if sig in seen:
                continue  # drop duplicate
            seen.add(sig)
            fixed.append(node_entry)
        except Exception:
            fixed.append(node_entry)

    container["thought_tree"] = fixed


def register_theorems(container: Dict[str, Any]) -> None:
    """
    Auto-register theorems with symbolic_registry using their name and glyph.
    """
    for entry in container.get("symbolic_logic", []):
        try:
            name = entry.get("name")
            if name:
                symbolic_registry.register(name, entry)
        except Exception:
            continue