from __future__ import annotations

from datetime import UTC, datetime
from typing import Callable, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from backend.modules.aion_business.runtime.photon_billing_contracts import (
    PhotonPriceBook,
    PriceBookSigner,
    sign_price_book,
)
from backend.modules.aion_business.runtime.photon_control_plane_access import (
    PhotonControlPlaneAccessError,
    VerifiedPhotonPrincipal,
    decode_control_plane_bearer,
    verify_control_plane_token,
)
from backend.modules.aion_business.runtime.photon_price_book_store import (
    PhotonPriceBookStore,
)
from backend.modules.aion_business.runtime.photon_pricing_admin import (
    PhotonPricingAdminAudit,
)


class PriceBookFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = Field(min_length=1, max_length=128)
    currency: str = Field(min_length=3, max_length=3)
    minor_units_per_1000_photons: int = Field(ge=1, le=1_000_000_000)
    action_rates: dict[str, int] = Field(min_length=1, max_length=200)
    effective_at: str = Field(min_length=1, max_length=64)
    region: str = Field(default="global", min_length=1, max_length=128)
    cohort: str = Field(default="all", min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=500)

    def price_book(self) -> PhotonPriceBook:
        return PhotonPriceBook(
            version=self.version,
            currency=self.currency,
            minor_units_per_1000_photons=self.minor_units_per_1000_photons,
            action_rates=self.action_rates,
            effective_at=self.effective_at,
            region=self.region,
            cohort=self.cohort,
            reason=self.reason,
        )


class PricingPreviewRequest(PriceBookFields):
    request_id: str = Field(min_length=1, max_length=160)


class PricingPublishRequest(PriceBookFields):
    request_id: str = Field(min_length=1, max_length=160)
    approved_preview_hash: str = Field(min_length=64, max_length=64)
    confirmation: str = Field(min_length=1, max_length=80)
    reauthentication_evidence_id: str = Field(min_length=1, max_length=200)


class PricingHistoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=160)
    limit: int = Field(default=100, ge=1, le=500)


class PricingCurrentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=160)
    currency: str = Field(min_length=3, max_length=3)
    region: str = Field(default="global", min_length=1, max_length=128)
    cohort: str = Field(default="all", min_length=1, max_length=128)
    as_of: str = Field(min_length=1, max_length=64)


class PricingCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=500)
    confirmation: str = Field(min_length=1, max_length=80)
    reauthentication_evidence_id: str = Field(min_length=1, max_length=200)


def create_photon_pricing_admin_router(
    *,
    store: PhotonPriceBookStore,
    audit: PhotonPricingAdminAudit,
    admin_authority_public_key: Ed25519PublicKey,
    price_book_signer: PriceBookSigner,
    platform_tenant_id: str,
    reauthentication_verifier: Callable[
        [VerifiedPhotonPrincipal, str, str], bool
    ],
    clock: Callable[[], str] | None = None,
) -> APIRouter:
    """Founder-only hosted pricing control; never mount this in a customer Node."""

    now = clock or (lambda: datetime.now(UTC).replace(microsecond=0).isoformat())
    security = HTTPBearer(auto_error=False)
    router = APIRouter(
        prefix="/api/control-plane/photon/admin/pricing",
        tags=["photon-pricing-admin"],
    )

    def principal(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> VerifiedPhotonPrincipal:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="photon_pricing_admin_bearer_required")
        try:
            return verify_control_plane_token(
                decode_control_plane_bearer(credentials.credentials),
                authority_public_key=admin_authority_public_key,
                now=now(),
            )
        except PhotonControlPlaneAccessError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    def authorize(
        actor: VerifiedPhotonPrincipal,
        *,
        request_id: str,
        action: str,
        version: str,
        preview_hash: str = "",
        reauthentication_required: bool = False,
        reauthenticated: bool = False,
    ) -> None:
        try:
            audit.authorize(
                actor,
                platform_tenant_id=platform_tenant_id,
                request_id=request_id,
                action=action,
                price_book_version=version,
                preview_hash=preview_hash,
                recorded_at=now(),
                reauthentication_required=reauthentication_required,
                reauthenticated=reauthenticated,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except PhotonControlPlaneAccessError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/preview")
    def preview(
        payload: PricingPreviewRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> dict:
        try:
            book = payload.price_book()
            result = book.preview()
            authorize(
                actor,
                request_id=payload.request_id,
                action="pricing.preview",
                version=payload.version,
                preview_hash=result["price_book_hash"],
            )
            return result
        except HTTPException:
            raise
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/publish")
    def publish(
        payload: PricingPublishRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> dict:
        recorded_at = now()
        try:
            reauthenticated = bool(
                reauthentication_verifier(
                    actor, payload.reauthentication_evidence_id, recorded_at
                )
            )
            authorize(
                actor,
                request_id=payload.request_id,
                action="pricing.publish",
                version=payload.version,
                preview_hash=payload.approved_preview_hash,
                reauthentication_required=True,
                reauthenticated=reauthenticated,
            )
            book = payload.price_book()
            envelope = sign_price_book(book, price_book_signer)
            return store.publish(
                envelope,
                approved_preview_hash=payload.approved_preview_hash,
                actor_id=actor.subject_id,
                published_at=recorded_at,
                reauthenticated=True,
                confirmation=payload.confirmation,
            )
        except HTTPException:
            raise
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/history")
    def history(
        payload: PricingHistoryRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> Mapping[str, object]:
        authorize(
            actor,
            request_id=payload.request_id,
            action="pricing.history",
            version="history",
        )
        return {
            "items": store.list(limit=payload.limit),
            "cancellations": store.list_cancellations(limit=payload.limit),
            "customer_content_included": False,
        }

    @router.post("/current")
    def current(
        payload: PricingCurrentRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> Mapping[str, object]:
        authorize(
            actor,
            request_id=payload.request_id,
            action="pricing.current",
            version="current",
        )
        try:
            active = store.applicable(
                currency=payload.currency,
                region=payload.region,
                cohort=payload.cohort,
                as_of=payload.as_of,
            )
        except KeyError:
            active = None
        return {
            "active": active,
            "scheduled": store.scheduled(
                currency=payload.currency,
                region=payload.region,
                cohort=payload.cohort,
                as_of=payload.as_of,
            ),
            "customer_content_included": False,
        }

    @router.post("/cancel")
    def cancel(
        payload: PricingCancelRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> Mapping[str, object]:
        recorded_at = now()
        try:
            reauthenticated = bool(
                reauthentication_verifier(
                    actor, payload.reauthentication_evidence_id, recorded_at
                )
            )
            authorize(
                actor,
                request_id=payload.request_id,
                action="pricing.cancel",
                version=payload.version,
                reauthentication_required=True,
                reauthenticated=reauthenticated,
            )
            return store.cancel(
                payload.version,
                actor_id=actor.subject_id,
                cancelled_at=recorded_at,
                reason=payload.reason,
                reauthenticated=True,
                confirmation=payload.confirmation,
            )
        except HTTPException:
            raise
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
