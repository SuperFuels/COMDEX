# File: backend/modules/lean/lean_utils.py
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

# ----------------------------------------------------
# LogicGlyph (single source of truth; optional)
# ----------------------------------------------------
try:
    from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph  # type: ignore
except Exception:
    LogicGlyph = None  # type: ignore


# ----------------------------------------------------
# CodexLangRewriter (soft simplifier; prefer symbolic_engine)
# ----------------------------------------------------
try:
    from backend.modules.symbolic_engine.codexlang_rewriter import CodexLangRewriter  # type: ignore
except Exception:
    try:
        from backend.modules.codex.codexlang_rewriter import CodexLangRewriter  # type: ignore
    except Exception:
        class CodexLangRewriter:  # type: ignore
            @staticmethod
            def simplify(expr: str, mode: str = "soft") -> str:
                return " ".join((expr or "").split())


# ----------------------------------------------------
# Symbolic registry (optional; best-effort)
# ----------------------------------------------------
def _resolve_symbolic_registry():
    try:
        from backend.modules.codex.symbolic_registry import symbolic_registry as _symreg  # type: ignore
        return _symreg
    except Exception:
        try:
            from backend.modules.hexcore.agent_memory import symbolic_registry as _symreg_hex  # type: ignore
            return _symreg_hex
        except Exception:
            class _LocalSymbolicRegistry:
                def __init__(self):
                    self._store: Dict[str, Any] = {}

                def register(self, name: str, payload: Any):
                    self._store[name] = payload

                def get(self, name: str):
                    return self._store.get(name)

            return _LocalSymbolicRegistry()


symbolic_registry = _resolve_symbolic_registry()

# ----------------------------------------------------
# Canonical op normalization (namespaced -> raw)
# ----------------------------------------------------
_CANONICAL_OP_NS_MAP: Dict[str, str] = {
    "logic:↔": "↔",
    "quantum:↔": "↔",
    "logic:⊕": "⊕",
    "quantum:⊕": "⊕",
    "symatics:⊕": "⊕",
    "symatics:⟲": "⟲",
    "control:⧖": "⧖",
    "logic:->": "->",
    "control:->": "->",
    "math:∇": "∇",
    "barrier:⟁": "⟁",
    "interf:⋈": "⋈",
    "mod:⌬": "⌬",
}


def _denamespace_ops(text: str) -> str:
    """
    Convert canonical namespaced op tokens into their raw glyph equivalents.
    Intended for Lean preview/validation (Lean doesn’t care about namespaces).
    """
    if not isinstance(text, str) or not text:
        return text

    # fast path: only do work if ':' appears
    if ":" not in text:
        return text

    # replace explicit known mappings first
    for k, v in _CANONICAL_OP_NS_MAP.items():
        if k in text:
            text = text.replace(k, v)

    # generic fallback: if something like "logic:XYZ" remains, strip prefix.
    # Keep it conservative: only strip if RHS is non-empty and contains a non-ascii glyph OR arrow-ish token.
    def _strip(m: re.Match) -> str:
        rhs = m.group(2) or ""
        if not rhs:
            return m.group(0)
        return rhs

    # e.g. "foo:↔" -> "↔"
    text = re.sub(r"\b([a-zA-Z_]\w*):([^\s]+)", _strip, text)
    return text


# ----------------------------------------------------
# Lean container + metadata helpers
# ----------------------------------------------------
def is_lean_container(container: Dict[str, Any]) -> bool:
    return (container.get("metadata", {}) or {}).get("origin") == "lean_import"


def is_lean_universal_container_system(obj: Any) -> bool:
    """
    Detect if object looks like a Lean-compatible UCS/container.
    Conservative heuristics.
    """
    try:
        if hasattr(obj, "is_lean") and bool(getattr(obj, "is_lean")):
            return True

        if isinstance(obj, dict):
            meta = obj.get("metadata", {}) or {}
            t = (obj.get("type") or meta.get("type") or "").lower()
            if meta.get("origin") == "lean_import":
                return True
            if t in {
                "lean_container",
                "dc_container",
                "symbolic_expansion_container",
                "hoberman_container",
                "exotic_container",
                "symmetry_container",
                "atom_container",
            }:
                return True

        obj_type = type(obj).__name__.lower()
        return ("lean" in obj_type) or ("ucs" in obj_type)
    except Exception:
        return False


