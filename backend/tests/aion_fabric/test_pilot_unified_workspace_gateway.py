from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.aion_business.runtime.commercial_adoption_service import CommercialAdoptionService
from backend.modules.pilot_unified.pairing import MobilePairingAuthority
from backend.modules.pilot_unified import AionBoardroomWorkspaceProvider, Membership, ProviderIndependentWorkspaceGateway


class TestProvider:
    provider_id = "test-boardroom"

    def __init__(self):
        self.calls = []

    def list_workspaces(self):
        return [
            {
                "id": "acme",
                "name": "Acme Boardroom",
                "business_type": "boardroom",
                "owner": "persona_owner",
                "governance_policy_ref": "acme.policy.v1",
            },
            {
                "id": "client-blue",
                "name": "Client Blue",
                "business_type": "workspace",
                "owner": "persona_client",
            },
        ]

    def describe_workspace(self, workspace_ref):
        return {
            "id": workspace_ref,
            "departments": [{"id": "marketing", "name": "Marketing"}],
            "agents": [{"id": "pilot-sales", "label": "Sales Pilot"}],
            "dashboards": [{"id": "revenue", "label": "Revenue"}],
            "files": [{"id": "proposal", "label": "Proposal"}],
            "packages": [{"id": "signoff", "label": "Sign-off"}],
            "decisions": [{"id": "decision-1", "label": "Expansion"}],
            "permitted_actions": ["workspace.read", "workspace.decisions.approve"],
        }

    def read_surface(self, workspace_ref, surface, *, persona_id):
        self.calls.append((workspace_ref, surface, persona_id))
        data = {"headline": f"{surface} for {workspace_ref}"}
        if surface == "departments":
            data["work"] = [{"task_id": "task-1", "department_id": "finance", "status": "waiting_approval", "title": "Review forecast"}]
        if surface == "files":
            data["files"] = [{"id": "file-1", "label": "Forecast.pdf", "document_type": "report", "protected": True}]
        return {"revision": 7, "data": data}

    def conversation_turn(self, workspace_ref, department_id, user_text, *, persona_id):
        self.calls.append((workspace_ref, department_id, user_text, persona_id))
        return {
            "conversation_id": f"conversation-{workspace_ref}",
            "department_id": department_id,
            "turn": {"turn_id": "turn-1", "role": "assistant", "content": f"Grounded answer: {user_text}"},
            "provider": {"provider": "test"},
            "evidence": [{"ref": "record-1"}],
            "reliability": "source_backed",
            "external_writes_performed": False,
        }

    def executive_channel_status(self, workspace_ref):
        self.calls.append((workspace_ref, "executive_status"))
        return {
            "schedule": {"enabled": True, "local_time": "08:00", "timezone": "Europe/Madrid"},
            "latest_briefing": {"reasoning_mode": "single_model_role_separated"},
        }

    def executive_channel_history(self, workspace_ref, department_id, *, limit=75):
        self.calls.append((workspace_ref, "executive_history", department_id, limit))
        return {
            "department_id": department_id,
            "turns": [{
                "id": "executive-message-1", "role": "assistant", "sender": "Sales Director Pilot",
                "content": "Morning minutes are ready.", "message_type": "morning_minutes",
                "evidence_source_ids": ["sales_revenue_spine"], "approval_gated": True,
            }],
        }

    def executive_channel_turn(self, workspace_ref, department_id, user_text, *, persona_id):
        self.calls.append((workspace_ref, "executive_turn", department_id, user_text, persona_id))
        return {
            "department_id": department_id,
            "response": {"sender": "Sales Director Pilot", "content": f"Department answer: {user_text}"},
            "external_writes_performed": False,
        }


def membership(*, membership_id="member_1", space_id="workspace/acme", scopes=("workspace.read",), status="active", expires=None):
    now = datetime.now(timezone.utc)
    expiry = datetime.fromisoformat(expires) if expires else now + timedelta(hours=1)
    issued = min(now, expiry - timedelta(hours=1))
    return Membership(
        membership_id=membership_id,
        persona_id="persona_alex",
        space_id=space_id,
        role_id="role_reviewer",
        scopes=tuple(scopes),
        status=status,
        issued_at=issued.isoformat(),
        expires_at=expiry.isoformat(),
    )


def gateway(tmp_path=None):
    kwargs = {}
    if tmp_path is not None:
        kwargs = {"issuer_id": "mother_home", "issuer_identity": IdentityStore(tmp_path / "issuer").load_or_create()}
    result = ProviderIndependentWorkspaceGateway(**kwargs)
    provider = TestProvider()
    result.register_provider(provider)
    result.discover(provider.provider_id)
    return result, provider


def test_gateway_projects_provider_workspace_without_copying_provider_records():
    subject, provider = gateway()
    subject.grant_membership(membership())

    spaces = subject.spaces_for("persona_alex")
    assert [item["space"]["display_name"] for item in spaces] == ["Acme Boardroom"]
    assert spaces[0]["space"]["kind"] == "boardroom"
    result = subject.read(persona_id="persona_alex", membership_id="member_1", surface="briefings")
    assert result["data"]["headline"] == "briefings for acme"
    assert result["source_of_truth"] == "workspace_provider"
    assert result["projection_hash"]
    assert provider.calls == [("acme", "briefings", "persona_alex")]


