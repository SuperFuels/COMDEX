from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.modules.aion_business.runtime.application_account_descriptor_registry import (
    ApplicationAccountDescriptorRegistry,
    ApplicationAccountDescriptorRegistryClient,
    ApplicationAccountDescriptorRegistryError,
)
from backend.modules.aion_business.runtime.application_account_recovery import (
    ApplicationAccountRecoveryStore,
)
from backend.modules.aion_business.runtime.aion_flow_session_authority import (
    AionFlowSessionAuthority,
)
from backend.scripts.run_application_account_descriptor_registry import (
    build_registry_app,
    main as registry_main,
)


PASSWORD = "a strong off device recovery password"


def _descriptor_chain(tmp_path):
    first_store = ApplicationAccountRecoveryStore(tmp_path / "device-a", runtime_mode="test")
    kit = tmp_path / "off-device" / "account-kit.json"
    first = first_store.initialize(
        workspace_id="home-fixed",
        owner_id="owner",
        device_id="desktop-a",
        password=PASSWORD,
        recovery_kit_path=kit,
        confirmation="CREATE OFF-DEVICE ACCOUNT RECOVERY KIT",
    )
    second_store = ApplicationAccountRecoveryStore(tmp_path / "device-b", runtime_mode="test")
    second = second_store.recover_clean_device(
        recovery_kit_path=kit,
        password=PASSWORD,
        current_descriptor=first["descriptor"],
        expected_account_id=first["account_id"],
        new_device_id="desktop-b",
        actor_id="owner",
        confirmation="RECOVER ACCOUNT AND REVOKE PRIOR DEVICES",
    )
    third_store = ApplicationAccountRecoveryStore(tmp_path / "device-c", runtime_mode="test")
    third = third_store.recover_clean_device(
        recovery_kit_path=kit,
        password=PASSWORD,
        current_descriptor=second["descriptor"],
        expected_account_id=first["account_id"],
        new_device_id="desktop-c",
        actor_id="owner",
        confirmation="RECOVER ACCOUNT AND REVOKE PRIOR DEVICES",
    )
    return first_store, first, second, third


def test_registry_preserves_monotonic_descriptor_history_and_idempotency(tmp_path):
    _, first, second, _ = _descriptor_chain(tmp_path)
    registry = ApplicationAccountDescriptorRegistry(tmp_path / "registry" / "accounts.sqlite3")

    accepted = registry.publish(first["descriptor"])
    assert accepted["accepted"] is True
    replay = registry.publish(first["descriptor"])
    assert replay["accepted"] is False
    assert replay["idempotent"] is True
    advanced = registry.publish(second["descriptor"])
    assert advanced["recovery_epoch"] == 2
    assert registry.current(first["account_id"])["active_devices"] == ["desktop-b"]
    assert [item["recovery_epoch"] for item in registry.history(first["account_id"])] == [1, 2]
    assert registry.status() == {
        "schema_version": "tessaris.application-account-descriptor-registry.v1",
        "account_count": 1,
        "descriptor_count": 2,
        "sqlite_integrity": "ok",
        "stores_recovery_secrets": False,
        "independent_deployment_required": True,
    }


def test_registry_rejects_rollback_gap_tampering_and_unknown_accounts(tmp_path):
    _, first, second, third = _descriptor_chain(tmp_path)
    registry = ApplicationAccountDescriptorRegistry(tmp_path / "registry.sqlite3")
    registry.publish(first["descriptor"])

    with pytest.raises(PermissionError, match="epoch_gap"):
        registry.publish(third["descriptor"])
    registry.publish(second["descriptor"])
    with pytest.raises(PermissionError, match="rollback_or_equivocation"):
        registry.publish(first["descriptor"])

    tampered = dict(second["descriptor"])
    tampered["active_devices"] = ["attacker"]
    with pytest.raises(PermissionError, match="signature_invalid"):
        registry.publish(tampered)
    with pytest.raises(KeyError, match="not_found"):
        registry.current("account_" + "0" * 40)
    with pytest.raises(ApplicationAccountDescriptorRegistryError, match="account_id_invalid"):
        registry.current("not-an-account")


