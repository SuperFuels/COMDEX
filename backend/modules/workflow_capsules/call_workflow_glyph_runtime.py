from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from backend.modules.workflow_capsules.call_workflow_glyph_validation import (
    CallWorkflowGlyphValidationResult,
    validate_call_workflow_glyph_contract,
)


JsonDict = dict[str, Any]


@dataclass(frozen=True)
class CallWorkflowGlyphRuntimeStep:
    index: int
    op: str
    status: str
    dry_run: bool
    input_preview: Any = None
    output_preview: Any = None

    def to_dict(self) -> JsonDict:
        return {
            "index": self.index,
            "op": self.op,
            "status": self.status,
            "dry_run": self.dry_run,
            "input_preview": self.input_preview,
            "output_preview": self.output_preview,
        }


@dataclass(frozen=True)
class CallWorkflowGlyphRuntimeResult:
    ok: bool
    status: str
    dry_run: bool
    glyph_code: str
    glyph_version: str
    child_workflow_id: str
    parent_run_id: str
    child_run_id: str
    validation: CallWorkflowGlyphValidationResult
    child_input: JsonDict = field(default_factory=dict)
    child_output: JsonDict = field(default_factory=dict)
    steps: list[CallWorkflowGlyphRuntimeStep] = field(default_factory=list)
    provenance: JsonDict = field(default_factory=dict)
    approval_policy: JsonDict = field(default_factory=dict)
    metrics: JsonDict = field(default_factory=dict)

    def to_dict(self) -> JsonDict:
        return {
            "ok": self.ok,
            "status": self.status,
            "dry_run": self.dry_run,
            "glyph_code": self.glyph_code,
            "glyph_version": self.glyph_version,
            "child_workflow_id": self.child_workflow_id,
            "parent_run_id": self.parent_run_id,
            "child_run_id": self.child_run_id,
            "validation": self.validation.to_dict(),
            "child_input": dict(self.child_input),
            "child_output": dict(self.child_output),
            "steps": [step.to_dict() for step in self.steps],
            "provenance": dict(self.provenance),
            "approval_policy": dict(self.approval_policy),
            "metrics": dict(self.metrics),
        }


def _as_dict(value: Any) -> JsonDict:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _registry_list(glyph_registry: Any) -> list[JsonDict]:
    if isinstance(glyph_registry, list):
        return [x for x in glyph_registry if isinstance(x, dict)]

    if isinstance(glyph_registry, dict):
        if isinstance(glyph_registry.get("glyphs"), list):
            return [x for x in glyph_registry["glyphs"] if isinstance(x, dict)]
        return [x for x in glyph_registry.values() if isinstance(x, dict)]

    return []


def resolve_call_workflow_glyph(call_node: Any, glyph_registry: Any) -> JsonDict | None:
    node = _as_dict(call_node)
    config = _as_dict(node.get("config"))
    code = str(node.get("glyph_code") or config.get("glyph_code") or "").strip().lower()

    if not code:
        return None

    for glyph in _registry_list(glyph_registry):
        if str(glyph.get("glyph_code") or glyph.get("code") or "").strip().lower() == code:
            return glyph

    return None


def _runtime_steps(glyph: Any) -> list[JsonDict]:
    glyph = _as_dict(glyph)
    plan = _as_dict(glyph.get("runtime_plan"))
    steps = plan.get("steps")
    return [x for x in _as_list(steps) if isinstance(x, dict)]


def _estimated_compiled_dry_run_cost(steps: list[JsonDict]) -> JsonDict:
    """
    Compiled glyph dry-runs bypass AI planning.

    Cost is intentionally deterministic and zero for this phase because no model
    calls, external writes, or paid connector actions are executed.
    """
    return {
        "currency": "USD",
        "estimated_total": 0.0,
        "ai_planning_cost": 0.0,
        "external_write_cost": 0.0,
        "compiled_step_count": len(steps),
        "cost_model": "compiled_dry_run_zero_cost_v1",
    }


