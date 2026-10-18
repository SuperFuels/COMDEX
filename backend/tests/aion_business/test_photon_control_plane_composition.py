from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from backend.modules.aion_business.api.photon_control_plane_composition import (
    PhotonControlPlaneConfiguration,
    PhotonControlPlaneConfigurationError,
    create_photon_control_plane_app,
)
from backend.modules.aion_business.runtime.photon_control_plane_access import (
    encode_control_plane_bearer,
    issue_control_plane_token,
)


NOW = "2026-10-17T20:30:00+00:00"
EXPIRES = "2026-10-17T21:30:00+00:00"


@dataclass
class Keys:
    access: Ed25519PrivateKey
    wallet: Ed25519PrivateKey

    def access_authority_public_key(self):
        return self.access.public_key()

    def wallet_authority_private_key(self):
        return self.wallet


def _keys() -> Keys:
    return Keys(Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate())


@dataclass
class PricingAdmin:
    admin: Ed25519PrivateKey
    price_book: Ed25519PrivateKey

    def pricing_admin_authority_public_key(self):
        return self.admin.public_key()

    def price_book_signing_private_key(self):
        return self.price_book

    def pricing_admin_tenant_id(self):
        return "tessaris-platform"

    def verify_pricing_reauthentication(self, principal, evidence_id, verified_at):
        return principal.subject_id == "founder-1" and evidence_id == "webauthn-ok"


def test_composition_creates_separate_durable_stores_and_serves_authenticated_api(
    tmp_path: Path,
) -> None:
    keys = _keys()
    state_root = tmp_path / "hosted-photon"
    app = create_photon_control_plane_app(
        configuration=PhotonControlPlaneConfiguration(
            state_root=state_root,
            application_roots=(tmp_path / "application",),
            business_vault_roots=(tmp_path / "customer-vault",),
        ),
        key_provider=keys,
        clock=lambda: NOW,
    )
    assert {item.name for item in state_root.iterdir()} >= {
        "ledger.sqlite3", "wallet-snapshots.sqlite3",
        "revolut-fulfilment.sqlite3", "access-audit.sqlite3",
    }
    token = issue_control_plane_token(
        authority_private_key=keys.access,
        token_id="token-1", subject_id="operator-1", tenant_id="tenant-1",
        scopes=["activity.read"], issued_at=NOW, expires_at=EXPIRES,
    )
    response = TestClient(app).post(
        "/api/control-plane/photon/activity",
        headers={"Authorization": f"Bearer {encode_control_plane_bearer(token)}"},
        json={"request_id": "activity-1", "limit": 10},
    )
    assert response.status_code == 200
    assert response.json() == {"items": [], "customer_content_included": False}
    assert TestClient(app).post(
        "/api/control-plane/photon/admin/pricing/history",
        json={"request_id": "not-mounted"},
    ).status_code == 404


def test_composition_mounts_pricing_admin_only_with_separate_hosted_authority(
    tmp_path: Path,
) -> None:
    keys = _keys()
    pricing = PricingAdmin(
        Ed25519PrivateKey.generate(), Ed25519PrivateKey.generate()
    )
    state_root = tmp_path / "hosted-photon"
    app = create_photon_control_plane_app(
        configuration=PhotonControlPlaneConfiguration(state_root=state_root),
        key_provider=keys,
        pricing_admin_provider=pricing,
        clock=lambda: NOW,
    )
    assert {item.name for item in state_root.iterdir()} >= {
        "price-books.sqlite3", "pricing-admin-audit.sqlite3"
    }
    token = issue_control_plane_token(
        authority_private_key=pricing.admin,
        token_id="pricing-token-1", subject_id="founder-1",
        tenant_id="tessaris-platform", scopes=["pricing.manage"],
        issued_at=NOW, expires_at=EXPIRES,
    )
    response = TestClient(app).post(
        "/api/control-plane/photon/admin/pricing/preview",
        headers={"Authorization": f"Bearer {encode_control_plane_bearer(token)}"},
        json={
            "request_id": "pricing-preview-1",
            "version": "gb-v1",
            "currency": "GBP",
            "minor_units_per_1000_photons": 1,
            "action_rates": {"quote.prepared": 25},
            "effective_at": "2026-11-01T00:00:00+00:00",
            "region": "GB",
            "cohort": "all",
            "reason": "Founder market calibration",
        },
    )
    assert response.status_code == 200
    assert response.json()["minor_units_per_1000_photons"] == 1


def test_composition_rejects_reused_customer_or_admin_pricing_keys(tmp_path: Path) -> None:
    keys = _keys()
    reused_admin = PricingAdmin(keys.access, Ed25519PrivateKey.generate())
    with pytest.raises(
        PhotonControlPlaneConfigurationError,
        match="photon_pricing_admin_key_must_be_separate",
    ):
        create_photon_control_plane_app(
            configuration=PhotonControlPlaneConfiguration(state_root=tmp_path / "state-1"),
            key_provider=keys,
            pricing_admin_provider=reused_admin,
        )

    reused_signer = PricingAdmin(Ed25519PrivateKey.generate(), keys.wallet)
    with pytest.raises(
        PhotonControlPlaneConfigurationError,
        match="photon_price_book_key_must_be_separate",
    ):
        create_photon_control_plane_app(
            configuration=PhotonControlPlaneConfiguration(state_root=tmp_path / "state-2"),
            key_provider=keys,
            pricing_admin_provider=reused_signer,
        )


@pytest.mark.parametrize("protected_kind", ["application", "vault"])
def test_composition_rejects_state_overlap_with_protected_roots(
    tmp_path: Path, protected_kind: str,
) -> None:
    protected = tmp_path / protected_kind
    configuration = PhotonControlPlaneConfiguration(
        state_root=protected / "photon",
        application_roots=(protected,) if protected_kind == "application" else (),
        business_vault_roots=(protected,) if protected_kind == "vault" else (),
    )
    with pytest.raises(
        PhotonControlPlaneConfigurationError,
        match="photon_state_root_boundary_overlap",
    ):
        create_photon_control_plane_app(configuration=configuration, key_provider=_keys())


def test_composition_rejects_invalid_key_provider(tmp_path: Path) -> None:
    class InvalidKeys:
        def access_authority_public_key(self):
            return object()

        def wallet_authority_private_key(self):
            return object()

    with pytest.raises(
        PhotonControlPlaneConfigurationError,
        match="photon_access_public_key_invalid",
    ):
        create_photon_control_plane_app(
            configuration=PhotonControlPlaneConfiguration(state_root=tmp_path / "state"),
            key_provider=InvalidKeys(),
        )