def extract_lean_metadata(container: Dict[str, Any]) -> Dict[str, Any]:
    meta = container.get("metadata", {}) or {}
    return {
        "origin": meta.get("origin"),
        "logic_type": meta.get("logic_type"),
        "source_path": meta.get("source_path"),
    }


# ----------------------------------------------------
# Logic entry collection (IMPORTANT: filter only “entry-shaped” dicts)
# ----------------------------------------------------
_ENTRY_SYMBOLS = {
    "⟦ Theorem ⟧",
    "⟦ Lemma ⟧",
    "⟦ Definition ⟧",
    "⟦ Axiom ⟧",
    "⟦ Constant ⟧",
}

_FALLBACK_SYMBOL = "⟦ Theorem ⟧"


def _is_logic_entry_dict(d: Dict[str, Any]) -> bool:
    """
    True only for Lean “logic entry” dicts, not generic codex instruction trees.
    """
    if not isinstance(d, dict):
        return False

    # Must have a name OR look like a Lean decl; codex instruction trees usually have op/args only.
    has_nameish = isinstance(d.get("name"), str) and d.get("name", "").strip() != ""
    has_symbolish = isinstance(d.get("symbol"), str) and d.get("symbol", "").strip() != ""
    has_logicish = ("logic" in d) or ("logic_raw" in d) or ("codexlang" in d)

    # If it looks like an instruction node only, reject.
    if "op" in d and "args" in d and not has_nameish:
        return False

    return has_nameish or (has_symbolish and has_logicish)


