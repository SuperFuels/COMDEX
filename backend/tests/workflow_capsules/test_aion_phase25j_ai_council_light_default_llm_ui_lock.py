from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = TEXT.index(f"function {name}")
    next_fn = TEXT.find("\nfunction ", start + len(f"function {name}"))
    if next_fn == -1:
        return TEXT[start:]
    return TEXT[start:next_fn]


def test_ai_council_is_light_not_dark():
    block = function_block("renderAionProviderCouncilPanel")

    assert 'data-aion-phase25j-provider-council="true"' in block
    assert "background:transparent;" in block
    assert "background:#1f201d" not in block


def test_gemma_is_default_free_local_llm():
    state_block = function_block("getAionProviderCouncilState")

    assert 'String(window.localStorage?.getItem("aion.defaultReasoningProvider") || "gemma")' in state_block
    assert 'key: "gemma"' in state_block
    assert 'label: "Gemma"' in state_block
    assert 'role: "Free local LLM"' in state_block
    assert "default_llm" in state_block


def test_provider_cards_support_default_key_and_remove_actions():
    block = function_block("renderAionProviderCouncilPanel")

    assert "Default LLM:" in block
    assert "data-aion-provider-council-default" in block
    assert "data-aion-provider-council-add-selected-model" in block
    assert "data-aion-provider-council-remove" in block
    assert "data-aion-provider-council-add-selected-model" in block


def test_add_model_is_small_link_button_not_full_card():
    block = function_block("renderAionProviderCouncilPanel")

    assert "+ add" in block
    assert 'data-aion-provider-council-seat="add_model"' not in block


def test_provider_council_handlers_installed():
    assert "__aionProviderCouncilHandlersInstalled" in TEXT
    assert "aion.defaultReasoningProvider" in TEXT
    assert "aion.gemma.disabled" in TEXT



def test_ai_council_shows_active_council_only_and_keeps_add_model_small():
    block = function_block("renderAionProviderCouncilPanel")

    assert "councilProviders" in block
    assert "visible_in_council" in block
    assert "data-aion-provider-council-active-seats" in block
    assert "+ add" in block
    assert "2 connected" not in block
    assert "Default LLM: Gemma" not in block
    assert "font-size:11px" in block



def test_ai_council_add_model_dropdown_exists():
    block = function_block("renderAionProviderCouncilPanel")

    assert "data-aion-provider-council-model-select" in block
    assert "availableToAdd" in block
    assert "data-aion-provider-council-add-selected-model" in block
