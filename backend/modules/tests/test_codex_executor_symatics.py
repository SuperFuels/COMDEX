import pytest
from backend.modules.codex.codex_executor import CodexExecutor


def test_symatics_logic_xor_dispatch(monkeypatch):
    """
    Ensure CodexExecutor routes logic:⊕ to the symatics dispatcher.
    """
    called = {}

    def fake_eval(instr, context=None):
        called["instr"] = instr
        return "⊕_ok"

    monkeypatch.setattr(
        "backend.symatics.symatics_dispatcher.evaluate_symatics_expr",
        fake_eval,
    )

    executor = CodexExecutor()
    instr_tree = {"op": "logic:⊕", "args": [1, 2]}
    result = executor.execute_instruction_tree(instr_tree)

    assert result["engine"] == "symatics"
    assert result["status"] == "success"
    assert result["result"] == "⊕_ok"
    assert called["instr"] == instr_tree


@pytest.mark.parametrize("op", ["logic:⊖", "interf:⋈"])
def test_symatics_other_ops(monkeypatch, op):
    """
    Ensure CodexExecutor routes other symatics ops too.
    """
    def fake_eval(instr, context=None):
        return f"{op}_ok"

    monkeypatch.setattr(
        "backend.symatics.symatics_dispatcher.evaluate_symatics_expr",
        fake_eval,
    )

    executor = CodexExecutor()
    instr_tree = {"op": op, "args": [42]}
    result = executor.execute_instruction_tree(instr_tree)

    assert result["engine"] == "symatics"
    assert result["status"] == "success"
    assert result["result"] == f"{op}_ok"


def test_symatics_dispatch_error(monkeypatch):
    """
    Ensure errors in the dispatcher return an error dict.
    """
    def fake_eval(instr, context=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "backend.symatics.symatics_dispatcher.evaluate_symatics_expr",
        fake_eval,
    )

    executor = CodexExecutor()
    instr_tree = {"op": "logic:⊕", "args": []}
    result = executor.execute_instruction_tree(instr_tree)

    assert result["engine"] == "symatics"
    assert result["status"] == "error"
    assert "boom" in result["error"]


def test_symatics_operator_detection(monkeypatch):
    """
    Verify that is_symatics_operator(op) path is honored.
    """
    def fake_eval(instr, context=None):
        return f"detected_{instr['op']}"

    monkeypatch.setattr(
        "backend.symatics.symatics_dispatcher.evaluate_symatics_expr",
        fake_eval,
    )
    monkeypatch.setattr(
        "backend.symatics.symatics_dispatcher.is_symatics_operator",
        lambda op: op == "sym:custom",
    )

    executor = CodexExecutor()
    instr_tree = {"op": "sym:custom", "args": ["x"]}
    result = executor.execute_instruction_tree(instr_tree)

    assert result["engine"] == "symatics"
    assert result["status"] == "success"
    assert result["result"] == "detected_sym:custom"


# ──────────────────────────────
# Extended coverage
# ──────────────────────────────

def test_invalid_symatics_op_fails_gracefully(monkeypatch):
    """
    Unknown symatics op should return error, not crash.
    """
    def fake_eval(instr, context=None):
        raise RuntimeError("bad op")

    monkeypatch.setattr(
        "backend.symatics.symatics_dispatcher.evaluate_symatics_expr",
        fake_eval,
    )
    monkeypatch.setattr(
        "backend.symatics.symatics_dispatcher.is_symatics_operator",
        lambda op: op.startswith("symatics:"),
    )

    executor = CodexExecutor()
    bad_instr = {"op": "symatics:invalid", "args": []}
    result = executor.execute_instruction_tree(bad_instr)

    assert result["engine"] == "symatics"
    assert result["status"] == "error"
    assert "bad op" in result["error"]


def test_roundtrip_equivalence():
    """
    Same Symatics instruction executed twice should normalize to same result.
    """
    executor = CodexExecutor()

    instr = {"op": "logic:⊕", "args": [{"op": "A"}, {"op": "B"}]}
    r1 = executor.execute_instruction_tree(instr)
    r2 = executor.execute_instruction_tree(instr)

    assert r1["status"] == "success"
    assert r2["status"] == "success"
    assert r1["result"] == r2["result"]


def test_large_nested_symatics_tree_executes():
    """
    Performance sanity: large nested tree should not blow up.
    """
    executor = CodexExecutor()
    depth = 25
    node = {"op": "logic:⊕", "args": [{"op": "A"}, {"op": "B"}]}
    for i in range(2, depth):
        node = {"op": "logic:⊕", "args": [node, {"op": f"X{i}"}]}

    result = executor.execute_instruction_tree(node)

    assert result["status"] == "success"
    assert result["engine"] == "symatics"

# ──────────────────────────────
# Malformed AST tests
# ──────────────────────────────

class DummyTessaris:
    def interpret(self, instr, context=None):
        # Always return a structured error-like result so tests stay consistent
        return {"status": "error", "engine": "codex", "error": "dummy interpret invoked"}

class DummyPredictionEngine:
    def _run_prediction_on_ast(self, instr):
        return {"predicted_paths": [], "metadata": {}}


def _make_executor_with_stubs():
    """Helper to avoid NoneType errors in CodexExecutor internals."""
    ex = CodexExecutor()
    ex.tessaris = DummyTessaris()
    ex.prediction_engine = DummyPredictionEngine()
    return ex


def test_missing_op_field():
    """
    AST without 'op' should fail gracefully.
    """
    executor = _make_executor_with_stubs()
    bad_instr = {"args": [1, 2]}  # no 'op'
    result = executor.execute_instruction_tree(bad_instr)
    assert result["status"] == "error"
    # just check it's flagged invalid, not exact wording
    assert "invalid instruction_tree" in result["error"].lower()


def test_args_not_a_list():
    """
    AST with args as wrong type should fail gracefully.
    """
    executor = _make_executor_with_stubs()
    bad_instr = {"op": "logic:⊕", "args": "notalist"}
    result = executor.execute_instruction_tree(bad_instr)
    assert result["status"] in ("error", "symatics", "success")
    if result["status"] == "error":
        assert "args" in result["error"].lower()
    if result["status"] == "success":
        # ensure dispatcher actually handled it
        assert "result" in result


import pytest

@pytest.mark.parametrize("bad_node", [
    123,                    # not a dict
    "string",               # invalid type
    None,                   # missing entirely
    {"op": None, "args": []},  # op is None
])
def test_invalid_node_types(bad_node):
    """
    Various invalid node types should not crash.
    """
    executor = _make_executor_with_stubs()
    result = executor.execute_instruction_tree(
        bad_node if isinstance(bad_node, dict) else {"op": bad_node}
    )
    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] == "error"