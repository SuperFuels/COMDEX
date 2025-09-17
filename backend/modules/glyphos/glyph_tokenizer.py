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
    tokens = []

    # Extended regex: includes symbolic ops, **, and punctuation
    pattern = r"([A-Za-z_]\w*|\d+\.?\d*|==|!=|<=|>=|\*\*|[\+\-\*/\^=<>!()]|[≡⊕⊗≤≥∧∨¬:,])"

    for match in re.finditer(pattern, text):
        token = match.group(0)
        token_type = classify_token(token)
        tokens.append({
            "type": token_type,
            "value": token
        })

    return tokens


# ─── Helper: Token Classifier ───────────────────────────────────────────────────

def classify_token(token: str) -> str:
    """
    Classifies a token as one of: variable, number, operator, paren, function, keyword, string, or unknown.
    """
    if re.fullmatch(r"\d+\.?\d*", token):
        return "number"

    # Known math/logic functions
    known_functions = {"sin", "cos", "tan", "log", "exp", "sqrt", "abs"}
    if token in known_functions:
        return "function"

    # Special keywords
    if token in {"if", "return"}:
        return "keyword"

    # Quoted string
    if re.fullmatch(r"'[^']*'|\"[^\"]*\"", token):
        return "string"

    # Regular variables
    if re.fullmatch(r"[A-Za-z_]\w*", token):
        return "variable"

    # Supported operators (classic + symbolic)
    if token in {
        "+", "-", "*", "/", "^", "=", "==", "!=", "<", ">", "<=", ">=", "**",
        "⊕", "⊗", "≡", "≤", "≥", "∧", "∨", "¬"
    }:
        return "operator"

    # Normalize parens
    if token in {"(", ")"}:
        return "paren"

    # Misc symbols (e.g., colons for Python-style syntax)
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
        "x**2 + y**2 == z**2"
    ]

    for case in test_cases:
        print(f"\n🔤 Input: {case}")
        tokens = tokenize_symbol_text_to_glyphs(case)
        for t in tokens:
            print(f"  - {t['type']:>8}: {t['value']}")