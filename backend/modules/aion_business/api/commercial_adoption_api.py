from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.commercial_adoption_service import CommercialAdoptionService


router = APIRouter(prefix="/api/aion/business/commercial", tags=["aion-commercial-adoption"])


def service() -> CommercialAdoptionService:
    root = Path(os.environ.get("TESSARIS_DATA_ROOT") or Path.cwd() / "data")
    return CommercialAdoptionService(root / "aion_business" / "commercial_adoption")


class TrialStart(BaseModel):
    tenant_id: str
    department: str
    actor_id: str
    days: int = Field(default=30, ge=1, le=90)
    action_limit: int = Field(default=100, ge=1, le=1_000_000)
    managed_cost_limit: float = Field(default=0, ge=0, le=1_000_000)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    offer_version: str
    consent_ref: str
    auto_renew: bool = False
    renewal_plan: str = ""
    renewal_price: float | None = None


class TrialCancel(BaseModel):
    tenant_id: str
    actor_id: str
    cancellation_ref: str


class CapacityChange(BaseModel):
    tenant_id: str
    department: str
    actor_id: str
    monthly_action_limit: int = Field(ge=0, le=1_000_000)
    overage_allowed: bool = False
    overage_approval_ref: str = ""


@router.get("/{tenant_id}")
def dashboard(tenant_id: str):
    return service().customer_dashboard(tenant_id=tenant_id)


@router.post("/trials/start")
def start_trial(request: TrialStart):
    now = datetime.now(UTC)
    try:
        return service().start_trial(
            trial_id=f"trial.{uuid4().hex}", tenant_id=request.tenant_id,
            department=request.department, actor_id=request.actor_id,
            starts_at=now.isoformat(), ends_at=(now + timedelta(days=request.days)).isoformat(),
            action_limit=request.action_limit, managed_cost_limit=request.managed_cost_limit,
            currency=request.currency, offer_version=request.offer_version,
            consent_ref=request.consent_ref, auto_renew=request.auto_renew,
            renewal_plan=request.renewal_plan, renewal_price=request.renewal_price,
        )
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/trials/{trial_id}/cancel")
def cancel_trial(trial_id: str, request: TrialCancel):
    try:
        current = service().trial_status(trial_id=trial_id)
        if current["tenant_id"] != request.tenant_id:
            raise PermissionError("trial_tenant_mismatch")
        return service().cancel(trial_id=trial_id, actor_id=request.actor_id,
                                cancellation_ref=request.cancellation_ref)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/capacity")
def change_capacity(request: CapacityChange):
    try:
        return service().set_capacity_control(**request.model_dump())
    except (ValueError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