def _boardroom_event(
    *,
    glyph_code: str,
    glyph_version: str,
    child_workflow_id: str,
    parent_run_id: str,
    child_run_id: str,
    status: str,
    elapsed_ms: float,
) -> JsonDict:
    return {
        "event_type": "call_workflow_glyph.dry_run",
        "source": "workflow_capsules.call_workflow_glyph_runtime",
        "glyph_code": glyph_code,
        "glyph_version": glyph_version,
        "child_workflow_id": child_workflow_id,
        "parent_run_id": parent_run_id,
        "child_run_id": child_run_id,
        "status": status,
        "dry_run": True,
        "elapsed_ms": elapsed_ms,
        "external_writes_performed": 0,
        "ai_planning_bypassed": True,
    }


def _workflow_id(glyph: Any, call_node: Any) -> str:
    glyph = _as_dict(glyph)
    node = _as_dict(call_node)
    config = _as_dict(node.get("config"))

    return str(
        node.get("child_workflow_id")
        or config.get("child_workflow_id")
        or config.get("workflow_id")
        or glyph.get("workflow_id")
        or glyph.get("child_workflow_id")
        or ""
    )


def _glyph_code(glyph: Any, call_node: Any) -> str:
    glyph = _as_dict(glyph)
    node = _as_dict(call_node)
    config = _as_dict(node.get("config"))
    return str(node.get("glyph_code") or config.get("glyph_code") or glyph.get("glyph_code") or glyph.get("code") or "")


def _glyph_version(glyph: Any, call_node: Any) -> str:
    glyph = _as_dict(glyph)
    node = _as_dict(call_node)
    config = _as_dict(node.get("config"))
    return str(node.get("glyph_version") or config.get("glyph_version") or glyph.get("glyph_version") or glyph.get("workflow_version") or "v1")


def _approval_policy(glyph: Any, call_node: Any) -> JsonDict:
    glyph = _as_dict(glyph)
    node = _as_dict(call_node)
    config = _as_dict(node.get("config"))

    return _as_dict(
        node.get("approval_policy")
        or config.get("approval_policy")
        or glyph.get("approval_policy")
        or {}
    )


def _simulate_step(step: JsonDict, payload: JsonDict, *, index: int) -> tuple[CallWorkflowGlyphRuntimeStep, JsonDict]:
    op = str(step.get("op") or step.get("kind") or step.get("step_id") or f"step_{index}")

    next_payload = {
        **payload,
        "_last_child_op": op,
        "_last_child_step_index": index,
    }

    runtime_step = CallWorkflowGlyphRuntimeStep(
        index=index,
        op=op,
        status="dry_run_simulated",
        dry_run=True,
        input_preview=dict(payload),
        output_preview=dict(next_payload),
    )

    return runtime_step, next_payload


