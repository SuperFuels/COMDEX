from backend.modules.symbolic.codex_ast_parser import parse_codexlang
from backend.modules.symbolic.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.symbolic.codex_ast_types import CodexAST
import os

# Path to the actual .codex file (not this .py file)
CODEXLANG_FILE = "backend/tests/test_glyphlogic_module.codex"

# Load raw CodexLang text
with open(CODEXLANG_FILE, "r", encoding="utf-8") as f:
    raw_codexlang = f.read()

# --- Split function blocks ---
functions = raw_codexlang.split("let ")

glyphs = []
for fn_block in functions:
    if fn_block.strip() == "":
        continue

    try:
        # Reconstruct full function text
        fn_text = "let " + fn_block.strip()
        fn_name = fn_block.split("=")[0].strip()

        print(f"\n🔍 Parsing: {fn_name}")

        # Parse to CodexAST
        ast: CodexAST = parse_codexlang(fn_text)
        print("✅ AST:", ast.to_dict())

        # Encode to glyphs
        encoded = encode_codex_ast_to_glyphs(ast)
        glyphs.append(encoded)

        print("✅ Encoded Glyphs:", encoded)

    except Exception as e:
        print(f"⚠️ Failed to parse '{fn_block[:30]}...': {e}")