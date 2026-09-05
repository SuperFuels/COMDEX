from __future__ import annotations

from datetime import datetime, timedelta, timezone

from backend.modules.aion_fabric.canonical import canonical_bytes, canonical_hash
from backend.modules.aion_fabric.identity import IdentityStore
from backend.modules.aion_fabric.private_identity import ProductionPrivateIdentity
from backend.modules.pilot_unified.shared_surface import SharedSurfaceManifestAuthority
from backend.modules.pilot_unified.contracts import Membership
from backend.modules.pilot_unified.workspace_gateway import ProviderIndependentWorkspaceGateway


class SurfaceWorkspaceProvider:
    provider_id = "surface-test"

    def list_workspaces(self):
        return [
            {"id": "client", "name": "Client Workspace", "business_type": "workspace", "owner": "client"},
            {"id": "company", "name": "Acme Boardroom", "business_type": "boardroom", "owner": "acme"},
        ]

    def describe_workspace(self, workspace_ref):
        return {
            "id": workspace_ref, "departments": [], "agents": [], "dashboards": [],
            "files": [], "packages": [], "decisions": [],
            "permitted_actions": ["workspace.read", "workspace.dashboards.read"],
        }

    def read_surface(self, workspace_ref, surface, *, persona_id):
        return {"revision": 1, "data": {}}