def test_registry_authority_rejects_lost_device_and_stale_epoch(tmp_path):
    first_store, first, second, _ = _descriptor_chain(tmp_path)
    registry = ApplicationAccountDescriptorRegistry(tmp_path / "registry.sqlite3")
    registry.publish(first["descriptor"])
    secret = b"session-secret-long-enough-for-hmac-use"
    signer = AionFlowSessionAuthority(
        secret=secret,
        clock=lambda: 1_790_000_000,
        persistent_replay=False,
        account_recovery_store=first_store,
    )
    old_headers = signer.sign_for_test(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        device_id="desktop-a",
        person_id="owner",
        workspace_id="home-fixed",
        issued_at=1_790_000_000,
    )
    verifier = AionFlowSessionAuthority(
        secret=secret,
        clock=lambda: 1_790_000_000,
        persistent_replay=False,
        account_descriptor_registry=registry,
        account_recovery_root=tmp_path / "no-local-account-state",
    )
    assert verifier.verify(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        headers=old_headers,
    ).recovery_epoch == 1

    registry.publish(second["descriptor"])
    with pytest.raises(PermissionError, match="epoch_revoked"):
        verifier.verify(
            method="POST",
            target="/api/aion/business/legal-signing/list",
            body=b"{}",
            headers=old_headers,
        )

    current_headers = signer.sign_for_test(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        device_id="desktop-b",
        person_id="owner",
        workspace_id="home-fixed",
        issued_at=1_790_000_000,
        nonce="abcdef0123456789abcdef0123456790",
        account_id=first["account_id"],
        recovery_epoch=2,
    )
    assert verifier.verify(
        method="POST",
        target="/api/aion/business/legal-signing/list",
        body=b"{}",
        headers=current_headers,
    ).device_id == "desktop-b"


def test_registry_refuses_unsafe_path_and_enforces_capacity(tmp_path):
    _, first, _, _ = _descriptor_chain(tmp_path)
    actual = tmp_path / "actual.sqlite3"
    link = tmp_path / "registry.sqlite3"
    link.symlink_to(actual)
    with pytest.raises(ApplicationAccountDescriptorRegistryError, match="path_unsafe"):
        ApplicationAccountDescriptorRegistry(link)

    registry = ApplicationAccountDescriptorRegistry(
        tmp_path / "bounded.sqlite3", max_accounts=1,
    )
    registry.publish(first["descriptor"])
    other_store = ApplicationAccountRecoveryStore(tmp_path / "other", runtime_mode="test")
    other = other_store.initialize(
        workspace_id="other-workspace",
        owner_id="other-owner",
        device_id="other-device",
        password=PASSWORD,
        recovery_kit_path=tmp_path / "other-kit.json",
        confirmation="CREATE OFF-DEVICE ACCOUNT RECOVERY KIT",
    )
    with pytest.raises(ApplicationAccountDescriptorRegistryError, match="capacity_exceeded"):
        registry.publish(other["descriptor"])


def test_standalone_registry_api_publishes_public_descriptors_with_bounded_errors(tmp_path):
    _, first, second, _ = _descriptor_chain(tmp_path)
    registry = ApplicationAccountDescriptorRegistry(tmp_path / "registry.sqlite3")
    client = TestClient(build_registry_app(registry))
    path = f"/v1/accounts/{first['account_id']}/descriptor"

    created = client.put(path, json=first["descriptor"])
    assert created.status_code == 201
    assert created.json()["stores_recovery_secrets"] is False
    assert created.headers["cache-control"] == "no-store"
    assert client.put(path, json=first["descriptor"]).status_code == 200
    assert client.get(path).json()["recovery_epoch"] == 1

    advanced = client.put(path, json=second["descriptor"])
    assert advanced.status_code == 201
    history = client.get(f"/v1/accounts/{first['account_id']}/history").json()
    assert [item["recovery_epoch"] for item in history["history"]] == [1, 2]
    assert history["contains_private_recovery_material"] is False
    assert client.get("/health").json()["sqlite_integrity"] == "ok"

    rollback = client.put(path, json=first["descriptor"])
    assert rollback.status_code == 409
    assert rollback.json()["detail"] == "account_registry_epoch_rollback_or_equivocation"
    assert client.put(path, content=b"{}", headers={"content-type": "text/plain"}).status_code == 415
    oversized = client.put(
        path,
        content=b"{" + (b" " * (256 * 1024)) + b"}",
        headers={"content-type": "application/json"},
    )
    assert oversized.status_code == 413


