"""HTTP boundary for Tessaris-owned creative planning and experiment governance."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, File, UploadFile
from pydantic import BaseModel, Field

from backend.modules.aion_business.runtime.marketing_creative_engine import MarketingCreativeEngine
from backend.modules.aion_business.runtime.creative_render_service import CreativeRenderService
from backend.modules.aion_business.runtime.creative_timeline_service import CreativeTimelineService
from backend.modules.aion_business.runtime.creative_publication_service import CreativePublicationService


router = APIRouter(prefix="/api/aion/marketing/creative", tags=["aion-marketing-creative"])
engine = MarketingCreativeEngine()
renders = CreativeRenderService()
timelines = CreativeTimelineService()
publications = CreativePublicationService()


class CreativePlanRequest(BaseModel):
    brief: str
    objective: str = "Generate qualified interest"
    audience: str = "Priority customer"
    offer: str = "Approved business offer"
    tone: str = "Clear, credible and human"
    call_to_action: str = "Take the next approved step"
    platforms: list[str] = Field(default_factory=lambda: ["instagram_feed", "facebook_feed", "tiktok"])
    formats: list[str] = Field(default_factory=lambda: ["image", "video", "clip"])
    variant_count: int = Field(default=3, ge=2, le=4)
    primary_metric: str = "qualified_action_rate"


class ExperimentEvaluationRequest(BaseModel):
    variants: list[dict[str, Any]]
    minimum_sample_per_variant: int = Field(default=100, ge=1)
    minimum_relative_improvement: float = Field(default=0.15, ge=0)


class RenderPrepareRequest(BaseModel):
    provider: str = "gemini"
    model: str | None = None
    prompt: str
    ratio: str = "9:16"
    duration_seconds: int = Field(default=8, ge=1, le=30)
    resolution: str = "720p"
    reference_asset_path: str | None = None
    reference_asset_paths: list[str] = Field(default_factory=list)
    rendition_id: str | None = None
    campaign_plan_hash: str | None = None
    created_by_person_id: str = "desktop_user"


class RenderApprovalRequest(BaseModel):
    expected_approval_hash: str
    approved_by_person_id: str
    maximum_cost_eur: float = Field(gt=0)
    paid_generation_authorized: bool


class TimelineClip(BaseModel):
    source_path: str
    start_seconds: float = Field(default=0, ge=0)
    end_seconds: float = Field(gt=0)
    label: str | None = None
    motion_preset: str = "none"
    motion_intensity: float = Field(default=0.5, ge=0, le=1)


class TimelineRequest(BaseModel):
    name: str = "Creative timeline"
    platform: str = "instagram_reels"
    clips: list[TimelineClip]
    subtitle_path: str | None = None
    subtitles: list[dict[str, Any]] = Field(default_factory=list)
    transition: dict[str, Any] = Field(default_factory=lambda: {"type": "cut", "duration_seconds": 0})
    text_overlays: list[dict[str, Any]] = Field(default_factory=list)
    logo_path: str | None = None
    music_path: str | None = None
    music_volume: float = Field(default=0.20, ge=0, le=1)
    voiceover_path: str | None = None
    voiceover_volume: float = Field(default=1.0, ge=0, le=2)
    voiceover_start_seconds: float = Field(default=0, ge=0)
    duck_music_under_voice: bool = True
    audio_mastering: str = "social"
    brand_preset: str = "clean"
    created_by_person_id: str = "desktop_user"


class PublicationPrepareRequest(BaseModel):
    asset_path: str
    channel: str = "instagram"
    mode: str = "organic"
    caption: str
    call_to_action: str = "Learn more"
    scheduled_for: str | None = None
    daily_budget_eur: float = Field(default=0, ge=0)
    campaign_name: str = "Tessaris campaign"
    created_by_person_id: str = "desktop_user"


class PublicationApprovalRequest(BaseModel):
    expected_approval_hash: str
    approved_by_person_id: str
    maximum_total_spend_eur: float = Field(default=0, ge=0)
    external_publish_authorized: bool


class PublicationOutcomeRequest(BaseModel):
    source: str = "manual_verified"
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    qualified_actions: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    spend_eur: float = Field(default=0, ge=0)
    revenue_eur: float = Field(default=0, ge=0)
    complaints: int = Field(default=0, ge=0)
    false_or_unsafe_claims: int = Field(default=0, ge=0)


def _call(method, payload: dict[str, Any]):
    try:
        return method(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/capabilities")
def capabilities():
    return {"ok": True, **engine.capabilities()}


@router.get("/platforms")
def platforms():
    return {"ok": True, "platforms": engine.platforms()}


@router.post("/plan")
def build_plan(request: CreativePlanRequest):
    return {"ok": True, "plan": _call(engine.build_plan, request.model_dump())}


@router.post("/experiment/evaluate")
def evaluate_experiment(request: ExperimentEvaluationRequest):
    return {"ok": True, "evaluation": _call(engine.evaluate_experiment, request.model_dump())}


def _service_call(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{workspace_id}/renders")
def list_renders(workspace_id: str):
    return {"ok": True, "jobs": _service_call(renders.list, workspace_id)}


@router.post("/{workspace_id}/renders")
def prepare_render(workspace_id: str, request: RenderPrepareRequest):
    return {"ok": True, "job": _service_call(renders.prepare, workspace_id, request.model_dump())}


@router.get("/{workspace_id}/renders/{job_id}")
def get_render(workspace_id: str, job_id: str):
    return {"ok": True, "job": _service_call(renders.get, workspace_id, job_id)}


@router.post("/{workspace_id}/renders/{job_id}/approve")
def approve_render(workspace_id: str, job_id: str, request: RenderApprovalRequest):
    return {"ok": True, "job": _service_call(renders.approve, workspace_id, job_id, request.model_dump())}


@router.post("/{workspace_id}/renders/{job_id}/submit")
def submit_render(workspace_id: str, job_id: str):
    return {"ok": True, "job": _service_call(renders.submit, workspace_id, job_id)}


@router.post("/{workspace_id}/renders/{job_id}/poll")
def poll_render(workspace_id: str, job_id: str):
    return {"ok": True, "job": _service_call(renders.poll, workspace_id, job_id)}


@router.post("/{workspace_id}/timelines")
def create_timeline(workspace_id: str, request: TimelineRequest):
    return {"ok": True, "timeline": _service_call(timelines.create, workspace_id, request.model_dump())}


@router.get("/{workspace_id}/timelines/{timeline_id}")
def get_timeline(workspace_id: str, timeline_id: str):
    return {"ok": True, "timeline": _service_call(timelines.get, workspace_id, timeline_id)}


@router.post("/{workspace_id}/timelines/{timeline_id}/export")
def export_timeline(workspace_id: str, timeline_id: str):
    return {"ok": True, "timeline": _service_call(timelines.export, workspace_id, timeline_id)}


@router.post("/{workspace_id}/voiceovers")
async def save_voiceover(workspace_id: str, file: UploadFile = File(...)):
    content = await file.read()
    return {"ok": True, "voiceover": _service_call(timelines.save_voiceover, workspace_id, file.filename or "voiceover.webm", content)}


@router.post("/{workspace_id}/publications")
def prepare_publication(workspace_id: str, request: PublicationPrepareRequest):
    return {"ok": True, "publication": _service_call(publications.prepare, workspace_id, request.model_dump())}


@router.get("/{workspace_id}/publications/{package_id}")
def get_publication(workspace_id: str, package_id: str):
    return {"ok": True, "publication": _service_call(publications.get, workspace_id, package_id)}


@router.post("/{workspace_id}/publications/{package_id}/approve")
def approve_publication(workspace_id: str, package_id: str, request: PublicationApprovalRequest):
    return {"ok": True, "publication": _service_call(publications.approve, workspace_id, package_id, request.model_dump())}


@router.post("/{workspace_id}/publications/{package_id}/outcomes")
def record_publication_outcome(workspace_id: str, package_id: str, request: PublicationOutcomeRequest):
    return {"ok": True, "publication": _service_call(publications.record_outcome, workspace_id, package_id, request.model_dump())}
