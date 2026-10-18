from __future__ import annotations

import stat
import json
import sqlite3
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.sovereign_installed_service import (
    prepare_node_state_root,
)
from backend.modules.local_node.private_sqlite import connect_private_sqlite
from backend.modules.local_node.node_state_store import NodeStateStore
from backend.modules.local_node.sync_cursor_store import SyncCursorStore


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_node_state_root_is_created_owner_only(tmp_path: Path) -> None:
    root = prepare_node_state_root(tmp_path / "external-node-state")

    assert root.is_dir()
    assert stat.S_IMODE(root.stat().st_mode) == 0o700


def test_node_state_root_rejects_application_update_or_vault_overlap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    application = tmp_path / "Tessaris.app"
    monkeypatch.setenv("TESSARIS_APPLICATION_ROOT", str(application))

    with pytest.raises(ValueError, match="node_state_root_overlaps_protected_root"):
        prepare_node_state_root(application / "runtime")


def test_node_sqlite_files_are_owner_only(tmp_path: Path) -> None:
    db_path = tmp_path / "node" / "state.sqlite3"

    connection = connect_private_sqlite(db_path)
    try:
        connection.execute("CREATE TABLE example (id TEXT PRIMARY KEY)")
        connection.commit()
    finally:
        connection.close()

    assert stat.S_IMODE(db_path.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(db_path.stat().st_mode) == 0o600


def test_private_sqlite_refuses_symlink_database_targets(tmp_path: Path) -> None:
    real = tmp_path / "real.sqlite3"
    real.touch()
    link = tmp_path / "linked.sqlite3"
    link.symlink_to(real)

    with pytest.raises(ValueError, match="private_sqlite_symlink_target_forbidden"):
        connect_private_sqlite(link)


def test_live_node_and_fabric_defaults_do_not_use_checkout_runtime() -> None:
    router_source = (REPOSITORY_ROOT / "backend/api/local_node_router.py").read_text(
        encoding="utf-8"
    )
    fabric_source = (
        REPOSITORY_ROOT / "backend/modules/aion_fabric/runtime.py"
    ).read_text(encoding="utf-8")
    cli_source = (REPOSITORY_ROOT / "backend/modules/aion_fabric/cli.py").read_text(
        encoding="utf-8"
    )

    assert 'base_dir=".runtime/local_node"' not in router_source
    assert 'base_dir: str | Path = ".runtime/aion_fabric"' not in fabric_source
    assert 'DEFAULT_RUNTIME = Path(".runtime/aion_fabric")' not in cli_source
    assert "prepare_node_state_root" in router_source
    assert "prepare_node_state_root" in fabric_source


def test_node_state_replaces_free_text_with_codes_and_fingerprints(
    tmp_path: Path,
) -> None:
    secret = "Customer Jane jane@example.test says alarm code 9284"
    store = NodeStateStore(str(tmp_path))

    store.save_heartbeat(
        {
            "node_id": "node_one",
            "workspace_id": "workspace_one",
            "deployment_mode": "local",
            "status": "running",
            "last_error": secret,
            "metadata": {"queued_count": 2, "customer_note": secret},
        }
    )
    store.save_runtime_flags(
        is_running=False,
        is_paused=True,
        is_stopped=False,
        pause_reason=secret,
    )
    store.set_control_state(
        command="pause",
        requested_by="Jane Customer <jane@example.test>",
        reason=secret,
    )
    store.save_sync_state(
        {
            "last_error": secret,
            "pending_upload_count": 3,
            "customer_payload": secret,
        }
    )

    state = store.get_full_state()
    assert state["heartbeat"]["last_error"] == "unclassified_error"
    assert state["heartbeat"]["metadata"] == {"queued_count": 2}
    assert state["runtime_flags"]["pause_reason"] == "unspecified"
    assert state["control_state"]["requested_by"] == "operator"
    assert state["control_state"]["reason"] == "unspecified"
    assert state["sync_state"]["last_error"] == "unclassified_error"
    heartbeat_fingerprint = state["heartbeat"]["last_error_fingerprint"]
    reopened = NodeStateStore(str(tmp_path))
    assert reopened.get_heartbeat()["last_error_fingerprint"] == heartbeat_fingerprint
    assert secret.encode() not in (tmp_path / "node_state.sqlite3").read_bytes()


def test_node_state_startup_scrubs_and_compacts_legacy_free_text(
    tmp_path: Path,
) -> None:
    secret = "Legacy customer secret contract value 4,500"
    db_path = tmp_path / "node_state.sqlite3"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE node_state (state_key TEXT PRIMARY KEY, payload_json TEXT NOT NULL, updated_at TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO node_state VALUES (?, ?, ?)",
            (
                "heartbeat",
                json.dumps({"status": "error", "last_error": secret}),
                "2026-10-18T00:00:00+00:00",
            ),
        )
        conn.commit()

    store = NodeStateStore(str(tmp_path))

    assert store.get_heartbeat()["last_error"] == "unclassified_error"
    assert secret.encode() not in db_path.read_bytes()


def test_sync_cursor_rejects_unknown_payloads_and_never_stores_error_text(
    tmp_path: Path,
) -> None:
    secret = "Invoice for jane@example.test failed at private address"
    store = SyncCursorStore(str(tmp_path))

    store.set_last_error(secret)

    assert store.get_last_error() == "unclassified_error"
    assert secret.encode() not in (tmp_path / "sync_cursor.sqlite3").read_bytes()
    with pytest.raises(ValueError, match="unsupported_sync_cursor_key"):
        store.upsert("customer_payload", {"note": secret})
