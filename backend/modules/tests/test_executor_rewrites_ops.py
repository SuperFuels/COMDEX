import pytest
from backend.modules.codex.codex_executor import CodexExecutor

def test_executor_rewrites_symatics_to_canonical(monkeypatch):
    called = {}

    def fake_rewrite(tree):
        called["canonicalize_ops"] = True
        if tree.get("op") == "⊕":
            tree["op"] = "logic:⊕"
        return tree

    monkeypatch.setattr(
        "backend.modules.codex.codexlang_rewriter.CodexLangRewriter.canonicalize_ops",
        lambda self, t: fake_rewrite(t),
    )

    monkeypatch.setattr(
        "backend.symatics.symatics_to_codex_rewriter.rewrite_symatics_to_codex",
        lambda t: t,
    )

    executor = CodexExecutor(test_mode=True)

    tree = {"op": "⊕", "args": ["A", "B"]}
    result = executor.execute_instruction_tree(tree, context={})

    assert "status" in result and result["status"] == "ok"
    assert called.get("canonicalize_ops") is True
    assert result["result"]["op"] == "logic:⊕"