def test_gateway_enforces_space_and_surface_scopes():
    subject, provider = gateway()
    subject.grant_membership(membership(scopes=("workspace.files.read",)))
    with pytest.raises(PermissionError):
        subject.read(persona_id="persona_alex", membership_id="member_1", surface="briefings")
    assert subject.read(persona_id="persona_alex", membership_id="member_1", surface="files")["ok"]
    with pytest.raises(ValueError):
        subject.read(persona_id="persona_alex", membership_id="member_1", surface="payroll")
    assert len(provider.calls) == 1


def test_gateway_adapts_read_only_workspace_conversation_with_exact_membership_scope():
    subject, provider = gateway()
    subject.grant_membership(membership(scopes=("workspace.department.finance.conversation",)))
    result = subject.conversation_turn(
        persona_id="persona_alex", membership_id="member_1", department_id="finance",
        user_text="  Why did margin fall?  ",
    )
    assert result["conversation"]["turn"]["content"] == "Grounded answer: Why did margin fall?"
    assert result["external_writes_performed"] is False
    assert result["question_hash"]
    assert provider.calls == [("acme", "finance", "Why did margin fall?", "persona_alex")]
    with pytest.raises(PermissionError):
        subject.conversation_turn(
            persona_id="persona_alex", membership_id="member_1", department_id="sales",
            user_text="What changed?",
        )


def test_gateway_rejects_conversation_provider_that_claims_an_external_write():
    subject, provider = gateway()
    subject.grant_membership(membership(scopes=("workspace.conversation",)))
    provider.conversation_turn = lambda *args, **kwargs: {
        "turn": {"content": "I changed the ledger."}, "external_writes_performed": True,
    }
    with pytest.raises(ValueError, match="external write"):
        subject.conversation_turn(
            persona_id="persona_alex", membership_id="member_1", department_id="boardroom",
            user_text="Change it",
        )


def test_gateway_exposes_the_same_persistent_executive_channels_to_mobile_clients():
    subject, provider = gateway()
    subject.grant_membership(membership(scopes=("workspace.conversation",)))

    status = subject.executive_channels_status(persona_id="persona_alex", membership_id="member_1")
    history = subject.executive_channel_history(
        persona_id="persona_alex", membership_id="member_1", department_id="sales",
    )
    turn = subject.executive_channel_turn(
        persona_id="persona_alex", membership_id="member_1", department_id="sales",
        user_text="How are we tracking against today's target?",
    )

    assert status["executive"]["schedule"]["local_time"] == "08:00"
    assert history["history"]["turns"][0]["message_type"] == "morning_minutes"
    assert turn["executive"]["response"]["content"].startswith("Department answer:")
    assert turn["external_writes_performed"] is False
    assert provider.calls == [
        ("acme", "executive_status"),
        ("acme", "executive_history", "sales", 75),
        ("acme", "executive_turn", "sales", "How are we tracking against today's target?", "persona_alex"),
    ]


def test_workspace_review_cards_bind_review_correction_delegation_and_approval_to_exact_scope():
    subject, _ = gateway()
    subject.grant_membership(membership(scopes=("workspace.read", "workspace.cards.act", "workspace.approve")))
    card = subject.review_cards(persona_id="persona_alex", membership_id="member_1")["cards"][0]
    corrected = subject.act_on_review_card(
        persona_id="persona_alex", membership_id="member_1", card_id=card["card_id"],
        operation="correct", expected_scope_hash=card["scope_hash"], correction="Use the reconciled forecast.",
        idempotency_key="correct-1",
    )
    assert corrected["state"] == "correction_requested"
    assert corrected["receipt"]["external_write_performed"] is False
    assert subject.act_on_review_card(
        persona_id="persona_alex", membership_id="member_1", card_id=card["card_id"],
        operation="correct", expected_scope_hash=card["scope_hash"], correction="Use the reconciled forecast.",
        idempotency_key="correct-1",
    ) == corrected
    changed = subject.review_cards(persona_id="persona_alex", membership_id="member_1")["cards"][0]
    with pytest.raises(PermissionError, match="changed"):
        subject.act_on_review_card(
            persona_id="persona_alex", membership_id="member_1", card_id=card["card_id"],
            operation="approve", expected_scope_hash=card["scope_hash"], idempotency_key="approve-stale",
        )
    delegated = subject.act_on_review_card(
        persona_id="persona_alex", membership_id="member_1", card_id=changed["card_id"],
        operation="delegate", expected_scope_hash=changed["scope_hash"], recipient_ref="person/adviser",
        idempotency_key="delegate-1",
    )
    assert delegated["state"] == "delegation_prepared"
    latest = subject.review_cards(persona_id="persona_alex", membership_id="member_1")["cards"][0]
    approved = subject.act_on_review_card(
        persona_id="persona_alex", membership_id="member_1", card_id=latest["card_id"],
        operation="approve", expected_scope_hash=latest["scope_hash"], idempotency_key="approve-1",
    )
    assert approved["state"] == "approved"
    assert approved["approval_is_execution"] is False


