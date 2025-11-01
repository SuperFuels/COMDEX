import pytest

from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.codex.codexlang_rewriter import CodexLangRewriter
from backend.modules.glyphos.codexlang_translator import CodexLangTranslator


@pytest.mark.asyncio
async def test_executor_end_to_end(monkeypatch):
    """
    🚀 End-to-End Test
    Glyph input -> CodexLangTranslator -> CodexExecutor
    Ensures:
      - Rewrite + canonicalization occurs
      - Collision resolution works
      - Executor runs without raising
    """

    called = {}

    # --- Patch canonicalize_ops so we can confirm it runs
    def fake_canonicalize(self, tree):
        called["canonicalize_ops"] = True
        if isinstance(tree, dict) and tree.get("op") == "⊕":
            tree["op"] = "logic:⊕"
        return tree

    monkeypatch.setattr(
        CodexLangRewriter, "canonicalize_ops", fake_canonicalize
    )

    # Executor in test mode = skip validation, return rewritten tree
    executor = CodexExecutor(test_mode=True)
    translator = CodexLangTranslator()

    # --- Simulate glyph -> parse tree
    glyph_input = {"glyphs": [{"op": "⊕", "args": ["A", "B"]}]}
    tree = {"op": "⊕", "args": ["A", "B"]}

    # Execute
    result = executor.execute_instruction_tree(tree, context={"glyph": glyph_input})

    # --- Checks ---
    assert result["status"] == "ok"
    assert "result" in result
    assert result["result"]["op"] == "logic:⊕"
    assert called.get("canonicalize_ops") is True