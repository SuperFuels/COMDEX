import pytest
from backend.modules.codex.codex_executor import CodexExecutor
from backend.modules.holograms.hst_generator import HSTGenerator

@pytest.fixture
def codex_executor():
    return CodexExecutor()

@pytest.fixture
def base_context():
    return {"container_id": "test_hst_cycle", "source": "integration_test"}

def test_codex_to_hst_cycle(codex_executor, base_context):
    codex_expr = "Φ₁ ⊕ Φ₂"
    result = codex_executor.execute_codex_program(codex_expr, context=base_context)
    assert "telemetry" in result
    assert "symbolic_score" in result["telemetry"]
    assert result["telemetry"]["symbolic_score"] >= 0

    # Generate holographic snapshot
    hst = HSTGenerator()
    snapshot = hst.capture_field_snapshot()
    assert isinstance(snapshot, dict)
    assert "nodes" in snapshot
    assert len(snapshot["nodes"]) >= 0