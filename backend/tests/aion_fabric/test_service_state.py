from __future__ import annotations

import os
import sys
import threading
import time
import types

import base64
import pytest

from backend.modules.aion_fabric.service_state import ConnectionHealthMonitor, PrivateServiceState


def test_private_service_credentials_survive_restart(tmp_path) -> None:
    first = PrivateServiceState(tmp_path).load()
    second = PrivateServiceState(tmp_path).load()

    assert first == second
    assert len(first["companion_pair_code"]) == 6
    assert oct(os.stat(tmp_path / "private_service_state.json").st_mode & 0o777) == "0o600"


def test_private_service_credentials_use_os_store_in_production(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored = {}
    keyring = types.SimpleNamespace(
        get_password=lambda service, account: stored.get((service, account)),
        set_password=lambda service, account, value: stored.__setitem__((service, account), value),
    )
    monkeypatch.setitem(sys.modules, "keyring", keyring)
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")
    monkeypatch.setenv("TESSARIS_BUSINESS_STABLE_ID", "private-business")

    first = PrivateServiceState(tmp_path).load()
    second = PrivateServiceState(tmp_path).load()

    assert first == second
    assert not (tmp_path / "private_service_state.json").exists()
    encoded = next(iter(stored.values()))
    assert first["companion_token"] in encoded


def test_private_service_credentials_migrate_to_os_store_and_retain_source(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = PrivateServiceState(tmp_path).load()
    source = tmp_path / "private_service_state.json"
    source_bytes = source.read_bytes()
    stored = {}
    keyring = types.SimpleNamespace(
        get_password=lambda service, account: stored.get((service, account)),
        set_password=lambda service, account, value: stored.__setitem__((service, account), value),
    )
    monkeypatch.setitem(sys.modules, "keyring", keyring)
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "guardian")
    monkeypatch.setenv("TESSARIS_BUSINESS_VAULT_PATH", str(tmp_path / "configured-vault"))
    monkeypatch.setenv("TESSARIS_BUSINESS_NAME", "Private Business")
    monkeypatch.setenv("TESSARIS_BUSINESS_STABLE_ID", "private-business")
    monkeypatch.setenv(
        "TESSARIS_BUSINESS_VAULT_KEY_B64",
        base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("="),
    )
    monkeypatch.setenv("TESSARIS_APPLICATION_ROOT", str(tmp_path / "application"))
    monkeypatch.setenv("TESSARIS_UPDATE_ROOT", str(tmp_path / "updates"))

    migrated = PrivateServiceState(tmp_path).load()

    assert migrated == original
    assert source.read_bytes() == source_bytes
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    assert original["companion_token"].encode() not in raw


def test_private_service_credentials_fail_closed_without_os_store(
    tmp_path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "keyring", None)
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")
    monkeypatch.setenv("TESSARIS_BUSINESS_STABLE_ID", "private-business")

    with pytest.raises(RuntimeError, match="os_credential_store_unavailable"):
        PrivateServiceState(tmp_path).load()


def test_connection_monitor_recovers_without_restarting() -> None:
    attempts = 0
    recovered = threading.Event()

    def check():
        nonlocal attempts
        attempts += 1
        connected = attempts >= 2
        if connected:
            recovered.set()
        return {"connected": connected, "host": "192.0.2.5"}

    monitor = ConnectionHealthMonitor(check, interval_seconds=0.01)
    monitor.start()
    try:
        monitor.retry_now()
        assert recovered.wait(2)
        limit = time.monotonic() + 1
        while monitor.snapshot()["status"] != "connected" and time.monotonic() < limit:
            time.sleep(0.01)
        state = monitor.snapshot()
        assert state["status"] == "connected"
        assert state["consecutive_failures"] == 0
    finally:
        monitor.stop()
