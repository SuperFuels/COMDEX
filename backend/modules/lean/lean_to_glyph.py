# File: backend/modules/lean/lean_to_glyph.py

import os
import re
import sys
import json
from typing import Dict, Any, List

# ---------------------------------------------------------------------
# Resilient imports (graceful fallbacks so this file never hard-crashes)
# ---------------------------------------------------------------------

# CodexLangRewriter (soft simplifier)
try:
    from backend.modules.codex.codexlang_rewriter import CodexLangRewriter  # type: ignore
except Exception:
    class CodexLangRewriter:  # minimal stub
        @classmethod
        def simplify(cls, expr: str, mode: str = "soft") -> str:
            return expr

# LogicGlyph (optional; we can fall back to dict trees)
try:
    from backend.modules.symbolic_engine.symbolic_kernels.logic_glyphs import LogicGlyph  # type: ignore
    _HAS_LOGIC_GLYPH = True
except Exception:
    LogicGlyph = None  # type: ignore
    _HAS_LOGIC_GLYPH = False

# Symbolic registry (optional; fall back to no-op)
try:
    from backend.modules.codex.symbolic_registry import symbolic_registry  # type: ignore
except Exception:
    class _NoOpRegistry:
        def register(self, *args, **kwargs):
            return None
    symbolic_registry = _NoOpRegistry()  # type: ignore


# ---------------------------------------
# Glyph kind mapping (Theorem/Lemma/etc.)
# ---------------------------------------
KIND_TO_GLYPH = {
    "theorem": "⟦ Theorem ⟧",
    "lemma":   "⟦ Lemma ⟧",
    "example": "⟦ Example ⟧",
    "def":     "⟦ Definition ⟧",
    "axiom":   "⟦ Axiom ⟧",
    "constant": "⟦ Constant ⟧",
}