def test_workspace_card_action_requires_separate_read_act_and_approval_scopes():
    subject, _ = gateway()
    subject.grant_membership(membership(scopes=("workspace.cards.read",)))
    card = subject.review_cards(persona_id="persona_alex", membership_id="member_1")["cards"][0]
    with pytest.raises(PermissionError, match="workspace.cards.act"):
        subject.act_on_review_card(
            persona_id="persona_alex", membership_id="member_1", card_id=card["card_id"],
            operation="review", expected_scope_hash=card["scope_hash"], idempotency_key="review-1",
        )
    with pytest.raises(PermissionError, match="workspace.approve"):
        subject.act_on_review_card(
            persona_id="persona_alex", membership_id="member_1", card_id=card["card_id"],
            operation="approve", expected_scope_hash=card["scope_hash"], idempotency_key="approve-1",
        )


@pytest.mark.parametrize("role", ["accountant", "auditor", "adviser", "director"])
def test_professional_signoff_packages_bind_role_scope_phone_possession_and_immutable_hash(role):
    subject, _ = gateway()
    subject.grant_membership(membership(scopes=(
        "workspace.read", "workspace.signoff.prepare", "workspace.signoff.read", f"workspace.signoff.{role}",
    )))
    card = subject.review_cards(persona_id="persona_alex", membership_id="member_1")["cards"][0]
    prepared = subject.prepare_signoff_package(
        persona_id="persona_alex", membership_id="member_1", card_id=card["card_id"],
        expected_scope_hash=card["scope_hash"], signatory_role=role,
        statement="I reviewed the exact evidence and scope shown.", idempotency_key=f"prepare-{role}",
    )
    package = prepared["package"]
    assert package["signatory_role"] == role
    assert package["status"] == "awaiting_signoff"
    result = subject.decide_signoff_package(
        persona_id="persona_alex", membership_id="member_1", package_id=package["package_id"],
        expected_package_hash=package["package_hash"], decision="signed",
        professional_reference=f"{role} acting in declared capacity", phone_device_id="phone-1",
        phone_signature="signed-request", idempotency_key=f"sign-{role}",
    )
    assert result["package"]["status"] == "signed"
    assert result["receipt"]["phone_device_id"] == "phone-1"
    assert result["receipt"]["phone_signature_hash"]
    assert result["receipt"]["external_write_performed"] is False
    assert result["independently_verifiable"] is True


def test_signoff_cannot_use_wrong_professional_role_or_changed_package_hash():
    subject, _ = gateway()
    subject.grant_membership(membership(scopes=(
        "workspace.read", "workspace.signoff.prepare", "workspace.signoff.read", "workspace.signoff.accountant",
    )))
    card = subject.review_cards(persona_id="persona_alex", membership_id="member_1")["cards"][0]
    package = subject.prepare_signoff_package(
        persona_id="persona_alex", membership_id="member_1", card_id=card["card_id"],
        expected_scope_hash=card["scope_hash"], signatory_role="auditor", statement="Independent review.",
        idempotency_key="prepare-audit",
    )["package"]
    with pytest.raises(PermissionError, match="professional sign-off role"):
        subject.decide_signoff_package(
            persona_id="persona_alex", membership_id="member_1", package_id=package["package_id"],
            expected_package_hash=package["package_hash"], decision="signed", professional_reference="Auditor",
            phone_device_id="phone-1", phone_signature="signature", idempotency_key="sign-audit",
        )
    subject.grant_membership(membership(scopes=(
        "workspace.read", "workspace.signoff.prepare", "workspace.signoff.read", "workspace.signoff.auditor",
    )))
    with pytest.raises(PermissionError, match="changed"):
        subject.decide_signoff_package(
            persona_id="persona_alex", membership_id="member_1", package_id=package["package_id"],
            expected_package_hash="wrong", decision="signed", professional_reference="Auditor",
            phone_device_id="phone-1", phone_signature="signature", idempotency_key="sign-audit-changed",
        )


def test_cross_space_file_reference_preserves_source_ownership_and_copies_no_content():
    subject, _ = gateway()
    subject.grant_membership(membership(membership_id="source", scopes=("workspace.files.read",)))
    subject.grant_membership(membership(
        membership_id="target", space_id="workspace/client-blue", scopes=("workspace.files.reference",),
    ))
    result = subject.create_cross_space_file_reference(
        persona_id="persona_alex", source_membership_id="source", target_membership_id="target",
        file_id="file-1", idempotency_key="file-ref-1",
    )
    reference = result["reference"]
    assert result["bytes_copied"] == 0
    assert result["source_ownership_preserved"] is True
    assert reference["content_included"] is False
    assert reference["storage_path_included"] is False
    assert reference["access_mode"] == "reference_only_reauthorize_at_source"
    snapshot = subject.cross_space_file_references(persona_id="persona_alex", membership_id="target")
    assert snapshot["references"] == [reference]