def test_registry_publication_can_require_out_of_band_operator_authority(tmp_path):
    _, first, _, _ = _descriptor_chain(tmp_path)
    token = "registry-publication-secret-with-at-least-32-characters"
    client = TestClient(build_registry_app(
        ApplicationAccountDescriptorRegistry(tmp_path / "registry.sqlite3"),
        publish_token=token,
    ))
    path = f"/v1/accounts/{first['account_id']}/descriptor"
    assert client.put(path, json=first["descriptor"]).status_code == 401
    assert client.put(
        path,
        json=first["descriptor"],
        headers={"authorization": "Bearer wrong-token"},
    ).status_code == 401
    accepted = client.put(
        path,
        json=first["descriptor"],
        headers={"authorization": f"Bearer {token}"},
    )
    assert accepted.status_code == 201
    with pytest.raises(ValueError, match="token_too_short"):
        build_registry_app(
            ApplicationAccountDescriptorRegistry(tmp_path / "other.sqlite3"),
            publish_token="short",
        )


def test_non_loopback_registry_refuses_start_without_tls_and_publish_secret(
    tmp_path, monkeypatch,
):
    monkeypatch.delenv("TESSARIS_ACCOUNT_REGISTRY_PUBLISH_TOKEN", raising=False)
    monkeypatch.setattr("sys.argv", [
        "registry",
        "--database", str(tmp_path / "registry.sqlite3"),
        "--host", "192.0.2.10",
    ])
    with pytest.raises(SystemExit):
        registry_main()

    monkeypatch.setattr("sys.argv", [
        "registry",
        "--database", str(tmp_path / "registry.sqlite3"),
        "--host", "192.0.2.10",
        "--ssl-certfile", str(tmp_path / "cert.pem"),
        "--ssl-keyfile", str(tmp_path / "key.pem"),
    ])
    with pytest.raises(SystemExit):
        registry_main()


def test_registry_client_requires_safe_transport_and_detects_server_rollback(tmp_path):
    _, first, second, _ = _descriptor_chain(tmp_path)
    current = {"value": first["descriptor"]}
    client = ApplicationAccountDescriptorRegistryClient(
        "https://registry.example.invalid",
        cache_root=tmp_path / "cache",
        runtime_mode="production",
        transport=lambda _url: current["value"],
    )
    assert client.current(first["account_id"])["recovery_epoch"] == 1
    current["value"] = second["descriptor"]
    assert client.authorize_device(
        account_id=first["account_id"],
        device_id="desktop-b",
        recovery_epoch=2,
        workspace_id="home-fixed",
    )["authority_source"] == "independent_registry_https.v1"
    current["value"] = first["descriptor"]
    with pytest.raises(PermissionError, match="rollback_detected"):
        client.current(first["account_id"])

    with pytest.raises(ApplicationAccountDescriptorRegistryError, match="https_required"):
        ApplicationAccountDescriptorRegistryClient(
            "http://registry.example.invalid",
            cache_root=tmp_path / "unsafe-cache",
            runtime_mode="production",
        )
    with pytest.raises(ApplicationAccountDescriptorRegistryError, match="https_required"):
        ApplicationAccountDescriptorRegistryClient(
            "http://registry.example.invalid",
            cache_root=tmp_path / "unsafe-cache-2",
            runtime_mode="development",
        )
    ApplicationAccountDescriptorRegistryClient(
        "http://127.0.0.1:8743",
        cache_root=tmp_path / "loopback-cache",
        runtime_mode="development",
        transport=lambda _url: first["descriptor"],
    )
    real_cache = tmp_path / "real-cache"
    real_cache.mkdir()
    linked_cache = tmp_path / "linked-cache"
    linked_cache.symlink_to(real_cache, target_is_directory=True)
    with pytest.raises(ApplicationAccountDescriptorRegistryError, match="cache_path_unsafe"):
        ApplicationAccountDescriptorRegistryClient(
            "https://registry.example.invalid",
            cache_root=linked_cache,
            runtime_mode="production",
            transport=lambda _url: first["descriptor"],
        )


def test_registry_client_never_uses_cache_as_freshness_fallback(tmp_path):
    _, first, _, _ = _descriptor_chain(tmp_path)
    online = ApplicationAccountDescriptorRegistryClient(
        "https://registry.example.invalid",
        cache_root=tmp_path / "cache",
        runtime_mode="production",
        transport=lambda _url: first["descriptor"],
    )
    online.current(first["account_id"])

    def unavailable(_url):
        raise OSError("offline")

    offline = ApplicationAccountDescriptorRegistryClient(
        "https://registry.example.invalid",
        cache_root=tmp_path / "cache",
        runtime_mode="production",
        transport=unavailable,
    )
    with pytest.raises(RuntimeError, match="registry_unavailable"):
        offline.authorize_device(
            account_id=first["account_id"],
            device_id="desktop-a",
            recovery_epoch=1,
            workspace_id="home-fixed",
        )
