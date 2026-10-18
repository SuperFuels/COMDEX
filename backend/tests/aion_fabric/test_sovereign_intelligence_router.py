from __future__ import annotations

import json

import pytest

from backend.modules.aion_business.contracts.intelligence import (
    DeliveryTarget,
    DisclosurePolicy,
    IntelligenceAdapterManifest,
    IntelligenceBudget,
    IntelligenceRequest,
    published_intelligence_schemas,
)
from backend.modules.aion_business.runtime.sovereign_brain_boundary import SovereignBrainBoundary
from backend.modules.aion_business.runtime.sovereign_intelligence_router import SovereignIntelligenceRouter


def manifest(adapter_id: str, *, kind="model", location="local", **values):
    return IntelligenceAdapterManifest(
        adapter_id=adapter_id,
        kind=kind,
        location=location,
        provider=values.pop("provider", "aion"),
        capabilities=values.pop("capabilities", ["analyse"]),
        estimated_quality=values.pop("estimated_quality", 0.8),
        estimated_cost=values.pop("estimated_cost", 0),
        estimated_latency_ms=values.pop("estimated_latency_ms", 10),
        estimated_energy_wh=values.pop("estimated_energy_wh", 0.1),
        **values,
    )


def request(request_id="request-1", **values):
    defaults = {
        "request_id": request_id,
        "brain_id": "brain-customer-1",
        "task_class": "business_analysis",
        "input": {"question": "private revenue question"},
        "required_capabilities": ["analyse"],
        "output_schema": {"required": ["answer"]},
        "budget": IntelligenceBudget(minimum_quality=0.7, maximum_cost=1, maximum_latency_ms=1000, maximum_energy_wh=2),
    }
    defaults.update(values)
    return IntelligenceRequest(**defaults)


def success(_request):
    return {"ok": True, "output": {"answer": "structured result"}, "quality_score": 0.9, "usage": {"cost": 0, "energy_wh": 0.1}}


def test_request_response_stream_and_adapter_schemas_are_publishable():
    schemas = published_intelligence_schemas()
    assert set(schemas) == {"request", "response", "stream_event", "adapter_manifest"}
    assert all(schema.get("type") == "object" for schema in schemas.values())


def test_provider_neutral_request_response_stream_and_hashed_receipt(tmp_path):
    brain = SovereignBrainBoundary.bootstrap(tmp_path / "brain", brain_id="brain-customer-1", owner_id="owner", public_key_fingerprint="sha256:test")
    router = SovereignIntelligenceRouter(adapters={"local": (manifest("local"), success)}, brain=brain)
    response = router.route(request(), candidates=["local"])

    assert response.ok is True
    assert response.output == {"answer": "structured result"}
    assert response.delivery["mode"] == "pilot_presentation"
    assert response.receipt["raw_prompt_retained"] is False
    assert response.receipt["raw_result_retained"] is False
    assert "private revenue question" not in json.dumps(response.receipt)
    assert brain.store("receipt")["records"][0]["receipt_id"] == response.receipt["receipt_id"]
    events = router.stream(response)
    assert [event.sequence for event in events] == list(range(len(events)))
    assert events[0].event == "accepted"
    assert events[-1].event == "completed"


def test_all_five_adapter_kinds_share_one_contract():
    kinds = ["capability", "model", "retrieval", "evidence", "agent_harness"]
    for kind in kinds:
        adapter_id = f"adapter-{kind}"
        router = SovereignIntelligenceRouter(adapters={adapter_id: (manifest(adapter_id, kind=kind), success)})
        response = router.route(request(f"request-{kind}"), candidates=[adapter_id])
        assert response.ok is True
        assert response.attempts[0].kind == kind


def test_external_route_requires_disclosure_destination_residency_and_fields():
    external = manifest("external", location="customer_cloud", provider="customer-aws", destination="customer-vpc", residency="eu")
    router = SovereignIntelligenceRouter(adapters={"external": (external, success)})
    blocked = router.route(request(), candidates=["external"])
    assert blocked.status == "limited"
    assert blocked.attempts[0].reason == "external_disclosure_forbidden"

    allowed_request = request(
        "request-2",
        disclosure=DisclosurePolicy(
            data_classification="confidential",
            allow_external=True,
            allowed_destinations=["customer-vpc"],
            allowed_residencies=["eu"],
            declared_fields=["aggregated_sales_metrics"],
        ),
    )
    assert router.route(allowed_request, candidates=["external"]).ok is True


