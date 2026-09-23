from pathlib import Path

DOC = Path("docs/rfc/aion_goal_engine_provider_capability_manifest_lock.tex")


def test_provider_capability_manifest_lock_doc_exists():
    assert DOC.exists()


def test_provider_capability_manifest_lock_names_schema_and_trace():
    text = DOC.read_text()

    assert "aion.business.provider_capability_manifest.v1" in text
    assert "provider_capability_manifest" in text


def test_provider_capability_manifest_lock_names_required_providers():
    text = DOC.read_text()

    for provider in ["local", "openai", "anthropic"]:
        assert provider in text


def test_provider_capability_manifest_lock_names_required_flags():
    text = DOC.read_text()

    for needle in [
        "supports_long_running_sessions",
        "supports_checkpoint_resume",
        "supports_sandboxed_execution",
        "supports_outcome_evaluation",
        "supports_memory_dreaming",
        "supports_multi_agent_orchestration",
    ]:
        assert needle in text


def test_provider_capability_manifest_lock_names_safety_invariants():
    text = DOC.read_text()

    assert "external_writes_require_approval = true" in text
    assert "business_state_mutations_require_human_review = true" in text
    assert "provider_disclosure_required_in_ui = true" in text


def test_provider_capability_manifest_lock_names_routing_guard():
    text = DOC.read_text()

    assert "ProviderRouter MUST check provider capability before routing" in text
    assert "provider_capability_not_supported" in text
    assert "capability_manifest_checked" in text


def test_provider_capability_manifest_lock_names_boardroom_rule():
    text = DOC.read_text()

    assert "Boardroom MUST expose provider_capability_manifest" in text
    assert "MUST NOT use provider manifest as storage" in text


def test_provider_capability_manifest_lock_has_footer():
    text = DOC.read_text()

    assert "Lock ID: AION-GOAL-ENGINE-PROVIDER-CAPABILITY-MANIFEST-V1" in text
    assert "Status: LOCKED" in text
    assert "Maintainer: Tessaris AI" in text
    assert "Author: Kevin Robinson" in text
