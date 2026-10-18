from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.runtime.application_account_recovery import (
    ApplicationAccountRecoveryError,
    ApplicationAccountRecoveryStore,
)
from backend.modules.aion_business.runtime.aion_flow_session_authority import (
    ACCOUNT_SESSION_HEADERS,
    AionFlowSessionAuthority,
)


PASSWORD = "a strong off device recovery password"


def _initialized(tmp_path):
    store = ApplicationAccountRecoveryStore(tmp_path / "device-a", runtime_mode="test")
    kit = tmp_path / "off-device" / "owner.tessaris-account-recovery"
    result = store.initialize(
        workspace_id="home-fixed",
        owner_id="owner@example.invalid",
        device_id="desktop-a",
        password=PASSWORD,
        recovery_kit_path=kit,
        confirmation="CREATE OFF-DEVICE ACCOUNT RECOVERY KIT",
    )
    return store, kit, result


def test_off_device_account_recovery_advances_epoch_and_revokes_prior_devices(tmp_path):
    source, kit, initialized = _initialized(tmp_path)
    descriptor = ApplicationAccountRecoveryStore.verify_descriptor(
        initialized["descriptor"], expected_account_id=initialized["account_id"],
    )
    assert source.authorize_device(device_id="desktop-a", recovery_epoch=1)["authorized"] is True
    assert kit.is_file()
    assert initialized["raw_private_key_exposed"] is False
    raw_kit = kit.read_text(encoding="utf-8")
    assert "root_private_key_base64" not in raw_kit

    restored = ApplicationAccountRecoveryStore(tmp_path / "device-b", runtime_mode="test")
    result = restored.recover_clean_device(
        recovery_kit_path=kit,
        password=PASSWORD,
        current_descriptor=descriptor,
        expected_account_id=initialized["account_id"],
        new_device_id="desktop-b",
        actor_id="owner@example.invalid",
        confirmation="RECOVER ACCOUNT AND REVOKE PRIOR DEVICES",
    )
    assert result["recovered"] is True
    assert result["recovery_epoch"] == 2
    assert result["prior_devices_revoked"] == ["desktop-a"]
    assert result["active_devices"] == ["desktop-b"]
    assert result["independent_freshness_required"] is True
    assert restored.authorize_device(device_id="desktop-b", recovery_epoch=2)["authorized"] is True
    with pytest.raises(PermissionError, match="epoch_revoked"):
        restored.authorize_device(device_id="desktop-a", recovery_epoch=1)
    with pytest.raises(PermissionError, match="device_revoked"):
        restored.authorize_device(device_id="desktop-a", recovery_epoch=2)

    verified = ApplicationAccountRecoveryStore.verify_descriptor(
        result["descriptor"],
        expected_account_id=initialized["account_id"],
        expected_previous_descriptor_sha256=initialized["descriptor_sha256"],
    )
    assert verified["recovery_epoch"] == 2
    assert verified["all_unlisted_devices_revoked"] is True


def test_recovery_rejects_wrong_password_tampering_wrong_account_and_reuse(tmp_path):
    _, kit, initialized = _initialized(tmp_path)
    target = ApplicationAccountRecoveryStore(tmp_path / "target", runtime_mode="test")
    arguments = dict(
        recovery_kit_path=kit,
        current_descriptor=initialized["descriptor"],
        expected_account_id=initialized["account_id"],
        new_device_id="desktop-b",
        actor_id="owner",
        confirmation="RECOVER ACCOUNT AND REVOKE PRIOR DEVICES",
    )
    with pytest.raises(PermissionError, match="could not be authenticated"):
        target.recover_clean_device(password="wrong password with enough characters", **arguments)
    with pytest.raises(PermissionError, match="expected_account_mismatch"):
        target.recover_clean_device(
            password=PASSWORD, **{**arguments, "expected_account_id": "account_" + "0" * 40},
        )

    tampered = tmp_path / "off-device" / "tampered.tessaris-account-recovery"
    payload = json.loads(kit.read_text(encoding="utf-8"))
    payload["ciphertext_base64"] = payload["ciphertext_base64"][:-2] + "AA"
    tampered.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(PermissionError, match="could not be authenticated"):
        target.recover_clean_device(
            password=PASSWORD, **{**arguments, "recovery_kit_path": tampered},
        )

    target.recover_clean_device(password=PASSWORD, **arguments)
    with pytest.raises(ApplicationAccountRecoveryError, match="clean_account_recovery_target_required"):
        target.recover_clean_device(password=PASSWORD, **arguments)


