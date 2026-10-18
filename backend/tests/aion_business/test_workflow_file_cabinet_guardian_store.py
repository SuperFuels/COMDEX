from __future__ import annotations

import base64

import pytest
from fastapi import HTTPException

from backend.modules.aion_business.runtime.workflow_file_cabinet_repository import (
    WorkflowFileCabinetRepository,
)
from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.api.workflow_file_cabinet_api import (
    get_workflow_file_cabinet,
    save_boardroom_session_artifact,
    save_workflow_file_cabinet,
)


def _env(tmp_path):
    return {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(tmp_path / "customer-data" / "Acme.business-vault"),
        "TESSARIS_BUSINESS_NAME": "Acme",
        "TESSARIS_BUSINESS_STABLE_ID": "acme",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(b"f" * 32).decode().rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "app"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }


def test_file_cabinet_tree_and_original_are_guardian_protected(tmp_path, monkeypatch):
    for key, value in _env(tmp_path).items():
        monkeypatch.setenv(key, value)
    artifact = WorkflowFileCabinetRepository.put_artifact(
        "acme",
        data=b"private customer evidence",
        original_name="evidence.txt",
        content_type="text/plain",
    )
    tree = WorkflowFileCabinetRepository.default_tree("acme")
    tree["folders"] = [
        {
            "id": "evidence-1",
            "type": "artifact",
            "name": "Customer evidence",
            "target": {"vault_object_id": artifact["vault_object_id"]},
        }
    ]
    tree["root"]["children"] = tree["folders"]
    WorkflowFileCabinetRepository.save("acme", tree)
    loaded = WorkflowFileCabinetRepository.load("acme")
    assert loaded["folders"][0]["target"]["vault_object_id"] == artifact["vault_object_id"]
    preview = WorkflowFileCabinetRepository.preview("acme", "evidence-1")
    assert preview["kind"] == "text"
    assert preview["text"] == "private customer evidence"
    vault_root = tmp_path / "customer-data" / "Acme.business-vault"
    for path in vault_root.rglob("*"):
        if path.is_file():
            assert b"private customer evidence" not in path.read_bytes()


def test_file_cabinet_original_generated_move_and_tombstone_survive_restart(tmp_path, monkeypatch):
    for key, value in _env(tmp_path).items():
        monkeypatch.setenv(key, value)
    tree = WorkflowFileCabinetRepository.default_tree("acme")
    tree["folders"] = [
        {"id": "incoming", "type": "folder", "name": "Incoming", "children": []},
        {"id": "archive", "type": "folder", "name": "Archive", "children": []},
    ]
    tree["root"]["children"] = tree["folders"]
    WorkflowFileCabinetRepository.save("acme", tree)
    original = WorkflowFileCabinetRepository.add_artifact(
        "acme", data=b"private original bytes", original_name="source.txt",
        content_type="text/plain", parent_id="incoming", actor_id="person.owner",
    )
    generated = WorkflowFileCabinetRepository.add_artifact(
        "acme", data=b"generated governed document", original_name="generated.txt",
        content_type="text/plain", parent_id="incoming", actor_id="person.owner",
        generated=True,
    )
    assert WorkflowFileCabinetRepository.preview(
        "acme", original["item"]["id"],
    )["text"] == "private original bytes"
    moved = WorkflowFileCabinetRepository.move_item(
        "acme", original["item"]["id"], parent_id="archive", actor_id="person.owner",
    )
    assert moved["receipt"]["operation"] == "moved"
    tombstoned = WorkflowFileCabinetRepository.tombstone_item(
        "acme", generated["item"]["id"], reason="superseded", actor_id="person.owner",
    )
    assert tombstoned["item"]["status"] == "tombstoned"
    assert tombstoned["receipt"]["details"]["vault_object_retained"] is True
    replay = WorkflowFileCabinetRepository.tombstone_item(
        "acme", generated["item"]["id"], reason="superseded", actor_id="person.owner",
    )
    assert replay["idempotent_replay"] is True

    restored = WorkflowFileCabinetRepository.load("acme")
    archive = next(node for node in restored["folders"] if node["id"] == "archive")
    assert archive["children"][0]["id"] == original["item"]["id"]
    assert WorkflowFileCabinetRepository.item(
        "acme", generated["item"]["id"],
    )["status"] == "tombstoned"
    store = VaultDomainStore(configured_business_vault_runtime().guardian)
    receipts = store.list("file_cabinet.governance", workspace_id="acme")
    assert sorted(row["payload"]["operation"] for row in receipts) == [
        "generated", "moved", "original_uploaded", "tombstoned",
    ]
    _, retained = configured_business_vault_runtime().objects.get_bytes(
        object_id=generated["object"]["vault_object_id"],
    )
    assert retained == b"generated governed document"
    for path in (tmp_path / "customer-data" / "Acme.business-vault").rglob("*"):
        if path.is_file():
            assert b"private original bytes" not in path.read_bytes()
            assert b"generated governed document" not in path.read_bytes()


def test_boardroom_file_cabinet_artifact_never_writes_plaintext_runtime_file_in_guardian_mode(
    tmp_path, monkeypatch
):
    for key, value in _env(tmp_path).items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(tmp_path)
    result = save_boardroom_session_artifact(
        "acme",
        {
            "business_id": "acme",
            "session_id": "session-1",
            "session_type": "business_assessment",
            "private_minutes": "Founder private acquisition plan",
        },
    )
    assert result["record"]["persisted_uri"].startswith("guardian://")
    assert "vault_object_id" in result["pointer"]["target"]
    assert "storage_path" not in result["pointer"]["target"]
    assert not (tmp_path / ".runtime").exists()
    for path in (tmp_path / "customer-data" / "Acme.business-vault").rglob("*"):
        if path.is_file():
            assert b"Founder private acquisition plan" not in path.read_bytes()


@pytest.mark.parametrize(
    ("operation", "args"),
    [
        (get_workflow_file_cabinet, ("business-not-registered",)),
        (save_workflow_file_cabinet, ("business-not-registered", {"folders": []})),
        (
            save_boardroom_session_artifact,
            (
                "business-not-registered",
                {
                    "business_id": "business-not-registered",
                    "session_id": "session-1",
                },
            ),
        ),
    ],
)
def test_file_cabinet_api_refuses_unregistered_business_before_repository_access(
    monkeypatch, operation, args
):
    monkeypatch.setattr(
        WorkflowFileCabinetRepository,
        "load",
        lambda *_args, **_kwargs: pytest.fail("repository must not be read"),
    )
    monkeypatch.setattr(
        WorkflowFileCabinetRepository,
        "save",
        lambda *_args, **_kwargs: pytest.fail("repository must not be written"),
    )
    with pytest.raises(HTTPException) as caught:
        operation(*args)
    assert caught.value.status_code == 400
    assert caught.value.detail == "valid_registered_business_id_required"
