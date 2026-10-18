from __future__ import annotations

import base64
import sys
import types
from dataclasses import replace
from pathlib import Path

import pytest

from backend.modules.aion_business.runtime.business_vault import provision_business_vault
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_business.runtime.vault_guardian import VaultGuardian
from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash
from backend.modules.aion_fabric.calendar_planning import (
    GovernedCalendarPlanning,
    configured_calendar_planning,
)
from backend.modules.aion_fabric.communication import (
    GovernedCommunication,
    configured_communication,
)
from backend.modules.aion_fabric.conversation import (
    ConversationMemory,
    configured_conversation_memory,
)
from backend.modules.aion_fabric.entertainment_personalization import (
    PrivateEntertainmentPersonalization,
    configured_private_entertainment_personalization,
)
from backend.modules.aion_fabric.contracts import (
    DeviceProfile,
    EnrollmentState,
    NodeRecord,
    NodeRole,
)
from backend.modules.aion_fabric.guardian_store import (
    GuardianFabricStore,
    configured_fabric_store,
)
from backend.modules.aion_fabric.guardian import PilotGuardian, configured_pilot_guardian
from backend.modules.aion_fabric.delta import new_delta_packet, new_glyph_delta_stream
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.live_context import LiveContextStore, configured_live_context_store
from backend.modules.aion_fabric.household import (
    HouseholdIdentityRegistry,
    UniversalNodeAuthority,
    configured_household_identity_registry,
    configured_universal_node_authority,
)
from backend.modules.aion_fabric.google_oauth import PersonaGoogleOAuth, configured_google_oauth
from backend.modules.aion_fabric.migrate_to_guardian import migrate_legacy_fabric_store
from backend.modules.aion_fabric.private_identity import (
    ProductionPrivateIdentity,
    configured_private_identity,
)
from backend.modules.aion_fabric.private_saves import (
    PrivateProgrammeSaves,
    configured_private_programme_saves,
)
from backend.modules.aion_fabric.pilot_inbox import PilotInbox, configured_pilot_inbox
from backend.modules.aion_fabric.runtime import AionFabricRuntime
from backend.modules.aion_fabric.store import FabricStore
from backend.modules.aion_fabric.webos import WebOsGateway


def _profile(node_id: str = "node-one", *, name: str = "Private boardroom display") -> DeviceProfile:
    return DeviceProfile(
        node_id=node_id,
        name=name,
        device_class="display",
        platform="private-platform",
        cpu_count=4,
        memory_bytes=8 * 1024**3,
        can_install_runtime=True,
        can_host_model=True,
        is_mains_powered=True,
        transports=("wifi",),
        controls=("display",),
        metadata={"room": "Confidential acquisition room"},
    )


def _record(node_id: str = "node-one") -> NodeRecord:
    return NodeRecord(
        profile=_profile(node_id),
        role=NodeRole.EDGE,
        public_key="customer-device-public-key",
        enrollment=EnrollmentState.ENROLLED,
        mother_id="mother-one",
        last_seen_at="2026-10-18T00:00:00+00:00",
    )


def _guardian_store(tmp_path: Path, workspace_id: str = "business-one") -> tuple[VaultGuardian, GuardianFabricStore]:
    layout = provision_business_vault(
        tmp_path / f"vault-{workspace_id}",
        business_name="Test Business",
        business_stable_id=workspace_id,
        application_root=tmp_path / "app",
        update_root=tmp_path / "updates",
    )
    guardian = VaultGuardian(
        layout,
        business_stable_id=workspace_id,
        encryption_key=b"z" * 32,
    )
    return guardian, GuardianFabricStore(
        workspace_id=workspace_id,
        domain_store=VaultDomainStore(guardian, actor_id="fabric-test"),
    )


def _guardian_environment(tmp_path: Path) -> dict[str, str]:
    return {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(tmp_path / "configured-vault"),
        "TESSARIS_BUSINESS_NAME": "Test Business",
        "TESSARIS_BUSINESS_STABLE_ID": "business-one",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(b"k" * 32).decode().rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
    }


