# -*- coding: utf-8 -*-
"""
Tessaris Lean -> CodexLang Bridge (v2.1, SRK-9 Enhanced)
────────────────────────────────────────────────────────
Converts Lean declarations (axioms, theorems, lemmas, defs, examples, constants)
into normalized CodexLang ASTs ({op, args}) using Symatics adapter + rewriter,
then exports verified entries into the Codex theorem ledger.

Upgrades over v1:
  * Semantic SHA-256 hash per normalized logic
  * Dependency inference
  * CodexLang AST embedding (glyph_tree)
  * Works from filesystem OR in-memory Lean text
  * Ledger-ready record builder (ledger_records)
"""

from __future__ import annotations

import os
import re
import math
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.symatics import adapter, rewriter as R


# ───────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────

def _strip_line_comment(s: str) -> str:
    """Remove Lean single-line comments (starting with `--`)."""
    return re.sub(r"--.*$", "", s).strip()


def _semantic_hash(text: str) -> str:
    """Deterministic short hash for logic identity tracking."""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()[:16]


def _infer_dependencies(text: str) -> List[str]:
    """
    Lightweight dependency scan:
      - catches identifiers like Foo, Bar.baz, Nat.add_comm, Iff.symm
      - removes obvious keywords
    """
    if not text:
        return []

    # strip block comments /- ... -/
    cleaned = re.sub(r"/-.*?-/", "", text, flags=re.DOTALL)
    # strip line comments
    cleaned = re.sub(r"^[ \t]*--.*?$", "", cleaned, flags=re.MULTILINE)

    # tokens including dot-qualified
    tokens = re.findall(r"\b[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*\b", cleaned)

    stop = {
        "theorem", "lemma", "axiom", "def", "example", "constant",
        "by", "simp", "simpa", "intro", "exact", "apply", "have", "show",
        "let", "in", "match", "with", "fun", "forall", "exists",
        "Prop", "Type", "Nat", "Int", "Bool", "True", "False",
    }

    out: List[str] = []
    seen = set()
    for t in tokens:
        if t in stop:
            continue
        if len(t) < 2:
            continue
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:96]


# ───────────────────────────────────────────────────────────────
# Lean -> CodexLang AST Translator (minimal / Symatics-aware)
# ───────────────────────────────────────────────────────────────

def lean_to_ast(logic: str) -> Dict[str, Any]:
    """
    Minimal parser for Symatics-style propositions:
      - ⊥
      - single-letter atoms A/B/C
      - (A ⋈[φ] B)
    Everything else becomes a literal node.

    NOTE: This is not a full Lean parser. It’s an adapter to get
    proof-carrying artifacts flowing through the pipeline.
    """
    logic = (logic or "").strip()

    if logic == "⊥":
        return {"op": "logic:⊥", "args": []}

    if re.fullmatch(r"[A-Z]", logic):
        return {"op": "lit", "value": logic}

    m = re.match(r"^\((\w+)\s*⋈\[(.*?)\]\s*(\w+)\)$", logic)
    if m:
        left, phi_str, right = m.groups()
        phi_str = (phi_str or "").strip()
        try:
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

    return {"op": "lit", "value": logic}


# ───────────────────────────────────────────────────────────────
# Lean -> CodexLang Conversion
# ───────────────────────────────────────────────────────────────

DECL_RE = re.compile(
    r"^(theorem|lemma|axiom|def|example|constant)\s+([A-Za-z_][A-Za-z0-9_']*)\s*(\([^)]*\))?\s*:\s*(.*)$"
)


