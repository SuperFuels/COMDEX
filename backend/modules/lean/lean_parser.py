# File: backend/modules/lean/lean_parser.py
"""
Lean Parser → CodexGlyph Translator
──────────────────────────────────────────────
Parses Lean source files (axioms, theorems, defs, etc.) into symbolic structures
usable by Tessaris and CodexGlyph translators.
"""

import re
from typing import List, Dict

# === Declaration patterns (multi-line + Unicode-safe) ===
DECLARATION_PATTERNS = {
    "theorem": re.compile(
        r"^\s*theorem\s+([^\s:]+)\s*(?:\((.*?)\))?\s*:\s*([\s\S]+?)(?=\n\s*(?:theorem|lemma|def|axiom|constant|example|end)\b|\Z)",
        re.MULTILINE,
    ),
    "lemma": re.compile(
        r"^\s*lemma\s+([^\s:]+)\s*(?:\((.*?)\))?\s*:\s*([\s\S]+?)(?=\n\s*(?:theorem|lemma|def|axiom|constant|example|end)\b|\Z)",
        re.MULTILINE,
    ),
    "def": re.compile(
        r"^\s*def\s+([^\s:]+)\s*(?:\((.*?)\))?\s*:\s*([\s\S]+?)(?=\n\s*(?:theorem|lemma|def|axiom|constant|example|end)\b|\Z)",
        re.MULTILINE,
    ),
    "example": re.compile(
        r"^\s*example\s*([^\s:]*)\s*:?([\s\S]*?)\s*:=\s*([\s\S]+?)(?=\n\s*(?:theorem|lemma|def|axiom|constant|example|end)\b|\Z)",
        re.MULTILINE,
    ),
    "axiom": re.compile(
        r"^\s*axiom\s+([^\s:]+)\s*:\s*([\s\S]+?)(?=\n\s*(?:--|axiom|constant|theorem|lemma|def|example|end)\b|\Z)",
        re.MULTILINE,
    ),
    "constant": re.compile(
        r"^\s*constant\s+([^\s:]+)\s*:\s*([\s\S]+?)(?=\n\s*(?:--|axiom|constant|theorem|lemma|def|example|end)\b|\Z)",
        re.MULTILINE,
    ),
}


# === Helpers ===
def _clean_logic(text: str) -> str:
    """Normalize whitespace but preserve explicit newlines."""
    if not isinstance(text, str):
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


# === Main Parser ===
def parse_lean_file(lean_text: str) -> List[Dict[str, str]]:
    """
    Parses raw Lean source code into a list of symbolic declaration dicts.
    """
    decls: List[Dict[str, str]] = []

    for kind, pattern in DECLARATION_PATTERNS.items():
        for match in pattern.finditer(lean_text):
            print(f"[DEBUG] matched {kind} {match.group(1).strip()}")

            if kind in ("axiom", "constant"):
                name = match.group(1).strip()
                logic = _clean_logic(match.group(2))
                body = ""

            elif kind == "example":
                name = match.group(1).strip() or "example"
                logic = _clean_logic(match.group(2) or "")
                body = match.group(3).strip()

            else:  # theorem / lemma / def
                name = match.group(1).strip()
                logic = _clean_logic(match.group(2) or "")
                body = match.group(3).strip()

            # Debug summary
            print(f"[DEBUG] {kind} matched → name={name!r}, logic={logic!r}")

            decls.append(
                {
                    "symbol": f"⟦ {kind.capitalize()} ⟧",
                    "name": name,
                    "logic": logic,
                    "logic_raw": logic,
                    "body": body,
                }
            )

    # === Notation extraction ===
    notation_pattern = re.compile(r'notation\s+([^\n]+)')
    for match in notation_pattern.finditer(lean_text):
        decls.append({
            "symbol": "⟦ Notation ⟧",
            "name": match.group(1).strip(),
            "logic": "",
            "logic_raw": "",
            "body": ""
        })

    return decls


# === Single block parser ===
def parse_single_declaration(block: str) -> Dict[str, str]:
    """
    Parses a single Lean declaration block into symbolic fields.
    """
    for kind, pattern in DECLARATION_PATTERNS.items():
        match = pattern.search(block)
        if match:
            if kind in ("axiom", "constant"):
                logic = _clean_logic(match.group(2))
                return {
                    "symbol": f"⟦ {kind.capitalize()} ⟧",
                    "name": match.group(1).strip(),
                    "logic": logic,
                    "logic_raw": logic,
                    "body": "",
                }
            elif kind == "example":
                logic = _clean_logic(match.group(2) or "")
                return {
                    "symbol": "⟦ Example ⟧",
                    "name": match.group(1).strip() or "example",
                    "logic": logic,
                    "logic_raw": logic,
                    "body": match.group(3).strip(),
                }
            else:  # theorem / lemma / def
                logic = _clean_logic(match.group(2) or "")
                return {
                    "symbol": f"⟦ {kind.capitalize()} ⟧",
                    "name": match.group(1).strip(),
                    "logic": logic,
                    "logic_raw": logic,
                    "body": match.group(3).strip(),
                }
    return {}


# === CLI Entry Point ===
if __name__ == "__main__":
    import sys, json

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
        print(f"• {d['symbol']} {d['name']}")
        print(f"  Logic: {d['logic']}")
        if d['body']:
            print(f"  Body: {d['body'][:60]}{'...' if len(d['body']) > 60 else ''}")
        print()

    # Optional JSON dump
    # print(json.dumps(decls, indent=2, ensure_ascii=False, sort_keys=True))

    try:
        from backend.routes.ws.glyphnet_ws import emit_websocket_event
        emit_websocket_event(
            "lean_parser_result",
            {"path": lean_path, "count": len(decls), "items": [d.get("name") for d in decls]},
        )
        print(f"[📡] Sent lean_parser_result for {len(decls)} items via WS")
    except Exception:
        pass