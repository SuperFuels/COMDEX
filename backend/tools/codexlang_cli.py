import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from backend.modules.symbolic.codex_ast_parser import parse_codexlang_to_ast
from backend.modules.symbolic.symbolic_parser import parse_raw_input_to_ast
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter, suggest_rewrite_candidates
from backend.modules.consciousness.logic_prediction_utils import detect_contradictions
from backend.modules.symbolic_engine.math_logic_kernel import LogicGlyph
from backend.modules.codex.codex_ast_encoder import encode_codex_ast_to_glyphs


def parse_and_format(expression: str) -> None:
    print(f"\n🧠 Parsing CodexLang: {expression}")
    ast = parse_codexlang_to_ast(expression)
    print("✅ AST:", json.dumps(ast, indent=2))

    rewriter = CodexLangRewriter()
    codex_form = rewriter.ast_to_codexlang(ast)
    simplified = rewriter.simplify(codex_form)

    print("\n🧾 Rewritten (raw):", codex_form)
    print("🔬 Simplified:", simplified)

    contradiction = detect_contradictions(ast)
    if contradiction:
        print("⚠️ Contradiction Detected:", json.dumps(contradiction, indent=2))
    else:
        print("✅ No contradictions found.")


def run_rewrite(expression: str) -> None:
    print(f"\n🧬 Attempting rewrite: {expression}")
    glyph = LogicGlyph.from_string(expression)
    candidates = suggest_rewrite_candidates(glyph.to_ast())

    if not candidates:
        print("ℹ️ No rewrite candidates found.")
        return

    rewriter = CodexLangRewriter()
    new_glyph = rewriter.apply_rewrite(glyph, candidates[0])

    print("📌 Original:", glyph.logic)
    print("🛠️ Rewritten:", new_glyph.logic)
    print("📚 Reason:", candidates[0].get("reason", "unspecified"))


def validate_container(path: Path) -> None:
    if not path.exists():
        print(f"❌ File not found: {path}")
        return

    with open(path) as f:
        container = json.load(f)

    count = 0
    rewritten = 0

    for section in ["glyphs", "glyph_grid", "electrons"]:
        items = container.get(section, [])
        for item in items:
            glyphs = item.get("glyphs") if isinstance(item.get("glyphs"), list) else [item]
            for glyph in glyphs:
                logic = glyph.get("logic")
                if not logic:
                    continue
                count += 1

                try:
                    glyph_obj = LogicGlyph.from_string(logic)
                    ast = glyph_obj.to_ast()

                    contradiction = detect_contradictions(ast)
                    if contradiction:
                        print(f"\n⚠️ Contradiction in {section}: {logic}")
                        print(json.dumps(contradiction, indent=2))

                    candidates = suggest_rewrite_candidates(ast)
                    if candidates:
                        new_glyph = CodexLangRewriter().apply_rewrite(glyph_obj, candidates[0])
                        print(f"\n🧬 Rewrite in {section}:\n- From: {logic}\n- To:   {new_glyph.logic}")
                        rewritten += 1

                except Exception as e:
                    print(f"\n❌ Failed to process glyph in {section}: {e}")

    print(f"\n📦 Container: {path.name}")
    print(f"🔢 Total glyphs checked: {count}")
    print(f"🧠 Rewrites suggested: {rewritten}")


def main():
    parser = argparse.ArgumentParser(description="CodexLang Symbolic CLI Tool")
    parser.add_argument("--expr", type=str, help="Raw CodexLang expression to parse")
    parser.add_argument("--rewrite", type=str, help="CodexLang expression to rewrite")
    parser.add_argument("--container", type=str, help="Path to .dc.json container to validate")

    args = parser.parse_args()

    if args.expr:
        parse_and_format(args.expr)
    elif args.rewrite:
        run_rewrite(args.rewrite)
    elif args.container:
        validate_container(Path(args.container))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()