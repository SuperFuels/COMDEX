"""
Lean Parser -> CodexGlyph Translator
──────────────────────────────────────────────
Parses Lean source files (axioms, theorems, defs, etc.) into symbolic structures
usable by Tessaris and CodexGlyph translators.
"""

import re
from pathlib import Path
from typing import List, Dict, Any


# NOTE:
# We capture:
#   - name
#   - optional params (...)
#   - type/logic after ':'
#   - optional proof/body after ':='
#
# We then sort all matches by position so results preserve file order.

DECLARATION_PATTERNS = {
    # theorem/lemma share same shape
    "theorem": re.compile(
        r"^\s*theorem\s+([^\s:(]+)\s*(?:\((.*?)\))?\s*:\s*([\s\S]*?)(?:\s*:=\s*([\s\S]*?))?"
        r"(?=\n\s*(?:theorem|lemma|def|axiom|constant|example|end)\b|\Z)",
        re.MULTILINE,
    ),
    "lemma": re.compile(
        r"^\s*lemma\s+([^\s:(]+)\s*(?:\((.*?)\))?\s*:\s*([\s\S]*?)(?:\s*:=\s*([\s\S]*?))?"
        r"(?=\n\s*(?:theorem|lemma|def|axiom|constant|example|end)\b|\Z)",
        re.MULTILINE,
    ),

    # def can be:
    #   def foo := ...
    #   def foo (x) := ...
    #   def foo (x) : T := ...
    "def": re.compile(
        r"^\s*def\s+([^\s:(]+)\s*(?:\((.*?)\))?\s*(?::\s*([\s\S]*?))?\s*:=\s*([\s\S]*?)"
        r"(?=\n\s*(?:theorem|lemma|def|axiom|constant|example|end)\b|\Z)",
        re.MULTILINE,
    ),

    # example:
    #   example : P := by ...
    #   example (x) : P := ...
    "example": re.compile(
        r"^\s*example\s*(?:\((.*?)\))?\s*:\s*([\s\S]*?)\s*:=\s*([\s\S]*?)"
        r"(?=\n\s*(?:theorem|lemma|def|axiom|constant|example|end)\b|\Z)",
        re.MULTILINE,
    ),

    # axiom/constant:
    "axiom": re.compile(
        r"^\s*axiom\s+([^\s:(]+)\s*(?:\((.*?)\))?\s*:\s*([\s\S]*?)"
        r"(?=\n\s*(?:axiom|constant|theorem|lemma|def|example|end)\b|\Z)",
        re.MULTILINE,
    ),
    "constant": re.compile(
        r"^\s*constant\s+([^\s:(]+)\s*(?:\((.*?)\))?\s*:\s*([\s\S]*?)"
        r"(?=\n\s*(?:axiom|constant|theorem|lemma|def|example|end)\b|\Z)",
        re.MULTILINE,
    ),
}


def _clean_logic(text: Any) -> str:
    """Normalize whitespace but preserve explicit newlines."""
    if not isinstance(text, str):
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def parse_lean_file(lean_text: str) -> List[Dict[str, str]]:
    """
    Parses raw Lean source code into a list of symbolic declaration dicts
    in source-order.
    """
    hits: List[tuple[int, str, re.Match]] = []

    for kind, pattern in DECLARATION_PATTERNS.items():
        for m in pattern.finditer(lean_text):
            hits.append((m.start(), kind, m))

    # Preserve file order
    hits.sort(key=lambda x: x[0])

    decls: List[Dict[str, str]] = []

    for _, kind, match in hits:
        if kind in ("axiom", "constant"):
            name = match.group(1).strip()
            params = (match.group(2) or "").strip()
            logic = _clean_logic(match.group(3))
            body = ""

        elif kind == "example":
            params = (match.group(1) or "").strip()
            name = "example"
            logic = _clean_logic(match.group(2) or "")
            body = (match.group(3) or "").strip()

        elif kind == "def":
            name = match.group(1).strip()
            params = (match.group(2) or "").strip()
            # type is optional for defs
            logic = _clean_logic(match.group(3) or "")
            body = (match.group(4) or "").strip()

        else:  # theorem / lemma
            name = match.group(1).strip()
            params = (match.group(2) or "").strip()
            logic = _clean_logic(match.group(3) or "")
            body = (match.group(4) or "").strip()

        decls.append(
            {
                "symbol": f"⟦ {kind.capitalize()} ⟧",
                "name": name,
                "params": params,
                "logic": logic,
                "logic_raw": logic,
                "body": body,
            }
        )

    # Notation extraction (kept)
    notation_pattern = re.compile(r"^\s*notation\s+([^\n]+)", re.MULTILINE)
    for match in notation_pattern.finditer(lean_text):
        decls.append({
            "symbol": "⟦ Notation ⟧",
            "name": match.group(1).strip(),
            "params": "",
            "logic": "",
            "logic_raw": "",
            "body": "",
        })

    return decls


