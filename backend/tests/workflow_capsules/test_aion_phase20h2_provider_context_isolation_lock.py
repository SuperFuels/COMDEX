import pytest

from backend.services.aion_mission_mode.provider_context_isolation import (
    assert_context_mount_allowed,
    contains_secret_key,
    create_model_visible_context,
    create_provider_context,
    create_provider_context_receipt,
    create_vault_reference,
    redact_model_visible_state,
    validate_provider,
)


def _vault(provider: str = "vercel"):
    return create_vault_reference(
        business_id="business_001",
        provider=provider,
        credential_scope="project_deploy",
        vault_key_id="vault_key_001",
    )


def _context(provider: str = "vercel"):
    return create_provider_context(
        mission_id="mission_001",
        mission_run_id="run_001",
        business_id="business_001",
        provider=provider,
        tool_name="prepare_vercel_deploy",
        vault_reference=_vault(provider),
        allowed_actions=["prepare_vercel_deploy", "deploy_to_vercel"],
        context_claims={"project": "homefixed"},
    )


def test_phase20h2_provider_validation() -> None:
    assert validate_provider("vercel") == "vercel"
    assert validate_provider("meta") == "meta"


def test_phase20h2_unknown_provider_rejected() -> None:
    with pytest.raises(ValueError):
        validate_provider("unknown_provider")


def test_phase20h2_vault_reference_hash_is_deterministic() -> None:
    first = _vault("vercel")
    second = _vault("vercel")
    assert first["vault_reference_hash"] == second["vault_reference_hash"]
    assert first["secret_material_exposed"] is False


def test_phase20h2_context_hash_is_deterministic() -> None:
    first = _context("vercel")
    second = _context("vercel")
    assert first["context_hash"] == second["context_hash"]


def test_phase20h2_vault_provider_mismatch_rejected() -> None:
    vault = _vault("meta")
    with pytest.raises(ValueError):
        create_provider_context(
            mission_id="mission_001",
            mission_run_id="run_001",
            business_id="business_001",
            provider="vercel",
            tool_name="prepare_vercel_deploy",
            vault_reference=vault,
            allowed_actions=["prepare_vercel_deploy"],
        )


def test_phase20h2_raw_secret_claims_rejected() -> None:
    with pytest.raises(ValueError):
        create_provider_context(
            mission_id="mission_001",
            mission_run_id="run_001",
            business_id="business_001",
            provider="vercel",
            tool_name="prepare_vercel_deploy",
            vault_reference=_vault("vercel"),
            allowed_actions=["prepare_vercel_deploy"],
            context_claims={"access_token": "plaintext"},
        )


def test_phase20h2_secret_key_detector_finds_nested_secret() -> None:
    assert contains_secret_key({"nested": {"api_key": "abc"}}) is True
    assert contains_secret_key({"nested": {"safe": "abc"}}) is False


def test_phase20h2_model_visible_context_redacts_secret_fields() -> None:
    context = _context("vercel")
    visible = create_model_visible_context(
        provider_context=context,
        page_state={
            "url": "https://vercel.com",
            "session_token": "abc",
            "form": {"password": "secret", "project": "homefixed"},
        },
    )

    assert visible["page_state"]["session_token"] == "[REDACTED]"
    assert visible["page_state"]["form"]["password"] == "[REDACTED]"
    assert visible["page_state"]["form"]["project"] == "homefixed"
    assert visible["vault_reference_visible"] is False
    assert visible["secret_material_exposed"] is False


def test_phase20h2_redaction_is_deterministic() -> None:
    value = {"cookie": "abc", "safe": ["one", {"authorization": "bearer"}]}
    first = redact_model_visible_state(value)
    second = redact_model_visible_state(value)
    assert first == second


def test_phase20h2_context_mount_allowed_for_matching_scope() -> None:
    context = _context("vercel")
    assertion = assert_context_mount_allowed(
        provider_context=context,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="vercel",
        requested_action="prepare_vercel_deploy",
    )

    assert assertion["runtime_mount_allowed"] is True
    assert assertion["gateway_state"] == "context_mounted"


def test_phase20h2_cross_mission_context_reuse_blocked() -> None:
    context = _context("vercel")
    assertion = assert_context_mount_allowed(
        provider_context=context,
        mission_id="mission_999",
        mission_run_id="run_001",
        provider="vercel",
        requested_action="prepare_vercel_deploy",
    )

    assert assertion["runtime_mount_allowed"] is False
    assert "mission_context_mismatch" in assertion["reasons"]


def test_phase20h2_cross_run_context_reuse_blocked() -> None:
    context = _context("vercel")
    assertion = assert_context_mount_allowed(
        provider_context=context,
        mission_id="mission_001",
        mission_run_id="run_999",
        provider="vercel",
        requested_action="prepare_vercel_deploy",
    )

    assert assertion["runtime_mount_allowed"] is False
    assert "mission_run_context_mismatch" in assertion["reasons"]


def test_phase20h2_cross_provider_context_reuse_blocked() -> None:
    context = _context("vercel")
    assertion = assert_context_mount_allowed(
        provider_context=context,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="meta",
        requested_action="prepare_vercel_deploy",
    )

    assert assertion["runtime_mount_allowed"] is False
    assert "provider_context_mismatch" in assertion["reasons"]


def test_phase20h2_action_outside_context_scope_blocked() -> None:
    context = _context("vercel")
    assertion = assert_context_mount_allowed(
        provider_context=context,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="vercel",
        requested_action="publish_facebook_post",
    )

    assert assertion["runtime_mount_allowed"] is False
    assert "action_outside_context_scope" in assertion["reasons"]


def test_phase20h2_mount_assertion_hash_is_deterministic() -> None:
    context = _context("vercel")
    first = assert_context_mount_allowed(
        provider_context=context,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="vercel",
        requested_action="deploy_to_vercel",
    )
    second = assert_context_mount_allowed(
        provider_context=context,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="vercel",
        requested_action="deploy_to_vercel",
    )

    assert first["mount_assertion_hash"] == second["mount_assertion_hash"]


def test_phase20h2_context_receipt_for_allowed_mount() -> None:
    context = _context("vercel")
    assertion = assert_context_mount_allowed(
        provider_context=context,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="vercel",
        requested_action="deploy_to_vercel",
    )
    receipt = create_provider_context_receipt(mount_assertion=assertion)

    assert receipt["receipt_hash"].startswith("sha256:")
    assert receipt["secret_material_exposed"] is False


def test_phase20h2_context_receipt_rejected_for_blocked_mount() -> None:
    context = _context("vercel")
    assertion = assert_context_mount_allowed(
        provider_context=context,
        mission_id="mission_001",
        mission_run_id="run_001",
        provider="meta",
        requested_action="deploy_to_vercel",
    )

    with pytest.raises(ValueError):
        create_provider_context_receipt(mount_assertion=assertion)