def test_fabric_customer_topology_round_trips_encrypted_and_is_workspace_isolated(
    tmp_path: Path,
) -> None:
    guardian, store = _guardian_store(tmp_path)
    other = GuardianFabricStore(
        workspace_id="business-two",
        domain_store=store.domain_store,
    )

    store.save_node(_record())

    restored = store.get_node("node-one")
    assert restored is not None
    assert restored.to_dict() == _record().to_dict()
    assert other.get_node("node-one") is None
    assert store.verify_audit_chain() is True
    raw = guardian.database.read_bytes()
    assert b"Private boardroom display" not in raw
    assert b"Confidential acquisition room" not in raw
    assert b"customer-device-public-key" not in raw


def test_fabric_guardian_accepts_signed_delta_and_compact_stream(tmp_path: Path) -> None:
    guardian, store = _guardian_store(tmp_path)
    identity = IdentityStore(tmp_path / "identity").load_or_create()
    first = {"temperature": 4.0, "customer_label": "Private cold room"}
    packet = new_delta_packet(
        node_id="cold-room",
        sequence=1,
        previous={},
        current=first,
        identity=identity,
    )

    assert store.accept_delta(packet, public_key=identity.public_key_b64) == first
    second = {"temperature": 4.2, "customer_label": "Private cold room"}
    stream = new_glyph_delta_stream(
        node_id="cold-room",
        start_sequence=2,
        states=[first, second],
        identity=identity,
    )
    assert store.accept_stream(stream, public_key=identity.public_key_b64) == second
    assert store.state_for("cold-room") == (2, second, canonical_hash(second))
    assert store.counts()["delta_ledger"] == 1
    assert store.counts()["stream_ledger"] == 1
    assert store.verify_audit_chain() is True
    assert b"Private cold room" not in guardian.database.read_bytes()


def test_fabric_factory_selects_guardian_and_production_refuses_legacy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    selected = configured_fabric_store(tmp_path / "must-not-exist.sqlite3")
    assert isinstance(selected, GuardianFabricStore)
    assert not (tmp_path / "must-not-exist.sqlite3").exists()

    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")
    with pytest.raises(RuntimeError, match="guardian_store_required"):
        configured_fabric_store(tmp_path / "forbidden.sqlite3")


