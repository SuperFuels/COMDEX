# File: backend/modules/glyphos/glyph_tokenizer.py
# 🔣 Tokenizer for parsing raw "symbol" text fields (e.g., "x + 2") into glyph tokens
# Used in pattern matching, SQI scoring, and symbolic reasoning layers

import re
from typing import List, Dict

# ─── Main Tokenizer Function ────────────────────────────────────────────────────

def tokenize_symbol_text_to_glyphs(text: str) -> List[Dict[str, str]]:
    """
    Converts a raw string like 'x + 2' into structured glyph tokens:
        Input:  "x + 2"
        Output: [
            {'type': 'variable', 'value': 'x'},
            {'type': 'operator', 'value': '+'},
            {'type': 'number', 'value': '2'}
        ]
    """
    tokens: List[Dict[str, str]] = []

    # IMPORTANT: put multi-character tokens first (longest-match wins), then single-char classes.
    # Added Phase-7 symbolic opcodes: ∇ (numeric), ∇c (compress alias), ↔, ⟲, ⧖, ->, ✦
    pattern = (
        r"(∇c|↔|⟲|⧖|->|✦|∇|"                # symbolic multi/single glyph ops (new)
        r"[A-Za-z_]\w*|"                     # identifiers
        r"\d+\.?\d*|"                        # numbers
        r"==|!=|<=|>=|\*\*|"                 # multi-char ASCII ops
        r"[\+\-\*/\^=<>!()]|"                # single-char ASCII ops/parens
        r"[≡⊕⊗<=>=∧∨¬:,])"                    # other symbolic singles we already supported
    )

    for match in re.finditer(pattern, text):
        token = match.group(0)
        token_type = classify_token(token)
        tokens.append({"type": token_type, "value": token})

    return tokens


# ─── Helper: Token Classifier ───────────────────────────────────────────────────

def classify_token(token: str) -> str:
    """
    Classifies a token as one of: variable, number, operator, paren, function, keyword, string, or unknown.
    """
    # number
    if re.fullmatch(r"\d+\.?\d*", token):
        return "number"

    # string literal
    if re.fullmatch(r"'[^']*'|\"[^\"]*\"", token):
        return "string"

    # keywords
    if token in {"if", "return"}:
        return "keyword"

    # known math functions
    if token in {"sin", "cos", "tan", "log", "exp", "sqrt", "abs"}:
        return "function"

    # identifier / variable
    if re.fullmatch(r"[A-Za-z_]\w*", token):
        return "variable"

    # operators (ASCII + symbolic)
    # Added Phase-7 ops here: ∇, ∇c, ↔, ⟲, ⧖, ->, ✦
    if token in {
        # ASCII
        "+", "-", "*", "/", "^", "=", "==", "!=", "<", ">", "<=", ">=", "**",
        # symbolic (existing)
        "⊕", "⊗", "≡", "<=", ">=", "∧", "∨", "¬",
        # symbolic (new)
        "∇", "∇c", "↔", "⟲", "⧖", "->", "✦",
    }:
        return "operator"

    # parens
    if token in {"(", ")"}:
        return "paren"

    # punctuation
    if token in {":", ","}:
        return "symbol"

    return "unknown"


# ─── Optional Preview CLI ───────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        "x + 2",
        "y = mx + b",
        "3.14 * r^2",
        "(a + b) / c",
        "delta != gamma",
        "⊕(x, y) ≡ z",
        "sin(theta) + cos(phi)",
        "if x > 0: return x**2",
        "overwrite('memory')",
        "x**2 + y**2 == z**2",
        # Phase-7 glyph opcodes
        "⊕ ∇ ↔ ⟲ ⧖ -> ✦",
        "∇c(a, b) ↔ c",
    ]

    for case in test_cases:
        print(f"\n🔤 Input: {case}")
        tokens = tokenize_symbol_text_to_glyphs(case)
        for t in tokens:
            print(f"  - {t['type']:>8}: {t['value']}")