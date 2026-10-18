from __future__ import annotations

from datetime import UTC, datetime
import csv
import io
from typing import Callable, Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from backend.modules.aion_business.runtime.photon_control_plane_access import (
    PhotonControlPlaneAccessError,
    PhotonControlPlaneService,
    VerifiedPhotonPrincipal,
    decode_control_plane_bearer,
    verify_control_plane_token,
)


class WalletSnapshotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=160)
    valid_until: str = Field(min_length=1, max_length=64)


class ActivityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=160)
    limit: int = Field(default=50, ge=1, le=200)


class BillingRecordsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=160)
    limit: int = Field(default=50, ge=1, le=200)
    export_format: Literal["json", "csv"] = "json"


class CommercialStatusRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=160)


class CheckoutIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str = Field(min_length=1, max_length=160)
    order_id: str = Field(min_length=1, max_length=160)
    external_reference: str = Field(min_length=1, max_length=160)
    product_id: str = Field(min_length=1, max_length=160)
    photons: int = Field(gt=0)
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    price_book_version: str = Field(min_length=1, max_length=160)


def create_photon_control_plane_router(
    *,
    service: PhotonControlPlaneService,
    authority_public_key: Ed25519PublicKey,
    clock: Callable[[], str] | None = None,
) -> APIRouter:
    """Build the hosted adapter with dependencies injected by the deployment composition root."""
    now = clock or (lambda: datetime.now(UTC).replace(microsecond=0).isoformat())
    security = HTTPBearer(auto_error=False)
    router = APIRouter(prefix="/api/control-plane/photon", tags=["photon-control-plane"])

    def principal(
        credentials: HTTPAuthorizationCredentials | None = Depends(security),
    ) -> VerifiedPhotonPrincipal:
        if credentials is None or credentials.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="photon_control_plane_bearer_required")
        try:
            return verify_control_plane_token(
                decode_control_plane_bearer(credentials.credentials),
                authority_public_key=authority_public_key,
                now=now(),
            )
        except PhotonControlPlaneAccessError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc

    @router.post("/wallet-snapshot")
    def wallet_snapshot(
        payload: WalletSnapshotRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> dict:
        issued_at = now()
        try:
            return service.wallet_snapshot(
                actor, request_id=payload.request_id, issued_at=issued_at,
                valid_until=payload.valid_until,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/activity")
    def activity(
        payload: ActivityRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> dict:
        try:
            rows = service.activity(
                actor, request_id=payload.request_id, limit=payload.limit,
                recorded_at=now(),
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"items": rows, "customer_content_included": False}

    @router.post("/billing-records", response_model=None)
    def billing_records(
        payload: BillingRecordsRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> dict | Response:
        try:
            rows = service.billing_records(
                actor, request_id=payload.request_id, limit=payload.limit,
                recorded_at=now(),
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if payload.export_format == "json":
            return {"items": rows, "customer_content_included": False}
        fields = [
            "receipt_id", "order_id", "external_reference", "product_id",
            "amount_minor", "refunded_minor", "disputed_minor", "currency",
            "photons_granted", "photons_reversed", "photons_dispute_reversed",
            "commercial_hold", "price_book_version", "provider_state",
            "paid_at", "ledger_transaction_id", "ledger_transaction_hash",
            "record_hash",
        ]
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return Response(
            content=stream.getvalue(), media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=photon-billing-records.csv"},
        )

    @router.post("/commercial-status")
    def commercial_status(
        payload: CommercialStatusRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> dict:
        try:
            return service.commercial_status(
                actor, request_id=payload.request_id, recorded_at=now()
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @router.post("/checkout-intents")
    def checkout_intent(
        payload: CheckoutIntentRequest,
        actor: VerifiedPhotonPrincipal = Depends(principal),
    ) -> dict:
        created_at = now()
        try:
            return service.record_checkout_intent(
                actor, request_id=payload.request_id, order_id=payload.order_id,
                external_reference=payload.external_reference,
                product_id=payload.product_id, photons=payload.photons,
                amount_minor=payload.amount_minor, currency=payload.currency,
                price_book_version=payload.price_book_version, created_at=created_at,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except (ValueError, KeyError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    return router