def test_fabric_runtime_bootstrap_uses_guardian_without_fabric_sqlite(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"

    runtime = AionFabricRuntime.bootstrap(
        root,
        profile=replace(_profile("mother-one"), device_class="computer"),
    )

    assert isinstance(runtime.store, GuardianFabricStore)
    assert runtime.store.get_node("mother-one") is not None
    assert not (root / "fabric.sqlite3").exists()


def test_fabric_factory_migrates_existing_source_once_and_keeps_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_path = tmp_path / "node-state" / "fabric.sqlite3"
    legacy = FabricStore(source_path)
    legacy.save_node(_record())
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    selected = configured_fabric_store(source_path)
    selected.append_audit("guardian_only_event", {"result": "preserve me"})
    audit_count = selected.counts()["audit_ledger"]
    selected_again = configured_fabric_store(source_path)

    assert isinstance(selected_again, GuardianFabricStore)
    assert selected_again.get_node("node-one") is not None
    assert selected_again.counts()["audit_ledger"] == audit_count
    assert source_path.exists()


def test_legacy_fabric_migration_copies_verifies_and_retains_source(tmp_path: Path) -> None:
    source_path = tmp_path / "legacy" / "fabric.sqlite3"
    source = FabricStore(source_path)
    source.save_node(_record())
    source.append_audit("customer_device_seen", {"room": "Private customer room"})
    _, target = _guardian_store(tmp_path / "target")

    receipt = migrate_legacy_fabric_store(source, target)

    assert receipt.verified is True
    assert receipt.source_retained is True
    assert source_path.exists()
    assert target.get_node("node-one") is not None
    assert target.counts() == source.counts()
    assert target.verify_audit_chain() is True


def test_fabric_conversation_restarts_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    memory = configured_conversation_memory(root)

    prepared = memory.prepare_request("Prepare the confidential acquisition plan")
    memory.record_turn(
        "user",
        "Private acquisition target Delta",
        channel="private_phone",
    )
    restarted = configured_conversation_memory(root)

    assert restarted.snapshot(channel="private_phone")["active_objective"] == prepared["objective"]
    assert restarted.snapshot(channel="private_phone")["recent_turns"][0]["text"] == "Private acquisition target Delta"
    assert restarted.snapshot(channel="shared_tv")["recent_turns"] == []
    assert not (root / "conversation" / "memory.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    assert b"confidential acquisition" not in raw
    assert b"Private acquisition target Delta" not in raw


def test_fabric_conversation_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    legacy = ConversationMemory(root)
    legacy.prepare_request("Retain this private legacy objective")
    source = root / "conversation" / "memory.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated = configured_conversation_memory(root)

    assert migrated.snapshot()["active_objective"] == "Retain this private legacy objective"
    assert source.read_bytes() == original


def test_fabric_conversation_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_conversation_required"):
        configured_conversation_memory(tmp_path / "node-state")


def test_fabric_private_identity_restarts_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    identities = configured_private_identity(root)
    owner = identities.onboard(display_name="Private Founder")
    phone = IdentityStore(tmp_path / "phone-key").load_or_create()
    identities.begin_phone_enrollment(
        persona_id=owner["persona_id"],
        device_label="Founder's confidential phone",
        public_key=phone.public_key_b64,
        biometric_capable=True,
    )
    identities.remember(
        persona_id=owner["persona_id"],
        kind="customer_preference",
        summary="Never disclose Project Nightingale",
    )

    restarted = configured_private_identity(root)

    assert restarted.snapshot(viewer_persona_id=owner["persona_id"])["viewer_memory_count"] == 1
    assert restarted.snapshot()["profiles"][0]["display_name"] == "Private Founder"
    assert not (root / "private_identity" / "state.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    for secret in (
        b"Private Founder",
        b"Founder's confidential phone",
        b"Never disclose Project Nightingale",
        phone.public_key_b64.encode(),
    ):
        assert secret not in raw


def test_fabric_private_identity_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    legacy = ProductionPrivateIdentity(root)
    legacy.onboard(display_name="Legacy Private Owner")
    source = root / "private_identity" / "state.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated = configured_private_identity(root)

    assert migrated.snapshot()["profiles"][0]["display_name"] == "Legacy Private Owner"
    assert source.read_bytes() == original


def test_fabric_private_identity_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_private_identity_required"):
        configured_private_identity(tmp_path / "node-state")


def test_fabric_pilot_inbox_restarts_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    identities = configured_private_identity(root)
    owner = identities.onboard(display_name="Inbox Owner")
    inbox = configured_pilot_inbox(root, identities=identities)
    private_list = inbox.create_list(
        owner_persona_id=owner["persona_id"],
        name="Confidential acquisition actions",
    )
    task = inbox.create_task(
        requester_persona_id=owner["persona_id"],
        owner_persona_id=owner["persona_id"],
        list_id=private_list["list_id"],
        title="Call Project Nightingale solicitor",
        notes="Do not expose the target company name",
    )

    restarted = configured_pilot_inbox(root, identities=configured_private_identity(root))
    stream = restarted.stream(persona_id=owner["persona_id"])

    assert stream["tasks"][0]["task_id"] == task["task_id"]
    assert stream["lists"][0]["name"] == "Confidential acquisition actions"
    assert not (root / "pilot_inbox" / "state.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    for secret in (
        b"Confidential acquisition actions",
        b"Call Project Nightingale solicitor",
        b"Do not expose the target company name",
    ):
        assert secret not in raw


def test_fabric_pilot_inbox_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    identities = ProductionPrivateIdentity(root)
    owner = identities.onboard(display_name="Legacy Inbox Owner")
    legacy = PilotInbox(root, identities=identities)
    legacy.create_list(owner_persona_id=owner["persona_id"], name="Legacy private list")
    source = root / "pilot_inbox" / "state.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated_identities = configured_private_identity(root)
    migrated = configured_pilot_inbox(root, identities=migrated_identities)

    assert migrated.snapshot()["list_count"] == 1
    assert source.read_bytes() == original


def test_fabric_pilot_inbox_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identities = ProductionPrivateIdentity(tmp_path / "node-state")
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_pilot_inbox_required"):
        configured_pilot_inbox(tmp_path / "node-state", identities=identities)


def test_fabric_calendar_restarts_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    identities = configured_private_identity(root)
    owner = identities.onboard(display_name="Calendar Owner")
    calendar = configured_calendar_planning(root, identities=identities)
    event = calendar.ingest_busy_event(
        persona_id=owner["persona_id"],
        provider_event_id="provider-private-board-meeting",
        start="2026-10-20T09:00:00+02:00",
        end="2026-10-20T10:00:00+02:00",
        title="Confidential acquisition board meeting",
        location="Private boardroom",
    )

    restarted = configured_calendar_planning(root, identities=configured_private_identity(root))
    snapshot = restarted.snapshot(persona_id=owner["persona_id"])

    assert snapshot["events"][0]["event_id"] == event["event_id"]
    assert not (root / "calendar_planning" / "state.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    assert b"Confidential acquisition board meeting" not in raw
    assert b"Private boardroom" not in raw


def test_fabric_calendar_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    identities = ProductionPrivateIdentity(root)
    owner = identities.onboard(display_name="Legacy Calendar Owner")
    legacy = GovernedCalendarPlanning(root, identities=identities)
    legacy.ingest_busy_event(
        persona_id=owner["persona_id"],
        provider_event_id="legacy-event",
        start="2026-10-20T09:00:00+02:00",
        end="2026-10-20T10:00:00+02:00",
        title="Legacy private meeting",
    )
    source = root / "calendar_planning" / "state.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated_identities = configured_private_identity(root)
    migrated = configured_calendar_planning(root, identities=migrated_identities)

    assert len(migrated.snapshot(persona_id=owner["persona_id"])["events"]) == 1
    assert source.read_bytes() == original


def test_fabric_calendar_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identities = ProductionPrivateIdentity(tmp_path / "node-state")
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_calendar_required"):
        configured_calendar_planning(tmp_path / "node-state", identities=identities)


def test_fabric_household_personas_restart_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    household = configured_household_identity_registry(root)
    owner = household.ensure_local_persona(
        mother_id="node_private_mother", display_name="Confidential Founder",
    )
    household.bind_service(
        owner["persona_id"], "calendar", "provider://calendar/project-nightingale",
    )

    restarted = configured_household_identity_registry(root)

    restored = restarted.get(owner["persona_id"])
    assert restored is not None
    assert restored["display_name"] == "Confidential Founder"
    assert restored["service_bindings"]["calendar"] == "provider://calendar/project-nightingale"
    assert not (root / "household" / "personas.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    assert b"Confidential Founder" not in raw
    assert b"project-nightingale" not in raw


def test_fabric_household_persona_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    legacy = HouseholdIdentityRegistry(root)
    owner = legacy.ensure_local_persona(
        mother_id="node_legacy_mother", display_name="Legacy Household Owner",
    )
    source = root / "household" / "personas.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated = configured_household_identity_registry(root)

    assert migrated.get(owner["persona_id"])["display_name"] == "Legacy Household Owner"
    assert source.read_bytes() == original


def test_fabric_household_personas_production_refuse_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_household_required"):
        configured_household_identity_registry(tmp_path / "node-state")


def test_fabric_universal_node_restarts_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    node = IdentityStore(tmp_path / "shared-node-key").load_or_create()
    mother = IdentityStore(tmp_path / "private-mother-key").load_or_create()
    authority = configured_universal_node_authority(
        root, node_id="node_shared_boardroom", identity=node,
    )
    started = authority.begin_handshake(
        mother_id="node_private_mother", public_key=mother.public_key_b64,
    )
    authority.complete_handshake(
        handshake_id=started["handshake_id"],
        confirmation_code=started["confirmation_code"],
        mother_signature=mother.sign(canonical_bytes(started["challenge"])),
        approved_by="confidential-local-owner",
    )

    restarted = configured_universal_node_authority(
        root, node_id="node_shared_boardroom", identity=node,
    )

    assert restarted.snapshot()["trusted_mothers"] == 1
    assert not (root / "universal_node" / "authority.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    assert b"confidential-local-owner" not in raw
    assert mother.public_key_b64.encode() not in raw


def test_fabric_universal_node_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    node = IdentityStore(tmp_path / "legacy-shared-key").load_or_create()
    mother = IdentityStore(tmp_path / "legacy-mother-key").load_or_create()
    legacy = UniversalNodeAuthority(root, node_id="node_legacy_tv", identity=node)
    legacy.enroll_mother(
        mother_id="node_legacy_mother",
        public_key=mother.public_key_b64,
        persona_id="principal_legacyowner",
        approved_by="legacy-local-owner",
    )
    source = root / "universal_node" / "authority.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated = configured_universal_node_authority(
        root, node_id="node_legacy_tv", identity=node,
    )

    assert migrated.snapshot()["trusted_mothers"] == 1
    assert source.read_bytes() == original


def test_fabric_universal_node_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")
    identity = IdentityStore(tmp_path / "node-key").load_or_create()

    with pytest.raises(RuntimeError, match="guardian_universal_node_required"):
        configured_universal_node_authority(
            tmp_path / "node-state", node_id="node_forbidden", identity=identity,
        )


def test_fabric_communication_restarts_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    identities = configured_private_identity(root)
    owner = identities.onboard(display_name="Private Communications Owner")
    inbox = configured_pilot_inbox(root, identities=identities)
    contact = inbox.save_contact(
        owner_persona_id=owner["persona_id"],
        display_name="Confidential Solicitor",
        email="nightingale-solicitor@example.test",
    )
    communication = configured_communication(
        root, identities=identities, inbox=inbox,
    )
    draft = communication.draft(
        persona_id=owner["persona_id"],
        contact_id=contact["contact_id"],
        channel="email",
        subject="Project Nightingale",
        body="Please prepare the confidential acquisition documents.",
    )

    restarted = configured_communication(
        root,
        identities=configured_private_identity(root),
        inbox=configured_pilot_inbox(root, identities=configured_private_identity(root)),
    )

    assert restarted.snapshot(persona_id=owner["persona_id"])["drafts"][0]["draft_id"] == draft["draft_id"]
    assert not (root / "communication" / "state.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    for secret in (
        b"Confidential Solicitor",
        b"nightingale-solicitor@example.test",
        b"Project Nightingale",
        b"confidential acquisition documents",
    ):
        assert secret not in raw


def test_fabric_communication_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    identities = ProductionPrivateIdentity(root)
    owner = identities.onboard(display_name="Legacy Communications Owner")
    inbox = PilotInbox(root, identities=identities)
    contact = inbox.save_contact(
        owner_persona_id=owner["persona_id"],
        display_name="Legacy private contact",
        email="legacy-private@example.test",
    )
    legacy = GovernedCommunication(root, identities=identities, inbox=inbox)
    legacy.draft(
        persona_id=owner["persona_id"], contact_id=contact["contact_id"],
        channel="email", subject="Legacy confidential matter", body="Retain this draft.",
    )
    source = root / "communication" / "state.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    protected_identities = configured_private_identity(root)
    protected_inbox = configured_pilot_inbox(root, identities=protected_identities)
    migrated = configured_communication(
        root, identities=protected_identities, inbox=protected_inbox,
    )

    assert len(migrated.snapshot(persona_id=owner["persona_id"])["drafts"]) == 1
    assert source.read_bytes() == original


def test_fabric_communication_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    identities = ProductionPrivateIdentity(root)
    inbox = PilotInbox(root, identities=identities)
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_communication_required"):
        configured_communication(root, identities=identities, inbox=inbox)


def test_fabric_pilot_guardian_restarts_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    identities = configured_private_identity(root)
    owner = identities.onboard(display_name="Protected Founder")
    inbox = configured_pilot_inbox(root, identities=identities)
    contact = inbox.save_contact(
        owner_persona_id=owner["persona_id"],
        display_name="Private Emergency Contact",
        whatsapp="+34600999888",
    )
    guardian = configured_pilot_guardian(root, identities=identities, inbox=inbox)
    guardian.grant_emergency_contact(
        persona_id=owner["persona_id"], contact_id=contact["contact_id"],
        channel="whatsapp", share_location=True,
        location_permission_receipt="private-location-consent-receipt",
    )
    incident = guardian.request_help(
        persona_id=owner["persona_id"], trigger="Help at the private boardroom",
        surface="private_phone", location={"label": "Private boardroom"},
    )

    restarted = configured_pilot_guardian(
        root,
        identities=configured_private_identity(root),
        inbox=configured_pilot_inbox(root, identities=configured_private_identity(root)),
    )

    assert restarted.snapshot(persona_id=owner["persona_id"])["incidents"][0]["incident_id"] == incident["incident_id"]
    assert not (root / "guardian" / "state.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    for secret in (
        b"Private Emergency Contact",
        b"Help at the private boardroom",
        b"Private boardroom",
        incident["response_token"].encode(),
    ):
        assert secret not in raw


def test_fabric_pilot_guardian_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    identities = ProductionPrivateIdentity(root)
    owner = identities.onboard(display_name="Legacy Protected Owner")
    inbox = PilotInbox(root, identities=identities)
    legacy = PilotGuardian(root, identities=identities, inbox=inbox)
    legacy.request_help(
        persona_id=owner["persona_id"], trigger="Legacy private help request",
        surface="private_phone",
    )
    source = root / "guardian" / "state.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    protected_identities = configured_private_identity(root)
    protected_inbox = configured_pilot_inbox(root, identities=protected_identities)
    migrated = configured_pilot_guardian(
        root, identities=protected_identities, inbox=protected_inbox,
    )

    assert len(migrated.snapshot(persona_id=owner["persona_id"])["incidents"]) == 1
    assert source.read_bytes() == original


def test_fabric_pilot_guardian_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    identities = ProductionPrivateIdentity(root)
    inbox = PilotInbox(root, identities=identities)
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_incident_store_required"):
        configured_pilot_guardian(root, identities=identities, inbox=inbox)


def test_fabric_google_oauth_metadata_restarts_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    identities = configured_private_identity(root)
    owner = identities.onboard(display_name="Google Account Owner")
    oauth = configured_google_oauth(root, identities=identities)
    started = oauth.begin(
        persona_id=owner["persona_id"], services=["calendar", "email_send"],
        client_id="private-business.apps.googleusercontent.com",
        redirect_uri="http://127.0.0.1:49152/oauth/callback",
    )
    oauth.complete(
        authorization_id=started["authorization_id"],
        state_token=started["state"],
        code="one-time-code",
        token_exchange=lambda pending, _code: {
            "access_token": "raw-access-token-never-in-fabric",
            "refresh_token": "raw-refresh-token-never-in-fabric",
            "expires_in": 3600,
            "token_type": "Bearer",
            "scope": " ".join(pending["scopes"]),
        },
        vault_store=lambda persona_id, _tokens: f"vault://os-keychain/google/{persona_id}",
    )

    restarted = configured_google_oauth(root, identities=configured_private_identity(root))

    assert restarted.snapshot(persona_id=owner["persona_id"])["bindings"][0]["provider"] == "google"
    assert not (root / "provider_accounts" / "google.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    for secret in (
        b"private-business.apps.googleusercontent.com",
        b"raw-access-token-never-in-fabric",
        b"raw-refresh-token-never-in-fabric",
        b"os-keychain/google",
    ):
        assert secret not in raw


def test_fabric_google_oauth_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    identities = ProductionPrivateIdentity(root)
    owner = identities.onboard(display_name="Legacy Google Owner")
    legacy = PersonaGoogleOAuth(root, identities=identities)
    legacy.begin(
        persona_id=owner["persona_id"], services=["calendar"],
        client_id="legacy-private.apps.googleusercontent.com",
        redirect_uri="http://127.0.0.1:49152/oauth/callback",
    )
    source = root / "provider_accounts" / "google.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated = configured_google_oauth(
        root, identities=configured_private_identity(root),
    )

    assert len(migrated._read()["pending"]) == 1
    assert source.read_bytes() == original


def test_fabric_google_oauth_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    identities = ProductionPrivateIdentity(tmp_path / "node-state")
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_google_oauth_required"):
        configured_google_oauth(tmp_path / "node-state", identities=identities)


def test_fabric_webos_pairing_uses_os_custody_and_guardian_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stored = {}
    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(
        get_password=lambda service, account: stored.get((service, account)),
        set_password=lambda service, account, value: stored.__setitem__((service, account), value),
    ))
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    pairing_dir = tmp_path / "node-state" / "pairing" / "webos"
    gateway = WebOsGateway(pairing_dir)
    node_id = "node_discovered_private_tv"

    gateway._save_key(node_id, "192.168.1.40", "private-webos-client-key")
    restarted = WebOsGateway(pairing_dir)

    assert restarted._load_key(node_id, "192.168.1.40") == "private-webos-client-key"
    assert not (pairing_dir / f"{node_id}.json").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    assert b"private-webos-client-key" not in raw
    assert b"192.168.1.40" not in raw


def test_fabric_webos_pairing_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pairing_dir = tmp_path / "node-state" / "pairing" / "webos"
    node_id = "node_discovered_legacy_tv"
    legacy = WebOsGateway(pairing_dir)
    legacy._save_key(node_id, "192.168.1.41", "legacy-webos-client-key")
    source = pairing_dir / f"{node_id}.json"
    original = source.read_bytes()
    stored = {}
    monkeypatch.setitem(sys.modules, "keyring", types.SimpleNamespace(
        get_password=lambda service, account: stored.get((service, account)),
        set_password=lambda service, account, value: stored.__setitem__((service, account), value),
    ))
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated = WebOsGateway(pairing_dir)

    assert migrated._load_key(node_id, "192.168.1.41") == "legacy-webos-client-key"
    assert source.read_bytes() == original


def test_fabric_webos_pairing_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_webos_pairing_required"):
        WebOsGateway(tmp_path / "pairing")


def _prepare_private_save(service: PrivateProgrammeSaves) -> dict:
    return service.prepare(
        category="product",
        request="Save the confidential boardroom product",
        live_context={"context_hash": "c" * 64, "recent_transcripts": ["Project Nightingale supplier"]},
        screen_understanding={"products": {"candidate_text": "Private prototype", "prices": ["EUR 42"], "confidence": 0.9}},
        provider_metadata={"title": "Private prototype"},
    )


def test_fabric_private_saves_restart_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    saves = configured_private_programme_saves(root)
    pending = _prepare_private_save(saves)
    saved = saves.claim(pending["save_id"], persona_id="persona_privatefounder")

    restarted = configured_private_programme_saves(root)

    assert restarted.get_saved(saved["save_id"], persona_id="persona_privatefounder")["title"] == "Private prototype"
    assert not (root / "private_saves").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    assert b"Private prototype" not in raw
    assert b"Project Nightingale supplier" not in raw


def test_fabric_private_saves_migration_retains_legacy_sources(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    legacy = PrivateProgrammeSaves(root)
    pending = _prepare_private_save(legacy)
    legacy.claim(pending["save_id"], persona_id="persona_legacyfounder")
    sources = sorted((root / "private_saves").glob("*.json"))
    originals = {path: path.read_bytes() for path in sources}
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated = configured_private_programme_saves(root)

    assert migrated.snapshot(persona_id="persona_legacyfounder")["saved_count"] == 1
    assert all(path.read_bytes() == value for path, value in originals.items())


def test_fabric_private_saves_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_private_saves_required"):
        configured_private_programme_saves(tmp_path / "node-state")


def test_fabric_entertainment_restart_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    service = configured_private_entertainment_personalization(root)
    service.add_watchlist(
        persona_id="founder-private",
        title="Confidential acquisition documentary",
        provider="Private provider",
    )
    service.remember(
        persona_id="founder-private",
        title="Board takeover film",
        outcome="liked",
    )

    restarted = configured_private_entertainment_personalization(root)
    snapshot = restarted.snapshot(persona_id="founder-private")

    assert [item["title"] for item in snapshot["watchlists"]] == [
        "Confidential acquisition documentary"
    ]
    assert [item["title"] for item in snapshot["private_history"]] == [
        "Board takeover film"
    ]
    assert not (root / "entertainment_personalization").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    assert b"Confidential acquisition documentary" not in raw
    assert b"Board takeover film" not in raw


def test_fabric_entertainment_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    legacy = PrivateEntertainmentPersonalization(root)
    legacy.add_watchlist(
        persona_id="legacy-founder",
        title="Legacy private watchlist",
    )
    source = root / "entertainment_personalization" / "state.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated = configured_private_entertainment_personalization(root)

    assert migrated.snapshot(persona_id="legacy-founder")["watchlists"][0]["title"] == (
        "Legacy private watchlist"
    )
    assert source.read_bytes() == original


def test_fabric_entertainment_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_entertainment_required"):
        configured_private_entertainment_personalization(tmp_path / "node-state")


def test_fabric_live_context_restart_encrypted_without_local_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)
    root = tmp_path / "node-state"
    context = configured_live_context_store(root).build(
        device_state={
            "foreground_app_id": "boardroom.private",
            "foreground_app_title": "Confidential strategy presentation",
        },
        recent_transcripts=["Project Nightingale acquisition target"],
        belief={"surface": "private_boardroom"},
    )

    restarted = configured_live_context_store(root)

    assert restarted.latest()["context_hash"] == context["context_hash"]
    assert not (root / "live").exists()
    raw = (tmp_path / "configured-vault" / "records" / "guardian.sqlite3").read_bytes()
    assert b"Project Nightingale acquisition target" not in raw
    assert b"Confidential strategy presentation" not in raw


def test_fabric_live_context_migration_retains_legacy_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "node-state"
    legacy = LiveContextStore(root)
    context = legacy.build(
        device_state={"foreground_app_id": "private.presentation"},
        recent_transcripts=["Legacy confidential spoken context"],
    )
    source = root / "live" / "latest_context.json"
    original = source.read_bytes()
    for name, value in _guardian_environment(tmp_path).items():
        monkeypatch.setenv(name, value)

    migrated = configured_live_context_store(root)

    assert migrated.latest()["context_hash"] == context["context_hash"]
    assert source.read_bytes() == original


def test_fabric_live_context_production_refuses_plaintext(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TESSARIS_BUSINESS_CONTAINER_BACKEND", "legacy")
    monkeypatch.setenv("TESSARIS_RUNTIME_MODE", "production")

    with pytest.raises(RuntimeError, match="guardian_live_context_required"):
        configured_live_context_store(tmp_path / "node-state")
