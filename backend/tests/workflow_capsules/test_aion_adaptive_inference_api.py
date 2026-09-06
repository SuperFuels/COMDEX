from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from backend.api.aion_inference_router import (
    get_adaptive_runtime,
    get_learning_store,
    resolve_inference_storage_root,
    router,
)
from backend.modules.aion_inference import AdaptiveInferenceRuntime, LearnedAtomSheetStore


@pytest.fixture
def client(tmp_path):
    app = FastAPI()
    app.include_router(router)
    runtime = AdaptiveInferenceRuntime(
        replay_path=tmp_path / "replay.sqlite3",
        trace_path=tmp_path / "trace.jsonl",
    )
    app.dependency_overrides[get_adaptive_runtime] = lambda: runtime
    learning = LearnedAtomSheetStore(tmp_path / "learning.sqlite3", tmp_path / "promoted")
    app.dependency_overrides[get_learning_store] = lambda: learning
    with TestClient(app) as test_client:
        yield test_client


def test_capabilities_publish_strict_bypass_boundary(client):
    response = client.get("/api/aion/inference/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert "CALCULATE_PROFIT" in body["verified_routes"]
    assert "CONVERT_LENGTH" in body["verified_routes"]
    assert body["compound_actions_bypass_allowed"] is False
    assert body["ambiguous_inputs_bypass_allowed"] is False
    assert body["learned_atomsheet_promotion"] is True
    assert body["sqi_candidate_beams"] == "bounded_deterministic_parallel_candidates"
    assert body["beam_event_bus_integration"] is True
    assert body["workflow_lookup"] is True
    assert body["workflow_execution_bound"] is False
    assert body["model_route_prediction"] is True
    assert body["expert_prefetch_execution"] == "experimental_sd_backed_runner"
    assert body["learned_verified_routes"] == [
        "CALCULATE_MARKED_UP_PRICE", "CALCULATE_DISCOUNTED_PRICE",
        "CALCULATE_PRICE_WITH_TAX", "CALCULATE_LABOUR_COST",
    ]
    assert body["learning_ingestion_api"] is False


def test_api_executes_verified_route_then_replay(client):
    payload = {"text": "Calculate the area of 5 m by 4 m."}
    first = client.post("/api/aion/inference/route", json=payload)
    second = client.post("/api/aion/inference/route", json=payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["route"] == "verified_atomsheet"
    assert second.json()["route"] == "verified_replay"
    assert second.json()["structured_result"] == {"area": "20", "unit": "m²"}
    assert second.json()["model_call_required"] is False


def test_api_returns_model_fallback_for_compound_action(client):
    response = client.post(
        "/api/aion/inference/route",
        json={"text": "Calculate the area of 5 m by 4 m and then book the job."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["route"] == "full_model"
    assert body["model_call_required"] is True
    assert body["answer"] is None


def test_api_rejects_empty_or_oversized_context_budget(client):
    assert client.post("/api/aion/inference/route", json={"text": ""}).status_code == 422
    assert client.post(
        "/api/aion/inference/route",
        json={"text": "hello", "context_max_bytes": 10},
    ).status_code == 422


def test_explicit_storage_root_has_priority(monkeypatch, tmp_path):
    monkeypatch.setenv("AION_INFERENCE_STORAGE_ROOT", str(tmp_path))
    resolve_inference_storage_root.cache_clear()
    assert resolve_inference_storage_root() == tmp_path
    resolve_inference_storage_root.cache_clear()


def test_learning_status_and_unknown_structured_route_fail_closed(client):
    status = client.get("/api/aion/inference/learning/status")
    assert status.status_code == 200
    assert status.json()["promoted_atomsheets"] == 0
    response = client.post(
        "/api/aion/inference/route-structured",
        json={"intent": "CALCULATE_NEW_THING", "inputs": {"a": "1", "b": "2"}},
    )
    assert response.status_code == 200
    assert response.json()["route"] == "full_model"
    assert response.json()["model_call_required"] is True
