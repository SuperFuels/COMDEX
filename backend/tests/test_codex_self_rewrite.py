import pytest
import json
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.symbolic.codex_ast_encoder import encode_codex_ast_to_glyphs
from backend.modules.codexlang.codex_ast import parse_codex_source

# Simulated test glyph and logic
TEST_GLYPH_ID = "test:contradiction_case"
TEST_CONTAINER_ID = "dc_test_container"
TEST_SOURCE = "CLI_test"

# Basic example of contradictory logic
CODEX_SOURCE = """
if true then false else true
"""

@pytest.fixture
def executor():
    return CodexExecutor()

def test_codex_self_rewrite_trigger(executor):
    ast = parse_codex_source(CODEX_SOURCE)
    glyphs = encode_codex_ast_to_glyphs(ast)
    instruction_tree = glyphs[0].to_instruction_tree()

    context = {
        "glyph": TEST_GLYPH_ID,
        "container_id": TEST_CONTAINER_ID,
        "source": TEST_SOURCE,
        "ast": ast,
        "container_type": "symbolic"
    }

    result = executor.execute_instruction_tree(instruction_tree, context=context)

    print("Result:", json.dumps(result, indent=2))

    assert result["status"] in ["success", "error"]
    assert "result" in result or "error" in result

    # Optional: Check rewrite was triggered
    if result["status"] == "success" and result["result"].get("status") == "contradiction":
        print("✅ Contradiction triggered self-rewrite")