def _active_surface(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    owner = identities.onboard(display_name="Owner")
    phone = IdentityStore(tmp_path / "phone").load_or_create()
    challenge = identities.begin_phone_enrollment(persona_id=owner["persona_id"], device_label="Owner phone", public_key=phone.public_key_b64, biometric_capable=True)
    signed = {key: challenge[key] for key in ("challenge_id", "persona_id", "device_id", "device_label", "biometric_capable", "nonce", "expires_at")}
    device = identities.complete_phone_enrollment(challenge["challenge_id"], signature=phone.sign(canonical_bytes(signed)))
    payload = {"purpose": "activate_shared_screen", "persona_id": owner["persona_id"], "device_id": device["device_id"], "nonce": "surface-acquire"}
    identities.activate_shared_screen(persona_id=owner["persona_id"], device_id=device["device_id"], nonce="surface-acquire", signature=phone.sign(canonical_bytes(payload)))
    mother = IdentityStore(tmp_path / "mother").load_or_create()
    return identities, owner, mother


def test_signed_surface_manifest_changes_with_active_identity_and_rejects_tampering(tmp_path):
    identities = ProductionPrivateIdentity(tmp_path)
    mother = IdentityStore(tmp_path / "mother").load_or_create()
    authority = SharedSurfaceManifestAuthority(tmp_path, issuer=mother, identities=identities)
    public = authority.issue_home_manifest(surface_id="surface.tv.lounge")
    assert SharedSurfaceManifestAuthority.verify(public)
    assert public["persona_id"] == "public"
    assert all(item["privacy"] in {"public", "locked"} for item in public["tiles"])
    assert {item["tile_id"] for item in public["tiles"] if item["privacy"] == "locked"} == {
        "personal", "household", "workspace", "boardroom",
    }
    assert not any(item["tile_id"] == "devices" for item in public["tiles"])

    identities, owner, mother = _active_surface(tmp_path / "active")
    authority = SharedSurfaceManifestAuthority(tmp_path / "active", issuer=mother, identities=identities)
    private = authority.issue_home_manifest(surface_id="surface.tv.lounge")
    assert private["persona_id"] == owner["persona_id"]
    assert any(item["tile_id"] == "tasks" and item["authority_domain"] == "personal" for item in private["tiles"])
    assert any(item["tile_id"] == "devices" and item["authority_domain"] == "household" for item in private["tiles"])
    assert not any(item["authority_domain"] == "boardroom" for item in private["tiles"])
    altered = {**private, "display_name": "Other"}
    assert SharedSurfaceManifestAuthority.verify(altered) is False


def test_workspace_and_boardroom_tiles_come_only_from_active_signed_memberships(tmp_path):
    identities, owner, mother = _active_surface(tmp_path)
    gateway = ProviderIndependentWorkspaceGateway(issuer_id="mother_home", issuer_identity=mother)
    gateway.register_provider(SurfaceWorkspaceProvider())
    bindings = gateway.discover("surface-test")
    now = datetime.now(timezone.utc)
    for index, binding in enumerate(bindings):
        gateway.grant_membership(Membership(
            membership_id=f"membership_{index}", persona_id=owner["persona_id"],
            space_id=binding.space.space_id, role_id="reviewer",
            scopes=("workspace.read",), status="active", issued_at=now.isoformat(),
            expires_at=(now + timedelta(hours=1)).isoformat(),
        ))
    authority = SharedSurfaceManifestAuthority(
        tmp_path, issuer=mother, identities=identities, workspace_gateway=gateway,
    )
    manifest = authority.issue_home_manifest(surface_id="surface.tv.lounge")
    business_tiles = [item for item in manifest["tiles"] if item["authority_domain"] in {"workspace", "boardroom"}]
    assert {(item["authority_domain"], item["label"]) for item in business_tiles} == {
        ("workspace", "Client Workspace"), ("boardroom", "Acme Boardroom"),
    }
    assert all(item["capabilities"] == ["workspace.read"] for item in business_tiles)
    assert all(item["role"] == "reviewer" for item in business_tiles)

    outsider = identities.onboard(display_name="Outsider")
    identities.release_shared_screen(persona_id=owner["persona_id"])
    outsider_phone = IdentityStore(tmp_path / "outsider-phone").load_or_create()
    challenge = identities.begin_phone_enrollment(
        persona_id=outsider["persona_id"], device_label="Outsider phone",
        public_key=outsider_phone.public_key_b64, biometric_capable=True,
    )
    signed = {key: challenge[key] for key in ("challenge_id", "persona_id", "device_id", "device_label", "biometric_capable", "nonce", "expires_at")}
    device = identities.complete_phone_enrollment(challenge["challenge_id"], signature=outsider_phone.sign(canonical_bytes(signed)))
    payload = {"purpose": "activate_shared_screen", "persona_id": outsider["persona_id"], "device_id": device["device_id"], "nonce": "outsider-acquire"}
    identities.activate_shared_screen(
        persona_id=outsider["persona_id"], device_id=device["device_id"], nonce="outsider-acquire",
        signature=outsider_phone.sign(canonical_bytes(payload)),
    )
    outsider_manifest = authority.issue_home_manifest(surface_id="surface.tv.lounge")
    assert not any(item["authority_domain"] in {"workspace", "boardroom"} for item in outsider_manifest["tiles"])


def test_deliberate_presentation_retains_only_hash_and_logout_purges_surface_cache(tmp_path):
    identities, owner, mother = _active_surface(tmp_path)
    authority = SharedSurfaceManifestAuthority(tmp_path, issuer=mother, identities=identities)
    manifest = authority.issue_home_manifest(surface_id="surface.tv.lounge")
    presented = authority.record_deliberate_presentation(
        manifest=manifest, content_kind="document", content_id="file/proposal",
        content_hash=canonical_hash("proposal bytes"),
    )
    assert presented["cached_content_retained"] is False
    assert "proposal bytes" not in str(authority._read())
    identities.release_shared_screen(persona_id=owner["persona_id"], reason="test_logout")
    purged = authority.purge_locked(surface_id="surface.tv.lounge")
    assert purged["purged"] is True and purged["removed_records"] == 1
    assert authority._read()["presentation_cache"] == []


def test_full_screen_presentation_is_bounded_volatile_and_identity_bound(tmp_path):
    identities, owner, mother = _active_surface(tmp_path)
    authority = SharedSurfaceManifestAuthority(tmp_path, issuer=mother, identities=identities)
    manifest = authority.issue_home_manifest(surface_id="surface.tv.lounge")
    receipt = authority.present(
        manifest=manifest,
        content_kind="briefing",
        content_id="briefing/today",
        title="Today",
        content={"summary": "Three priorities", "api_token": "must-not-reach-tv"},
        authority_domain="personal",
    )
    assert receipt["cached_content_retained"] is False
    active = authority.active_presentation(surface_id="surface.tv.lounge")
    assert active["content"] == {"summary": "Three priorities"}
    assert active["volatile_only"] is True
    assert "Three priorities" not in authority.path.read_text()
    assert authority.dismiss_presentation(
        surface_id="surface.tv.lounge", persona_id=owner["persona_id"],
    )["dismissed"] is True
    assert authority.active_presentation(surface_id="surface.tv.lounge") is None

    authority.present(
        manifest=manifest, content_kind="document", content_id="file/proposal",
        title="Proposal", content={"body": "Private draft"}, authority_domain="personal",
    )
    identities.release_shared_screen(persona_id=owner["persona_id"], reason="left_room")
    assert authority.active_presentation(surface_id="surface.tv.lounge") is None
    assert "Private draft" not in authority.path.read_text()