def test_external_adapter_receives_only_declared_context_fields():
    seen = []

    def external_call(safe_request):
        seen.append(safe_request.input)
        return success(safe_request)

    external = manifest("external", location="customer_cloud", destination="customer-vpc", residency="eu")
    router = SovereignIntelligenceRouter(adapters={"external": (external, external_call)})
    safe = request(
        input={"aggregated_sales": {"total": 4}, "customer_names": ["Private Name"]},
        disclosure=DisclosurePolicy(
            allow_external=True,
            allowed_destinations=["customer-vpc"],
            allowed_residencies=["eu"],
            declared_fields=["aggregated_sales"],
        ),
    )
    assert router.route(safe, candidates=["external"]).ok is True
    assert seen == [{"aggregated_sales": {"total": 4}}]


def test_fallback_cannot_cross_cost_or_privacy_boundary():
    failing_local = manifest("local")
    expensive = manifest("premium", location="external_api", provider="premium", destination="premium-api", residency="us", estimated_cost=2)
    called = []

    def fail(_request):
        return {"ok": False, "error_code": "local_unavailable"}

    def premium(_request):
        called.append(True)
        return success(_request)

    router = SovereignIntelligenceRouter(adapters={"local": (failing_local, fail), "premium": (expensive, premium)})
    response = router.route(request(), candidates=["local", "premium"])
    assert response.ok is False
    assert response.attempts[-1].reason in {"cost_budget_exceeded", "external_disclosure_forbidden"}
    assert called == []


def test_health_circuit_and_idempotency_prevent_repeated_unsafe_calls(tmp_path):
    calls = []

    def fail(_request):
        calls.append(True)
        raise TimeoutError("offline")

    router = SovereignIntelligenceRouter(
        adapters={"unstable": (manifest("unstable"), fail)},
        health_path=tmp_path / "health.json",
        failure_threshold=1,
    )
    first = router.route(request(), candidates=["unstable"])
    replay = router.route(request(), candidates=["unstable"])
    second = router.route(request("request-2"), candidates=["unstable"])
    assert first.model_dump() == replay.model_dump()
    assert len(calls) == 1
    assert second.attempts[0].reason == "circuit_open"
    with pytest.raises(PermissionError, match="idempotency_key_reused"):
        router.route(request(input={"question": "different"}), candidates=["unstable"])


def test_governed_capability_delivery_requires_approval_and_authority():
    delivered = []

    def sink(req, output):
        delivered.append((req.delivery.capability_id, output))
        return {"ok": True, "mode": "governed_capability", "receipt": "capability-receipt"}

    router = SovereignIntelligenceRouter(adapters={"local": (manifest("local"), success)}, capability_sink=sink)
    without_approval = router.route(
        request("request-1", delivery=DeliveryTarget(mode="governed_capability", capability_id="calendar.propose")),
        candidates=["local"],
    )
    assert without_approval.ok is False
    assert delivered == []

    approved = router.route(
        request("request-2", delivery=DeliveryTarget(mode="governed_capability", capability_id="calendar.propose", approval_receipt="approval-hash")),
        candidates=["local"],
    )
    assert approved.ok is True
    assert delivered == [("calendar.propose", {"answer": "structured result"})]


def test_context_latency_energy_quality_and_structure_budgets_fail_closed():
    low_quality = manifest("low", estimated_quality=0.4)
    router = SovereignIntelligenceRouter(adapters={"low": (low_quality, success)})
    response = router.route(request(), candidates=["low"])
    assert response.attempts[0].reason == "quality_budget_not_met"

    tiny_context = request("request-context", budget=IntelligenceBudget(maximum_context_bytes=2, maximum_cost=1))
    assert router.route(tiny_context, candidates=["low"]).status == "failed"
