#!/usr/bin/env python3
"""
CodexLang CLI Linter

Validate glyph files:
- Detect ambiguous operators needing resolver
- Flag use of explicit aliases
- Ensure canonicalization works
"""

import sys
import argparse
from pathlib import Path

from backend.modules.glyphos.codexlang_translator import parse_codexlang_string, translate_node
from backend.modules.codex.collision_resolver import is_collision, ALIASES


def lint_code(code: str) -> int:
    """Lint a glyph string. Returns exit code (0=ok, 1=issues)."""
    parsed = parse_codexlang_string(code)
    if not parsed:
        print("❌ Parse error")
        return 1

    action = parsed.get("action", {})
    issues = []

    def walk(node):
        if isinstance(node, dict) and "op" in node:
            op = node["op"]

            # Alias detection
            if op in ALIASES.values() or op in ALIASES:
                issues.append(f"Alias used: {op}")

            # Collision detection
            raw_symbol = op.split(":")[-1] if ":" in op else op
            if is_collision(raw_symbol):
                issues.append(f"⚠️ Collision: {raw_symbol}")

            for arg in node.get("args", []):
                walk(arg)

    walk(action)

    if issues:
        for issue in issues:
            print(issue)
        return 1

    print("✅ OK")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="CodexLang Glyph Linter")
    parser.add_argument("file", help="Glyph file to lint, or - for stdin")
    args = parser.parse_args(argv)

    if args.file == "-":
        code = sys.stdin.read()
    else:
        code = Path(args.file).read_text(encoding="utf-8")

    return lint_code(code)


if __name__ == "__main__":
    sys.exit(main())