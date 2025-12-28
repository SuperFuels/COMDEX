# -*- coding: utf-8 -*-
"""
Glyph -> Lean Translator
──────────────────────────────────────────────────────────────
Reconstruct Lean declarations (axioms/theorems/lemmas/defs/examples)
from Tessaris/Codex containers (symbolic_logic entries) or plaintext glyph dumps.

Key upgrades:
- Uses entry fields safely: params, logic_raw, logic, codexlang.logic, body
- Handles ⟦ Theorem ⟧ / ⟦ Lemma ⟧ / ⟦ Definition ⟧ etc.
- Optional prelude/axioms imports (symatics_prelude / symatics_axioms)
- Optional namespace wrapper
- Sensible stubs (theorem/lemma/example -> `:= by sorry`) when body missing
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Operator mapping (glyph -> Lean identifier). Soft-import.
try:
    from backend.modules.lean.imports.glyph_bindings import GLYPH_TO_LEAN  # type: ignore
except Exception:
    GLYPH_TO_LEAN = {}  # type: ignore


# ----------------------------
# Core mapping / normalization
# ----------------------------
KIND_MAP = {
    "Axiom": "axiom",
    "Theorem": "theorem",
    "Lemma": "lemma",
    "Definition": "def",
    "Def": "def",
    "Constant": "constant",
    "Example": "example",
    "Notation": "-- notation",
}

# Common Tessaris symbol tokens → kind
SYMBOL_TO_KIND = {
    "⟦ Axiom ⟧": "axiom",
    "⟦ Theorem ⟧": "theorem",
    "⟦ Lemma ⟧": "lemma",
    "⟦ Definition ⟧": "def",
    "⟦ Constant ⟧": "constant",
    "⟦ Example ⟧": "example",
    "⟦ Notation ⟧": "-- notation",
}


def glyph_to_lean_expr(expr: str) -> str:
    """Replace symbolic glyph operators with corresponding Lean identifiers."""
    if not isinstance(expr, str):
        return "True"
    lean_expr = expr
    for glyph, lean_name in (GLYPH_TO_LEAN or {}).items():
        if glyph and lean_name:
            lean_expr = lean_expr.replace(glyph, lean_name)
    return lean_expr.strip() or "True"


def _normalize_params(params: str) -> str:
    """
    Ensure params is either "" or " (..)"-prefixed chunk.
    Accepts "(a b : Nat)" or "a b : Nat" or "".
    """
    if not params or not isinstance(params, str):
        return ""
    p = params.strip()
    if not p:
        return ""
    if p.startswith("(") and p.endswith(")"):
        return f" {p}"
    # If someone passed "a b : Nat", wrap it.
    return f" ({p})"


def _extract_kind(entry: Dict[str, Any]) -> str:
    # Prefer explicit Lean-ish keyword if present
    sym = (entry.get("symbol") or entry.get("glyph_symbol") or "").strip()
    if sym in SYMBOL_TO_KIND:
        return SYMBOL_TO_KIND[sym]

    # Or if it was "⟦ Theorem ⟧" without spaces
    if sym.startswith("⟦") and sym.endswith("⟧"):
        cleaned = sym.replace("⟦", "").replace("⟧", "").strip()
        return KIND_MAP.get(cleaned, cleaned.lower())

    # Or a plain string like "theorem"
    k = (entry.get("kind") or "").strip()
    if k:
        kl = k.lower()
        if kl in {"axiom", "theorem", "lemma", "def", "constant", "example"}:
            return kl

    # Fallback
    return "axiom"


def _extract_logic_and_body(entry: Dict[str, Any]) -> Tuple[str, str]:
    """
    Prefer logic_raw, then codexlang.logic, then logic.
    Prefer body field; else split logic on ':=' if present.
    """
    codex = entry.get("codexlang") or {}
    if not isinstance(codex, dict):
        codex = {}

    logic = (
        entry.get("logic_raw")
        or codex.get("logic")
        or entry.get("logic")
        or "True"
    )
    if not isinstance(logic, str) or not logic.strip():
        logic = "True"

    body = entry.get("body") or ""
    if not isinstance(body, str):
        body = ""

    # If body is empty but logic string includes ':=', split it
    if not body and ":=" in logic:
        left, right = logic.split(":=", 1)
        logic = left.strip() or "True"
        body = right.strip()

    return logic.strip() or "True", body.strip()


def _render_imports(
    *,
    use_symatics_prelude: bool,
    use_symatics_axioms: bool,
    extra_imports: Optional[List[str]] = None,
) -> str:
    """
    Emits Lean imports as plain lines.
    NOTE: These are relative imports assuming the generated .lean sits next to the .lean libs.
    If your build uses a Lean project, you can switch these to module imports later.
    """
    lines: List[str] = []
    if use_symatics_prelude:
        lines.append("import ./symatics_prelude")
    if use_symatics_axioms:
        lines.append("import ./symatics_axioms")
    for imp in (extra_imports or []):
        if imp and isinstance(imp, str):
            lines.append(f"import {imp.strip()}")
    return ("\n".join(lines) + "\n\n") if lines else ""


def glyph_to_lean_declaration(
    entry: Dict[str, Any],
    *,
    fill_sorry: bool = True,
) -> str:
    """
    Convert one symbolic_logic entry into a Lean declaration.
    - theorem/lemma/example: if body missing and fill_sorry=True -> `:= by sorry`
    - def: if body missing -> emit as `def name : T := by`? (we choose `:= by` with sorry)
    - axiom/constant: no body by default
    """
    name = (entry.get("name") or "unnamed").strip()
    if not name:
        name = "unnamed"

    kind = _extract_kind(entry)
    params = _normalize_params(entry.get("params") or "")

    logic_raw, body = _extract_logic_and_body(entry)
    logic = glyph_to_lean_expr(logic_raw)

    # Keyword normalization
    keyword = KIND_MAP.get(kind.capitalize(), kind)
    if keyword not in {"axiom", "theorem", "lemma", "def", "constant", "example"} and not keyword.startswith("--"):
        keyword = "axiom"

    # Notation passthrough (rare)
    if keyword.startswith("--"):
        return f"-- {name} {logic}".strip()

    # If we have an explicit body, use it.
    if body:
        # body might already include `by ...` or be a term; we keep it as-is
        return f"{keyword} {name}{params} : {logic} := {body}"

    # No body: choose a safe stub strategy
    if keyword in {"theorem", "lemma", "example"} and fill_sorry:
        return f"{keyword} {name}{params} : {logic} := by\n  sorry"

    if keyword == "def" and fill_sorry:
        return f"def {name}{params} : {logic} := by\n  sorry"

    # Axiom/constant (or no-sorry mode): no proof attached
    return f"{keyword} {name}{params} : {logic}"


def build_lean_from_container(
    container: Dict[str, Any],
    *,
    use_symatics_prelude: bool = False,
    use_symatics_axioms: bool = False,
    namespace: Optional[str] = None,
    fill_sorry: bool = True,
    extra_imports: Optional[List[str]] = None,
) -> str:
    entries = container.get("symbolic_logic") or []
    if not isinstance(entries, list):
        entries = []

    decls = [glyph_to_lean_declaration(e, fill_sorry=fill_sorry) for e in entries if isinstance(e, dict)]

    header = _render_imports(
        use_symatics_prelude=use_symatics_prelude,
        use_symatics_axioms=use_symatics_axioms,
        extra_imports=extra_imports,
    )

    body = "\n\n".join([d for d in decls if d.strip()])

    if namespace:
        ns = namespace.strip()
        if ns:
            return f"{header}namespace {ns}\n\n{body}\n\nend {ns}\n"
    return f"{header}{body}\n"


# ----------------------------
# Input loading (JSON or text)
# ----------------------------
_GLYPH_TEXT_PATTERN = re.compile(
    r"⟦\s*([A-Za-z]+)\s*⟧\s+([A-Za-z_][\w']*)[\s\S]*?Logic:\s*(.+?)(?=\n\s*\Z|\n\s*⟦|\Z)",
    re.MULTILINE,
)

def _load_input(path: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Returns (container, entries). If not JSON, container is {}, entries parsed from text.
    """
    text = Path(path).read_text(encoding="utf-8").strip()
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj, (obj.get("symbolic_logic") or [])
        # if it's a list of entries
        if isinstance(obj, list):
            return {}, obj
    except json.JSONDecodeError:
        pass

    # Plaintext glyph extraction
    entries: List[Dict[str, Any]] = []
    for m in _GLYPH_TEXT_PATTERN.finditer(text):
        kind, name, logic = m.groups()
        entries.append({"symbol": kind, "name": name, "logic": logic, "body": ""})
    return {}, entries