def convert_lean_to_codexlang(path: str) -> Dict[str, Any]:
    """
    Parse a .lean file and convert declarations to CodexLang + glyph trees.
    Returns a dict that downstream can embed into any container.

    Fixes:
      1) Do NOT flush when encountering '--' comment lines (comments can appear inside proofs/types).
      2) Track an `in_body` state so we properly split type vs proof after ':='.
      3) Correctly parse ':=' (inline or later line) and stop shoving proof lines into `typ`.
      4) Never sys.exit() inside library functions (raise instead). sys.exit only in __main__.
    """
    if not os.path.isfile(path):
        # Try resolving relative to project root silently
        alt_path = os.path.abspath(os.path.join(os.getcwd(), path))
        if os.path.isfile(alt_path):
            path = alt_path
        else:
            raise FileNotFoundError(f"Lean file not found: {path}")

    if not path.endswith(".lean"):
        raise ValueError(f"Expected a .lean file, got: {path}")

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # normalize line endings
    lines = [line.replace("\r", "").rstrip("\n") for line in lines]

    declarations: List[Dict[str, Any]] = []
    current_decl: List[str] = []
    name: str | None = None
    kind: str | None = None
    params: str = ""
    typ: str | None = None
    body: str = ""
    glyph_symbol: str = "⟦ Theorem ⟧"
    in_body: bool = False  # ✅ NEW: track whether we've crossed ':=' into proof

    def flush_declaration():
        nonlocal declarations, current_decl, name, kind, params, typ, body, glyph_symbol, in_body

        # Incomplete decl -> reset safely
        if not name or not typ:
            current_decl = []
            name = None
            kind = None
            typ = None
            body = ""
            params = ""
            in_body = False
            glyph_symbol = "⟦ Theorem ⟧"
            return

        typ_clean = " ".join(line.strip() for line in typ.splitlines()).strip()

        decl: Dict[str, Any] = {
            "kind": kind,
            "glyph_symbol": glyph_symbol,
            "name": name,
            "params": params.strip() if params else "",
            "type": typ_clean,
            "logic": typ_clean,
            "body": body.strip(),
        }

        # Build CodexLang with the actual type string
        decl["codexlang"] = lean_decl_to_codexlang(decl)

        # Normalize (soft) for nice display
        try:
            decl["codexlang"]["normalized"] = CodexLangRewriter.simplify(
                decl["codexlang"]["logic"], mode="soft"
            )
        except TypeError:
            decl["codexlang"]["normalized"] = CodexLangRewriter.simplify(
                decl["codexlang"]["logic"]
            )

        # Glyph tree
        decl["glyph_tree"] = build_glyph_tree(decl)

        # Registry hook
        try:
            symbolic_registry.register(decl["name"], decl["glyph_tree"])  # type: ignore[attr-defined]
        except Exception:
            pass

        # Human preview
        decl["preview"] = emit_codexlang_glyph(decl["codexlang"], glyph_symbol)

        # Params + deps
        decl["parsed_params"] = parse_params(decl["params"])
        decl["depends_on"] = detect_dependencies(decl["body"])

        declarations.append(decl)

        # reset state
        current_decl = []
        name = None
        kind = None
        typ = None
        body = ""
        glyph_symbol = "⟦ Theorem ⟧"
        params = ""
        in_body = False

    # Parse decl header:
    # theorem foo (x : T) : P := ...
    decl_re = re.compile(
        r"^(theorem|lemma|example|def|axiom|constant)\s+([A-Za-z_][\w']*)\s*(\([^)]*\))?\s*:\s*(.*)$"
    )

    for i, line in enumerate(lines):
        stripped = line.strip()

        # ✅ 1) Do NOT flush on comment lines; comments can appear inside proofs/types.
        if stripped.startswith("--"):
            if name:
                current_decl.append(line)
                # Only store comment into body if we are in proof body.
                if in_body:
                    body += ("\n" if body else "") + line
            continue

        match = decl_re.match(stripped)
        if match:
            # Close previous decl if one is open
            if name:
                flush_declaration()

            kind, nm, params_part, logic_part = match.groups()
            name = nm
            params = params_part or ""
            typ = (logic_part or "").strip()
            body = ""
            glyph_symbol = KIND_TO_GLYPH.get(kind, "⟦ Theorem ⟧")
            current_decl = [line]
            in_body = False

            # ✅ 3) If ':=' already appears on the header line, split immediately (except axiom/constant)
            if kind not in ("axiom", "constant") and typ is not None and ":=" in typ:
                left, right = typ.split(":=", 1)
                typ = left.strip()
                body = right.strip()
                in_body = True

            # 🧩 optional debug
            print(f"[DEBUG] new decl -> kind={kind}, name={name}, params={params}, logic={typ}", file=sys.stderr)
            continue

        elif name:
            # If we see a new declaration start, close the previous one (reprocess this line)
            if re.match(r"^(theorem|lemma|example|def|axiom|constant)\s+", stripped):
                flush_declaration()
                m2 = decl_re.match(stripped)
                if m2:
                    kind, nm, params_part, logic_part = m2.groups()
                    name = nm
                    params = params_part or ""
                    typ = (logic_part or "").strip()
                    body = ""
                    glyph_symbol = KIND_TO_GLYPH.get(kind, "⟦ Theorem ⟧")
                    current_decl = [line]
                    in_body = False

                    if kind not in ("axiom", "constant") and typ is not None and ":=" in typ:
                        left, right = typ.split(":=", 1)
                        typ = left.strip()
                        body = right.strip()
                        in_body = True
                continue

            current_decl.append(line)

            # ✅ 3) Split type/proof on ':=' when it appears later (except axiom/constant)
            if not in_body and kind not in ("axiom", "constant") and ":=" in stripped:
                left, right = stripped.split(":=", 1)

                if typ is None:
                    typ = left.strip()
                else:
                    typ = (typ + " " + left.strip()).strip()

                body = (body + ("\n" if body else "") + right).strip()
                in_body = True
                continue

            # Accumulate either type (before :=) or proof body (after :=)
            if in_body:
                body += ("\n" if body else "") + line
            else:
                if typ is None:
                    typ = stripped
                else:
                    typ = (typ + " " + stripped).strip()
            continue

        # Outside decl: ignore
        continue

    flush_declaration()

    if not declarations:
        raise ValueError(
            f"No Lean declarations found in {path}. "
            "Expected lines like: 'theorem name : type := proof' or 'axiom name : type'"
        )

    return {
        "source": os.path.normpath(path),
        "logic_type": "lean_math",
        "parsed_declarations": declarations,
    }


def parse_params(param_str: str) -> List[str]:
    if not param_str:
        return []
    if "," in param_str:
        parts = [p.strip() for p in param_str.split(",")]
    else:
        parts = [param_str.strip()]
    return [p for p in parts if p]


def detect_dependencies(body: str) -> List[str]:
    if not body:
        return []
    b = re.sub(r"/-.*?-/", "", body, flags=re.DOTALL)
    b = re.sub(r"^[ \t]*--.*?$", "", b, flags=re.MULTILINE)

    hits: List[str] = []
    hits += re.findall(r"\b(?:[A-Z]?[a-zA-Z_]\w*(?:\.[A-Za-z_]\w+)*)\b", b)
    hits += re.findall(r"\b\w+_(?:lemma|thm|proof)\b", b)

    seen, out = set(), []
    for h in hits:
        if h not in seen and len(h) > 2:
            seen.add(h)
            out.append(h)
    return out[:64]


