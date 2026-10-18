"""Public, owner-local API for the guarded adaptive inference runtime."""

from __future__ import annotations

from functools import lru_cache
import os
from pathlib import Path

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.modules.aion_inference import AdaptiveInferenceRuntime, LearnedAtomSheetStore


router = APIRouter(prefix="/api/aion/inference", tags=["aion-inference"])


class InferenceRouteRequest(BaseModel):
    text: str = Field(min_length=1, max_length=32_768)
    context: list[str] = Field(default_factory=list, max_length=100)
    context_max_bytes: int = Field(default=2048, ge=128, le=131_072)


class LearnedRouteRequest(BaseModel):
    intent: str = Field(min_length=3, max_length=64, pattern=r"^[A-Z][A-Z0-9_]+$")
    inputs: dict[str, str] = Field(min_length=2, max_length=3)


@lru_cache(maxsize=1)
def resolve_inference_storage_root() -> Path:
    configured = os.getenv("AION_INFERENCE_STORAGE_ROOT")
    if configured:
        return Path(configured).expanduser()
    mounted = sorted(Path("/Volumes").glob("*/AION-Inference"))
    if len(mounted) == 1:
        return mounted[0]
    return Path("data/aion_inference")


@lru_cache(maxsize=1)
def get_adaptive_runtime() -> AdaptiveInferenceRuntime:
    root = resolve_inference_storage_root()
    learning_root = root / "learning/falsification-runs/multifamily-v4-domain-bounds"
    return AdaptiveInferenceRuntime(
        replay_path=root / "runtime/replay.sqlite3",
        trace_path=root / "runtime/execution_receipts.jsonl",
        learned_store=LearnedAtomSheetStore(
            learning_root / "learning.sqlite3",
            learning_root / "promoted",
        ),
    )


@lru_cache(maxsize=1)
def get_learning_store() -> LearnedAtomSheetStore:
    root = resolve_inference_storage_root()
    learning_root = root / "learning/falsification-runs/multifamily-v4-domain-bounds"
    return LearnedAtomSheetStore(
        learning_root / "learning.sqlite3",
        learning_root / "promoted",
    )


@router.get("/capabilities")
def inference_capabilities() -> dict:
    return {
        "schema_version": "aion.adaptive_runtime.capabilities.v1",
        "verified_routes": [
            "CALCULATE_PROFIT",
            "CALCULATE_PERCENTAGE",
            "CALCULATE_RECTANGLE_AREA",
            "CALCULATE_RECTANGULAR_VOLUME",
            "CONVERT_LENGTH",
        ],
        "fallback_route": "full_model",
        "compound_actions_bypass_allowed": False,
        "ambiguous_inputs_bypass_allowed": False,
        "proof_receipts": True,
        "semantic_gateway_pipeline": True,
        "sqi_candidate_beams": "bounded_deterministic_parallel_candidates",
        "beam_event_bus_integration": True,
        "workflow_lookup": True,
        "workflow_execution_bound": False,
        "model_route_prediction": True,
        "expert_prefetch_execution": "experimental_sd_backed_runner",
        "verified_replay": True,
        "learned_atomsheet_promotion": True,
        "learned_route_cohort": "multifamily-v4-domain-bounds",
        "learned_verified_routes": [
            "CALCULATE_MARKED_UP_PRICE",
            "CALCULATE_DISCOUNTED_PRICE",
            "CALCULATE_PRICE_WITH_TAX",
            "CALCULATE_LABOUR_COST",
        ],
        "learning_ingestion_api": False,
        "learning_ingestion_reason": "verified outcomes enter through the trusted internal verifier boundary",
    }


@router.post("/route")
def route_inference(
    request: InferenceRouteRequest,
    runtime: AdaptiveInferenceRuntime = Depends(get_adaptive_runtime),
) -> dict:
    return runtime.route(
        request.text,
        context=request.context,
        context_max_bytes=request.context_max_bytes,
    ).to_dict()


@router.get("/learning/status")
def learning_status(store: LearnedAtomSheetStore = Depends(get_learning_store)) -> dict:
    return dict(store.status())


@router.post("/route-structured")
def route_learned_atomsheet(
    request: LearnedRouteRequest,
    store: LearnedAtomSheetStore = Depends(get_learning_store),
) -> dict:
    return store.execute(request.intent, request.inputs).to_dict()
