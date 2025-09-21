# File: backend/modules/lean/lean_parser.py

import re
from typing import List, Dict

# Patterns for different Lean declarations
DECLARATION_PATTERNS = {
    "theorem": re.compile(r"\btheorem\s+([a-zA-Z0-9_']+)\s*(:.*?)?:\s*(.*?)\s*:=\s*(.+)", re.DOTALL),
    "lemma":   re.compile(r"\blemma\s+([a-zA-Z0-9_']+)\s*(:.*?)?:\s*(.*?)\s*:=\s*(.+)", re.DOTALL),
    "def":     re.compile(r"\bdef\s+([a-zA-Z0-9_']+)\s*(:.*?)?:\s*(.*?)\s*:=\s*(.+)", re.DOTALL),
    "example": re.compile(r"\bexample\s+([a-zA-Z0-9_']*)\s*:?(\s*.*?)?\s*:=\s*(.+)", re.DOTALL),
    # Axioms and constants: often only a type, no :=
    "axiom":   re.compile(r"\baxiom\s+([a-zA-Z0-9_']+)\s*:\s*(.+)", re.DOTALL),
    "constant":re.compile(r"\bconstant\s+([a-zA-Z0-9_']+)\s*:\s*(.+)", re.DOTALL),
}


def parse_lean_file(lean_text: str) -> List[Dict[str, str]]:
    """
    Parses raw Lean source code into a list of symbolic declaration dicts.

    Returns:
        List[Dict] — each dict includes:
            • symbol: "⟦ Theorem ⟧" / "⟦ Lemma ⟧" / "⟦ Axiom ⟧" / "⟦ Constant ⟧" / etc.
            • name: identifier
            • logic: type / statement
            • body: proof content (may be empty for axioms/constants)
    """
    decls = []

    for kind, pattern in DECLARATION_PATTERNS.items():
        for match in pattern.finditer(lean_text):
            if kind in ("axiom", "constant"):
                # Axioms/constants have no body, just type
                name, logic = match.group(1).strip(), match.group(2).strip()
                body = ""
            elif kind == "example":
                name = match.group(1).strip() or "example"
                logic = (match.group(2) or "").strip()
                body = match.group(3).strip()
            else:
                name = match.group(1).strip()
                logic = match.group(3).strip()
                body = match.group(4).strip()

            decls.append({
                "symbol": f"⟦ {kind.capitalize()} ⟧",
                "name": name,
                "logic": logic,
                "body": body
            })

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
                return {
                    "symbol": f"⟦ {kind.capitalize()} ⟧",
                    "name": match.group(1).strip(),
                    "logic": match.group(2).strip(),
                    "body": ""
                }
            elif kind == "example":
                return {
                    "symbol": "⟦ Example ⟧",
                    "name": match.group(1).strip() or "example",
                    "logic": (match.group(2) or "").strip(),
                    "body": match.group(3).strip()
                }
            else:
                return {
                    "symbol": f"⟦ {kind.capitalize()} ⟧",
                    "name": match.group(1).strip(),
                    "logic": match.group(3).strip(),
                    "body": match.group(4).strip()
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
        emit_websocket_event("lean_parser_result", {
            "path": lean_path,
            "count": len(decls),
            "items": [d.get("name") for d in decls],
        })
        print(f"[📡] Sent lean_parser_result for {len(decls)} items via WS")
    except Exception:
        # Fail silent if WS unavailable
        pass