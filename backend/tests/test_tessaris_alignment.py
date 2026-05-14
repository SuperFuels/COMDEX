import pytest

# Dummy Tessaris stub
class DummyTessaris:
    def extract_intents_from_glyphs(self, glyphs, origin=None):
        return [{"intent": "mock_intent", "origin": origin or "unknown"}]

@pytest.fixture
def patch_tessaris(monkeypatch):
    monkeypatch.setattr(
        "backend.modules.codex.codex_executor._get_tessaris",
        lambda: DummyTessaris()
    )

def test_tessaris_alignment_injection(patch_tessaris):
    from backend.modules.codex.codex_executor import CodexExecutor

    executor = CodexExecutor()
    glyphs = {"glyphs": [{"text": "⊕ sample"}]}
    context = {"source": "photon", "glyph": glyphs}

    result = executor.execute_instruction_tree({"op": "noop"}, context=context)

    assert "intents" in context
    assert context["intents"][0]["intent"] == "mock_intent"
    assert context["intents"][0]["origin"] == "photon"
