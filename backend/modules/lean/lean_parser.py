import re
from typing import List, Dict

# Patterns for different Lean declarations (Unicode-safe)
DECLARATION_PATTERNS = {
    "theorem": re.compile(
        r"\btheorem\s+([^\s:]+)\s*:?([\s\S]*?)\s*:=\s*([\s\S]+?)(?=\n\s*(?:theorem|lemma|def|axiom|constant|example)\b|\Z)",
        re.MULTILINE,
    ),
    "lemma": re.compile(
        r"\blemma\s+([^\s:]+)\s*:?([\s\S]*?)\s*:=\s*([\s\S]+?)(?=\n\s*(?:theorem|lemma|def|axiom|constant|example)\b|\Z)",
        re.MULTILINE,
    ),
    "def": re.compile(
        r"\bdef\s+([^\s:]+)\s*:?([\s\S]*?)\s*:=\s*([\s\S]+?)(?=\n\s*(?:theorem|lemma|def|axiom|constant|example)\b|\Z)",
        re.MULTILINE,
    ),
    "example": re.compile(
        r"\bexample\s*([^\s:]*)\s*:?([\s\S]*?)\s*:=\s*([\s\S]+?)(?=\n\s*(?:theorem|lemma|def|axiom|constant|example)\b|\Z)",
        re.MULTILINE,
    ),
    "axiom": re.compile(
        r"^\s*axiom\s+([^\s:]+)\s*:\s*([\s\S]*?)(?=\n(?:\s*(?:--|axiom|constant|theorem|lemma|def|example)\b)|\Z)",
        re.MULTILINE,
    ),
    "constant": re.compile(
        r"^\s*constant\s+([^\s:]+)\s*:\s*([\s\S]*?)(?=\n(?:\s*(?:--|axiom|constant|theorem|lemma|def|example)\b)|\Z)",
        re.MULTILINE,
    ),
}


def _clean_logic(text: str) -> str:
    """Normalize whitespace but preserve explicit newlines."""
    if not isinstance(text, str):
        return ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def parse_lean_file(lean_text: str) -> List[Dict[str, str]]:
    """
    Parses raw Lean source code into a list of symbolic declaration dicts.
    """
    decls: List[Dict[str, str]] = []

    for kind, pattern in DECLARATION_PATTERNS.items():
        for match in pattern.finditer(lean_text):
            print(f"[DEBUG] matched {kind} {match.group(1).strip()} -> {repr(match.group(2).strip())}")
            if kind in ("axiom", "constant"):
                name = match.group(1).strip()
                logic = _clean_logic(match.group(2))

                # 🔍 DEBUG PRINT
                print(f"[DEBUG] {kind} matched → name={name!r}, logic={logic!r}")

                body = ""
            elif kind == "example":
                name = match.group(1).strip() or "example"
                logic = _clean_logic(match.group(2) or "")

                # 🔍 DEBUG PRINT
                print(f"[DEBUG] example matched → name={name!r}, logic={logic!r}")

                body = match.group(3).strip()
            else:  # theorem / lemma / def
                name = match.group(1).strip()
                logic = _clean_logic(match.group(2) or "")

                # 🔍 DEBUG PRINT
                print(f"[DEBUG] {kind} matched → name={name!r}, logic={logic!r}")

                body = match.group(3).strip()

            decls.append(
                {
                    "symbol": f"⟦ {kind.capitalize()} ⟧",
                    "name": name,
                    "logic": logic,
                    "logic_raw": logic,
                    "body": body,
                }
            )

    return decls


def parse_single_declaration(block: str) -> Dict[str, str]:
    """
    Parses a single Lean declaration block into symbolic fields.
    Handles theorem/lemma/def/example/axiom/constant.
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


# ─────────────────────────────
# Optional CLI Entry Point
# ─────────────────────────────
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

    # Print to stdout (always)
    print(json.dumps(decls, indent=2, ensure_ascii=False))

    # Optionally emit WebSocket event
    try:
        from backend.routes.ws.glyphnet_ws import emit_websocket_event

        emit_websocket_event(
            "lean_parser_result",
            {
                "path": lean_path,
                "count": len(decls),
                "items": [d.get("name") for d in decls],
            },
        )
        print(f"[📡] Sent lean_parser_result for {len(decls)} items via WS")
    except Exception:
        # Fail silent if WS unavailable
        pass