def convert_lean_to_codexlang(
    *,
    lean_path: str | None = None,
    lean_text: str | None = None,
    source_id: str | None = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Converts a Lean source into CodexLang symbolic declarations.

    Provide either:
      - lean_path (read file), OR
      - lean_text (in-memory)

    source_id:
      - optional override identifier for source tracking (KG/container id etc)

    Returns:
      { "parsed_declarations": [ {name, logic, logic_raw, glyph_tree, ...}, ... ] }
    """
    if lean_text is None:
        if not lean_path:
            raise ValueError("Must provide lean_text or lean_path")
        if not os.path.isfile(lean_path):
            raise FileNotFoundError(f"Lean file not found: {lean_path}")
        with open(lean_path, "r", encoding="utf-8") as f:
            lean_text = f.read()

    lines = lean_text.splitlines(keepends=True)
    src = source_id or lean_path or "<in-memory>"

    declarations: List[Dict[str, Any]] = []
    current_decl: List[str] = []
    name: Optional[str] = None
    kind: Optional[str] = None
    params: str = ""
    logic_head: Optional[str] = None
    start_line: int = 0
    glyph_symbol: str = "⟦ Theorem ⟧"

    def _glyph_for_kind(k: str) -> str:
        if k == "axiom":
            return "⟦ Axiom ⟧"
        if k == "lemma":
            return "⟦ Lemma ⟧"
        if k == "def":
            return "⟦ Definition ⟧"
        if k == "example":
            return "⟦ Example ⟧"
        if k == "constant":
            return "⟦ Constant ⟧"
        return "⟦ Theorem ⟧"

    def flush_declaration():
        nonlocal current_decl, name, kind, params, logic_head, start_line, glyph_symbol

        if not current_decl or not name or not logic_head:
            current_decl = []
            name = None
            kind = None
            params = ""
            logic_head = None
            start_line = 0
            glyph_symbol = "⟦ Theorem ⟧"
            return

        raw_body = "".join(current_decl).strip()

        # logic_raw should be stable and human-readable
        logic_raw = " ".join(_strip_line_comment(logic_head).split()).strip()
        if not logic_raw:
            logic_raw = "True"

        # Try to normalize using symatics adapter/rewriter; fallback to logic_raw
        glyph_tree: Dict[str, Any] = {}
        normalized_logic: str = logic_raw
        try:
            codex_ast = lean_to_ast(logic_raw)
            sym_expr = adapter.codex_ast_to_sym(codex_ast)
            normalized_expr = R.normalize(sym_expr)
            glyph_tree = adapter.sym_to_codex_ast(normalized_expr)
            normalized_logic = str(glyph_tree)
        except Exception:
            glyph_tree = {}
            normalized_logic = logic_raw

        depends = _infer_dependencies(raw_body + "\n" + logic_raw)

        decl_hash = _semantic_hash(normalized_logic)

        declarations.append({
            "name": name,
            "kind": kind,
            "params": params.strip() if params else "",
            "logic": normalized_logic,      # normalized / canonical-ish
            "logic_raw": logic_raw,         # original stable string
            "codexlang": {
                "logic": logic_raw,
                "normalized": normalized_logic,
                "explanation": "Auto-converted + normalized from Lean source",
            },
            "codexlang_string": normalized_logic,
            "glyph_symbol": glyph_symbol,
            "glyph_string": f"{glyph_symbol} {name}",
            "glyph_tree": glyph_tree,
            "body": raw_body,
            "line": start_line,
            "source_file": src,
            "hash": decl_hash,
            "depends_on": depends,
            "axioms_used": [d for d in depends if "axiom" in d.lower()],
        })

        current_decl = []
        name = None
        kind = None
        params = ""
        logic_head = None
        start_line = 0
        glyph_symbol = "⟦ Theorem ⟧"

    # Parse line-by-line
    for i, line in enumerate(lines):
        stripped = line.strip()

        # A new decl begins
        m = DECL_RE.match(stripped)
        if m:
            flush_declaration()
            kind, nm, params_part, logic_part = m.groups()
            name = nm
            params = params_part or ""
            logic_head = logic_part
            start_line = i + 1
            glyph_symbol = _glyph_for_kind(kind)
            current_decl = [line]
            continue

        # continue current declaration
        if name:
            current_decl.append(line)

            # we only extend logic_head very lightly; it is NOT a proof parser.
            # This keeps logic_raw stable and avoids smearing the proof body.
            # If the type wraps across lines, we pick those up:
            if logic_head is not None:
                # stop appending once we hit ":=" (proof) on the same line
                if ":=" in stripped:
                    pass
                else:
                    # only append if it still looks like type continuation
                    if stripped and not stripped.startswith("by"):
                        logic_head = (logic_head + " " + _strip_line_comment(stripped)).strip()

    flush_declaration()
    return {"parsed_declarations": declarations}


# ───────────────────────────────────────────────────────────────
# Ledger helpers
# ───────────────────────────────────────────────────────────────

def ledger_records(verified: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for decl in verified:
        out.append({
            "symbol": decl.get("name"),
            "status": "proved",
            "hash": decl.get("hash", _semantic_hash(decl.get("logic", ""))),
            "depends_on": decl.get("depends_on", []),
            "axioms_used": decl.get("axioms_used", []),
            "source_file": decl.get("source_file"),
            "glyph_symbol": decl.get("glyph_symbol"),
            "codexlang_string": decl.get("codexlang_string"),
            "codex_ast": decl.get("glyph_tree", {}),
            "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        })
    return out


def export_theorems_to_ledger(verified: List[Dict[str, Any]], ledger_path: str) -> bool:
    """
    Writes verified theorem data into the Codex theorem ledger (JSONL).
    """
    os.makedirs(os.path.dirname(ledger_path) or ".", exist_ok=True)

    records = ledger_records(verified)
    with open(ledger_path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[Ledger v2.1] Exported {len(records)} verified theorems -> {ledger_path}")
    return True


# ───────────────────────────────────────────────────────────────
# CLI Entry
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    lean_file = "backend/modules/lean/symatics_axioms.lean"
    result = convert_lean_to_codexlang(lean_path=lean_file, source_id=lean_file)
    print(json.dumps(result, indent=2, ensure_ascii=False))