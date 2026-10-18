"""Authenticated loopback adapter for the Photon discovery journey."""

from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException

from backend.modules.aion_business.runtime.photon_discovery_qualification import (
    PhotonDiscoveryQualificationContext,
    execute_photon_discovery_qualification,
)


def create_photon_discovery_qualification_router(
    *, context: PhotonDiscoveryQualificationContext, access_token: str,
    endpoint: str,
) -> APIRouter:
    router = APIRouter(
        prefix="/api/aion/business/data/photon", tags=["photon-discovery-qualification"],
    )

    @router.post("/{candidate}/qualification/run")
    def run(
        candidate: str,
        x_tessaris_discovery_token: str = Header(default=""),
    ) -> dict:
        if not access_token or not hmac.compare_digest(
            access_token.encode("utf-8"), x_tessaris_discovery_token.encode("utf-8"),
        ):
            raise HTTPException(status_code=401, detail="photon_qualification_unauthorised")
        try:
            result = execute_photon_discovery_qualification(
                context, business_id=candidate, endpoint=endpoint,
            )
        except (ValueError, PermissionError, KeyError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return {"ok": True, "sandbox_only": True, **result}

    return router
