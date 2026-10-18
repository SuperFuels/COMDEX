from __future__ import annotations

import json
import os
from pathlib import Path
import time
from typing import Any, Callable, Dict, Iterable

from backend.modules.aion_business.contracts.intelligence import (
    IntelligenceAdapterManifest,
    IntelligenceAttempt,
    IntelligenceRequest,
    IntelligenceResponse,
    IntelligenceStreamEvent,
)
from backend.modules.aion_business.contracts.sovereign_brain import build_intelligence_route_receipt
from backend.modules.aion_business.runtime.sovereign_brain_boundary import SovereignBrainBoundary
from backend.modules.aion_fabric.canonical import canonical_hash, utc_now_iso


AdapterCallable = Callable[[IntelligenceRequest], Dict[str, Any]]
DeliveryCallable = Callable[[IntelligenceRequest, Dict[str, Any]], Dict[str, Any]]
CLASSIFICATION_RANK = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}


class SovereignIntelligenceRouter:
    """Provider-neutral AION route authority with bounded failover and receipts."""

    def __init__(
        self,
        *,
        adapters: Dict[str, tuple[IntelligenceAdapterManifest, AdapterCallable]],
        brain: SovereignBrainBoundary | None = None,
        health_path: str | Path | None = None,
        presentation_sink: DeliveryCallable | None = None,
        capability_sink: DeliveryCallable | None = None,
        failure_threshold: int = 2,
        circuit_seconds: int = 60,
    ) -> None:
        self.adapters = dict(adapters)
        self.brain = brain
        self.health_path = Path(health_path) if health_path else None
        self.presentation_sink = presentation_sink
        self.capability_sink = capability_sink
        self.failure_threshold = max(1, int(failure_threshold))
        self.circuit_seconds = max(1, int(circuit_seconds))
        self._responses: Dict[str, tuple[str, IntelligenceResponse]] = {}
        self._health = self._read_health()

    def route(self, request: IntelligenceRequest, *, candidates: Iterable[str]) -> IntelligenceResponse:
        request_hash = request.content_hash()
        cached = self._responses.get(request.request_id)
        if cached:
            if cached[0] != request_hash:
                raise PermissionError("idempotency_key_reused_for_different_request")
            return cached[1].model_copy(deep=True)

        context_bytes = len(json.dumps(request.input, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        if context_bytes > request.budget.maximum_context_bytes:
            return self._finish(request, request_hash, [], {}, "", "failed", "context_budget_exceeded")

        attempts: list[IntelligenceAttempt] = []
        spent_cost = 0.0
        spent_energy = 0.0
        started = time.monotonic()
        selected_output: Dict[str, Any] = {}
        selected_adapter = ""

        for adapter_id in list(candidates)[: request.budget.maximum_attempts]:
            entry = self.adapters.get(adapter_id)
            if not entry:
                attempts.append(IntelligenceAttempt(adapter_id=adapter_id, kind="model", status="skipped", reason="adapter_not_registered"))
                continue
            manifest, caller = entry
            reason = self._ineligible_reason(request, manifest, spent_cost, spent_energy, started)
            if reason:
                attempts.append(IntelligenceAttempt(adapter_id=adapter_id, kind=manifest.kind, status="skipped", reason=reason, external=manifest.location != "local"))
                continue
            began = time.monotonic()
            try:
                result = dict(caller(self._request_for_adapter(request, manifest)) or {})
                latency_ms = int((time.monotonic() - began) * 1000)
                cost = max(0.0, float((result.get("usage") or {}).get("cost") or manifest.estimated_cost))
                energy = max(0.0, float((result.get("usage") or {}).get("energy_wh") or manifest.estimated_energy_wh))
                quality = max(0.0, min(1.0, float(result.get("quality_score") or manifest.estimated_quality)))
                spent_cost += cost
                spent_energy += energy
                valid = result.get("ok") is True and isinstance(result.get("output"), dict)
                if valid and quality >= request.budget.minimum_quality and self._matches_schema(result["output"], request.output_schema):
                    attempts.append(IntelligenceAttempt(adapter_id=adapter_id, kind=manifest.kind, status="succeeded", latency_ms=latency_ms, cost=cost, energy_wh=energy, quality_score=quality, external=manifest.location != "local"))
                    self._mark_success(adapter_id)
                    selected_output = dict(result["output"])
                    selected_adapter = adapter_id
                    break
                failure = str(result.get("error_code") or ("quality_below_minimum" if quality < request.budget.minimum_quality else "structured_output_invalid"))
                attempts.append(IntelligenceAttempt(adapter_id=adapter_id, kind=manifest.kind, status="failed", reason=failure, latency_ms=latency_ms, cost=cost, energy_wh=energy, quality_score=quality, external=manifest.location != "local"))
                self._mark_failure(adapter_id)
            except Exception as exc:
                latency_ms = int((time.monotonic() - began) * 1000)
                attempts.append(IntelligenceAttempt(adapter_id=adapter_id, kind=manifest.kind, status="failed", reason=type(exc).__name__, latency_ms=latency_ms, external=manifest.location != "local"))
                self._mark_failure(adapter_id)

        if not selected_adapter:
            return self._finish(request, request_hash, attempts, {}, "", "limited", "no_eligible_route_succeeded")

        delivery = self._deliver(request, selected_output)
        if delivery.get("ok") is not True:
            return self._finish(request, request_hash, attempts, selected_output, selected_adapter, "failed", str(delivery.get("reason") or "delivery_failed"), delivery=delivery)
        return self._finish(request, request_hash, attempts, selected_output, selected_adapter, "completed", "", delivery=delivery)

    def stream(self, response: IntelligenceResponse) -> list[IntelligenceStreamEvent]:
        events = [IntelligenceStreamEvent(request_id=response.request_id, sequence=0, event="accepted", payload={"raw_prompt_retained": False})]
        for attempt in response.attempts:
            event = "fallback" if attempt.status != "succeeded" else "route_attempt"
            events.append(IntelligenceStreamEvent(request_id=response.request_id, sequence=len(events), event=event, payload=attempt.model_dump(mode="json")))
        if response.delivery:
            events.append(IntelligenceStreamEvent(request_id=response.request_id, sequence=len(events), event="delivery", payload={key: value for key, value in response.delivery.items() if key not in {"content", "prompt"}}))
        events.append(IntelligenceStreamEvent(request_id=response.request_id, sequence=len(events), event="completed" if response.ok else "failed", payload={"status": response.status, "receipt_hash": canonical_hash(response.receipt)}))
        return events

    def _ineligible_reason(self, request: IntelligenceRequest, manifest: IntelligenceAdapterManifest, spent_cost: float, spent_energy: float, started: float) -> str:
        if not set(request.required_capabilities).issubset(set(manifest.capabilities)):
            return "required_capability_missing"
        if self._circuit_open(manifest.adapter_id):
            return "circuit_open"
        if manifest.estimated_quality < request.budget.minimum_quality:
            return "quality_budget_not_met"
        if spent_cost + manifest.estimated_cost > request.budget.maximum_cost:
            return "cost_budget_exceeded"
        if spent_energy + manifest.estimated_energy_wh > request.budget.maximum_energy_wh:
            return "energy_budget_exceeded"
        elapsed_ms = int((time.monotonic() - started) * 1000)
        if elapsed_ms + manifest.estimated_latency_ms > request.budget.maximum_latency_ms:
            return "latency_budget_exceeded"
        if manifest.location != "local":
            policy = request.disclosure
            if not policy.allow_external:
                return "external_disclosure_forbidden"
            if manifest.destination not in policy.allowed_destinations:
                return "external_destination_not_allowed"
            if manifest.residency not in policy.allowed_residencies:
                return "external_residency_not_allowed"
            if not policy.declared_fields:
                return "external_disclosure_fields_not_declared"
            if CLASSIFICATION_RANK[policy.data_classification] > CLASSIFICATION_RANK[manifest.maximum_data_classification]:
                return "data_classification_not_allowed"
        return ""

    @staticmethod
    def _request_for_adapter(request: IntelligenceRequest, manifest: IntelligenceAdapterManifest) -> IntelligenceRequest:
        if manifest.location == "local":
            return request
        allowed = set(request.disclosure.declared_fields)
        permitted_input = {key: value for key, value in request.input.items() if key in allowed}
        return request.model_copy(update={"input": permitted_input}, deep=True)

    @staticmethod
    def _matches_schema(output: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        required = schema.get("required") if isinstance(schema, dict) else []
        return all(str(key) in output for key in required or [])

    def _deliver(self, request: IntelligenceRequest, output: Dict[str, Any]) -> Dict[str, Any]:
        if request.delivery.mode == "pilot_presentation":
            if self.presentation_sink:
                return dict(self.presentation_sink(request, output) or {})
            return {"ok": True, "mode": "pilot_presentation", "surface": request.delivery.surface, "state": "ready"}
        if not request.delivery.approval_receipt:
            return {"ok": False, "mode": "governed_capability", "reason": "approval_receipt_required"}
        if not self.capability_sink:
            return {"ok": False, "mode": "governed_capability", "reason": "capability_authority_unavailable"}
        return dict(self.capability_sink(request, output) or {})

    def _finish(self, request: IntelligenceRequest, request_hash: str, attempts: list[IntelligenceAttempt], output: Dict[str, Any], adapter_id: str, status: str, reason: str, *, delivery: Dict[str, Any] | None = None) -> IntelligenceResponse:
        route_record = {
            "adapter_id": adapter_id,
            "attempts": [attempt.model_dump(mode="json") for attempt in attempts],
            "status": status,
            "reason": reason,
        }
        receipt = build_intelligence_route_receipt(
            brain_id=request.brain_id,
            request=request.model_dump(mode="json"),
            route=route_record,
            result=output,
            disclosure=request.disclosure.model_dump(mode="json"),
            budget=request.budget.model_dump(mode="json"),
        )
        receipt["receipt_id"] = f"route_{canonical_hash(receipt)[:24]}"
        response = IntelligenceResponse(request_id=request.request_id, ok=status == "completed", status=status, output=output, adapter_id=adapter_id, attempts=attempts, delivery=delivery or {"ok": False, "reason": reason}, receipt=receipt)
        self._responses[request.request_id] = (request_hash, response.model_copy(deep=True))
        if self.brain:
            self.brain.upsert_store_record("receipt", receipt, record_id=receipt["receipt_id"])
        return response

    def _read_health(self) -> Dict[str, Any]:
        if not self.health_path or not self.health_path.exists():
            return {"schema_version": "aion.intelligence.health.v1", "adapters": {}}
        try:
            value = json.loads(self.health_path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {"schema_version": "aion.intelligence.health.v1", "adapters": {}}
        except (OSError, ValueError):
            return {"schema_version": "aion.intelligence.health.v1", "adapters": {}}

    def _write_health(self) -> None:
        if not self.health_path:
            return
        self.health_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.health_path.with_suffix(self.health_path.suffix + ".tmp")
        temporary.write_text(json.dumps(self._health, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, self.health_path)

    def _mark_success(self, adapter_id: str) -> None:
        self._health.setdefault("adapters", {})[adapter_id] = {"failures": 0, "circuit_open_until": 0, "last_success_at": utc_now_iso()}
        self._write_health()

    def _mark_failure(self, adapter_id: str) -> None:
        current = dict(self._health.setdefault("adapters", {}).get(adapter_id) or {})
        failures = int(current.get("failures") or 0) + 1
        current.update({"failures": failures, "last_failure_at": utc_now_iso()})
        if failures >= self.failure_threshold:
            current["circuit_open_until"] = time.time() + self.circuit_seconds
        self._health["adapters"][adapter_id] = current
        self._write_health()

    def _circuit_open(self, adapter_id: str) -> bool:
        state = dict((self._health.get("adapters") or {}).get(adapter_id) or {})
        return float(state.get("circuit_open_until") or 0) > time.time()
