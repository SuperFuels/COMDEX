from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives import serialization
from fastapi import FastAPI

from backend.modules.aion_business.api.photon_control_plane_api import (
    create_photon_control_plane_router,
)
from backend.modules.aion_business.api.photon_pricing_admin_api import (
    create_photon_pricing_admin_router,
)
from backend.modules.aion_business.runtime.photon_control_plane_access import (
    VerifiedPhotonPrincipal,
)
from backend.modules.aion_business.runtime.photon_price_book_store import (
    PhotonPriceBookStore,
)
from backend.modules.aion_business.runtime.photon_pricing_admin import (
    PhotonPricingAdminAudit,
)
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.aion_business.runtime.photon_control_plane_access import (
    PhotonControlPlaneService,
)
from backend.modules.aion_business.runtime.photon_ledger_store import PhotonLedgerStore
from backend.modules.aion_business.runtime.photon_revolut_fulfillment import (
    PhotonRevolutFulfilment,
)
from backend.modules.aion_business.runtime.photon_wallet_snapshot import (
    PhotonWalletSnapshotAuthority,
)


class PhotonControlPlaneConfigurationError(ValueError):
    pass


class PhotonControlPlaneKeyProvider(Protocol):
    """Deployment-owned key custody; implementations may use an HSM or secret manager."""

    def access_authority_public_key(self) -> Ed25519PublicKey: ...

    def wallet_authority_private_key(self) -> Ed25519PrivateKey: ...


class PhotonPricingAdminProvider(Protocol):
    """Hosted-only custody and identity checks for founder pricing administration."""

    def pricing_admin_authority_public_key(self) -> Ed25519PublicKey: ...

    def price_book_signing_private_key(self) -> Ed25519PrivateKey: ...

    def pricing_admin_tenant_id(self) -> str: ...

    def verify_pricing_reauthentication(
        self,
        principal: VerifiedPhotonPrincipal,
        evidence_id: str,
        verified_at: str,
    ) -> bool: ...


@dataclass(frozen=True)
class PhotonControlPlaneConfiguration:
    state_root: Path
    application_roots: tuple[Path, ...] = ()
    business_vault_roots: tuple[Path, ...] = ()


def _overlaps(left: Path, right: Path) -> bool:
    try:
        left.relative_to(right)
        return True
    except ValueError:
        pass
    try:
        right.relative_to(left)
        return True
    except ValueError:
        return False


def _validated_root(configuration: PhotonControlPlaneConfiguration) -> Path:
    state_root = configuration.state_root.expanduser().resolve()
    if state_root == Path(state_root.anchor):
        raise PhotonControlPlaneConfigurationError("photon_state_root_too_broad")
    protected = tuple(configuration.application_roots) + tuple(configuration.business_vault_roots)
    for candidate in protected:
        if _overlaps(state_root, candidate.expanduser().resolve()):
            raise PhotonControlPlaneConfigurationError("photon_state_root_boundary_overlap")
    state_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        state_root.chmod(0o700)
    except OSError as exc:
        raise PhotonControlPlaneConfigurationError("photon_state_root_permissions_failed") from exc
    return state_root


def create_photon_control_plane_app(
    *,
    configuration: PhotonControlPlaneConfiguration,
    key_provider: PhotonControlPlaneKeyProvider,
    pricing_admin_provider: PhotonPricingAdminProvider | None = None,
    clock: Callable[[], str] | None = None,
) -> FastAPI:
    """Compose the content-free Photon service; live provider network calls remain separate."""
    state_root = _validated_root(configuration)
    access_public_key = key_provider.access_authority_public_key()
    wallet_private_key = key_provider.wallet_authority_private_key()
    if not isinstance(access_public_key, Ed25519PublicKey):
        raise PhotonControlPlaneConfigurationError("photon_access_public_key_invalid")
    if not isinstance(wallet_private_key, Ed25519PrivateKey):
        raise PhotonControlPlaneConfigurationError("photon_wallet_private_key_invalid")

    ledger = PhotonLedgerStore(state_root / "ledger.sqlite3")
    wallet_snapshots = PhotonWalletSnapshotAuthority(
        state_root / "wallet-snapshots.sqlite3",
        ledger=ledger,
        authority_private_key=wallet_private_key,
    )
    revolut = PhotonRevolutFulfilment(
        state_root / "revolut-fulfilment.sqlite3", ledger=ledger
    )
    service = PhotonControlPlaneService(
        state_root / "access-audit.sqlite3",
        ledger=ledger,
        wallet_snapshots=wallet_snapshots,
        revolut=revolut,
    )
    app = FastAPI(title="Tessaris Photon Control Plane", docs_url=None, redoc_url=None)
    app.include_router(
        create_photon_control_plane_router(
            service=service,
            authority_public_key=access_public_key,
            clock=clock,
        )
    )
    if pricing_admin_provider is not None:
        pricing_admin_public_key = (
            pricing_admin_provider.pricing_admin_authority_public_key()
        )
        price_book_private_key = (
            pricing_admin_provider.price_book_signing_private_key()
        )
        if not isinstance(pricing_admin_public_key, Ed25519PublicKey):
            raise PhotonControlPlaneConfigurationError(
                "photon_pricing_admin_public_key_invalid"
            )
        if not isinstance(price_book_private_key, Ed25519PrivateKey):
            raise PhotonControlPlaneConfigurationError(
                "photon_price_book_private_key_invalid"
            )

        def raw(public_key: Ed25519PublicKey) -> bytes:
            return public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )

        price_book_public_key = price_book_private_key.public_key()
        wallet_public_key = wallet_private_key.public_key()
        if raw(pricing_admin_public_key) in {
            raw(access_public_key),
            raw(wallet_public_key),
        }:
            raise PhotonControlPlaneConfigurationError(
                "photon_pricing_admin_key_must_be_separate"
            )
        if raw(price_book_public_key) in {
            raw(access_public_key),
            raw(pricing_admin_public_key),
            raw(wallet_public_key),
        }:
            raise PhotonControlPlaneConfigurationError(
                "photon_price_book_key_must_be_separate"
            )
        platform_tenant_id = str(
            pricing_admin_provider.pricing_admin_tenant_id() or ""
        ).strip()
        if not platform_tenant_id:
            raise PhotonControlPlaneConfigurationError(
                "photon_pricing_admin_tenant_invalid"
            )
        price_books = PhotonPriceBookStore(state_root / "price-books.sqlite3")
        pricing_audit = PhotonPricingAdminAudit(
            state_root / "pricing-admin-audit.sqlite3"
        )
        app.include_router(
            create_photon_pricing_admin_router(
                store=price_books,
                audit=pricing_audit,
                admin_authority_public_key=pricing_admin_public_key,
                price_book_signer=DeviceIdentity(price_book_private_key),
                platform_tenant_id=platform_tenant_id,
                reauthentication_verifier=(
                    pricing_admin_provider.verify_pricing_reauthentication
                ),
                clock=clock,
            )
        )
        app.state.photon_price_books = price_books
        app.state.photon_pricing_admin_audit = pricing_audit
    app.state.photon_control_plane = service
    app.state.photon_state_root = state_root
    return app