def test_cross_space_file_reference_requires_both_memberships_and_never_accepts_unknown_file():
    subject, _ = gateway()
    subject.grant_membership(membership(membership_id="source", scopes=("workspace.files.read",)))
    subject.grant_membership(membership(
        membership_id="target", space_id="workspace/client-blue", scopes=("workspace.files.reference",),
    ))
    with pytest.raises(LookupError, match="file was not found"):
        subject.create_cross_space_file_reference(
            persona_id="persona_alex", source_membership_id="source", target_membership_id="target",
            file_id="missing", idempotency_key="missing",
        )
    subject.grant_membership(membership(
        membership_id="blocked-target", space_id="workspace/client-blue", scopes=("workspace.read",),
    ))
    with pytest.raises(PermissionError, match="target membership"):
        subject.create_cross_space_file_reference(
            persona_id="persona_alex", source_membership_id="source", target_membership_id="blocked-target",
            file_id="file-1", idempotency_key="blocked",
        )


def test_desktop_handoff_is_short_lived_signed_and_never_grants_workspace_access(tmp_path):
    subject, _ = gateway(tmp_path)
    subject.grant_membership(membership(scopes=("workspace.desktop.handoff",)))
    result = subject.prepare_desktop_handoff(
        persona_id="persona_alex", membership_id="member_1", purpose="Complete company setup",
        idempotency_key="desktop-1", ttl_seconds=300,
    )
    ticket = result["ticket"]
    assert result["desktop_path"].startswith("/aion-business?workspace_id=acme&pilot_handoff=")
    assert ticket["authentication_required"] is True
    assert ticket["grants_workspace_access"] is False
    assert ticket["token_hash"] and ticket["signature"]
    assert datetime.fromisoformat(ticket["expires_at"]) - datetime.fromisoformat(ticket["issued_at"]) == timedelta(minutes=5)
    assert subject.prepare_desktop_handoff(
        persona_id="persona_alex", membership_id="member_1", purpose="Complete company setup",
        idempotency_key="desktop-1", ttl_seconds=300,
    ) == result


def test_desktop_handoff_requires_exact_scope(tmp_path):
    subject, _ = gateway(tmp_path)
    subject.grant_membership(membership(scopes=("workspace.read",)))
    with pytest.raises(PermissionError, match="desktop handoff"):
        subject.prepare_desktop_handoff(
            persona_id="persona_alex", membership_id="member_1", purpose="Deep work",
            idempotency_key="desktop-denied",
        )


def test_expired_membership_immediately_blocks_every_stage_six_surface(tmp_path):
    subject, _ = gateway(tmp_path)
    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    subject.grant_membership(membership(
        expires=expired,
        scopes=(
            "workspace.read", "workspace.conversation", "workspace.cards.read", "workspace.cards.act",
            "workspace.approve", "workspace.signoff.prepare", "workspace.signoff.read", "workspace.signoff",
            "workspace.files.read", "workspace.files.reference", "workspace.desktop.handoff",
        ),
    ))
    operations = (
        lambda: subject.read(persona_id="persona_alex", membership_id="member_1", surface="overview"),
        lambda: subject.conversation_turn(persona_id="persona_alex", membership_id="member_1", department_id="finance", user_text="Status?"),
        lambda: subject.review_cards(persona_id="persona_alex", membership_id="member_1"),
        lambda: subject.signoff_packages(persona_id="persona_alex", membership_id="member_1"),
        lambda: subject.cross_space_file_references(persona_id="persona_alex", membership_id="member_1"),
        lambda: subject.prepare_desktop_handoff(persona_id="persona_alex", membership_id="member_1", purpose="Deep work", idempotency_key="expired"),
    )
    for operation in operations:
        with pytest.raises(PermissionError, match="inactive or expired"):
            operation()


def test_overbroad_administrator_cannot_grant_signoff_or_personal_authority():
    subject, _ = gateway()
    subject.grant_membership(membership(
        membership_id="admin", scopes=("workspace.members.manage", "workspace.read"),
    ))
    subject.grant_membership(membership(membership_id="member", scopes=("workspace.read",)))
    with pytest.raises(PermissionError, match="cannot grant scopes"):
        subject.manage_membership(
            actor_persona_id="persona_alex", actor_membership_id="admin", target_membership_id="member",
            operation="change_role", role_id="role_director",
            scopes=("workspace.read", "workspace.signoff.director", "personal_memory.read"),
        )