def lean_decl_to_codexlang(decl: Dict[str, str]) -> Dict[str, Any]:
    name = decl["name"]
    typ = decl.get("type", "").strip()
    glyph_symbol = decl.get("glyph_symbol", "⟦ Theorem ⟧")

    # ✅ Only fallback if empty
    logic = typ if typ else "True"

    # Normalize symbols just in case
    logic = (
        logic.replace("∀", "∀")
             .replace("∃", "∃")
             .replace("->", "->")
             .replace("↔", "↔")
             .replace("∧", "∧")
             .replace("∨", "∨")
             .replace("¬", "¬")
             .replace("⊤", "⊤")
             .replace("⊥", "⊥")
    )

    return {
        "symbol": glyph_symbol,
        "name": name,
        "logic": logic,   # ✅ preserve the actual type (axiom signature)
        "operator": "⊕",
        "args": [
            {"type": "CodexLang", "value": logic},
            {
                "type": "Definition" if glyph_symbol == "⟦ Definition ⟧" else "Proof",
                "value": decl.get("body", ""),
            },
        ],
    }


def build_glyph_tree(decl: Dict[str, Any]) -> Dict[str, Any]:
    node = decl["codexlang"]
    if _HAS_LOGIC_GLYPH and hasattr(LogicGlyph, "from_codexlang"):
        try:
            lg = LogicGlyph.from_codexlang(node)  # type: ignore[attr-defined]
            return lg.to_dict()
        except Exception:
            pass

    return {
        "type": "LogicGlyph",
        "name": node.get("name"),
        "logic": node.get("logic"),
        "operator": node.get("operator"),
        "args": node.get("args", []),
    }


def emit_codexlang_glyph(node: Dict[str, Any], glyph_symbol: str = "⟦ Theorem ⟧") -> str:
    name = node.get("name", "unknown")
    logic = node.get("logic", "???")
    if glyph_symbol == "⟦ Definition ⟧":
        label = "Define"
    elif glyph_symbol in ("⟦ Axiom ⟧", "⟦ Constant ⟧"):
        label = "Assume"
    else:
        label = "Prove"
    return f"{glyph_symbol} | {name} : {logic} -> {label} ⟧"


def lean_to_dc_container(path: str) -> Dict[str, Any]:
    parsed = convert_lean_to_codexlang(path)

    container: Dict[str, Any] = {
        "type": "dc_container",
        "id": f"lean::{os.path.basename(path)}",
        "metadata": {
            "origin": "lean_import",
            "source_path": parsed["source"],
            "logic_type": parsed["logic_type"],
        },
        "glyphs": [],
        "thought_tree": [],
        "symbolic_logic": [],
        "previews": [],
        "dependencies": [],
    }

    for decl in parsed["parsed_declarations"]:
        gsym = decl.get("glyph_symbol", "⟦ Theorem ⟧")

        # ✅ include all recognized Lean declaration kinds
        if gsym not in (
            "⟦ Theorem ⟧", "⟦ Lemma ⟧", "⟦ Example ⟧",
            "⟦ Definition ⟧", "⟦ Axiom ⟧", "⟦ Constant ⟧"
        ):
            continue

        # 🔹 1. Human-readable glyph
        container["glyphs"].append(emit_codexlang_glyph(decl["codexlang"], gsym))

        # 🔹 2. Thought tree node
        container["thought_tree"].append({
            "name": decl["name"],
            "glyph": gsym,
            "node": decl["glyph_tree"],
        })

        # 🔹 3. Symbolic logic entry (used by glyph_to_lean.py)
        container["symbolic_logic"].append({
            "name": decl["name"],
            "symbol": gsym,
            "logic": decl["codexlang"]["logic"],
            "params": decl.get("params", ""),
            "codexlang": decl["codexlang"],
            "glyph_tree": decl["glyph_tree"],
            "source": path,
            "body": decl.get("body", ""),
        })

        # 🔹 4. Previews + dependency tracking
        container["previews"].append(decl["preview"])
        container["dependencies"].append({
            "theorem": decl["name"],
            "depends_on": decl["depends_on"],
        })

    return container


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python lean_to_glyph.py <path_to_lean_file>")
        sys.exit(1)

    input_path = sys.argv[1]
    try:
        dc_container = lean_to_dc_container(input_path)
        print(json.dumps(dc_container, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"[❌] Error: {e}", file=sys.stderr)
        sys.exit(1)