def _collect_logic_entries(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Collect logic entries from all known container fields.
    Filters out non-entry dicts (like raw instruction trees).
    """
    entries: List[Dict[str, Any]] = []
    for fld in (
        "symbolic_logic",
        "expanded_logic",
        "hoberman_logic",
        "exotic_logic",
        "symmetric_logic",
        "axioms",
    ):
        v = container.get(fld)
        if isinstance(v, list) and v:
            for it in v:
                if isinstance(it, dict) and _is_logic_entry_dict(it):
                    entries.append(it)
    return entries


def extract_theorems(container: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Back-compat: callers expect “theorem-ish” entries; return all logic entries.
    return _collect_logic_entries(container)


# ----------------------------------------------------
# Name + summary helpers
# ----------------------------------------------------
def get_theorem_names(container: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    for entry in extract_theorems(container):
        if entry.get("symbol") == "⟦ Theorem ⟧":
            nm = entry.get("name")
            if nm:
                out.append(nm)
    return out


def summarize_lean_container(container: Dict[str, Any]) -> Dict[str, Any]:
    logic = extract_theorems(container)
    counts = {"theorems": 0, "lemmas": 0, "defs": 0, "axioms": 0, "constants": 0}
    names: Dict[str, List[str]] = {k: [] for k in counts.keys()}

    for e in logic:
        sym = e.get("symbol", "")
        nm = e.get("name") or "?"
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
        "source_path": (container.get("metadata", {}) or {}).get("source_path"),
        "counts": counts,
        "names": names,
    }


def pretty_print_lean_summary(container: Dict[str, Any]) -> None:
    print("\n📦 Lean Container Summary:")
    print(json.dumps(summarize_lean_container(container), indent=2, ensure_ascii=False))


# ----------------------------------------------------
# Normalization helpers for entries
# ----------------------------------------------------
def _coerce_symbol(sym: Any) -> str:
    if isinstance(sym, str) and sym.strip() and sym.strip() not in {"⟦ ? ⟧", "?"}:
        s = sym.strip()
        # If user gave raw "Theorem"/"Lemma" etc, map to glyph form.
        low = s.lower()
        if low == "theorem":
            return "⟦ Theorem ⟧"
        if low == "lemma":
            return "⟦ Lemma ⟧"
        if low in {"def", "definition"}:
            return "⟦ Definition ⟧"
        if low == "axiom":
            return "⟦ Axiom ⟧"
        if low == "constant":
            return "⟦ Constant ⟧"
        # If it already looks like ⟦ ... ⟧, keep.
        if s.startswith("⟦") and s.endswith("⟧"):
            return s
        # Otherwise, fallback.
    return _FALLBACK_SYMBOL


def _coerce_name(name: Any, fallback: str = "unnamed") -> str:
    if isinstance(name, str) and name.strip():
        return name.strip()
    return fallback


def _coerce_logic(entry: Dict[str, Any]) -> str:
    codex = entry.get("codexlang")
    logic_raw = (
        (codex.get("logic") if isinstance(codex, dict) else None)
        or entry.get("logic")
        or entry.get("logic_raw")
        or entry.get("type")
        or "True"
    )
    if not isinstance(logic_raw, str) or not logic_raw.strip():
        logic_raw = "True"

    # Denamespace first so Lean sees raw ops.
    logic_raw = _denamespace_ops(logic_raw)

    # Soft simplify.
    try:
        logic_soft = CodexLangRewriter.simplify(logic_raw, mode="soft") or logic_raw
    except TypeError:
        logic_soft = CodexLangRewriter.simplify(logic_raw) or logic_raw  # type: ignore

    return logic_soft


def normalize_codexlang(container: Dict[str, Any]) -> None:
    """
    Soft-normalize logic strings in-place (safe).
    Also denamespaces canonical ops so validation/preview matches Lean expectations.
    """
    for entry in _collect_logic_entries(container):
        entry["name"] = _coerce_name(entry.get("name"))
        entry["symbol"] = _coerce_symbol(entry.get("symbol") or (entry.get("codexlang", {}) or {}).get("symbol"))
        logic_soft = _coerce_logic(entry)
        entry["logic"] = logic_soft
        if "logic_raw" not in entry or not isinstance(entry.get("logic_raw"), str) or not entry["logic_raw"].strip():
            entry["logic_raw"] = logic_soft

        codex = entry.get("codexlang")
        if not isinstance(codex, dict):
            codex = {}
        codex.setdefault("symbol", entry["symbol"])
        codex["logic"] = logic_soft
        codex.setdefault("normalized", logic_soft)
        entry["codexlang"] = codex


# ----------------------------------------------------
# Validation + normalization
# ----------------------------------------------------
def validate_logic_trees(container: Dict[str, Any]) -> List[str]:
    """
    Validate container logic entries.
    Returns list[str] for backward compatibility (your CLI later normalizes).
    """
    errors: List[str] = []
    entries = _collect_logic_entries(container)

    # Ensure normalization has run (safe even if already normalized).
    try:
        normalize_codexlang(container)
        entries = _collect_logic_entries(container)
    except Exception:
        pass

    # Law 1: unique non-empty names
    seen_names: Dict[str, bool] = {}
    for e in entries:
        n = e.get("name")
        if not n or not isinstance(n, str) or not n.strip():
            errors.append("Missing theorem/axiom name")
            continue
        if n in seen_names:
            errors.append(f"Duplicate entry name: {n}")
        seen_names[n] = True

    # Law 2: unique signature (name, symbol, logic_raw|logic)
    seen_sigs = set()
    for e in entries:
        sig = (
            e.get("name"),
            e.get("symbol"),
            (e.get("logic_raw") or e.get("logic") or ""),
        )
        if sig in seen_sigs:
            errors.append(f"Duplicate signature: {sig}")
        else:
            seen_sigs.add(sig)

    # Law 3: self-dep is hard error; external deps are allowed (soft warning string)
    names = {e.get("name") for e in entries if e.get("name")}
    for e in entries:
        n = e.get("name") or "?"
        deps = e.get("depends_on") or []
        if isinstance(deps, list):
            if n in deps:
                errors.append(f"Circular dependency: {n} depends on itself")
            for dep in deps:
                if dep and dep not in names:
                    errors.append(f"Unresolved dependency (external?): {n} depends on {dep}")

    # Law 4: logic must be a non-empty string
    for e in entries:
        n = e.get("name") or "?"
        logic = e.get("logic") or e.get("logic_raw")
        if not isinstance(logic, str) or not logic.strip():
            errors.append(f"{n} has missing/empty logic")

    # Law 5: symbol validity
    for e in entries:
        n = e.get("name") or "?"
        sym = e.get("symbol")
        if not sym or not isinstance(sym, str) or sym.strip() in {"⟦ ? ⟧", "?"}:
            errors.append(f"{n} has invalid or missing symbol")

    return errors


def normalize_validation_errors(errors: Any) -> List[Dict[str, str]]:
    """
    Normalize validation errors to list[{code,message}].
    Accepts: None, str, dict, list[str], list[dict], mixed.
    """
    if not errors:
        return []

    out: List[Dict[str, str]] = []

    def wrap(msg: str) -> Dict[str, str]:
        m = (msg or "").lower()
        code = "validation_error"
        if "missing" in m:
            code = "E001"
        elif "syntax" in m or "parse" in m:
            code = "E002"
        elif "unsupported" in m:
            code = "E003"
        return {"code": code, "message": msg}

    if isinstance(errors, str):
        return [wrap(errors)]

    if isinstance(errors, dict):
        if "code" in errors and "message" in errors:
            return [{"code": str(errors["code"]), "message": str(errors["message"])}]
        return [wrap(str(errors))]

    if isinstance(errors, list):
        for e in errors:
            if isinstance(e, dict) and "code" in e and "message" in e:
                out.append({"code": str(e["code"]), "message": str(e["message"])})
            else:
                out.append(wrap(str(e)))
        return out

    return [wrap(str(errors))]


# ----------------------------------------------------
# Preview + link inference
# ----------------------------------------------------
def inject_preview_and_links(container: Dict[str, Any]) -> None:
    """
    Populate preview/glyph_string and infer depends_on via name mentions (best-effort).
    Operates on symbolic_logic if present, otherwise all logic fields.
    """
    logic_list = container.get("symbolic_logic")
    if not isinstance(logic_list, list) or not logic_list:
        logic_list = _collect_logic_entries(container)

    # Ensure entries are normalized before preview generation
    try:
        normalize_codexlang(container)
    except Exception:
        pass

    name_map = {e.get("name"): e for e in logic_list if e.get("name")}

    for entry in logic_list:
        try:
            entry["name"] = _coerce_name(entry.get("name"))
            codex = entry.get("codexlang", {}) or {}
            glyph_symbol = _coerce_symbol(codex.get("symbol") or entry.get("symbol"))
            entry["symbol"] = glyph_symbol

            logic = entry.get("logic") or codex.get("logic") or ""
            if not isinstance(logic, str):
                logic = str(logic)
            logic = _denamespace_ops(logic)

            name = entry.get("name") or ""

            if glyph_symbol == "⟦ Definition ⟧":
                label = "Define"
            elif glyph_symbol in ("⟦ Axiom ⟧", "⟦ Constant ⟧"):
                label = "Assume"
            else:
                label = "Prove"

            entry["preview"] = f"{glyph_symbol} | {name} : {logic} ⟧"
            if not entry.get("glyph_string"):
                entry["glyph_string"] = f"{glyph_symbol} | {name} : {logic} -> {label} ⟧"

            deps: List[str] = []
            haystacks = [entry.get("body", "") or "", logic or ""]
            for other_name in name_map.keys():
                if other_name and other_name != name:
                    if any(other_name in (h or "") for h in haystacks):
                        deps.append(other_name)
            entry["depends_on"] = sorted(set(deps))

            entry["logic"] = logic
            if not isinstance(codex, dict):
                codex = {}
            codex["symbol"] = glyph_symbol
            codex["logic"] = logic
            entry["codexlang"] = codex
        except Exception:
            continue


def harmonize_symbols_and_trees(container: Dict[str, Any]) -> None:
    """
    Ensure thought_tree nodes match symbols/types from logic entries.
    """
    logic_list = container.get("symbolic_logic")
    if not isinstance(logic_list, list) or not logic_list:
        logic_list = _collect_logic_entries(container)

    # Ensure normalization has run
    try:
        normalize_codexlang(container)
    except Exception:
        pass

    glyph_by_name: Dict[str, Any] = {}
    for e in logic_list:
        name = e.get("name") or ""
        codex = e.get("codexlang", {}) or {}
        gsym = _coerce_symbol(codex.get("symbol") or e.get("symbol"))
        logic = _denamespace_ops(codex.get("logic") or e.get("logic") or "")
        if name:
            glyph_by_name[name] = (gsym, logic)

    tree = container.get("thought_tree", [])
    if not isinstance(tree, list):
        return

    fixed: List[Dict[str, Any]] = []
    seen = set()

    for node_entry in tree:
        try:
            name = node_entry.get("name") or ""
            node = node_entry.get("node")
            gsym, logic = glyph_by_name.get(name, (_coerce_symbol(node_entry.get("glyph")), ""))

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

            sig = (name, node_entry["glyph"], logic)
            if sig in seen:
                continue
            seen.add(sig)
            fixed.append(node_entry)
        except Exception:
            fixed.append(node_entry)

    container["thought_tree"] = fixed


def register_theorems(container: Dict[str, Any]) -> None:
    """
    Register entries into symbolic_registry for lookup.
    """
    for entry in _collect_logic_entries(container):
        try:
            name = entry.get("name")
            if name:
                symbolic_registry.register(name, {"entry": entry, "kind": entry.get("symbol")})
        except Exception:
            continue


# ----------------------------------------------------
# Back-compat helper (some pipelines import this)
# ----------------------------------------------------
def _normalize_logic_entry(decl: Dict[str, Any], lean_path: str) -> Dict[str, Any]:
    """
    Normalize a Lean declaration into a logic entry with safe codexlang dict.
    Keeps behavior compatible with older injector/CLI codepaths.
    """
    glyph_symbol = _coerce_symbol(decl.get("glyph_symbol", _FALLBACK_SYMBOL))
    name = _coerce_name(decl.get("name"), fallback="unnamed")
    codexlang = decl.get("codexlang", {}) or {}

    if isinstance(decl.get("codexlang_string"), str) and "legacy" not in codexlang:
        codexlang["legacy"] = decl["codexlang_string"]

    logic_raw = (
        (codexlang.get("logic") if isinstance(codexlang, dict) else None)
        or decl.get("codexlang_string")
        or decl.get("logic")
        or decl.get("type")
        or "True"
    )
    if not isinstance(logic_raw, str) or not logic_raw.strip():
        logic_raw = "True"

    logic_raw = _denamespace_ops(logic_raw)

    if not isinstance(codexlang, dict):
        codexlang = {}

    if not isinstance(codexlang.get("logic"), str) or not str(codexlang.get("logic")).strip():
        codexlang["logic"] = logic_raw
    if not isinstance(codexlang.get("normalized"), str) or not str(codexlang.get("normalized")).strip():
        codexlang["normalized"] = logic_raw
    if "explanation" not in codexlang:
        codexlang["explanation"] = "Auto-converted from Lean source"

    try:
        logic_soft = CodexLangRewriter.simplify(logic_raw, mode="soft") or logic_raw
    except TypeError:
        logic_soft = CodexLangRewriter.simplify(logic_raw) or logic_raw  # type: ignore

    return {
        "name": name,
        "symbol": glyph_symbol,
        "logic": logic_soft,
        "logic_raw": logic_raw,
        "codexlang": codexlang,
        "glyph_tree": decl.get("glyph_tree", {}),
        "source": lean_path,
        "body": decl.get("body", ""),
        "depends_on": decl.get("depends_on", []) or [],
        "params": decl.get("params", "") or "",
    }