def test_mobile_commercial_controls_use_signed_phone_and_exact_workspace_membership(tmp_path):
    class PhoneAuthority:
        def validate_signed_request(self, **kwargs):
            assert kwargs["phone_signature"] == "signed"
            assert kwargs["required_scope"] in {"workspace.commercial.read", "workspace.commercial.control"}
            return {"persona_id": "persona_alex"}

    commercial = CommercialAdoptionService(tmp_path / "commercial")
    subject = ProviderIndependentWorkspaceGateway(pairing_authority=PhoneAuthority(), commercial_service=commercial)
    provider = TestProvider(); subject.register_provider(provider); subject.discover(provider.provider_id)
    subject.grant_membership(membership(scopes=("workspace.commercial.read", "workspace.commercial.control")))
    envelope = {"certificate": {}, "lease": {}, "phone_signature": "signed"}
    started = subject.mobile_commercial_action({
        "persona_id": "persona_alex", "membership_id": "member_1", "operation": "start_trial",
        "department": "sales", "days": 30, "action_limit": 100, "managed_cost_limit": 0,
        "currency": "EUR", "offer_version": "mobile-test-v1", "consent_ref": "exact-visible-terms",
    }, **envelope)
    assert started["dashboard"]["tenant_id"] == "acme"
    assert started["dashboard"]["private_content_included"] is False
    snapshot = subject.mobile_commercial_snapshot({
        "persona_id": "persona_alex", "membership_id": "member_1",
        "purpose": "read_content_free_commercial_dashboard",
    }, **envelope)
    assert snapshot["dashboard"]["trials"][0]["department"] == "sales"
    assert snapshot["external_writes_performed"] is False
    capacity = subject.mobile_commercial_action({
        "persona_id": "persona_alex", "membership_id": "member_1", "operation": "set_capacity",
        "department": "sales", "monthly_action_limit": 250, "overage_allowed": True,
        "overage_approval_ref": "exact-mobile-overage-approval",
    }, **envelope)
    assert capacity["dashboard"]["controls"][0]["monthly_action_limit"] == 250
    assert capacity["dashboard"]["controls"][0]["overage_allowed"] is True


def test_mobile_commercial_controls_fail_closed_without_membership_scope(tmp_path):
    class PhoneAuthority:
        def validate_signed_request(self, **kwargs):
            return {"persona_id": "persona_alex"}

    subject, provider = gateway()
    subject._pairing = PhoneAuthority()
    subject._commercial = CommercialAdoptionService(tmp_path / "commercial")
    subject.grant_membership(membership(scopes=("workspace.read",)))
    with pytest.raises(PermissionError, match="commercial status"):
        subject.mobile_commercial_snapshot(
            {"persona_id": "persona_alex", "membership_id": "member_1"},
            certificate={}, lease={}, phone_signature="signed",
        )


def test_gateway_fails_closed_for_wrong_person_inactive_or_expired_membership():
    subject, _ = gateway()
    subject.grant_membership(membership())
    with pytest.raises(PermissionError):
        subject.read(persona_id="persona_intruder", membership_id="member_1", surface="overview")

    subject.grant_membership(membership(membership_id="suspended", status="suspended"))
    with pytest.raises(PermissionError):
        subject.read(persona_id="persona_alex", membership_id="suspended", surface="overview")

    expired = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    subject.grant_membership(membership(membership_id="expired", expires=expired))
    with pytest.raises(PermissionError):
        subject.read(persona_id="persona_alex", membership_id="expired", surface="overview")


def test_workspace_administrator_cannot_request_or_receive_personal_pilot_data():
    subject, provider = gateway()
    subject.grant_membership(membership(scopes=("workspace.read", "workspace.members.manage")))
    with pytest.raises(ValueError, match="surface is not supported"):
        subject.read(persona_id="persona_alex", membership_id="member_1", surface="personal_pilot")
    original = provider.read_surface
    provider.read_surface = lambda *args, **kwargs: {
        "revision": 1, "data": {"headline": "Workspace", "personal_memory": [{"secret": "home"}]},
    }
    with pytest.raises(PermissionError, match="Personal Pilot data"):
        subject.read(persona_id="persona_alex", membership_id="member_1", surface="overview")
    provider.read_surface = original


def test_gateway_keeps_unrelated_client_memberships_separate():
    subject, provider = gateway()
    subject.grant_membership(membership())
    subject.grant_membership(
        membership(
            membership_id="member_2",
            space_id="workspace/client-blue",
            scopes=("workspace.departments.read",),
        )
    )
    blue = subject.read(
        persona_id="persona_alex", membership_id="member_2", surface="departments"
    )
    assert blue["space"]["display_name"] == "Client Blue"
    with pytest.raises(PermissionError):
        subject.read(persona_id="persona_alex", membership_id="member_2", surface="files")
    assert provider.calls[-1][0] == "client-blue"


