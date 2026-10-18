from __future__ import annotations

import hmac
from typing import Literal

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from backend.modules.aion_business.runtime.business_data_discovery_runtime_controller import (
    BusinessDataDiscoveryRuntimeController,
    BusinessDataDiscoveryRuntimeControllerError,
)
from backend.modules.aion_business.runtime.business_data_external_surface_controller import (
    BusinessDataExternalSurfaceController,
    BusinessDataExternalSurfaceControllerError,
)


class DiscoveryStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    scenario: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


class DiscoveryStopRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scenario_completed: bool


ExternalSurface = Literal["provider_sandbox", "mobile_companion"]


class ExternalSurfaceStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    scenario: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    surface: ExternalSurface


class ExternalSurfaceEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surface: ExternalSurface
    operation: str = Field(min_length=1, max_length=128, pattern=r"^[a-z][a-z0-9_.-]*$")
    external_class: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_.-]*$")
    identifier_hmac_sha256: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    approved: bool


class ExternalSurfaceStopRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    surface: ExternalSurface
    scenario_completed: bool


def create_business_data_discovery_runtime_router(
    *, controller: BusinessDataDiscoveryRuntimeController, access_token: str
) -> APIRouter:
    if len(access_token) < 32:
        raise ValueError("discovery_runtime_access_token_too_short")
    router = APIRouter(
        prefix="/api/aion/business/discovery-runtime",
        tags=["business-data-discovery-runtime"],
    )

    def authorise(value: str | None) -> None:
        if value is None or not hmac.compare_digest(value, access_token):
            raise HTTPException(status_code=401, detail="discovery_runtime_unauthorised")

    @router.get("/status")
    def status(x_tessaris_discovery_token: str | None = Header(default=None)) -> dict:
        authorise(x_tessaris_discovery_token)
        return controller.status()

    @router.post("/start")
    def start(
        payload: DiscoveryStartRequest,
        x_tessaris_discovery_token: str | None = Header(default=None),
    ) -> dict:
        authorise(x_tessaris_discovery_token)
        try:
            return controller.start(session_id=payload.session_id, scenario=payload.scenario)
        except BusinessDataDiscoveryRuntimeControllerError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @router.post("/stop")
    def stop(
        payload: DiscoveryStopRequest,
        x_tessaris_discovery_token: str | None = Header(default=None),
    ) -> dict:
        authorise(x_tessaris_discovery_token)
        try:
            return controller.stop(scenario_completed=payload.scenario_completed)
        except BusinessDataDiscoveryRuntimeControllerError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    return router


def create_business_data_external_surface_router(
    *, controller: BusinessDataExternalSurfaceController, access_token: str
) -> APIRouter:
    if len(access_token) < 32:
        raise ValueError("discovery_runtime_access_token_too_short")
    router = APIRouter(
        prefix="/api/aion/business/discovery-runtime/external",
        tags=["business-data-discovery-runtime"],
    )

    def authorise(value: str | None) -> None:
        if value is None or not hmac.compare_digest(value, access_token):
            raise HTTPException(status_code=401, detail="discovery_runtime_unauthorised")

    def conflict(exc: BusinessDataExternalSurfaceControllerError) -> HTTPException:
        return HTTPException(status_code=409, detail=str(exc))

    @router.get("/status")
    def status(x_tessaris_discovery_token: str | None = Header(default=None)) -> dict:
        authorise(x_tessaris_discovery_token)
        return controller.status()

    @router.post("/start")
    def start(
        payload: ExternalSurfaceStartRequest,
        x_tessaris_discovery_token: str | None = Header(default=None),
    ) -> dict:
        authorise(x_tessaris_discovery_token)
        try:
            return controller.start(
                session_id=payload.session_id,
                scenario=payload.scenario,
                surface=payload.surface,
            )
        except BusinessDataExternalSurfaceControllerError as exc:
            raise conflict(exc) from exc

    @router.post("/event")
    def event(
        payload: ExternalSurfaceEventRequest,
        x_tessaris_discovery_token: str | None = Header(default=None),
    ) -> dict:
        authorise(x_tessaris_discovery_token)
        try:
            return controller.record(
                surface=payload.surface,
                operation=payload.operation,
                external_class=payload.external_class,
                identifier_hmac_sha256=payload.identifier_hmac_sha256,
                approved=payload.approved,
            )
        except BusinessDataExternalSurfaceControllerError as exc:
            raise conflict(exc) from exc

    @router.post("/stop")
    def stop(
        payload: ExternalSurfaceStopRequest,
        x_tessaris_discovery_token: str | None = Header(default=None),
    ) -> dict:
        authorise(x_tessaris_discovery_token)
        try:
            return controller.stop(
                surface=payload.surface,
                scenario_completed=payload.scenario_completed,
            )
        except BusinessDataExternalSurfaceControllerError as exc:
            raise conflict(exc) from exc

    return router
