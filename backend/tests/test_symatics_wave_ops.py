import pytest
from backend.symatics.symatics_dispatcher import evaluate_symatics_expr
from backend.modules.sqi.sqi_scorer import compute_entropy
from backend.modules.glyphvault.soul_law_validator import verify_transition

# --- Fixtures ---
@pytest.fixture
def base_context():
    return {"container_id": "test_symatics_01", "source": "unit_test"}

# --- Core Operator Tests ---
def test_superpose_wave_op(base_context):
    expr = {"op": "⊕", "inputs": ["Φ₁", "Φ₂"]}
    result = evaluate_symatics_expr(expr, context=base_context)
    assert result is not None
    assert "wave" in str(result)
    assert compute_entropy(result) > 0

def test_entangle_wave_op(base_context):
    expr = {"op": "↔", "inputs": ["Ψ₁", "Ψ₂"]}
    result = evaluate_symatics_expr(expr, context=base_context)
    assert result is not None
    assert "entangled" in str(result).lower()

def test_measurement_op(base_context):
    expr = {"op": "μ", "inputs": ["Ψ₁"]}
    result = evaluate_symatics_expr(expr, context=base_context)
    assert result is not None
    assert isinstance(result, (dict, list))

def test_resonance_op(base_context):
    expr = {"op": "⟲", "inputs": ["Ω₁"]}
    result = evaluate_symatics_expr(expr, context=base_context)
    assert result is not None

# --- SQI Stability Check ---
def test_sqi_consistency(base_context):
    expr = {"op": "⊕", "inputs": ["Φ₁", "Φ₂"]}
    result = evaluate_symatics_expr(expr, context=base_context)
    pre = compute_entropy(expr)
    post = compute_entropy(result)
    assert abs(post - pre) < pre * 0.5  # no wild divergence

# --- SoulLaw Veto ---
def test_soullaw_veto_triggers(base_context):
    codex_str = "Ψ₁ ⊕ Ψ₂"
    # assume context violates constraint for testing
    base_context["allow_collapse"] = False
    allowed = verify_transition(base_context, codex_str)
    assert allowed is False