def test_signed_manifest_is_bounded_to_membership_provider_and_expiry(tmp_path):
    subject, _ = gateway(tmp_path)
    subject.grant_membership(
        membership(scopes=("workspace.read", "workspace.decisions.approve"))
    )
    envelope = subject.publish_signed_manifest(
        persona_id="persona_alex",
        membership_id="member_1",
        device_id="phone_alex",
        lease_id="lease_1",
        surface_id="phone_alex",
        requested_capabilities=("workspace.read", "workspace.decisions.approve"),
        redactions=("finance.private",),
    )
    assert subject.verify_signed_manifest(
        envelope, expected_persona_id="persona_alex", expected_device_id="phone_alex"
    )
    assert envelope["manifest"]["capabilities"] == [
        "workspace.read", "workspace.decisions.approve"
    ]
    assert envelope["catalog"]["departments"] == [{"id": "marketing", "label": "Marketing"}]

    tampered = dict(envelope)
    tampered["catalog"] = {**envelope["catalog"], "files": [{"id": "secret", "label": "Secret"}]}
    assert not subject.verify_signed_manifest(tampered)


def test_manifest_cannot_expand_membership_or_provider_declaration(tmp_path):
    subject, _ = gateway(tmp_path)
    subject.grant_membership(membership(scopes=("workspace.read",)))
    with pytest.raises(PermissionError):
        subject.publish_signed_manifest(
            persona_id="persona_alex", membership_id="member_1", device_id="phone_alex",
            lease_id="lease_1", surface_id="phone_alex",
            requested_capabilities=("workspace.decisions.approve",),
        )
    with pytest.raises(ValueError):
        subject.publish_signed_manifest(
            persona_id="persona_alex", membership_id="member_1", device_id="phone_alex",
            lease_id="lease_1", surface_id="phone_alex",
            requested_capabilities=("workspace.read",), ttl_seconds=901,
        )


def test_workspace_invitation_has_exact_scope_constraints_expiry_and_revocation_route():
    subject, _ = gateway()
    subject.grant_membership(
        membership(scopes=("workspace.invite", "workspace.read", "workspace.files.read"))
    )
    created = subject.create_invitation(
        inviter_persona_id="persona_alex", inviter_membership_id="member_1",
        recipient_ref="person/freelancer", role_id="role_marketing",
        requested_scopes=("workspace.read",), constraints={"departments": ["marketing"]},
        expires_in_seconds=3_600, idempotency_key="invite-freelancer-1",
    )
    assert created["organization"]["display_name"] == "Acme Boardroom"
    assert created["invitation"]["requested_scopes"] == ["workspace.read"]
    assert created["constraints"] == {"departments": ["marketing"]}
    assert created["revocation_route"].endswith("/revoke")
    replay = subject.create_invitation(
        inviter_persona_id="persona_alex", inviter_membership_id="member_1",
        recipient_ref="person/freelancer", role_id="role_marketing",
        requested_scopes=("workspace.read",), constraints={"departments": ["marketing"]},
        expires_in_seconds=3_600, idempotency_key="invite-freelancer-1",
    )
    assert replay["invitation"]["invitation_id"] == created["invitation"]["invitation_id"]
    revoked = subject.revoke_invitation(
        invitation_id=created["invitation"]["invitation_id"],
        actor_persona_id="persona_alex", actor_membership_id="member_1",
    )
    assert revoked["invitation"]["state"] == "revoked"


def test_invitation_cannot_delegate_more_authority_or_reuse_key_with_changed_scope():
    subject, _ = gateway()
    subject.grant_membership(membership(scopes=("workspace.invite", "workspace.read")))
    with pytest.raises(PermissionError):
        subject.create_invitation(
            inviter_persona_id="persona_alex", inviter_membership_id="member_1",
            recipient_ref="person/freelancer", role_id="role_finance",
            requested_scopes=("workspace.finance.read",), idempotency_key="overbroad",
        )
    subject.create_invitation(
        inviter_persona_id="persona_alex", inviter_membership_id="member_1",
        recipient_ref="person/freelancer", role_id="role_viewer",
        requested_scopes=("workspace.read",), idempotency_key="stable",
    )
    with pytest.raises(ValueError):
        subject.create_invitation(
            inviter_persona_id="persona_alex", inviter_membership_id="member_1",
            recipient_ref="person/other", role_id="role_viewer",
            requested_scopes=("workspace.read",), idempotency_key="stable",
        )