# ----------------------------
# CLI
# ----------------------------
def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Glyph/Container -> Lean translator")
    ap.add_argument("glyph_path", help="Path to container JSON or plaintext glyph dump")
    ap.add_argument("--out", "-o", help="Write Lean output to file")
    ap.add_argument("--namespace", help="Wrap output in a Lean namespace")
    ap.add_argument("--symatics-prelude", action="store_true", help="Add `import ./symatics_prelude`")
    ap.add_argument("--symatics-axioms", action="store_true", help="Add `import ./symatics_axioms`")
    ap.add_argument("--no-sorry", action="store_true", help="Do not emit `by sorry` stubs")
    ap.add_argument("--import", dest="extra_imports", action="append", default=[], help="Extra Lean imports (repeatable)")
    args = ap.parse_args(argv)

    if not os.path.exists(args.glyph_path):
        print(f"❌ File not found: {args.glyph_path}")
        return 1

    container, entries = _load_input(args.glyph_path)

    # If input wasn't a container, synthesize one
    if not container:
        container = {"symbolic_logic": entries}
    elif "symbolic_logic" not in container:
        container["symbolic_logic"] = entries

    out_text = build_lean_from_container(
        container,
        use_symatics_prelude=args.symatics_prelude,
        use_symatics_axioms=args.symatics_axioms,
        namespace=args.namespace,
        fill_sorry=(not args.no_sorry),
        extra_imports=args.extra_imports,
    )

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(out_text, encoding="utf-8")
        print(f"[✅] Written Lean -> {args.out}")
    else:
        print(out_text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())