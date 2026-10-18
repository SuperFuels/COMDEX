from __future__ import annotations

from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.boardroom_conversation_service import (
    BoardroomConversationService,
)
from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.department_operational_store import (
    DepartmentOperationalStore,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian


def _service(tmp_path: Path) -> tuple[BoardroomConversationService, Path]:
    layout = provision_business_vault(
        tmp_path / "customer-vault", business_name="Acme", business_stable_id="acme",
        application_root=tmp_path / "application", update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(layout, business_stable_id="acme", encryption_key=b"b" * 32)
    return BoardroomConversationService(
        domain_store=VaultDomainStore(guardian, actor_id="boardroom-test")
    ), layout.records / "guardian.sqlite3"


def test_boardroom_conversation_survives_restart_is_isolated_and_encrypted(tmp_path):
    service, database = _service(tmp_path)
    secret = "Acquire the confidential regional supplier"
    saved = service.save(
        "acme", team_mode="executive", seat_key="finance",
        messages=[
            {"role": "user", "text": secret, "at": "2026-10-17T20:00:00Z"},
            {"role": "assistant", "text": "I will prepare a governed review.", "provider": "local"},
        ],
    )

    restarted, _ = _service(tmp_path)
    loaded = restarted.load("acme", team_mode="executive", seat_key="finance")
    another_seat = restarted.load("acme", team_mode="executive", seat_key="sales")

    assert loaded["revision"] == saved["revision"] == 1
    assert [item["text"] for item in loaded["messages"]] == [
        secret, "I will prepare a governed review.",
    ]
    assert another_seat["messages"] == []
    audit = DepartmentOperationalStore(
        domain_store=restarted.domain_store
    ).list_audit(
        workspace_id="acme",
        department_id="boardroom",
        feature_id="seat_conversations",
    )
    assert len(audit) == 1
    assert audit[0]["payload"]["revision"] == 1
    assert audit[0]["payload"]["message_count"] == 2
    assert audit[0]["payload"]["content_digest"]
    assert secret not in str(audit[0]["payload"])
    assert secret.encode() not in database.read_bytes()


def test_boardroom_conversation_keeps_content_minimised_receipt_for_each_revision(tmp_path):
    service, _ = _service(tmp_path)
    first = service.save(
        "acme", team_mode="board", seat_key="ceo",
        messages=[{"role": "user", "text": "Approve the first operating map"}],
        expected_revision=0,
    )
    second = service.save(
        "acme", team_mode="board", seat_key="ceo",
        messages=[
            {"role": "user", "text": "Approve the first operating map"},
            {"role": "assistant", "text": "Decision recorded"},
        ],
        expected_revision=first["revision"],
    )

    audit = DepartmentOperationalStore(
        domain_store=service.domain_store
    ).list_audit(
        workspace_id="acme",
        department_id="boardroom",
        feature_id="seat_conversations",
    )
    assert second["revision"] == 2
    assert [row["payload"]["revision"] for row in audit] == [1, 2]
    assert [row["payload"]["previous_revision"] for row in audit] == [0, 1]
    assert "Approve the first operating map" not in str(audit)


def test_boardroom_conversation_rejects_stale_revision(tmp_path):
    service, _ = _service(tmp_path)
    service.save(
        "acme", team_mode="board", seat_key="ceo",
        messages=[{"role": "user", "text": "First decision"}], expected_revision=0,
    )

    with pytest.raises(ValueError, match="boardroom_conversation_revision_conflict"):
        service.save(
            "acme", team_mode="board", seat_key="ceo",
            messages=[{"role": "user", "text": "Stale overwrite"}], expected_revision=0,
        )


def test_boardroom_renderer_imports_legacy_once_and_never_writes_local_storage():
    source = Path("desktop/mac/src/lib/boardroom-seat-conversation.js").read_text()

    assert "localStorage.setItem" not in source
    assert "localStorage.getItem(targetStorageKey)" in source
    assert "if (saved) localStorage.removeItem(targetStorageKey)" in source
    assert 'method: "PUT"' in source
    assert "/api/aion/business/boardroom/" in source
