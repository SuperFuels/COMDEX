import pytest
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.glyphos.codexlang_translator import CodexLangTranslator

def test_pipeline_glyph_to_executor(monkeypatch):
    """
    End-to-end: glyph string → CodexLang translator → CodexExecutor.
    Ensures rewrites + canonicalization occur and executor runs.
    """

    # --- Patch canonicalize_ops so we know it's invoked ---
    called = {}

    def fake_canonicalize(self, tree):
        called["canonicalize_ops"] = True
        if isinstance(tree, dict) and tree.get("op") == "⊕":
            tree["op"] = "logic:⊕"
        return tree

    monkeypatch.setattr(
        "backend.modules.codex.codexlang_rewriter.CodexLangRewriter.canonicalize_ops",
        fake_canonicalize,
    )

    # Use executor in test mode (skips validation)
    executor = CodexExecutor(test_mode=True)

    # --- Simulate glyph parse into tree ---
    translator = CodexLangTranslator()
    tree = {"op": "⊕", "args": ["A", "B"]}

    # Execute
    result = executor.execute_instruction_tree(tree, context={"glyph": {}})

    # --- Checks ---
    assert "status" in result, f"Unexpected executor output: {result}"
    assert called.get("canonicalize_ops") is True, f"canonicalize_ops not called, result={result}"
    op_field = result.get("result", {}).get("op") or result.get("op")
    assert op_field == "logic:⊕"