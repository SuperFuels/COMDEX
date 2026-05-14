import pytest
import json
import asyncio

# 🔐 Patch the vault manager to avoid real encryption during tests
from backend.modules.glyphvault import container_vault_integration

class DummyVaultManager:
    def save_container_glyph_data(self, glyph_data):
        return b"ENCRYPTED_DUMMY"  # ✅ Must return bytes, not str

container_vault_integration.vault_manager = DummyVaultManager()

# 🧠 Core imports
from backend.modules.patterns.codex_pattern_commands import (
    detect_pattern_in_container,
    mutate_pattern_in_container,
    predict_next_from_pattern
)
from backend.modules.patterns.symbolic_pattern_engine import SymbolicPatternEngine
from backend.modules.dna_chain.dc_handler import save_dc_container
from backend.modules.codex.codex_executor import codex_executor
from backend.modules.patterns.pattern_registry import Pattern, registry

# ✅ Paths for test container and mutation output
TEST_CONTAINER_PATH = "backend/modules/dimensions/containers/test_pattern_container.dc.json"
MUTATED_CONTAINER_ID = "test_container_mutated"

@pytest.fixture
def container():
    with open(TEST_CONTAINER_PATH, "r") as f:
        container = json.load(f)
    assert "symbolic_tree" in container, "Missing symbolic tree in container"
    container.setdefault("patterns", [])
    container.setdefault("tick", 0)
    container.setdefault("cubes", {})  # ✅ Required for vault integration
    container["id"] = container.get("container_id", "test_container_001")
    return container

@pytest.fixture(autouse=True)
def preload_test_pattern(container=None):
    """
    Register XOR pattern directly into the shared pattern registry.
    """
    registry.clear()

    xor_glyphs = [
        {"type": "variable", "value": "a"},
        {"type": "operator", "value": "⊕"},
        {"type": "variable", "value": "b"},
    ]

    xor_pattern = Pattern(
        name="XOR Pattern",
        glyphs=xor_glyphs,
        pattern_type="expression",
        trigger_logic="",
        source_container="test_container_001"
    )

    registry.register(xor_pattern)

    # ✅ Confirm pattern was registered
    print("✅ Loaded patterns:", [p.to_dict() for p in registry.get_all()])

    # 🧪 Print test container glyphs if available
    if container:
        print("🧪 Test container glyphs:", container.get("glyphs"))

def test_detect_pattern(container):
    pattern_matches = detect_pattern_in_container(container)
    assert isinstance(pattern_matches, list)
    assert len(pattern_matches) > 0, "No patterns detected"
    assert all("pattern_id" in match or "name" in match for match in pattern_matches)

def test_mutate_pattern(container):
    # 🧪 Debug print statements
    print("🧪 Test container glyphs:", container.get("glyphs"))
    print("🧪 Loaded patterns:", [p.to_dict() for p in registry.get_all()])

    # ✅ Fix: extract glyphs properly before detection
    engine = SymbolicPatternEngine()
    glyphs = container.get("glyphs", [])
    patterns = engine.detect_patterns(glyphs, container_id=container.get("container_id"), container=container)

    assert len(patterns) > 0, "No matching patterns found for mutation test"

    result = mutate_pattern_in_container(container)

    assert isinstance(result, dict), "Mutation result is not a dictionary"
    assert "mutated" in result, f"Mutation failed: {result}"

def test_predict_next(container):
    predictions = predict_next_from_pattern(container)
    assert isinstance(predictions, list)
    for p in predictions:
        assert "glyph" in p or "label" in p

@pytest.mark.asyncio
async def test_codexlang_pattern_command_execution():
    code = """
    pattern_engine::detect()
    pattern_engine::mutate()
    pattern_engine::predict_next()
    """
    context = {"container_id": "test_codex_container", "test_mode": True}
    result = codex_executor.execute_codexlang(code, context=context)
    if asyncio.iscoroutine(result):
        result = await result
    assert result.get("status") in ("ok", "success"), f"CodexLang pattern command failed: {result}"

def test_save_container_after_mutation(container):
    result = mutate_pattern_in_container(container)
    assert "mutated" in result, f"Save mutation failed: {result}"
    save_dc_container(MUTATED_CONTAINER_ID, container)