def test_recipient_reviews_and_accepts_invitation_only_from_possession_bound_phone(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path / "state")
    recipient = identities.onboard(display_name="Freelancer", role="adult")
    mother = IdentityStore(tmp_path / "mother").load_or_create()
    pairing = MobilePairingAuthority(
        tmp_path / "state", mother_id="mother_home", mother_identity=mother,
        endpoint="https://home.test:8770", ca_sha256="ab" * 32, identity_registry=identities,
    )
    phone = IdentityStore(tmp_path / "phone").load_or_create()
    challenge = pairing.begin_pairing(
        persona_id=recipient["persona_id"], device_label="Freelancer phone",
        phone_public_key=phone.public_key_b64,
        requested_scopes=("workspace.invitations.read", "workspace.invitations.respond"),
    )
    payload = {key: challenge["phone_challenge"][key] for key in (
        "schema_version", "challenge_id", "mother_id", "mother_fingerprint", "mother_descriptor_hash",
        "persona_id", "device_id", "device_label", "requested_scopes", "nonce", "issued_at", "expires_at",
    )}
    connected = pairing.complete_pairing(
        challenge_id=payload["challenge_id"],
        confirmation_code=challenge["local_confirmation"]["confirmation_code"],
        phone_signature=phone.sign(canonical_bytes(payload)),
    )
    subject = ProviderIndependentWorkspaceGateway(pairing_authority=pairing)
    provider = TestProvider()
    subject.register_provider(provider)
    subject.discover(provider.provider_id)
    subject.grant_membership(
        Membership(
            membership_id="inviter", persona_id="persona_alex", space_id="workspace/acme",
            role_id="role_owner", scopes=("workspace.invite", "workspace.read"), status="active",
            issued_at=datetime.now(timezone.utc).isoformat(),
            expires_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        )
    )
    created = subject.create_invitation(
        inviter_persona_id="persona_alex", inviter_membership_id="inviter",
        recipient_ref=f"person/{recipient['persona_id']}", role_id="role_marketing",
        requested_scopes=("workspace.read",), constraints={"departments": ["marketing"]},
        idempotency_key="invite-phone-review",
    )
    review = {"persona_id": recipient["persona_id"], "purpose": "review_workspace_invitations", "idempotency_key": "read-1"}
    snapshot = subject.invitation_snapshot(
        review, certificate=connected["certificate"], lease=connected["lease"],
        phone_signature=phone.sign(canonical_bytes(review)),
    )
    assert len(snapshot["invitations"]) == 1
    assert "request_hash" not in snapshot["invitations"][0]
    response = {
        "persona_id": recipient["persona_id"],
        "invitation_id": created["invitation"]["invitation_id"],
        "decision": "accepted", "idempotency_key": "accept-1",
    }
    accepted = subject.respond_to_invitation(
        response, certificate=connected["certificate"], lease=connected["lease"],
        phone_signature=phone.sign(canonical_bytes(response)),
    )
    assert accepted["invitation"]["state"] == "accepted"
    assert accepted["membership"]["persona_id"] == recipient["persona_id"]
    assert accepted["decision_receipt"]["device_id"] == connected["certificate"]["device_id"]

    forged = dict(response, invitation_id="invite/not-real")
    with pytest.raises(PermissionError):
        subject.respond_to_invitation(
            forged, certificate=connected["certificate"], lease=connected["lease"],
            phone_signature=phone.sign(canonical_bytes(response)),
        )


def test_membership_role_suspension_restore_expiry_and_revocation_are_immediate():
    subject, _ = gateway()
    subject.grant_membership(
        membership(
            membership_id="admin", scopes=(
                "workspace.members.manage", "workspace.read", "workspace.files.read"
            ),
        )
    )
    subject.grant_membership(membership(membership_id="member", scopes=("workspace.read",)))
    changed = subject.manage_membership(
        actor_persona_id="persona_alex", actor_membership_id="admin",
        target_membership_id="member", operation="change_role", role_id="role_files",
        scopes=("workspace.files.read",), reason="Move to document review",
    )
    assert changed["membership"]["revision"] == 2
    assert subject.read(persona_id="persona_alex", membership_id="member", surface="files")["ok"]
    with pytest.raises(PermissionError):
        subject.read(persona_id="persona_alex", membership_id="member", surface="briefings")
    subject.manage_membership(
        actor_persona_id="persona_alex", actor_membership_id="admin",
        target_membership_id="member", operation="suspend",
    )
    with pytest.raises(PermissionError):
        subject.read(persona_id="persona_alex", membership_id="member", surface="files")
    subject.manage_membership(
        actor_persona_id="persona_alex", actor_membership_id="admin",
        target_membership_id="member", operation="restore",
    )
    assert subject.read(persona_id="persona_alex", membership_id="member", surface="files")["ok"]
    subject.manage_membership(
        actor_persona_id="persona_alex", actor_membership_id="admin",
        target_membership_id="member", operation="revoke", reason="Engagement ended",
    )
    with pytest.raises(PermissionError):
        subject.read(persona_id="persona_alex", membership_id="member", surface="files")


def test_membership_admin_cannot_cross_workspace_or_expand_own_scope():
    subject, _ = gateway()
    subject.grant_membership(
        membership(membership_id="admin", scopes=("workspace.members.manage", "workspace.read"))
    )
    subject.grant_membership(
        membership(membership_id="blue", space_id="workspace/client-blue", scopes=("workspace.read",))
    )
    with pytest.raises(PermissionError):
        subject.manage_membership(
            actor_persona_id="persona_alex", actor_membership_id="admin",
            target_membership_id="blue", operation="suspend",
        )
    subject.grant_membership(membership(membership_id="member", scopes=("workspace.read",)))
    with pytest.raises(PermissionError):
        subject.manage_membership(
            actor_persona_id="persona_alex", actor_membership_id="admin",
            target_membership_id="member", operation="change_role", role_id="role_finance",
            scopes=("workspace.finance.read",),
        )


