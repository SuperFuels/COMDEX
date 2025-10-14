# -*- coding: utf-8 -*-
"""
Tessaris Lean → CodexLang Bridge (v2.0, SRK-9 Enhanced)
────────────────────────────────────────────────────────
Converts Lean declarations (axioms, theorems, lemmas) into normalized
CodexLang ASTs ({op, args}) using Symatics adapter and rewriter,
then exports verified entries into the Codex theorem ledger.

Upgrades over v1:
  • Semantic SHA-256 hash per normalized logic
  • Dependency + axiom inference
  • Full CodexLang AST embedding for introspection
  • Compatible with lean_parser outputs
"""

import os
import re
import math
import json
import hashlib
from typing import List, Dict, Any
from datetime import datetime

from backend.symatics import adapter, rewriter as R

def convert_lean_expr(expr: str):
    """Stub translator from Lean syntax → CodexLang symbolic form."""
    return {"converted_expr": expr, "status": "ok"}
# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────
def _strip_comments(s: str) -> str:
    """Remove Lean-style comments (starting with `--`)."""
    return re.sub(r"--.*$", "", s).strip()

def _semantic_hash(text: str) -> str:
    """Deterministic short hash for logic identity tracking."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

def _infer_dependencies(body: str) -> list[str]:
    """Naive scan for lemma/theorem/axiom references."""
    deps = set()
    for token in re.findall(r"(?:using|by)\s+([A-Za-z0-9_]+)", body):
        deps.add(token)
    for token in re.findall(r"(?:lemma|theorem|axiom)\s+([A-Za-z0-9_]+)", body):
        deps.add(token)
    return sorted(deps)


# ───────────────────────────────────────────────────────────────
# Lean → CodexLang AST Translator
# ───────────────────────────────────────────────────────────────
def lean_to_ast(logic: str) -> Dict[str, Any]:
    """
    Very minimal parser: supports patterns like
      (A ⋈[φ] B), ⊥, atoms A/B/C.
    Produces CodexLang AST nodes.
    """
    logic = logic.strip()

    # Bottom
    if logic == "⊥":
        return {"op": "logic:⊥", "args": []}

    # Atom
    if re.fullmatch(r"[A-Z]", logic):
        return {"op": "lit", "value": logic}

    # Interference connective
    m = re.match(r"^\((\w+)\s*⋈\[(.*?)\]\s*(\w+)\)$", logic)
    if m:
        left, phi_str, right = m.groups()
        try:
            # Normalize Lean phase symbols
            if phi_str in ("π", "pi_phase"):
                φ = math.pi
            elif phi_str in ("0", "zero_phase"):
                φ = 0.0
            else:
                φ = float(phi_str)
        except Exception:
            φ = 0.0
        return {
            "op": "interf:⋈",
            "phase": φ,
            "args": [
                {"op": "lit", "value": left},
                {"op": "lit", "value": right},
            ],
        }

    # Fallback: literal
    return {"op": "lit", "value": logic}


# ───────────────────────────────────────────────────────────────
# Lean → CodexLang Conversion
# ───────────────────────────────────────────────────────────────
def convert_lean_to_codexlang(lean_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Converts a Lean file into CodexLang symbolic declarations.
    Returns { "parsed_declarations": [ {name, logic, ...}, ... ] }.
    """
    if not os.path.isfile(lean_path):
        raise FileNotFoundError(f"Lean file not found: {lean_path}")

    with open(lean_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    declarations: List[Dict[str, Any]] = []
    current_decl: List[str] = []
    name, logic, start_line = None, None, 0
    glyph_symbol = "⟦ Theorem ⟧"

    def flush_declaration():
        nonlocal declarations, current_decl, name, logic, start_line, glyph_symbol
        if not current_decl or not name:
            return

        raw_body = "".join(current_decl).strip()
        logic_str = _strip_comments(logic or "True")

        try:
            codex_ast = lean_to_ast(logic_str)
            sym_expr = adapter.codex_ast_to_sym(codex_ast)
            normalized_expr = R.normalize(sym_expr)
            glyph_tree = adapter.sym_to_codex_ast(normalized_expr)
            normalized_logic = str(glyph_tree)
        except Exception:
            glyph_tree = {}
            normalized_logic = logic_str

        depends = _infer_dependencies(raw_body)
        decl_hash = _semantic_hash(normalized_logic)

        declarations.append({
            "name": name,
            "logic": normalized_logic,
            "logic_raw": logic_str,
            "codexlang": {
                "logic": logic_str,
                "normalized": normalized_logic,
                "explanation": "Auto-converted + normalized from Lean source",
            },
            "codexlang_string": normalized_logic,
            "glyph_symbol": glyph_symbol,
            "glyph_string": f"{glyph_symbol} {name}",
            "glyph_tree": glyph_tree,
            "body": raw_body,
            "line": start_line,
            "source_file": lean_path,
            "hash": decl_hash,
            "depends_on": depends,
            "axioms_used": [d for d in depends if "axiom" in d.lower()],
        })

        current_decl.clear()
        name, logic, start_line = None, None, 0
        glyph_symbol = "⟦ Theorem ⟧"

    # Parse line-by-line
    for i, line in enumerate(lines):
        stripped = line.strip()
        match = re.match(r"^(theorem|lemma|axiom)\s+([A-Za-z0-9_']+)\s*:\s*(.+)$", stripped)
        if match:
            flush_declaration()
            kind, nm, logic_part = match.groups()
            name = nm
            start_line = i + 1
            logic = _strip_comments(logic_part)
            glyph_symbol = "⟦ Axiom ⟧" if kind == "axiom" else "⟦ Theorem ⟧"
            current_decl = [line]
        elif name:
            current_decl.append(line)
            logic = (logic or "") + " " + _strip_comments(stripped)

    flush_declaration()
    return {"parsed_declarations": declarations}


# ───────────────────────────────────────────────────────────────
# Ledger Exporter (SRK-9)
# ───────────────────────────────────────────────────────────────
def export_theorems_to_ledger(verified, ledger_path):
    """
    Writes verified theorem data into the Codex theorem ledger (JSONL).
    Each record includes semantic hash, dependencies, and CodexLang AST.
    """
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    count = 0
    with open(ledger_path, "w", encoding="utf-8") as f:
        for decl in verified:
            record = {
                "symbol": decl.get("name"),
                "status": "proved",
                "hash": decl.get("hash", _semantic_hash(decl.get("logic", ""))),
                "depends_on": decl.get("depends_on", []),
                "axioms_used": decl.get("axioms_used", []),
                "source_file": decl.get("source_file"),
                "glyph_symbol": decl.get("glyph_symbol"),
                "codexlang_string": decl.get("codexlang_string"),
                "codex_ast": decl.get("glyph_tree", {}),
                "timestamp": datetime.utcnow().isoformat(),
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    print(f"[Ledger v2] Exported {count} verified theorems → {ledger_path}")
    return True


# ───────────────────────────────────────────────────────────────
# CLI Entry
# ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import json
    lean_file = "backend/modules/lean/symatics_axioms.lean"
    result = convert_lean_to_codexlang(lean_file)
    print(json.dumps(result, indent=2, ensure_ascii=False))