def execute_call_workflow_glyph_dry_run(
    *,
    parent_run_id: str,
    call_node: Any,
    parent_payload: Any,
    glyph_registry: Any,
    available_connectors: Any | None = None,
    parent_approval_policy: Any | None = None,
) -> CallWorkflowGlyphRuntimeResult:
    """
    Dry-run nested call_workflow_glyph execution.

    It does not call AI.
    It does not perform external writes.
    It does not send email.
    It does not mutate stored glyphs.
    """
    started = perf_counter()

    node = _as_dict(call_node)
    payload = _as_dict(parent_payload)

    # E4 native speed path: resolve registry once, then reuse this pinned glyph
    # through validation and dry-run execution. No AI planning is involved.
    registry_glyph = resolve_call_workflow_glyph(call_node, glyph_registry)
    registry_lookup_cache_hit = registry_glyph is not None

    validation = validate_call_workflow_glyph_contract(
        parent_output_payload=payload,
        call_node=node,
        registry_glyph=registry_glyph,
        available_connectors=available_connectors,
        parent_approval_policy=parent_approval_policy,
    )

    glyph_code = _glyph_code(registry_glyph or {}, node)
    glyph_version = _glyph_version(registry_glyph or {}, node)
    child_workflow_id = _workflow_id(registry_glyph or {}, node)
    child_run_id = f"{parent_run_id}::{glyph_code or 'call_workflow_glyph'}::dry_run_child"

    runtime_steps = _runtime_steps(registry_glyph)
    estimated_cost = _estimated_compiled_dry_run_cost(runtime_steps)

    if not registry_glyph:
        validation = CallWorkflowGlyphValidationResult(
            valid=False,
            errors=[*validation.errors, "glyph_registry_resolution_failed"],
            warnings=list(validation.warnings),
            missing_connectors=list(validation.missing_connectors),
            version_mismatch=validation.version_mismatch,
            approval_policy_mismatch=validation.approval_policy_mismatch,
            runtime_blocked=True,
        )

    if not validation.valid:
        elapsed_ms = round((perf_counter() - started) * 1000, 3)
        return CallWorkflowGlyphRuntimeResult(
            ok=False,
            status="blocked_by_validation",
            dry_run=True,
            glyph_code=glyph_code,
            glyph_version=glyph_version,
            child_workflow_id=child_workflow_id,
            parent_run_id=parent_run_id,
            child_run_id=child_run_id,
            validation=validation,
            child_input=dict(payload),
            child_output={},
            steps=[],
            provenance={
                "parent_run_id": parent_run_id,
                "child_run_id": child_run_id,
                "edge": "parent_payload -> child_runtime_plan",
                "mode": "dry_run_only",
                "registry_lookup_cached": registry_lookup_cache_hit,
            },
            approval_policy=_approval_policy(registry_glyph or {}, node),
            metrics={
                "elapsed_ms": elapsed_ms,
                "runtime_blocked": True,
                "steps_executed": 0,
                "ai_planning_bypassed": True,
                "external_writes_performed": 0,
                "registry_lookup_cached": registry_lookup_cache_hit,
                "estimated_cost": estimated_cost,
                "boardroom_events_emitted": 1,
            },
        )

    current_payload = dict(payload)
    executed_steps: list[CallWorkflowGlyphRuntimeStep] = []

    for index, step in enumerate(runtime_steps, start=1):
        runtime_step, current_payload = _simulate_step(step, current_payload, index=index)
        executed_steps.append(runtime_step)

    child_output = {
        **current_payload,
        "child_workflow_id": child_workflow_id,
        "glyph_code": glyph_code,
        "dry_run": True,
        "runtime_plan_completed": True,
    }

    elapsed_ms = round((perf_counter() - started) * 1000, 3)

    boardroom_events = [
        _boardroom_event(
            glyph_code=glyph_code,
            glyph_version=glyph_version,
            child_workflow_id=child_workflow_id,
            parent_run_id=parent_run_id,
            child_run_id=child_run_id,
            status="dry_run_completed",
            elapsed_ms=elapsed_ms,
        )
    ]

    return CallWorkflowGlyphRuntimeResult(
        ok=True,
        status="dry_run_completed",
        dry_run=True,
        glyph_code=glyph_code,
        glyph_version=glyph_version,
        child_workflow_id=child_workflow_id,
        parent_run_id=parent_run_id,
        child_run_id=child_run_id,
        validation=validation,
        child_input=dict(payload),
        child_output=child_output,
        steps=executed_steps,
        provenance={
            "parent_run_id": parent_run_id,
            "child_run_id": child_run_id,
            "parent_payload_passed_to_child": True,
            "child_output_returned_to_parent": True,
            "mode": "dry_run_only",
            "registry_lookup_cached": registry_lookup_cache_hit,
            "boardroom_events": boardroom_events,
        },
        approval_policy=_approval_policy(registry_glyph or {}, node),
        metrics={
            "elapsed_ms": elapsed_ms,
            "runtime_blocked": False,
            "steps_executed": len(executed_steps),
            "ai_planning_bypassed": True,
            "external_writes_performed": 0,
            "registry_lookup_cached": registry_lookup_cache_hit,
            "estimated_cost": estimated_cost,
            "boardroom_events_emitted": len(boardroom_events),
        },
    )