def test_aion_boardroom_adapter_returns_bounded_mobile_summaries_without_secrets():
    class Model:
        def model_dump(self, mode="json"):
            return {"id": "acme", "name": "Acme", "business_type": "boardroom", "owner": "owner"}
    class Workspaces:
        def list_ids(self): return ["acme"]
        def load(self, workspace_ref): return Model()
    class Containers:
        def load_optional_dict(self, workspace_ref, kind):
            if kind == "boardroom_snapshot":
                return {"boardroom": {"departments": [{"id": "sales", "name": "Sales", "api_key": "never"}], "pulse": {"headline": "Revenue improved"}}}
            return {"meta": {"revision": 4}, "runtime_summary": {"boardroom_summary": {"headline": "Morning briefing", "queue": {"pending": 2}, "provider_token": "never"}}, "dashboard_summary": {"health": {"status": "healthy"}, "customer_email": "never@example.test"}}
    class Departments:
        def list_for_workspace(self, workspace_ref): return []
    adapter = AionBoardroomWorkspaceProvider(Workspaces(), Containers(), Departments())
    assert adapter.list_workspaces()[0]["name"] == "Acme"
    descriptor = adapter.describe_workspace("acme")
    assert descriptor["departments"][0] == {"id": "sales", "label": "Sales"}
    briefing = adapter.read_surface("acme", "briefings", persona_id="persona_alex")
    assert briefing["revision"] == 4
    assert briefing["data"]["headline"] == "Morning briefing"
    assert "provider_token" not in briefing["data"]
    dashboard = adapter.read_surface("acme", "dashboards", persona_id="persona_alex")
    assert dashboard["data"] == {"health": {"status": "healthy"}}


def test_aion_boardroom_adapter_projects_published_minutes_and_delegated_actions_for_mobile():
    class Model:
        def model_dump(self, mode="json"):
            return {"id": "acme", "name": "Acme", "business_type": "boardroom", "owner": "owner"}
    class Workspaces:
        def list_ids(self): return ["acme"]
        def load(self, workspace_ref): return Model()
    class Containers:
        def load_optional_dict(self, workspace_ref, kind):
            if kind == "boardroom_snapshot":
                return {
                    "boardroom": {
                        "board_members": [
                            {"id": "aion", "name": "AION"},
                            {"id": "openai", "name": "OpenAI"},
                        ],
                        "runtime": {
                            "meeting_history": [
                                {"session_id": "august", "session_type": "monthly_review", "status": "published", "published_at": "2026-08-31T09:00:00Z", "summary": "Approved the September plan."},
                                {"session_id": "draft", "session_type": "monthly_review", "status": "draft", "summary": "Must stay private."},
                            ],
                            "delegated_actions": [
                                {"action_id": "sales-1", "title": "Review qualified pipeline", "department_id": "sales", "status": "delegated", "due_at": "2026-09-20"},
                            ],
                        },
                    }
                }
            return {"meta": {"revision": 9}, "runtime_summary": {"boardroom_summary": {}}, "dashboard_summary": {}}
    class Departments:
        def list_for_workspace(self, workspace_ref): return []

    briefing = AionBoardroomWorkspaceProvider(Workspaces(), Containers(), Departments()).read_surface(
        "acme", "briefings", persona_id="persona_alex"
    )
    data = briefing["data"]
    assert [member["name"] for member in data["board_members"]] == ["AION", "OpenAI"]
    assert data["meeting_history"] == [{
        "id": "august", "title": "monthly review", "occurred_at": "2026-08-31T09:00:00Z",
        "summary": "Approved the September plan.", "status": "published",
    }]
    assert data["department_actions"] == [{
        "id": "sales-1", "title": "Review qualified pipeline", "department": "sales",
        "status": "delegated", "due_at": "2026-09-20",
    }]
    assert data["mobile_meeting_policy"]["first_meeting"] == "desktop_required"


def test_aion_boardroom_adapter_reuses_finance_conversation_and_fails_honestly_elsewhere():
    class Model:
        def model_dump(self, mode="json"):
            return {"id": "acme", "name": "Acme", "business_type": "boardroom", "owner": "owner"}
    class Workspaces:
        def list_ids(self): return ["acme"]
        def load(self, workspace_ref): return Model()
    class Containers:
        def load_optional_dict(self, workspace_ref, kind): return {}
    class Departments:
        def list_for_workspace(self, workspace_ref): return []
    class Finance:
        def answer(self, workspace_ref, text):
            return {"turn": {"content": "Finance answer", "provider": {"provider": "local"}, "sources": [{"id": "model"}], "reliability": "source_backed"}}
    adapter = AionBoardroomWorkspaceProvider(Workspaces(), Containers(), Departments(), Finance())
    finance = adapter.conversation_turn("acme", "finance", "How are we doing?", persona_id="persona_alex")
    assert finance["turn"]["content"] == "Finance answer"
    assert finance["external_writes_performed"] is False
    sales = adapter.conversation_turn("acme", "sales", "How are we doing?", persona_id="persona_alex")
    assert sales["reliability"] == "insufficient_evidence"
    assert "do not have enough" in sales["turn"]["content"]