def parse_single_declaration(block: str) -> Dict[str, str]:
    """
    Parses a single Lean declaration block into symbolic fields.
    """
    for kind, pattern in DECLARATION_PATTERNS.items():
        match = pattern.search(block)
        if not match:
            continue

        if kind in ("axiom", "constant"):
            logic = _clean_logic(match.group(3))
            return {
                "symbol": f"⟦ {kind.capitalize()} ⟧",
                "name": match.group(1).strip(),
                "params": (match.group(2) or "").strip(),
                "logic": logic,
                "logic_raw": logic,
                "body": "",
            }

        if kind == "example":
            logic = _clean_logic(match.group(2) or "")
            return {
                "symbol": "⟦ Example ⟧",
                "name": "example",
                "params": (match.group(1) or "").strip(),
                "logic": logic,
                "logic_raw": logic,
                "body": (match.group(3) or "").strip(),
            }

        if kind == "def":
            logic = _clean_logic(match.group(3) or "")
            return {
                "symbol": "⟦ Def ⟧",
                "name": match.group(1).strip(),
                "params": (match.group(2) or "").strip(),
                "logic": logic,
                "logic_raw": logic,
                "body": (match.group(4) or "").strip(),
            }

        # theorem/lemma
        logic = _clean_logic(match.group(3) or "")
        return {
            "symbol": f"⟦ {kind.capitalize()} ⟧",
            "name": match.group(1).strip(),
            "params": (match.group(2) or "").strip(),
            "logic": logic,
            "logic_raw": logic,
            "body": (match.group(4) or "").strip(),
        }

    return {}


def parse_proof_dir(directory: str) -> List[Dict[str, str]]:
    """
    Recursively scans a directory for .lean files, parses them,
    and returns a flat list of declaration dicts.
    NOTE: Do NOT mark 'proved' here — only Lean verification should do that.
    """
    directory_path = Path(directory)
    if not directory_path.exists():
        print(f"[LeanParser] Directory not found: {directory}")
        return []

    all_declarations: List[Dict[str, str]] = []

    for lean_file in directory_path.rglob("*.lean"):
        try:
            text = lean_file.read_text(encoding="utf-8")
            decls = parse_lean_file(text)
            for d in decls:
                d["source_file"] = str(lean_file)
                d["status"] = "unverified"  # ✅ never lie here
            all_declarations.extend(decls)
            print(f"[LeanParser] Parsed {len(decls)} decls from {lean_file}")
        except Exception as e:
            print(f"[LeanParser] Failed to parse {lean_file}: {e}")

    print(f"[LeanParser] Total parsed declarations: {len(all_declarations)}")
    return all_declarations


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python lean_parser.py <path_to_file.lean>")
        sys.exit(1)

    lean_path = sys.argv[1]
    try:
        with open(lean_path, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        print(f"❌ Failed to read {lean_path}: {e}")
        sys.exit(1)

    decls = parse_lean_file(text)

    print("\n=== Parsed Declarations ===")
    for d in decls:
        print(f"* {d['symbol']} {d['name']}")
        if d.get("params"):
            print(f"  Params: {d['params']}")
        print(f"  Logic: {d['logic']}")
        if d["body"]:
            print(f"  Body: {d['body'][:60]}{'...' if len(d['body']) > 60 else ''}")
        print()

    try:
        from backend.routes.ws.glyphnet_ws import emit_websocket_event
        emit_websocket_event(
            "lean_parser_result",
            {"path": lean_path, "count": len(decls), "items": [d.get("name") for d in decls]},
        )
        print(f"[📡] Sent lean_parser_result for {len(decls)} items via WS")
    except Exception:
        pass