def test_recovery_kit_must_be_outside_runtime_and_descriptor_tampering_fails(tmp_path):
    store = ApplicationAccountRecoveryStore(tmp_path / "device", runtime_mode="test")
    with pytest.raises(ApplicationAccountRecoveryError, match="off_device"):
        store.initialize(
            workspace_id="home-fixed",
            owner_id="owner",
            device_id="desktop-a",
            password=PASSWORD,
            recovery_kit_path=tmp_path / "device" / "kit.json",
            confirmation="CREATE OFF-DEVICE ACCOUNT RECOVERY KIT",
        )

    _, _, initialized = _initialized(tmp_path / "valid")
    tampered = dict(initialized["descriptor"])
    tampered["active_devices"] = ["attacker-device"]
    with pytest.raises(PermissionError, match="signature_invalid"):
        ApplicationAccountRecoveryStore.verify_descriptor(tampered)


def test_signed_desktop_sessions_enforce_recovery_epoch_and_active_device(tmp_path):
    source = ApplicationAccountRecoveryStore(tmp_path / "device-a", runtime_mode="test")
    kit = tmp_path / "off-device" / "kit.json"
    initial = source.initialize(
        workspace_id="home-fixed",
        owner_id="owner",
        device_id="desktop-device-1",
        password=PASSWORD,
        recovery_kit_path=kit,
        confirmation="CREATE OFF-DEVICE ACCOUNT RECOVERY KIT",
    )
    secret = b"session-secret-long-enough-for-hmac-use"
    first = AionFlowSessionAuthority(
        secret=secret,
        clock=lambda: 1_790_000_000,
        persistent_replay=False,
        account_recovery_store=source,
    )
    headers = first.sign_for_test(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        device_id="desktop-device-1",
        person_id="owner",
        workspace_id="home-fixed",
        issued_at=1_790_000_000,
    )
    verified = first.verify(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        headers=headers,
    )
    assert verified.account_id == initial["account_id"]
    assert verified.recovery_epoch == 1
    assert verified.actor()["authority_source"].endswith("canonical_organisation.v2")

    missing_epoch = dict(first.sign_for_test(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        device_id="desktop-device-1",
        person_id="owner",
        workspace_id="home-fixed",
        issued_at=1_790_000_000,
    ))
    missing_epoch.pop(ACCOUNT_SESSION_HEADERS["recovery_epoch"])
    with pytest.raises(PermissionError, match="account_epoch_required"):
        first.verify(
            method="POST", target="/api/aion/business/legal-signing/list",
            body=b"{}", headers=missing_epoch,
        )

    recovered_store = ApplicationAccountRecoveryStore(tmp_path / "device-b", runtime_mode="test")
    recovered_store.recover_clean_device(
        recovery_kit_path=kit,
        password=PASSWORD,
        current_descriptor=initial["descriptor"],
        expected_account_id=initial["account_id"],
        new_device_id="desktop-device-2",
        actor_id="owner",
        confirmation="RECOVER ACCOUNT AND REVOKE PRIOR DEVICES",
    )
    after_recovery = AionFlowSessionAuthority(
        secret=secret,
        clock=lambda: 1_790_000_000,
        persistent_replay=False,
        account_recovery_store=recovered_store,
    )
    with pytest.raises(PermissionError, match="epoch_revoked"):
        after_recovery.verify(
            method="POST", target="/api/aion/business/legal-signing/list",
            body=b"{}", headers=headers,
        )
    current = after_recovery.sign_for_test(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        device_id="desktop-device-2",
        person_id="owner",
        workspace_id="home-fixed",
        issued_at=1_790_000_000,
    )
    assert after_recovery.verify(
        method="POST", target="/api/aion/business/legal-signing/list",
        body=b"{}", headers=current,
    ).recovery_epoch == 2


def test_account_headers_fail_closed_when_backend_registry_is_unavailable(tmp_path):
    authority = AionFlowSessionAuthority(
        secret=b"session-secret-long-enough-for-hmac-use",
        clock=lambda: 1_790_000_000,
        persistent_replay=False,
        account_recovery_root=tmp_path / "missing-registry",
    )
    headers = authority.sign_for_test(
        method="POST", target="/api/aion/business/legal-signing/list", body=b"{}",
        device_id="desktop-device-1", person_id="owner", workspace_id="home-fixed",
        issued_at=1_790_000_000,
        account_id="account_" + "1" * 40, recovery_epoch=1,
    )
    with pytest.raises(PermissionError, match="account_registry_unavailable"):
        authority.verify(
            method="POST", target="/api/aion/business/legal-signing/list",
            body=b"{}", headers=headers,
        )
