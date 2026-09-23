from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from typing import Any

from backend.modules.aion.goal_engine.contracts import (
    EnvironmentRevalidationContract,
    ExperimentNodeContract,
    GoalNodeContract,
    LoopNodeContract,
    OutcomeEvaluationContract,
    ReflectionLearningContract,
    StateDeltaAccumulatorContract,
)
from backend.modules.aion.goal_engine.dry_run import build_goal_engine_dry_run_manifest
from backend.modules.aion.goal_engine.boardroom_trace import build_goal_engine_boardroom_trace


GOAL_ENGINE_ACTION_PREFIX = "goal_engine."


CONTRACT_BY_ACTION_ID = {
    "goal_engine.goal": GoalNodeContract,
    "goal_engine.experiment": ExperimentNodeContract,
    "goal_engine.loop": LoopNodeContract,
    "goal_engine.outcome_evaluation": OutcomeEvaluationContract,
    "goal_engine.reflect_learn": ReflectionLearningContract,
    "goal_engine.state_delta_accumulator": StateDeltaAccumulatorContract,
    "goal_engine.environment_revalidation": EnvironmentRevalidationContract,
}


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if is_dataclass(value):
        return {field.name: getattr(value, field.name, None) for field in fields(value)}

    if hasattr(value, "__dict__"):
        return dict(getattr(value, "__dict__", {}) or {})

    return {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _step_action_id(step: Any) -> str:
    data = _as_dict(step)
    config = _as_dict(data.get("config"))

    for value in (
        data.get("action_id"),
        data.get("module_id"),
        data.get("action"),
        data.get("kind"),
        config.get("action_id"),
        config.get("module_id"),
    ):
        text = str(value or "").strip()
        if text.startswith(GOAL_ENGINE_ACTION_PREFIX):
            return text

    return ""


def is_goal_engine_step(step: Any) -> bool:
    return bool(_step_action_id(step))


def _workflow_steps_from_capsule(capsule: Any) -> list[Any]:
    data = _as_dict(capsule)

    direct_steps = data.get("steps")
    if isinstance(direct_steps, list):
        return direct_steps

    for key in ("workflow", "definition", "expanded_workflow", "compiled_workflow", "capsule"):
        nested = data.get(key)
        nested_data = _as_dict(nested)
        if isinstance(nested_data.get("steps"), list):
            return nested_data["steps"]

    expanded = data.get("expanded")
    expanded_data = _as_dict(expanded)
    if isinstance(expanded_data.get("steps"), list):
        return expanded_data["steps"]

    if hasattr(capsule, "steps"):
        steps = getattr(capsule, "steps")
        if isinstance(steps, list):
            return steps

    return []


def _workflow_id_from_capsule(capsule: Any) -> str:
    data = _as_dict(capsule)
    for key in ("workflow_id", "id", "canonical_key", "name"):
        value = str(data.get(key) or "").strip()
        if value:
            return value

    workflow = _as_dict(data.get("workflow"))
    for key in ("workflow_id", "id", "name"):
        value = str(workflow.get(key) or "").strip()
        if value:
            return value

    return "workflow_goal_engine_dry_run"


def _default_value_for_field(name: str, action_id: str, step_data: dict[str, Any]) -> Any:
    config = _as_dict(step_data.get("config"))

    if name in step_data:
        return step_data[name]
    if name in config:
        return config[name]

    step_id = str(
        step_data.get("id")
        or step_data.get("step_id")
        or step_data.get("node_id")
        or action_id.replace(".", "_")
    )

    if name.endswith("_id"):
        if name == "goal_id":
            return str(config.get("goal_id") or step_data.get("goal_id") or "goal_001")
        if name == "run_id":
            return str(config.get("run_id") or step_data.get("run_id") or "dry_run_001")
        if name == "checkpoint_id":
            return str(config.get("checkpoint_id") or "checkpoint_001")
        if name == "parent_goal_id":
            return str(config.get("parent_goal_id") or "goal_001")
        return str(config.get(name) or step_id)

    if name in {"goal_name", "experiment_name", "name", "title"}:
        return str(step_data.get("title") or step_data.get("label") or action_id)

    if name in {"target_metric"}:
        return str(config.get(name) or "outcome_score")

    if name in {"target_value", "metric_target", "metric_actual", "max_spend", "cost"}:
        return config.get(name, 1)

    if name in {"quality_score", "outcome_score", "confidence"}:
        return config.get(name, 0.8)

    if name in {"max_iterations", "max_runtime_minutes", "max_external_writes"}:
        return int(config.get(name) or 1)

    if name == "loop_mode":
        return str(config.get(name) or "fixed_iterations")

    if name == "status":
        return str(config.get(name) or "dry_run_preview")

    if name == "time_to_result_seconds":
        return int(config.get(name) or 0)

    if name in {
        "requires_human_approval",
        "kill_switch_triggered",
        "allow_learn",
        "adr_active",
        "approval_still_valid",
        "vault_ready",
        "connectors_ready",
        "parent_goal_still_required",
        "external_state_changed",
        "advisory_only",
    }:
        defaults = {
            "requires_human_approval": True,
            "kill_switch_triggered": False,
            "allow_learn": False,
            "adr_active": False,
            "approval_still_valid": True,
            "vault_ready": True,
            "connectors_ready": True,
            "parent_goal_still_required": True,
            "external_state_changed": False,
            "advisory_only": True,
        }
        return bool(config.get(name, defaults[name]))

    if name in {"variants", "deltas", "evidence", "evidence_refs"}:
        return list(config.get(name) or [])

    if name in {"loop_context_snapshot"}:
        return dict(config.get(name) or {"dry_run": True})

    if name in {"reason", "hypothesis", "state_delta_strategy"}:
        defaults = {
            "reason": "Dry-run goal engine preview.",
            "hypothesis": "Dry-run experiment hypothesis.",
            "state_delta_strategy": "bounded_delta_only",
        }
        return str(config.get(name) or defaults[name])

    return None


def _contract_for_goal_engine_step(step: Any) -> Any | None:
    step_data = _as_dict(step)
    action_id = _step_action_id(step)
    contract_cls = CONTRACT_BY_ACTION_ID.get(action_id)
    if contract_cls is None:
        return None

    kwargs: dict[str, Any] = {}
    for field in fields(contract_cls):
        value = _default_value_for_field(field.name, action_id, step_data)

        if value is None and field.default is not MISSING:
            continue

        if value is None and field.default_factory is not MISSING:  # type: ignore[attr-defined]
            continue

        kwargs[field.name] = value

    return contract_cls(**kwargs)



def _canonical_goal_engine_manifest(
    manifest: dict[str, Any],
    *,
    run_id: str,
    workflow_id: str,
) -> dict[str, Any]:
    """
    Normalize Goal Engine dry-run manifests for Workflow Capsule consumers.

    The lower-level Goal Engine builder owns the internal manifest details.
    This bridge guarantees stable top-level fields for Boardroom/workflow
    preview consumers.
    """
    payload = dict(manifest or {})

    payload.setdefault("runtime", "aion_goal_engine")
    payload.setdefault("run_id", run_id or "goal_engine_dry_run")
    payload.setdefault("workflow_id", workflow_id or "workflow_goal_engine_dry_run")
    payload.setdefault("dry_run_only", True)
    payload.setdefault("would_execute", False)
    payload.setdefault("would_write_external", False)
    payload.setdefault("would_grant_permission", False)

    safety = dict(payload.get("safety_contract") or {})
    safety.setdefault("goals_grant_permission", False)
    safety.setdefault("experiments_grant_permission", False)
    safety.setdefault("loops_grant_permission", False)
    safety.setdefault("learning_grants_permission", False)
    safety.setdefault("external_writes_require_approval", True)
    safety.setdefault("unbounded_loops_allowed", False)
    safety.setdefault("resume_requires_environment_revalidation", True)
    payload["safety_contract"] = safety

    steps = payload.get("steps")
    if isinstance(steps, list):
        normalized_steps = []
        for step in steps:
            row = dict(step or {})
            row.setdefault("dry_run_only", True)
            row.setdefault("would_execute", False)
            row.setdefault("would_write_external", False)
            row.setdefault("would_grant_permission", False)
            normalized_steps.append(row)
        payload["steps"] = normalized_steps

    return payload


def build_goal_engine_manifest_for_capsule(
    capsule: Any,
    *,
    run_id: str = "goal_engine_dry_run",
) -> dict[str, Any] | None:
    steps = _workflow_steps_from_capsule(capsule)
    contracts = []

    for step in steps:
        if not is_goal_engine_step(step):
            continue

        contract = _contract_for_goal_engine_step(step)
        if contract is not None:
            contracts.append(contract)

    if not contracts:
        return None

    workflow_id = _workflow_id_from_capsule(capsule)
    safe_run_id = run_id or "goal_engine_dry_run"

    manifest = build_goal_engine_dry_run_manifest(
        run_id=safe_run_id,
        workflow_id=workflow_id,
        contracts=contracts,
    )

    return _canonical_goal_engine_manifest(
        manifest,
        run_id=safe_run_id,
        workflow_id=workflow_id,
    )



def _goal_engine_trace_node_kind(node: dict[str, object]) -> str:
    action_id = str(
        node.get("action_id")
        or node.get("action")
        or node.get("type")
        or node.get("id")
        or ""
    ).strip()

    if action_id.startswith("goal_engine."):
        return action_id.replace("goal_engine.", "")

    return "goal_engine"



def _goal_engine_manifest_nodes(manifest: dict[str, object]) -> list[dict[str, object]]:
    """
    Extract Goal Engine rows from all manifest shapes used by tests/runtime.

    Be deliberately tolerant: once a payload is already a Goal Engine manifest,
    grouped rows may be named "goals", "loops", "experiments", etc. and may not
    repeat goal_engine.* in every row.
    """

    if not isinstance(manifest, dict):
        return []

    buckets: list[object] = []

    for key in (
        "nodes",
        "goal_engine_nodes",
        "steps",
        "trace",
        "goals",
        "experiments",
        "loops",
        "outcome_evaluations",
        "outcomes",
        "reflection_learning",
        "reflections",
        "state_delta_accumulators",
        "state_deltas",
        "environment_revalidations",
        "revalidations",
    ):
        buckets.append(manifest.get(key))

    goal_engine = manifest.get("goal_engine")
    if isinstance(goal_engine, dict):
        for key in (
            "nodes",
            "goal_engine_nodes",
            "steps",
            "trace",
            "goals",
            "experiments",
            "loops",
            "outcome_evaluations",
            "outcomes",
            "reflection_learning",
            "reflections",
            "state_delta_accumulators",
            "state_deltas",
            "environment_revalidations",
            "revalidations",
        ):
            buckets.append(goal_engine.get(key))

    for group_key in ("node_groups", "groups", "grouped_nodes", "manifest_groups"):
        grouped = manifest.get(group_key)
        if isinstance(grouped, dict):
            buckets.extend(grouped.values())
        if isinstance(goal_engine, dict):
            grouped_inner = goal_engine.get(group_key)
            if isinstance(grouped_inner, dict):
                buckets.extend(grouped_inner.values())

    rows: list[dict[str, object]] = []
    seen: set[str] = set()

    for bucket in buckets:
        if isinstance(bucket, dict):
            bucket = list(bucket.values())

        if not isinstance(bucket, list):
            continue

        for raw in bucket:
            if not isinstance(raw, dict):
                continue

            action_id = str(
                raw.get("action_id")
                or raw.get("action")
                or raw.get("node_action")
                or raw.get("type")
                or raw.get("kind")
                or raw.get("id")
                or ""
            )

            # Accept explicit goal_engine rows, but also accept grouped rows from
            # an already-canonical Goal Engine manifest even when action_id is terse.
            looks_goal_engine = (
                "goal_engine" in action_id
                or str(raw.get("runtime") or "") == "aion_goal_engine"
                or str(raw.get("app") or "") == "aion_goal_engine"
                or str(raw.get("kind") or "") in {
                    "goal",
                    "experiment",
                    "loop",
                    "outcome_evaluation",
                    "reflect_learn",
                    "reflection_learning",
                    "state_delta_accumulator",
                    "environment_revalidation",
                    "goal_engine",
                }
                or any(
                    key in raw
                    for key in (
                        "goal_id",
                        "experiment_id",
                        "loop_id",
                        "outcome_score",
                        "max_iterations",
                        "checkpoint_id",
                        "revalidation_id",
                    )
                )
            )

            if not looks_goal_engine:
                continue

            node_id = str(raw.get("node_id") or raw.get("id") or action_id or len(rows))
            dedupe = f"{node_id}:{action_id}:{len(rows)}"
            if dedupe in seen:
                continue

            seen.add(dedupe)
            rows.append(raw)

    return rows


def build_goal_engine_step_trace_rows(
    manifest: dict[str, object],
    *,
    run_id: str | None = None,
) -> list[dict[str, object]]:
    """
    Build reviewable, dry-run-only trace rows for every Goal Engine node.

    These rows are intentionally non-executing. They describe what AION would
    evaluate/simulate, and they preserve the safety contract that Goal Engine
    nodes grant no permission and perform no external writes.
    """

    nodes = _goal_engine_manifest_nodes(manifest)

    trace_rows: list[dict[str, object]] = []

    for index, raw_node in enumerate(nodes):
        if not isinstance(raw_node, dict):
            continue

        node_id = str(raw_node.get("id") or raw_node.get("node_id") or f"goal_engine_node_{index + 1}")
        action_id = str(raw_node.get("action_id") or raw_node.get("action") or raw_node.get("type") or "")
        node_kind = _goal_engine_trace_node_kind(raw_node)
        title = str(raw_node.get("title") or raw_node.get("label") or node_kind.replace("_", " ").title())

        trace_rows.append(
            {
                "trace_schema_version": "aion.goal_engine.step_trace.v1",
                "runtime": "aion_goal_engine",
                "run_id": run_id or manifest.get("run_id") or "",
                "step_index": index,
                "node_id": node_id,
                "node_title": title,
                "node_kind": node_kind,
                "action_id": action_id,
                "status": "dry_run_simulated",
                "dry_run_only": True,
                "external_write_performed": False,
                "grants_permission": False,
                "would_grant_permission": False,
                "requires_approval_before_external_write": True,
                "bounded_execution": True,
                "suggested_next_action": "review_goal_engine_trace",
                "blocked_reasons": [],
                "warnings": list(raw_node.get("warnings") or []),
                "summary": (
                    f"Goal Engine {node_kind} node was simulated only. "
                    "No permission was granted and no external write was performed."
                ),
            }
        )

    return trace_rows


def attach_goal_engine_step_trace_rows_to_dry_result(
    dry_result: object,
    manifest: dict[str, object],
    *,
    run_id: str | None = None,
) -> object:
    rows = build_goal_engine_step_trace_rows(manifest, run_id=run_id)

    if not rows:
        return dry_result

    setattr(dry_result, "goal_engine_step_trace", rows)

    if hasattr(dry_result, "to_dict"):
        original_to_dict = dry_result.to_dict

        def to_dict_with_goal_engine_step_trace():
            payload = original_to_dict()
            if isinstance(payload, dict):
                payload["goal_engine_step_trace"] = rows

                existing_trace = payload.get("trace")
                if isinstance(existing_trace, list):
                    payload["trace"] = [*existing_trace, *rows]
                else:
                    payload["trace"] = rows

            return payload

        dry_result.to_dict = to_dict_with_goal_engine_step_trace  # type: ignore[method-assign]

    return dry_result

def attach_goal_engine_manifest_to_dry_result(
    dry_result: Any,
    capsule: Any,
    *,
    run_id: str | None = None,
) -> Any:
    """
    Attach Goal Engine dry-run manifest and Boardroom trace to a dry-run result.

    Contract:
    - advisory only
    - dry-run only
    - grants no permission
    - performs no external writes
    """
    manifest = build_goal_engine_manifest_for_capsule(capsule, run_id=run_id)

    if not manifest:
        return dry_result

    boardroom_trace = build_goal_engine_boardroom_trace(manifest)

    # Compatibility shape for older/current UI + tests.
    # Keep canonical nested trace, but expose the safety booleans top-level too.
    if isinstance(boardroom_trace, dict):
        boardroom_trace.setdefault("dry_run_only", True)
        boardroom_trace.setdefault("would_execute", False)
        boardroom_trace.setdefault("would_write_external", False)
        boardroom_trace.setdefault("would_grant_permission", False)
        boardroom_trace.setdefault("grants_permission", False)
        boardroom_trace.setdefault("external_writes_require_approval", True)

    setattr(dry_result, "goal_engine_manifest", manifest)
    setattr(dry_result, "goal_engine", manifest)
    setattr(dry_result, "goal_engine_boardroom_trace", boardroom_trace)

    if hasattr(dry_result, "to_dict"):
        original_to_dict = dry_result.to_dict

        def to_dict_with_goal_engine_manifest():
            payload = original_to_dict()
            if isinstance(payload, dict):
                payload["goal_engine_manifest"] = manifest
                payload["goal_engine"] = manifest
                payload["goal_engine_boardroom_trace"] = boardroom_trace
            return payload

        dry_result.to_dict = to_dict_with_goal_engine_manifest  # type: ignore[method-assign]

    dry_result = attach_goal_engine_step_trace_rows_to_dry_result(
        dry_result,
        manifest,
        run_id=run_id,
    )

    return dry_result


# AION PATCH: Goal Engine step trace wide collector v6
# Purpose:
# - Build step-level dry-run rows from the Goal Engine manifest.
# - Preserve explicit ids such as goal_1, experiment_1, loop_1.
# - Attach rows to both result.goal_engine_step_trace and payload["trace"].

GOAL_ENGINE_STEP_TRACE_SCHEMA_VERSION = "aion.goal_engine.step_trace.v1"


def _goal_engine_kind_from_text_v6(*values):
    raw = " ".join(str(v or "") for v in values).lower()

    if "experiment" in raw or "variant" in raw or "a-b" in raw or "ab_test" in raw:
        return "experiment"
    if "loop" in raw or "iteration" in raw:
        return "loop"
    if "outcome" in raw or "evaluation" in raw:
        return "outcome_evaluation"
    if "reflect" in raw or "learn" in raw or "reflection" in raw:
        return "reflect_learn"
    if "state_delta" in raw or "state delta" in raw or "accumulator" in raw:
        return "state_delta_accumulator"
    if "environment_revalidation" in raw or "revalidation" in raw:
        return "environment_revalidation"
    if "checkpoint" in raw or "resume" in raw:
        return "checkpoint"
    if "goal" in raw:
        return "goal"

    return ""


def _goal_engine_action_id_v6(kind):
    return {
        "goal": "goal_engine.goal",
        "experiment": "goal_engine.experiment",
        "loop": "goal_engine.loop",
        "outcome_evaluation": "goal_engine.outcome_evaluation",
        "reflect_learn": "goal_engine.reflect_learn",
        "state_delta_accumulator": "goal_engine.state_delta_accumulator",
        "environment_revalidation": "goal_engine.environment_revalidation",
        "checkpoint": "goal_engine.checkpoint",
    }.get(str(kind or ""), "goal_engine.step")


def _goal_engine_node_id_v6(item, kind, index):
    if not isinstance(item, dict):
        return f"{kind or 'goal_engine'}_{index}"

    for key in (
        "node_id",
        "id",
        "step_id",
        "goal_id",
        "experiment_id",
        "loop_id",
        "outcome_id",
        "reflection_id",
        "checkpoint_id",
    ):
        value = item.get(key)
        if value:
            return str(value)

    return f"{kind or 'goal_engine'}_{index}"


def _looks_like_goal_engine_node_v6(item, parent_key=""):
    if not isinstance(item, dict):
        return ""

    explicit = _goal_engine_kind_from_text_v6(
        item.get("node_kind"),
        item.get("kind"),
        item.get("type"),
        item.get("action_id"),
        item.get("action"),
        item.get("node_id"),
        item.get("id"),
        item.get("step_id"),
        item.get("title"),
        item.get("label"),
        item.get("name"),
    )

    if explicit:
        return explicit

    parent_kind = _goal_engine_kind_from_text_v6(parent_key)
    if parent_kind and any(
        key in item
        for key in (
            "node_id",
            "id",
            "step_id",
            "title",
            "label",
            "name",
            "config",
            "payload",
        )
    ):
        return parent_kind

    return ""


def _collect_goal_engine_nodes_v6(value, *, parent_key="", out=None):
    if out is None:
        out = []

    if isinstance(value, dict):
        kind = _looks_like_goal_engine_node_v6(value, parent_key=parent_key)

        # Do not accidentally collect the whole manifest/root object as a node.
        root_like = any(
            key in value
            for key in (
                "goal_engine_manifest",
                "goal_engine_boardroom_trace",
                "goal_engine",
                "safety_contract",
                "nodes",
                "steps",
                "trace",
                "manifest_type",
            )
        ) and not any(
            key in value
            for key in (
                "node_id",
                "id",
                "step_id",
                "goal_id",
                "experiment_id",
                "loop_id",
                "action_id",
                "action",
            )
        )

        if kind and not root_like:
            index = len(out) + 1
            node_id = _goal_engine_node_id_v6(value, kind, index)
            action_id = str(value.get("action_id") or value.get("action") or _goal_engine_action_id_v6(kind))

            out.append({
                **value,
                "node_id": node_id,
                "id": value.get("id") or node_id,
                "node_kind": kind,
                "kind": kind,
                "action_id": action_id,
            })
            return out

        for key, child in value.items():
            _collect_goal_engine_nodes_v6(child, parent_key=str(key), out=out)

    elif isinstance(value, list):
        for child in value:
            _collect_goal_engine_nodes_v6(child, parent_key=parent_key, out=out)

    return out


def _sort_goal_engine_nodes_v6(nodes):
    order = {
        "goal": 10,
        "experiment": 20,
        "loop": 30,
        "outcome_evaluation": 40,
        "reflect_learn": 50,
        "checkpoint": 55,
        "state_delta_accumulator": 60,
        "environment_revalidation": 70,
    }

    return sorted(
        nodes,
        key=lambda item: (
            order.get(str(item.get("node_kind") or item.get("kind") or ""), 999),
            str(item.get("node_id") or item.get("id") or ""),
        ),
    )


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    if not isinstance(manifest, dict):
        return []

    nodes = _sort_goal_engine_nodes_v6(_collect_goal_engine_nodes_v6(manifest))

    rows = []
    for index, node in enumerate(nodes, start=1):
        kind = str(node.get("node_kind") or node.get("kind") or "goal")
        node_id = str(node.get("node_id") or node.get("id") or f"{kind}_{index}")
        title = str(
            node.get("node_title")
            or node.get("title")
            or node.get("label")
            or node.get("name")
            or node_id
        )
        action_id = str(node.get("action_id") or _goal_engine_action_id_v6(kind))

        rows.append({
            "trace_schema_version": GOAL_ENGINE_STEP_TRACE_SCHEMA_VERSION,
            "schema_version": GOAL_ENGINE_STEP_TRACE_SCHEMA_VERSION,
            "runtime": "aion_goal_engine",
            "step_index": index,
            "run_id": run_id or manifest.get("run_id") or "",
            "node_id": node_id,
            "id": node_id,
            "node_title": title,
            "title": title,
            "node_kind": kind,
            "kind": kind,
            "action_id": action_id,
            "status": "dry_run_simulated",
            "dry_run": True,
            "dry_run_only": True,
            "grants_permission": False,
            "would_grant_permission": False,
            "requires_approval_before_external_write": True,
            "blocks_unbounded_execution": True,
            "suggested_next_action": "review_before_live_execution",
            "payload": dict(node),
        })

    return rows


def attach_goal_engine_step_trace_rows_to_dry_result(dry_result, manifest, *, run_id=None):
    rows = build_goal_engine_step_trace_rows(manifest, run_id=run_id)
    if not rows:
        return dry_result

    setattr(dry_result, "goal_engine_step_trace", rows)

    original_to_dict = getattr(dry_result, "to_dict", None)
    if callable(original_to_dict):
        def to_dict_with_goal_engine_step_trace():
            payload = original_to_dict()
            if not isinstance(payload, dict):
                return payload

            existing_trace = payload.get("trace")
            if not isinstance(existing_trace, list):
                existing_trace = []

            payload["trace"] = existing_trace + rows
            payload["goal_engine_step_trace"] = rows
            return payload

        setattr(dry_result, "to_dict", to_dict_with_goal_engine_step_trace)

    return dry_result


_previous_attach_goal_engine_manifest_to_dry_result_v6 = attach_goal_engine_manifest_to_dry_result


def attach_goal_engine_manifest_to_dry_result(dry_result, capsule, *, run_id=None):
    result = _previous_attach_goal_engine_manifest_to_dry_result_v6(
        dry_result,
        capsule,
        run_id=run_id,
    )

    manifest = getattr(result, "goal_engine_manifest", None)

    if not isinstance(manifest, dict):
        to_dict = getattr(result, "to_dict", None)
        payload = to_dict() if callable(to_dict) else {}
        if isinstance(payload, dict):
            manifest = payload.get("goal_engine_manifest") or payload.get("goal_engine")

    if isinstance(manifest, dict):
        result = attach_goal_engine_step_trace_rows_to_dry_result(
            result,
            manifest,
            run_id=run_id,
        )

    return result


# AION PATCH: Goal Engine step trace hard override v9
# This intentionally appears at EOF so these names win over any earlier definitions.

GOAL_ENGINE_STEP_TRACE_SCHEMA_VERSION = "aion.goal_engine.step_trace.v1"


def _aion_goal_engine_kind_v9(*values):
    raw = " ".join(str(v or "") for v in values).lower()
    if "experiment" in raw or "variant" in raw or "ab_test" in raw or "a-b" in raw:
        return "experiment"
    if "loop" in raw or "iteration" in raw:
        return "loop"
    if "outcome" in raw or "evaluation" in raw:
        return "outcome_evaluation"
    if "reflect" in raw or "learn" in raw:
        return "reflect_learn"
    if "state_delta" in raw or "accumulator" in raw:
        return "state_delta_accumulator"
    if "environment" in raw or "revalidation" in raw:
        return "environment_revalidation"
    if "checkpoint" in raw or "resume" in raw:
        return "checkpoint"
    if "goal" in raw:
        return "goal"
    return ""


def _aion_goal_engine_action_v9(kind):
    return {
        "goal": "goal_engine.goal",
        "experiment": "goal_engine.experiment",
        "loop": "goal_engine.loop",
        "outcome_evaluation": "goal_engine.outcome_evaluation",
        "reflect_learn": "goal_engine.reflect_learn",
        "state_delta_accumulator": "goal_engine.state_delta_accumulator",
        "environment_revalidation": "goal_engine.environment_revalidation",
        "checkpoint": "goal_engine.checkpoint",
    }.get(str(kind or ""), "goal_engine.step")


def _aion_goal_engine_collect_v9(value, parent_key="", rows=None):
    if rows is None:
        rows = []

    if isinstance(value, list):
        for item in value:
            _aion_goal_engine_collect_v9(item, parent_key=parent_key, rows=rows)
        return rows

    if not isinstance(value, dict):
        return rows

    kind = _aion_goal_engine_kind_v9(
        parent_key,
        value.get("node_kind"),
        value.get("kind"),
        value.get("type"),
        value.get("action_id"),
        value.get("action"),
        value.get("node_id"),
        value.get("id"),
        value.get("step_id"),
        value.get("title"),
        value.get("label"),
        value.get("name"),
    )

    has_node_identity = any(
        value.get(k)
        for k in (
            "node_id",
            "id",
            "step_id",
            "goal_id",
            "experiment_id",
            "loop_id",
            "outcome_id",
            "checkpoint_id",
            "action_id",
        )
    )

    # Collect leaf node records only. Do not collect root manifest objects.
    if kind and has_node_identity:
        node_id = (
            value.get("node_id")
            or value.get("id")
            or value.get("step_id")
            or value.get("goal_id")
            or value.get("experiment_id")
            or value.get("loop_id")
            or value.get("outcome_id")
            or value.get("checkpoint_id")
            or f"{kind}_{len(rows) + 1}"
        )
        node_id = str(node_id)

        rows.append({
            **value,
            "node_id": node_id,
            "id": str(value.get("id") or node_id),
            "node_kind": kind,
            "kind": kind,
            "action_id": str(value.get("action_id") or value.get("action") or _aion_goal_engine_action_v9(kind)),
        })
        return rows

    for key, child in value.items():
        _aion_goal_engine_collect_v9(child, parent_key=str(key), rows=rows)

    return rows


def _aion_goal_engine_sort_v9(nodes):
    order = {
        "goal": 10,
        "experiment": 20,
        "loop": 30,
        "outcome_evaluation": 40,
        "reflect_learn": 50,
        "checkpoint": 55,
        "state_delta_accumulator": 60,
        "environment_revalidation": 70,
    }
    return sorted(
        nodes,
        key=lambda item: (
            order.get(str(item.get("node_kind") or item.get("kind") or ""), 999),
            str(item.get("node_id") or item.get("id") or ""),
        ),
    )


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    if not isinstance(manifest, dict):
        return []

    nodes = _aion_goal_engine_sort_v9(_aion_goal_engine_collect_v9(manifest))

    rows = []
    for index, node in enumerate(nodes, start=1):
        kind = str(node.get("node_kind") or node.get("kind") or "goal")
        node_id = str(node.get("node_id") or node.get("id") or f"{kind}_{index}")
        title = str(
            node.get("node_title")
            or node.get("title")
            or node.get("label")
            or node.get("name")
            or node_id
        )

        rows.append({
            "trace_schema_version": GOAL_ENGINE_STEP_TRACE_SCHEMA_VERSION,
            "schema_version": GOAL_ENGINE_STEP_TRACE_SCHEMA_VERSION,
            "runtime": "aion_goal_engine",
            "run_id": run_id or manifest.get("run_id") or "",
            "step_index": index,
            "node_id": node_id,
            "id": node_id,
            "node_title": title,
            "title": title,
            "node_kind": kind,
            "kind": kind,
            "action_id": str(node.get("action_id") or _aion_goal_engine_action_v9(kind)),
            "status": "dry_run_simulated",
            "dry_run": True,
            "dry_run_only": True,
            "grants_permission": False,
            "would_grant_permission": False,
            "requires_approval_before_external_write": True,
            "blocks_unbounded_execution": True,
            "suggested_next_action": "review_before_live_execution",
            "payload": dict(node),
        })

    return rows


def attach_goal_engine_step_trace_rows_to_dry_result(dry_result, manifest, *, run_id=None):
    rows = build_goal_engine_step_trace_rows(manifest, run_id=run_id)
    if not rows:
        return dry_result

    setattr(dry_result, "goal_engine_step_trace", rows)

    original_to_dict = getattr(dry_result, "to_dict", None)
    if callable(original_to_dict):
        def to_dict_with_goal_engine_step_trace():
            payload = original_to_dict()
            if not isinstance(payload, dict):
                return payload

            existing_trace = payload.get("trace")
            if not isinstance(existing_trace, list):
                existing_trace = []

            payload["trace"] = existing_trace + rows
            payload["goal_engine_step_trace"] = rows
            return payload

        setattr(dry_result, "to_dict", to_dict_with_goal_engine_step_trace)

    return dry_result


_aion_previous_attach_goal_engine_manifest_to_dry_result_v9 = attach_goal_engine_manifest_to_dry_result


def attach_goal_engine_manifest_to_dry_result(dry_result, capsule, *, run_id=None):
    result = _aion_previous_attach_goal_engine_manifest_to_dry_result_v9(
        dry_result,
        capsule,
        run_id=run_id,
    )

    manifest = getattr(result, "goal_engine_manifest", None)

    if not isinstance(manifest, dict):
        to_dict = getattr(result, "to_dict", None)
        payload = to_dict() if callable(to_dict) else {}
        if isinstance(payload, dict):
            manifest = payload.get("goal_engine_manifest") or payload.get("goal_engine")

    if isinstance(manifest, dict):
        result = attach_goal_engine_step_trace_rows_to_dry_result(
            result,
            manifest,
            run_id=run_id,
        )

    return result



# AION PATCH: Goal Engine step trace rows final override v10
# Reason:
# build_goal_engine_manifest_for_capsule emits a flat manifest["steps"] list.
# Older step-trace patches expected grouped manifest["goals"], ["experiments"], ["loops"].
# This override reads the real locked manifest shape and attaches rows to both
# goal_engine_step_trace and the normal dry-run trace list.
def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    if not isinstance(manifest, dict):
        return []

    steps = manifest.get("steps")
    if not isinstance(steps, list):
        return []

    resolved_run_id = str(run_id or manifest.get("run_id") or "")
    rows = []

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict):
            continue

        contract = step.get("contract") if isinstance(step.get("contract"), dict) else {}

        node_kind = str(
            step.get("step_type")
            or contract.get("step_type")
            or contract.get("node_kind")
            or contract.get("kind")
            or ""
        ).strip()

        if not node_kind:
            contract_type = str(step.get("contract_type") or contract.get("contract_type") or "")
            if "Experiment" in contract_type:
                node_kind = "experiment"
            elif "Loop" in contract_type:
                node_kind = "loop"
            elif "Outcome" in contract_type:
                node_kind = "outcome_evaluation"
            elif "Reflection" in contract_type or "Learning" in contract_type:
                node_kind = "reflect_learn"
            elif "StateDelta" in contract_type:
                node_kind = "state_delta_accumulator"
            elif "EnvironmentRevalidation" in contract_type:
                node_kind = "environment_revalidation"
            else:
                node_kind = "goal"

        node_id = str(
            contract.get(f"{node_kind}_id")
            or contract.get("goal_id") if node_kind == "goal" else ""
        ).strip()

        if not node_id:
            node_id = str(
                contract.get("experiment_id")
                or contract.get("loop_id")
                or contract.get("outcome_id")
                or contract.get("reflection_id")
                or contract.get("state_delta_id")
                or contract.get("environment_revalidation_id")
                or step.get("node_id")
                or step.get("id")
                or step.get("contract_id")
                or f"goal_engine_step_{index}"
            ).strip()

        title = str(
            contract.get("goal_name")
            or contract.get("title")
            or step.get("title")
            or node_id
        ).strip()

        action_id = {
            "goal": "goal_engine.goal",
            "experiment": "goal_engine.experiment",
            "loop": "goal_engine.loop",
            "outcome_evaluation": "goal_engine.outcome_evaluation",
            "reflect_learn": "goal_engine.reflect_learn",
            "state_delta_accumulator": "goal_engine.state_delta_accumulator",
            "environment_revalidation": "goal_engine.environment_revalidation",
        }.get(node_kind, f"goal_engine.{node_kind}")

        row = {
            "trace_schema_version": "aion.goal_engine.step_trace.v1",
            "schema_version": "aion.goal_engine.step_trace.v1",
            "runtime": "aion_goal_engine",
            "run_id": resolved_run_id,
            "step_index": index,
            "node_id": node_id,
            "id": node_id,
            "node_title": title,
            "title": title,
            "node_kind": node_kind,
            "kind": node_kind,
            "action_id": action_id,
            "status": "dry_run_simulated",
            "dry_run": True,
            "dry_run_only": True,
            "grants_permission": False,
            "would_grant_permission": False,
            "external_write_performed": False,
            "would_write_external": False,
            "bounded_execution": True,
            "blocks_unbounded_execution": True,
            "requires_approval_before_external_write": True,
            "suggested_next_action": "review_before_live_execution",
            "validation_errors": list(step.get("validation_errors") or contract.get("validation_errors") or []),
            "payload": {
                "node_id": node_id,
                "title": title,
                "node_kind": node_kind,
                "action_id": action_id,
                "contract_id": step.get("contract_id"),
                "contract_type": step.get("contract_type") or contract.get("contract_type"),
                "contract": contract,
            },
        }

        rows.append(row)

    return rows


def attach_goal_engine_step_trace_rows_to_dry_result(dry_result, manifest, *, run_id=None):
    rows = build_goal_engine_step_trace_rows(manifest, run_id=run_id)

    if not rows:
        return dry_result

    setattr(dry_result, "goal_engine_step_trace", rows)

    previous_to_dict = getattr(dry_result, "to_dict", None)

    def to_dict_with_goal_engine_step_trace():
        payload = previous_to_dict() if callable(previous_to_dict) else {}
        if not isinstance(payload, dict):
            payload = {}

        payload["goal_engine_step_trace"] = rows

        existing_trace = payload.get("trace")
        if not isinstance(existing_trace, list):
            existing_trace = []

        # Preserve existing trace rows and append Goal Engine rows.
        payload["trace"] = [*existing_trace, *rows]

        return payload

    dry_result.to_dict = to_dict_with_goal_engine_step_trace
    return dry_result


_aion_previous_attach_goal_engine_manifest_to_dry_result_v10 = attach_goal_engine_manifest_to_dry_result

def attach_goal_engine_manifest_to_dry_result(dry_result, capsule, *, run_id=None):
    result = _aion_previous_attach_goal_engine_manifest_to_dry_result_v10(
        dry_result,
        capsule,
        run_id=run_id,
    )

    manifest = getattr(result, "goal_engine_manifest", None)

    if not isinstance(manifest, dict):
        to_dict = getattr(result, "to_dict", None)
        payload = to_dict() if callable(to_dict) else {}
        if isinstance(payload, dict):
            manifest = payload.get("goal_engine_manifest") or payload.get("goal_engine")

    if isinstance(manifest, dict):
        result = attach_goal_engine_step_trace_rows_to_dry_result(
            result,
            manifest,
            run_id=run_id,
        )

    return result



# AION PATCH: Goal Engine step trace source node id priority v11
# The manifest contract may normalize goal_id to goal_001, but step trace rows
# must preserve the original workflow/canvas step id such as goal_1.
_aion_previous_build_goal_engine_step_trace_rows_v11 = build_goal_engine_step_trace_rows

def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_v11(manifest, run_id=run_id)

    if not isinstance(manifest, dict) or not isinstance(rows, list):
        return rows

    steps = manifest.get("steps")
    if not isinstance(steps, list):
        return rows

    for index, row in enumerate(rows):
        if not isinstance(row, dict) or index >= len(steps):
            continue

        source_step = steps[index]
        if not isinstance(source_step, dict):
            continue

        source_node_id = str(
            source_step.get("node_id")
            or source_step.get("id")
            or ""
        ).strip()

        if not source_node_id:
            continue

        row["node_id"] = source_node_id
        row["id"] = source_node_id

        payload = row.get("payload")
        if isinstance(payload, dict):
            payload["node_id"] = source_node_id
            payload["id"] = source_node_id

    return rows


_aion_previous_attach_goal_engine_step_trace_rows_to_dry_result_v11 = attach_goal_engine_step_trace_rows_to_dry_result

def attach_goal_engine_step_trace_rows_to_dry_result(dry_result, manifest, *, run_id=None):
    rows = build_goal_engine_step_trace_rows(manifest, run_id=run_id)

    if not rows:
        return dry_result

    setattr(dry_result, "goal_engine_step_trace", rows)

    previous_to_dict = getattr(dry_result, "to_dict", None)

    def to_dict_with_goal_engine_step_trace():
        payload = previous_to_dict() if callable(previous_to_dict) else {}
        if not isinstance(payload, dict):
            payload = {}

        payload["goal_engine_step_trace"] = rows

        existing_trace = payload.get("trace")
        if not isinstance(existing_trace, list):
            existing_trace = []

        payload["trace"] = [*existing_trace, *rows]
        return payload

    dry_result.to_dict = to_dict_with_goal_engine_step_trace
    return dry_result


_aion_previous_attach_goal_engine_manifest_to_dry_result_v11 = attach_goal_engine_manifest_to_dry_result

def attach_goal_engine_manifest_to_dry_result(dry_result, capsule, *, run_id=None):
    result = _aion_previous_attach_goal_engine_manifest_to_dry_result_v11(
        dry_result,
        capsule,
        run_id=run_id,
    )

    manifest = getattr(result, "goal_engine_manifest", None)

    if not isinstance(manifest, dict):
        to_dict = getattr(result, "to_dict", None)
        payload = to_dict() if callable(to_dict) else {}
        if isinstance(payload, dict):
            manifest = payload.get("goal_engine_manifest") or payload.get("goal_engine")

    if isinstance(manifest, dict):
        result = attach_goal_engine_step_trace_rows_to_dry_result(
            result,
            manifest,
            run_id=run_id,
        )

    return result


# AION PATCH: Preserve source workflow node IDs in Goal Engine manifest v12
# Contract IDs such as goal_001 are internal runtime IDs.
# Dry-run trace rows must preserve the original workflow/canvas step IDs
# such as goal_1, experiment_1, loop_1.
_aion_previous_build_goal_engine_manifest_for_capsule_v12 = build_goal_engine_manifest_for_capsule

def build_goal_engine_manifest_for_capsule(capsule, *, run_id=None):
    manifest = _aion_previous_build_goal_engine_manifest_for_capsule_v12(
        capsule,
        run_id=run_id,
    )

    if not isinstance(manifest, dict):
        return manifest

    capsule_steps = []
    if isinstance(capsule, dict):
        capsule_steps = capsule.get("steps") or []
    else:
        capsule_steps = getattr(capsule, "steps", []) or []

    if not isinstance(capsule_steps, list):
        capsule_steps = []

    manifest_steps = manifest.get("steps")
    if not isinstance(manifest_steps, list):
        return manifest

    for index, manifest_step in enumerate(manifest_steps):
        if not isinstance(manifest_step, dict):
            continue
        if index >= len(capsule_steps):
            continue

        source_step = capsule_steps[index]
        if not isinstance(source_step, dict):
            source_step = {
                "id": getattr(source_step, "id", None) or getattr(source_step, "step_id", None),
                "node_id": getattr(source_step, "node_id", None),
                "title": getattr(source_step, "title", None) or getattr(source_step, "name", None),
                "action_id": getattr(source_step, "action_id", None),
            }

        source_node_id = str(
            source_step.get("node_id")
            or source_step.get("id")
            or source_step.get("step_id")
            or ""
        ).strip()

        source_title = str(
            source_step.get("title")
            or source_step.get("name")
            or source_node_id
            or ""
        ).strip()

        source_action_id = str(
            source_step.get("action_id")
            or source_step.get("action")
            or source_step.get("type")
            or ""
        ).strip()

        if source_node_id:
            manifest_step["source_node_id"] = source_node_id
            manifest_step["node_id"] = source_node_id
            manifest_step["id"] = source_node_id

        if source_title:
            manifest_step["source_title"] = source_title
            manifest_step["title"] = source_title

        if source_action_id:
            manifest_step["source_action_id"] = source_action_id
            manifest_step["action_id"] = source_action_id

    return manifest


# AION PATCH: Goal Engine step trace must prefer manifest source_node_id v12
_aion_previous_build_goal_engine_step_trace_rows_v12 = build_goal_engine_step_trace_rows

def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_v12(
        manifest,
        run_id=run_id,
    )

    if not isinstance(rows, list) or not isinstance(manifest, dict):
        return rows

    steps = manifest.get("steps")
    if not isinstance(steps, list):
        return rows

    for index, row in enumerate(rows):
        if not isinstance(row, dict) or index >= len(steps):
            continue

        step = steps[index]
        if not isinstance(step, dict):
            continue

        source_node_id = str(
            step.get("source_node_id")
            or step.get("node_id")
            or step.get("id")
            or ""
        ).strip()

        source_title = str(
            step.get("source_title")
            or step.get("title")
            or source_node_id
            or ""
        ).strip()

        source_action_id = str(
            step.get("source_action_id")
            or step.get("action_id")
            or row.get("action_id")
            or ""
        ).strip()

        if source_node_id:
            row["node_id"] = source_node_id
            row["id"] = source_node_id

        if source_title:
            row["node_title"] = source_title
            row["title"] = source_title

        if source_action_id:
            row["action_id"] = source_action_id

        payload = row.get("payload")
        if isinstance(payload, dict):
            if source_node_id:
                payload["node_id"] = source_node_id
                payload["id"] = source_node_id
            if source_title:
                payload["title"] = source_title
            if source_action_id:
                payload["action_id"] = source_action_id

    return rows


# AION PATCH: Goal Engine loop iteration preview v1
GOAL_ENGINE_LOOP_ITERATION_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.loop_iteration_preview.v1"
GOAL_ENGINE_MAX_DRY_RUN_LOOP_ITERATIONS = 100


def _aion_goal_engine_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def build_goal_engine_loop_iteration_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}

    raw_max_iterations = (
        payload.get("max_iterations")
        or nested.get("max_iterations")
        or contract.get("max_iterations")
        or config.get("max_iterations")
        or 1
    )

    requested_iterations = max(0, _aion_goal_engine_int(raw_max_iterations, 1))
    max_iterations = min(requested_iterations, GOAL_ENGINE_MAX_DRY_RUN_LOOP_ITERATIONS)
    would_run_iterations = max_iterations

    node_id = (
        payload.get("node_id")
        or payload.get("id")
        or nested.get("node_id")
        or nested.get("id")
        or contract.get("loop_id")
        or "goal_engine_loop"
    )

    return {
        "schema_version": GOAL_ENGINE_LOOP_ITERATION_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or payload.get("run_id") or "",
        "node_id": str(node_id),
        "max_iterations": max_iterations,
        "requested_iterations": requested_iterations,
        "current_iteration": 0,
        "would_run_iterations": would_run_iterations,
        "kill_switch_available": True,
        "bounded_execution": True,
        "unbounded_execution_blocked": True,
        "external_write_performed": False,
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
    }


_aion_previous_build_goal_engine_step_trace_rows_loop_preview_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_loop_preview_v1(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        if isinstance(row, dict) and str(row.get("node_kind") or row.get("kind") or "") == "loop":
            preview = build_goal_engine_loop_iteration_preview(row, run_id=run_id)
            row = {
                **row,
                "loop_iteration_preview": preview,
                "bounded_execution": True,
                "unbounded_execution_blocked": True,
            }
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row["payload"] = {
                **payload,
                "loop_iteration_preview": preview,
            }
        enriched.append(row)

    return enriched


# AION PATCH: Goal Engine loop iteration preview source-step fix v2
_aion_previous_build_goal_engine_step_trace_rows_loop_preview_source_v2 = build_goal_engine_step_trace_rows


def _aion_goal_engine_manifest_steps_by_node_id(manifest):
    if not isinstance(manifest, dict):
        return {}

    steps = manifest.get("steps")
    if not isinstance(steps, list):
        return {}

    out = {}
    for step in steps:
        if not isinstance(step, dict):
            continue

        contract = step.get("contract") if isinstance(step.get("contract"), dict) else {}

        candidates = [
            step.get("node_id"),
            step.get("id"),
            step.get("step_id"),
            step.get("contract_id"),
            contract.get("node_id"),
            contract.get("id"),
            contract.get("goal_id"),
            contract.get("experiment_id"),
            contract.get("loop_id"),
            contract.get("outcome_id"),
            contract.get("evaluation_id"),
        ]

        for candidate in candidates:
            if candidate:
                out[str(candidate)] = step

    return out


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_loop_preview_source_v2(
        manifest,
        run_id=run_id,
    )

    source_steps = _aion_goal_engine_manifest_steps_by_node_id(manifest)
    enriched = []

    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        source_step = (
            source_steps.get(str(row.get("node_id") or ""))
            or source_steps.get(str(row.get("id") or ""))
            or {}
        )

        source_contract = (
            source_step.get("contract")
            if isinstance(source_step.get("contract"), dict)
            else {}
        )

        if source_step:
            row = {
                **row,
                "source_manifest_step": source_step,
                "contract": {
                    **(row.get("contract") if isinstance(row.get("contract"), dict) else {}),
                    **source_contract,
                },
            }

        if str(row.get("node_kind") or row.get("kind") or "") == "loop":
            preview_source = {
                **row,
                "contract": {
                    **source_contract,
                    **(row.get("contract") if isinstance(row.get("contract"), dict) else {}),
                },
            }

            preview = build_goal_engine_loop_iteration_preview(
                preview_source,
                run_id=run_id,
            )

            row = {
                **row,
                "loop_iteration_preview": preview,
                "bounded_execution": True,
                "unbounded_execution_blocked": True,
            }

            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row["payload"] = {
                **payload,
                "loop_iteration_preview": preview,
            }

        enriched.append(row)

    return enriched


# AION PATCH: Goal Engine experiment variant preview v1
GOAL_ENGINE_EXPERIMENT_VARIANT_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.experiment_variant_preview.v1"


def _aion_goal_engine_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _aion_goal_engine_variant_labels(value):
    if isinstance(value, list):
        labels = [str(item).strip() for item in value if str(item).strip()]
        return labels or ["Variant A", "Variant B"]

    if isinstance(value, str):
        labels = [
            part.strip()
            for part in value.replace("|", "\n").replace(",", "\n").splitlines()
            if part.strip()
        ]
        return labels or ["Variant A", "Variant B"]

    return ["Variant A", "Variant B"]


def build_goal_engine_experiment_variant_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}

    variants = _aion_goal_engine_variant_labels(
        payload.get("variants")
        or nested.get("variants")
        or contract.get("variants")
        or config.get("variants")
    )

    allocation = round(100 / max(len(variants), 1), 4)
    variant_rows = [
        {
            "index": index,
            "variant_id": f"variant_{index + 1}",
            "label": label,
            "allocation_percent": allocation,
            "sample_count": 0,
            "score": None,
            "winner": False,
            "dry_run_only": True,
            "external_write_performed": False,
        }
        for index, label in enumerate(variants)
    ]

    node_id = (
        payload.get("node_id")
        or payload.get("id")
        or nested.get("node_id")
        or nested.get("id")
        or contract.get("experiment_id")
        or "goal_engine_experiment"
    )

    winner_policy = str(
        payload.get("winner_policy")
        or nested.get("winner_policy")
        or contract.get("winner_policy")
        or config.get("winner_policy")
        or "manual"
    )

    return {
        "schema_version": GOAL_ENGINE_EXPERIMENT_VARIANT_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or payload.get("run_id") or "",
        "node_id": str(node_id),
        "metric": (
            payload.get("metric")
            or nested.get("metric")
            or contract.get("metric")
            or config.get("metric")
            or None
        ),
        "variants": variant_rows,
        "winner_policy": winner_policy,
        "requires_manual_winner": winner_policy == "manual",
        "manual_review_required_before_winner": True,
        "auto_allocate_full_winner": False,
        "exploration_factor": _aion_goal_engine_float(
            payload.get("exploration_factor")
            or nested.get("exploration_factor")
            or contract.get("exploration_factor")
            or config.get("exploration_factor"),
            0.15,
        ),
        "min_exploration_floor": _aion_goal_engine_float(
            payload.get("min_exploration_floor")
            or nested.get("min_exploration_floor")
            or contract.get("min_exploration_floor")
            or config.get("min_exploration_floor"),
            0.05,
        ),
        "confidence_threshold": _aion_goal_engine_float(
            payload.get("confidence_threshold")
            or nested.get("confidence_threshold")
            or contract.get("confidence_threshold")
            or config.get("confidence_threshold"),
            0.95,
        ),
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
        "external_write_performed": False,
        "suggested_next_action": "collect_evidence_then_manual_review",
    }


_aion_previous_build_goal_engine_step_trace_rows_experiment_preview_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_experiment_preview_v1(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        if isinstance(row, dict) and str(row.get("node_kind") or row.get("kind") or "") == "experiment":
            preview = build_goal_engine_experiment_variant_preview(row, run_id=run_id)
            row = {
                **row,
                "experiment_variant_preview": preview,
                "dry_run_only": True,
                "grants_permission": False,
                "would_grant_permission": False,
                "external_write_performed": False,
            }
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row["payload"] = {
                **payload,
                "experiment_variant_preview": preview,
            }
        enriched.append(row)

    return enriched


# AION PATCH: Goal Engine outcome score preview v1
GOAL_ENGINE_OUTCOME_SCORE_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.outcome_score_preview.v1"


def _aion_goal_engine_num(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _aion_goal_engine_list(value):
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def build_goal_engine_outcome_score_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}

    node_id = (
        payload.get("node_id")
        or payload.get("id")
        or nested.get("node_id")
        or nested.get("id")
        or contract.get("outcome_id")
        or "goal_engine_outcome"
    )

    metric_target = _aion_goal_engine_num(
        payload.get("metric_target")
        or nested.get("metric_target")
        or contract.get("metric_target")
        or config.get("metric_target")
        or contract.get("target_value")
        or config.get("target_value"),
        1.0,
    )

    metric_actual = _aion_goal_engine_num(
        payload.get("metric_actual")
        or nested.get("metric_actual")
        or contract.get("metric_actual")
        or config.get("metric_actual"),
        0.0,
    )

    denominator = metric_target if metric_target > 0 else 1.0
    outcome_score = max(0.0, min(metric_actual / denominator, 1.0))

    evidence_refs = _aion_goal_engine_list(
        payload.get("evidence_refs")
        or nested.get("evidence_refs")
        or contract.get("evidence_refs")
        or config.get("evidence_refs")
    )

    return {
        "schema_version": GOAL_ENGINE_OUTCOME_SCORE_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or payload.get("run_id") or "",
        "node_id": str(node_id),
        "metric_name": (
            payload.get("metric_name")
            or nested.get("metric_name")
            or contract.get("metric_name")
            or config.get("metric_name")
            or contract.get("target_metric")
            or config.get("target_metric")
            or "outcome_score"
        ),
        "metric_target": int(metric_target) if metric_target.is_integer() else metric_target,
        "metric_actual": int(metric_actual) if metric_actual.is_integer() else metric_actual,
        "outcome_score": round(outcome_score, 4),
        "confidence": _aion_goal_engine_num(
            payload.get("confidence")
            or nested.get("confidence")
            or contract.get("confidence")
            or config.get("confidence"),
            0.0,
        ),
        "source": (
            payload.get("source")
            or nested.get("source")
            or contract.get("source")
            or config.get("source")
            or "manual_confirmation"
        ),
        "cost": _aion_goal_engine_num(
            payload.get("cost")
            or nested.get("cost")
            or contract.get("cost")
            or config.get("cost"),
            0.0,
        ),
        "time_to_result": (
            payload.get("time_to_result")
            or nested.get("time_to_result")
            or contract.get("time_to_result")
            or config.get("time_to_result")
        ),
        "evidence_refs": evidence_refs,
        "requires_evidence": True,
        "completed_workflow_is_not_success_without_evidence": True,
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
        "external_write_performed": False,
        "suggested_next_action": "collect_or_confirm_evidence",
    }


_aion_previous_build_goal_engine_step_trace_rows_outcome_preview_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_outcome_preview_v1(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        if isinstance(row, dict) and str(row.get("node_kind") or row.get("kind") or "") == "outcome_evaluation":
            preview = build_goal_engine_outcome_score_preview(row, run_id=run_id)
            row = {
                **row,
                "outcome_score_preview": preview,
                "outcome_score": preview["outcome_score"],
                "requires_evidence": True,
                "completed_workflow_is_not_success_without_evidence": True,
            }
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row["payload"] = {
                **payload,
                "outcome_score_preview": preview,
            }
        enriched.append(row)

    return enriched


# AION PATCH: Goal Engine outcome score preview source-step fix v2

_aion_previous_build_goal_engine_step_trace_rows_outcome_source_fix_v2 = build_goal_engine_step_trace_rows


def _aion_goal_engine_find_source_step_for_row(manifest, row):
    if not isinstance(manifest, dict) or not isinstance(row, dict):
        return {}

    source_steps = manifest.get("source_steps")
    if not isinstance(source_steps, list):
        source_steps = manifest.get("capsule_steps")
    if not isinstance(source_steps, list):
        source_steps = manifest.get("_source_steps")
    if not isinstance(source_steps, list):
        source_steps = []

    row_id = str(row.get("node_id") or row.get("id") or "")
    row_action = str(row.get("action_id") or "")

    for step in source_steps:
        if not isinstance(step, dict):
            continue
        step_id = str(step.get("id") or step.get("node_id") or "")
        step_action = str(step.get("action_id") or step.get("action") or "")
        if row_id and step_id == row_id:
            return step
        if row_action and step_action == row_action and step_action == "goal_engine.outcome_evaluation":
            return step

    return {}


def _aion_goal_engine_enrich_outcome_row_from_source(manifest, row):
    if not isinstance(row, dict):
        return row

    if str(row.get("node_kind") or row.get("kind") or "") != "outcome_evaluation":
        return row

    source_step = _aion_goal_engine_find_source_step_for_row(manifest, row)
    source_config = source_step.get("config") if isinstance(source_step.get("config"), dict) else {}

    if not source_config:
        return row

    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    config = row.get("config") if isinstance(row.get("config"), dict) else {}

    merged_config = {
        **source_config,
        **config,
    }

    merged_payload = {
        **source_config,
        **payload,
    }

    return {
        **row,
        "config": merged_config,
        "payload": merged_payload,
        "metric_name": row.get("metric_name") or source_config.get("metric_name"),
        "metric_target": row.get("metric_target") or source_config.get("metric_target"),
        "metric_actual": row.get("metric_actual") if row.get("metric_actual") is not None else source_config.get("metric_actual"),
        "confidence": row.get("confidence") if row.get("confidence") is not None else source_config.get("confidence"),
        "source": row.get("source") or source_config.get("source"),
        "cost": row.get("cost") if row.get("cost") is not None else source_config.get("cost"),
        "time_to_result": row.get("time_to_result") if row.get("time_to_result") is not None else source_config.get("time_to_result"),
        "evidence_refs": row.get("evidence_refs") or source_config.get("evidence_refs") or [],
    }


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_outcome_source_fix_v2(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        row = _aion_goal_engine_enrich_outcome_row_from_source(manifest, row)

        if isinstance(row, dict) and str(row.get("node_kind") or row.get("kind") or "") == "outcome_evaluation":
            preview = build_goal_engine_outcome_score_preview(row, run_id=run_id)
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row = {
                **row,
                "outcome_score_preview": preview,
                "outcome_score": preview["outcome_score"],
                "requires_evidence": True,
                "completed_workflow_is_not_success_without_evidence": True,
                "payload": {
                    **payload,
                    "outcome_score_preview": preview,
                },
            }

        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine outcome score preview hard override v3
GOAL_ENGINE_OUTCOME_SCORE_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.outcome_score_preview.v1"


def _aion_goal_engine_float(value, default=0.0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except Exception:
        return default


def _aion_goal_engine_list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None or value == "":
        return []
    return [str(value)]


def build_goal_engine_outcome_score_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}

    metric_name = (
        payload.get("metric_name")
        or nested.get("metric_name")
        or config.get("metric_name")
        or contract.get("metric_name")
        or payload.get("target_metric")
        or nested.get("target_metric")
        or config.get("target_metric")
        or contract.get("target_metric")
        or "outcome_score"
    )

    metric_target = (
        payload.get("metric_target")
        or nested.get("metric_target")
        or config.get("metric_target")
        or contract.get("metric_target")
        or payload.get("target_value")
        or nested.get("target_value")
        or config.get("target_value")
        or contract.get("target_value")
        or 1
    )

    metric_actual = (
        payload.get("metric_actual")
        if payload.get("metric_actual") is not None
        else nested.get("metric_actual")
        if nested.get("metric_actual") is not None
        else config.get("metric_actual")
        if config.get("metric_actual") is not None
        else contract.get("metric_actual")
    )

    target_num = _aion_goal_engine_float(metric_target, 1.0)
    actual_num = _aion_goal_engine_float(metric_actual, 0.0)

    if target_num <= 0:
        outcome_score = 0.0
    else:
        outcome_score = max(0.0, min(1.0, actual_num / target_num))

    evidence_refs = (
        payload.get("evidence_refs")
        or nested.get("evidence_refs")
        or config.get("evidence_refs")
        or contract.get("evidence_refs")
        or []
    )

    return {
        "schema_version": GOAL_ENGINE_OUTCOME_SCORE_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or payload.get("run_id") or "",
        "node_id": str(payload.get("node_id") or payload.get("id") or nested.get("node_id") or nested.get("id") or "goal_engine_outcome"),
        "metric_name": str(metric_name),
        "metric_target": metric_target,
        "metric_actual": metric_actual,
        "outcome_score": outcome_score,
        "confidence": _aion_goal_engine_float(
            payload.get("confidence")
            if payload.get("confidence") is not None
            else nested.get("confidence")
            if nested.get("confidence") is not None
            else config.get("confidence")
            if config.get("confidence") is not None
            else contract.get("confidence"),
            0.0,
        ),
        "source": str(payload.get("source") or nested.get("source") or config.get("source") or contract.get("source") or "manual"),
        "cost": payload.get("cost") if payload.get("cost") is not None else nested.get("cost") if nested.get("cost") is not None else config.get("cost") if config.get("cost") is not None else contract.get("cost"),
        "time_to_result": payload.get("time_to_result") if payload.get("time_to_result") is not None else nested.get("time_to_result") if nested.get("time_to_result") is not None else config.get("time_to_result") if config.get("time_to_result") is not None else contract.get("time_to_result"),
        "evidence_refs": _aion_goal_engine_list(evidence_refs),
        "requires_evidence": True,
        "manual_confirmation_required": True,
        "completed_workflow_is_not_success_without_evidence": True,
        "external_write_performed": False,
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
    }


_aion_previous_build_goal_engine_step_trace_rows_outcome_hard_override_v3 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_outcome_hard_override_v3(
        manifest,
        run_id=run_id,
    )

    source_steps = manifest.get("source_steps") if isinstance(manifest, dict) else None
    if not isinstance(source_steps, list):
        source_steps = manifest.get("capsule_steps") if isinstance(manifest, dict) else None
    if not isinstance(source_steps, list):
        source_steps = manifest.get("_source_steps") if isinstance(manifest, dict) else None
    if not isinstance(source_steps, list):
        source_steps = []

    enriched = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        if str(row.get("node_kind") or row.get("kind") or "") != "outcome_evaluation":
            enriched.append(row)
            continue

        source_step = {}
        row_id = str(row.get("node_id") or row.get("id") or "")
        for step in source_steps:
            if not isinstance(step, dict):
                continue
            step_id = str(step.get("id") or step.get("node_id") or "")
            step_action = str(step.get("action_id") or step.get("action") or "")
            if step_id == row_id or step_action == "goal_engine.outcome_evaluation":
                source_step = step
                break

        source_config = source_step.get("config") if isinstance(source_step.get("config"), dict) else {}
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        config = row.get("config") if isinstance(row.get("config"), dict) else {}

        row = {
            **source_config,
            **row,
            "config": {**source_config, **config},
            "payload": {**source_config, **payload},
        }

        preview = build_goal_engine_outcome_score_preview(row, run_id=run_id)
        row["outcome_score_preview"] = preview
        row["outcome_score"] = preview["outcome_score"]
        row["requires_evidence"] = True
        row["completed_workflow_is_not_success_without_evidence"] = True
        row["payload"] = {
            **row.get("payload", {}),
            "outcome_score_preview": preview,
        }

        enriched.append(row)

    return enriched



# AION PATCH: Goal Engine source step config preservation v1
_aion_previous_build_goal_engine_manifest_for_capsule_source_config_v1 = build_goal_engine_manifest_for_capsule


def _aion_goal_engine_source_step_id(step):
    if isinstance(step, dict):
        return str(
            step.get("id")
            or step.get("node_id")
            or step.get("step_id")
            or step.get("action_id")
            or ""
        )
    return str(
        getattr(step, "id", None)
        or getattr(step, "node_id", None)
        or getattr(step, "step_id", None)
        or getattr(step, "action_id", None)
        or ""
    )


def _aion_goal_engine_source_step_action_id(step):
    if isinstance(step, dict):
        return str(
            step.get("action_id")
            or step.get("action")
            or step.get("type")
            or step.get("kind")
            or ""
        )
    return str(
        getattr(step, "action_id", None)
        or getattr(step, "action", None)
        or getattr(step, "type", None)
        or getattr(step, "kind", None)
        or ""
    )


def _aion_goal_engine_source_step_config(step):
    if isinstance(step, dict):
        config = step.get("config")
        return dict(config) if isinstance(config, dict) else {}
    config = getattr(step, "config", None)
    return dict(config) if isinstance(config, dict) else {}


def _aion_goal_engine_source_step_title(step):
    if isinstance(step, dict):
        return str(step.get("title") or step.get("name") or step.get("label") or "")
    return str(
        getattr(step, "title", None)
        or getattr(step, "name", None)
        or getattr(step, "label", None)
        or ""
    )


def _aion_goal_engine_normalise_source_steps(capsule):
    if isinstance(capsule, dict):
        source_steps = capsule.get("steps") if isinstance(capsule.get("steps"), list) else []
    else:
        source_steps = getattr(capsule, "steps", []) or []

    normalised = []
    for index, step in enumerate(source_steps):
        step_id = _aion_goal_engine_source_step_id(step)
        action_id = _aion_goal_engine_source_step_action_id(step)
        config = _aion_goal_engine_source_step_config(step)

        normalised.append({
            "index": index,
            "id": step_id,
            "node_id": step_id,
            "step_id": step_id,
            "title": _aion_goal_engine_source_step_title(step),
            "action_id": action_id,
            "config": config,
        })

    return normalised


def _aion_goal_engine_match_source_step(manifest_step, source_steps):
    if not isinstance(manifest_step, dict):
        return None

    manifest_index = manifest_step.get("index")
    manifest_contract = manifest_step.get("contract") if isinstance(manifest_step.get("contract"), dict) else {}

    candidate_ids = {
        str(manifest_step.get("node_id") or ""),
        str(manifest_step.get("id") or ""),
        str(manifest_step.get("step_id") or ""),
        str(manifest_step.get("contract_id") or ""),
        str(manifest_contract.get("goal_id") or ""),
        str(manifest_contract.get("experiment_id") or ""),
        str(manifest_contract.get("loop_id") or ""),
        str(manifest_contract.get("outcome_id") or ""),
        str(manifest_contract.get("evaluation_id") or ""),
    }
    candidate_ids.discard("")

    for source in source_steps:
        if source.get("node_id") in candidate_ids or source.get("id") in candidate_ids:
            return source

    if isinstance(manifest_index, int) and 0 <= manifest_index < len(source_steps):
        return source_steps[manifest_index]

    return None


def build_goal_engine_manifest_for_capsule(capsule, *, run_id=None):
    manifest = _aion_previous_build_goal_engine_manifest_for_capsule_source_config_v1(
        capsule,
        run_id=run_id,
    )

    if not isinstance(manifest, dict):
        return manifest

    source_steps = _aion_goal_engine_normalise_source_steps(capsule)
    manifest["source_steps"] = source_steps

    steps = manifest.get("steps")
    if not isinstance(steps, list):
        return manifest

    for manifest_step in steps:
        if not isinstance(manifest_step, dict):
            continue

        source = _aion_goal_engine_match_source_step(manifest_step, source_steps)
        if not isinstance(source, dict):
            continue

        source_config = source.get("config") if isinstance(source.get("config"), dict) else {}
        contract = manifest_step.get("contract") if isinstance(manifest_step.get("contract"), dict) else {}

        # Preserve the original canvas/capsule identifiers beside generated contract IDs.
        manifest_step.setdefault("source_node_id", source.get("node_id") or source.get("id") or "")
        manifest_step.setdefault("node_id", source.get("node_id") or source.get("id") or manifest_step.get("node_id") or "")
        manifest_step.setdefault("id", source.get("id") or source.get("node_id") or manifest_step.get("id") or "")
        manifest_step.setdefault("action_id", source.get("action_id") or "")
        manifest_step.setdefault("title", source.get("title") or manifest_step.get("title") or "")

        # This is the key fix: keep the original step config so previews can use
        # metric_name, metric_target, metric_actual, evidence_refs, variants, max_iterations, etc.
        manifest_step["source_config"] = source_config
        manifest_step["config"] = {
            **source_config,
            **(manifest_step.get("config") if isinstance(manifest_step.get("config"), dict) else {}),
        }

        if isinstance(contract, dict):
            contract.setdefault("source_node_id", source.get("node_id") or source.get("id") or "")
            contract.setdefault("source_config", source_config)

            # Fill outcome/evaluation preview fields from source config when the
            # contract builder defaulted to generic outcome_score values.
            for key in (
                "metric_name",
                "metric",
                "metric_target",
                "metric_actual",
                "evidence_refs",
                "evidence_sources",
                "confidence",
                "source",
                "time_to_result",
                "cost",
            ):
                if key in source_config and (
                    contract.get(key) in (None, "", [], {})
                    or (key in {"metric_name", "metric"} and contract.get(key) == "outcome_score")
                ):
                    contract[key] = source_config[key]

    return manifest


# AION PATCH: Goal Engine outcome score preview source-config repair v2
_aion_previous_build_goal_engine_outcome_score_preview_source_config_v2 = build_goal_engine_outcome_score_preview


def build_goal_engine_outcome_score_preview(row, *, run_id=None):
    preview = _aion_previous_build_goal_engine_outcome_score_preview_source_config_v2(
        row,
        run_id=run_id,
    )

    if not isinstance(preview, dict):
        return preview

    payload = row if isinstance(row, dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}

    merged = {
        **contract,
        **nested,
        **config,
        **source_config,
    }

    metric_name = (
        merged.get("metric_name")
        or merged.get("metric")
        or merged.get("target_metric")
        or preview.get("metric_name")
        or "outcome_score"
    )

    evidence_refs = (
        merged.get("evidence_refs")
        or merged.get("evidence_sources")
        or preview.get("evidence_refs")
        or []
    )

    if isinstance(evidence_refs, str):
        evidence_refs = [evidence_refs] if evidence_refs.strip() else []

    preview["metric_name"] = str(metric_name)
    preview["metric"] = str(metric_name)
    preview["metric_target"] = merged.get("metric_target", preview.get("metric_target"))
    preview["metric_actual"] = merged.get("metric_actual", preview.get("metric_actual"))
    preview["evidence_refs"] = list(evidence_refs) if isinstance(evidence_refs, list) else []
    preview["manual_confirmation_required"] = True
    preview["external_write_performed"] = False
    preview["dry_run_only"] = True
    preview["grants_permission"] = False
    preview["would_grant_permission"] = False

    return preview

# AION PATCH: Goal Engine checkpoint + state-delta preview v1
GOAL_ENGINE_CHECKPOINT_RESUME_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.checkpoint_resume_preview.v1"
GOAL_ENGINE_STATE_DELTA_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.state_delta_preview.v1"
GOAL_ENGINE_ENVIRONMENT_REVALIDATION_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.environment_revalidation_preview.v1"


def _aion_goal_engine_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _aion_goal_engine_row_config(row):
    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}

    return {
        **contract,
        **nested,
        **config,
        **source_config,
    }


def build_goal_engine_checkpoint_resume_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    merged = _aion_goal_engine_row_config(payload)

    node_id = str(payload.get("node_id") or payload.get("id") or merged.get("node_id") or "goal_engine_checkpoint")

    checkpoint_every = _aion_goal_engine_int(merged.get("checkpoint_every") or 1, 1)
    max_checkpoint_size = _aion_goal_engine_int(merged.get("max_checkpoint_size") or 4096, 4096)

    return {
        "schema_version": GOAL_ENGINE_CHECKPOINT_RESUME_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or payload.get("run_id") or "",
        "node_id": node_id,
        "checkpoint_required": True,
        "checkpoint_every": max(1, checkpoint_every),
        "max_checkpoint_size": max(256, min(max_checkpoint_size, 262144)),
        "checkpoint_summary": str(
            merged.get("checkpoint_summary")
            or "Dry-run checkpoint preview. Only compact loop state is persisted."
        ),
        "checkpoint_compaction": True,
        "prune_obsolete_checkpoints": True,
        "hydrate_resume_from_checkpoint": True,
        "resume_requires_environment_revalidation": True,
        "revalidate_approval_before_resume": True,
        "revalidate_vault_before_resume": True,
        "revalidate_connectors_before_resume": True,
        "revalidate_parent_goal_before_resume": True,
        "stop_if_external_state_changed": True,
        "dry_run_only": True,
        "external_write_performed": False,
        "grants_permission": False,
        "would_grant_permission": False,
    }


def build_goal_engine_state_delta_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    merged = _aion_goal_engine_row_config(payload)

    node_id = str(payload.get("node_id") or payload.get("id") or merged.get("node_id") or "goal_engine_state_delta")
    max_delta_bytes = _aion_goal_engine_int(merged.get("max_delta_bytes") or 4096, 4096)
    snapshot = merged.get("loop_context_snapshot") if isinstance(merged.get("loop_context_snapshot"), dict) else {}

    return {
        "schema_version": GOAL_ENGINE_STATE_DELTA_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or payload.get("run_id") or "",
        "node_id": node_id,
        "state_delta_strategy": str(merged.get("state_delta_strategy") or "bounded_delta_only"),
        "max_delta_bytes": max(256, min(max_delta_bytes, 262144)),
        "loop_context_snapshot": snapshot,
        "append_full_history": False,
        "bounded_delta_only": True,
        "checkpoint_compaction": True,
        "prune_obsolete_deltas": True,
        "dry_run_only": True,
        "external_write_performed": False,
        "grants_permission": False,
        "would_grant_permission": False,
    }


def build_goal_engine_environment_revalidation_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    merged = _aion_goal_engine_row_config(payload)

    node_id = str(payload.get("node_id") or payload.get("id") or merged.get("node_id") or "goal_engine_environment_revalidation")

    return {
        "schema_version": GOAL_ENGINE_ENVIRONMENT_REVALIDATION_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or payload.get("run_id") or "",
        "node_id": node_id,
        "revalidate_approval": _aion_goal_engine_bool(merged.get("revalidate_approval"), True),
        "revalidate_vault": _aion_goal_engine_bool(merged.get("revalidate_vault"), True),
        "revalidate_connectors": _aion_goal_engine_bool(merged.get("revalidate_connectors"), True),
        "revalidate_parent_goal": _aion_goal_engine_bool(merged.get("revalidate_parent_goal"), True),
        "stop_if_external_state_changed": True,
        "resume_allowed_without_revalidation": False,
        "dry_run_only": True,
        "external_write_performed": False,
        "grants_permission": False,
        "would_grant_permission": False,
    }


_aion_previous_build_goal_engine_step_trace_rows_checkpoint_state_delta_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_checkpoint_state_delta_v1(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        node_kind = str(row.get("node_kind") or row.get("kind") or row.get("step_type") or "").lower()
        action_id = str(row.get("action_id") or "").lower()

        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}

        if node_kind == "loop" or action_id == "goal_engine.loop":
            checkpoint_preview = build_goal_engine_checkpoint_resume_preview(row, run_id=run_id)
            row = {
                **row,
                "checkpoint_resume_preview": checkpoint_preview,
            }
            payload = {
                **payload,
                "checkpoint_resume_preview": checkpoint_preview,
            }

        if (
            node_kind in {"state_delta", "state_delta_accumulator"}
            or action_id == "goal_engine.state_delta_accumulator"
        ):
            state_delta_preview = build_goal_engine_state_delta_preview(row, run_id=run_id)
            row = {
                **row,
                "state_delta_preview": state_delta_preview,
            }
            payload = {
                **payload,
                "state_delta_preview": state_delta_preview,
            }

        if (
            node_kind in {"environment_revalidation", "revalidation"}
            or action_id == "goal_engine.environment_revalidation"
        ):
            revalidation_preview = build_goal_engine_environment_revalidation_preview(row, run_id=run_id)
            row = {
                **row,
                "environment_revalidation_preview": revalidation_preview,
            }
            payload = {
                **payload,
                "environment_revalidation_preview": revalidation_preview,
            }

        row["payload"] = payload
        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine checkpoint/state-delta source-config repair v2
def _aion_goal_engine_deep_row_config_v2(row):
    payload = row if isinstance(row, dict) else {}

    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}

    source_step = payload.get("source_step") if isinstance(payload.get("source_step"), dict) else {}
    source_step_config = (
        source_step.get("config") if isinstance(source_step.get("config"), dict) else {}
    )

    nested_source_config = (
        nested.get("source_config") if isinstance(nested.get("source_config"), dict) else {}
    )
    nested_source_step = nested.get("source_step") if isinstance(nested.get("source_step"), dict) else {}
    nested_source_step_config = (
        nested_source_step.get("config")
        if isinstance(nested_source_step.get("config"), dict)
        else {}
    )

    contract_source_config = (
        contract.get("source_config") if isinstance(contract.get("source_config"), dict) else {}
    )

    return {
        **contract,
        **contract_source_config,
        **nested,
        **nested_source_config,
        **nested_source_step_config,
        **config,
        **source_step_config,
        **source_config,
    }


_aion_previous_build_goal_engine_checkpoint_resume_preview_source_config_v2 = build_goal_engine_checkpoint_resume_preview


def build_goal_engine_checkpoint_resume_preview(row, *, run_id=None):
    preview = _aion_previous_build_goal_engine_checkpoint_resume_preview_source_config_v2(
        row,
        run_id=run_id,
    )

    payload = row if isinstance(row, dict) else {}
    merged = _aion_goal_engine_deep_row_config_v2(payload)

    if "checkpoint_every" in merged:
        preview["checkpoint_every"] = max(
            1,
            _aion_goal_engine_int(merged.get("checkpoint_every"), preview.get("checkpoint_every", 1)),
        )

    if "max_checkpoint_size" in merged:
        preview["max_checkpoint_size"] = max(
            256,
            min(
                _aion_goal_engine_int(
                    merged.get("max_checkpoint_size"),
                    preview.get("max_checkpoint_size", 4096),
                ),
                262144,
            ),
        )

    if merged.get("checkpoint_summary"):
        preview["checkpoint_summary"] = str(merged.get("checkpoint_summary"))

    return preview


_aion_previous_build_goal_engine_state_delta_preview_source_config_v2 = build_goal_engine_state_delta_preview


def build_goal_engine_state_delta_preview(row, *, run_id=None):
    preview = _aion_previous_build_goal_engine_state_delta_preview_source_config_v2(
        row,
        run_id=run_id,
    )

    payload = row if isinstance(row, dict) else {}
    merged = _aion_goal_engine_deep_row_config_v2(payload)

    if "max_delta_bytes" in merged:
        preview["max_delta_bytes"] = max(
            256,
            min(
                _aion_goal_engine_int(
                    merged.get("max_delta_bytes"),
                    preview.get("max_delta_bytes", 4096),
                ),
                262144,
            ),
        )

    if merged.get("state_delta_strategy"):
        preview["state_delta_strategy"] = str(merged.get("state_delta_strategy"))

    if isinstance(merged.get("loop_context_snapshot"), dict):
        preview["loop_context_snapshot"] = dict(merged.get("loop_context_snapshot"))

    preview["append_full_history"] = False
    preview["bounded_delta_only"] = True
    preview["external_write_performed"] = False

    return preview

# AION PATCH: Goal Engine simulation / what-if preview v1
GOAL_ENGINE_SIMULATION_WHAT_IF_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.simulation_what_if_preview.v1"


def _aion_goal_engine_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _aion_goal_engine_merge_preview_config_v1(row):
    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}

    return {
        **contract,
        **config,
        **nested,
        **source_config,
        **payload,
    }


def build_goal_engine_simulation_what_if_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    merged = _aion_goal_engine_merge_preview_config_v1(payload)

    scenarios = (
        merged.get("simulation_scenarios")
        or merged.get("scenarios")
        or ["baseline"]
    )
    scenarios = _aion_goal_engine_list(scenarios) if "_aion_goal_engine_list" in globals() else list(scenarios if isinstance(scenarios, list) else [scenarios])
    scenarios = [str(item) for item in scenarios if str(item).strip()] or ["baseline"]

    risk_score = max(0.0, min(_aion_goal_engine_float(merged.get("risk_score"), 0.0), 1.0))
    success_probability = max(
        0.0,
        min(_aion_goal_engine_float(merged.get("success_probability"), 0.0), 1.0),
    )

    node_id = (
        merged.get("node_id")
        or merged.get("id")
        or payload.get("node_id")
        or payload.get("id")
        or "goal_engine_node"
    )

    recommended_action = (
        "do_not_run_risk_too_high"
        if risk_score >= 0.8
        else "review_before_live_execution"
    )

    return {
        "schema_version": GOAL_ENGINE_SIMULATION_WHAT_IF_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or merged.get("run_id") or "",
        "node_id": str(node_id),
        "node_kind": str(merged.get("node_kind") or merged.get("kind") or merged.get("step_type") or "goal_engine_step"),
        "scenarios": scenarios,
        "estimated_cost": _aion_goal_engine_float(merged.get("estimated_cost"), 0.0),
        "estimated_runtime_minutes": _aion_goal_engine_float(
            merged.get("estimated_runtime_minutes"),
            0.0,
        ),
        "success_probability": success_probability,
        "risk_score": risk_score,
        "recommended_action": recommended_action,
        "requires_human_review": True,
        "dry_run_only": True,
        "external_write_performed": False,
        "grants_permission": False,
        "would_grant_permission": False,
    }


_aion_previous_build_goal_engine_step_trace_rows_simulation_what_if_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_simulation_what_if_v1(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        kind = str(row.get("node_kind") or row.get("kind") or row.get("step_type") or "")
        if kind in {"goal", "experiment", "loop", "outcome_evaluation", "state_delta_accumulator", "environment_revalidation"}:
            preview = build_goal_engine_simulation_what_if_preview(row, run_id=run_id)
            row = {
                **row,
                "simulation_what_if_preview": preview,
            }
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row["payload"] = {
                **payload,
                "simulation_what_if_preview": preview,
            }

        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine simulation / what-if source-config repair v2
_aion_previous_build_goal_engine_simulation_what_if_preview_source_config_v2 = build_goal_engine_simulation_what_if_preview


def build_goal_engine_simulation_what_if_preview(row, *, run_id=None):
    preview = _aion_previous_build_goal_engine_simulation_what_if_preview_source_config_v2(
        row,
        run_id=run_id,
    )

    payload = row if isinstance(row, dict) else {}

    merged = {}
    if "_aion_goal_engine_deep_row_config_v2" in globals():
        merged.update(_aion_goal_engine_deep_row_config_v2(payload))
    else:
        nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
        config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
        source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}
        merged.update({**contract, **config, **nested, **source_config, **payload})

    scenarios = (
        merged.get("simulation_scenarios")
        or merged.get("scenarios")
        or preview.get("scenarios")
        or ["baseline"]
    )

    if isinstance(scenarios, str):
        scenarios = [scenarios] if scenarios.strip() else ["baseline"]
    elif isinstance(scenarios, list):
        scenarios = [str(item) for item in scenarios if str(item).strip()]
    else:
        scenarios = ["baseline"]

    risk_score = max(
        0.0,
        min(
            _aion_goal_engine_float(
                merged.get("risk_score"),
                preview.get("risk_score", 0.0),
            ),
            1.0,
        ),
    )

    success_probability = max(
        0.0,
        min(
            _aion_goal_engine_float(
                merged.get("success_probability"),
                preview.get("success_probability", 0.0),
            ),
            1.0,
        ),
    )

    estimated_cost = _aion_goal_engine_float(
        merged.get("estimated_cost"),
        preview.get("estimated_cost", 0.0),
    )

    estimated_runtime_minutes = _aion_goal_engine_float(
        merged.get("estimated_runtime_minutes"),
        preview.get("estimated_runtime_minutes", 0.0),
    )

    preview["scenarios"] = scenarios or ["baseline"]
    preview["risk_score"] = risk_score
    preview["success_probability"] = success_probability
    preview["estimated_cost"] = estimated_cost
    preview["estimated_runtime_minutes"] = estimated_runtime_minutes
    preview["recommended_action"] = (
        "do_not_run_risk_too_high"
        if risk_score >= 0.8
        else "review_before_live_execution"
    )
    preview["requires_human_review"] = True
    preview["dry_run_only"] = True
    preview["external_write_performed"] = False
    preview["grants_permission"] = False
    preview["would_grant_permission"] = False

    return preview


_aion_previous_build_goal_engine_step_trace_rows_simulation_source_config_v2 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_simulation_source_config_v2(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        kind = str(row.get("node_kind") or row.get("kind") or row.get("step_type") or "")
        if kind in {
            "goal",
            "experiment",
            "loop",
            "outcome_evaluation",
            "state_delta_accumulator",
            "environment_revalidation",
        }:
            preview = build_goal_engine_simulation_what_if_preview(row, run_id=run_id)
            row["simulation_what_if_preview"] = preview

            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row["payload"] = {
                **payload,
                "simulation_what_if_preview": preview,
            }

        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine resource + cost governance preview v1
GOAL_ENGINE_RESOURCE_COST_GOVERNANCE_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.resource_cost_governance_preview.v1"


def build_goal_engine_resource_cost_governance_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}

    merged = {}
    if "_aion_goal_engine_deep_row_config_v2" in globals():
        merged.update(_aion_goal_engine_deep_row_config_v2(payload))
    else:
        nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
        contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
        config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
        source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}
        merged.update({**contract, **config, **nested, **source_config, **payload})

    node_id = str(
        merged.get("node_id")
        or merged.get("id")
        or payload.get("node_id")
        or payload.get("id")
        or "goal_engine_resource_node"
    )

    goal_budget = _aion_goal_engine_float(merged.get("goal_budget"), 0.0)
    estimated_cost = _aion_goal_engine_float(merged.get("estimated_cost"), 0.0)
    token_quota = _aion_goal_engine_int(merged.get("token_quota"), 0)
    estimated_tokens = _aion_goal_engine_int(merged.get("estimated_tokens"), 0)
    runtime_quota_minutes = _aion_goal_engine_float(merged.get("runtime_quota_minutes"), 0.0)
    estimated_runtime_minutes = _aion_goal_engine_float(merged.get("estimated_runtime_minutes"), 0.0)
    provider_cost_quota = _aion_goal_engine_float(merged.get("provider_cost_quota"), 0.0)
    connector_cost_quota = _aion_goal_engine_float(merged.get("connector_cost_quota"), 0.0)
    external_write_quota = _aion_goal_engine_int(merged.get("external_write_quota"), 0)
    parallel_run_quota = _aion_goal_engine_int(merged.get("parallel_run_quota"), 1)
    budget_warning_threshold = _aion_goal_engine_float(merged.get("budget_warning_threshold"), 0.8)

    budget_remaining = round(goal_budget - estimated_cost, 6)
    budgetless_spend_blocked = goal_budget <= 0 and estimated_cost > 0
    over_budget = goal_budget > 0 and estimated_cost > goal_budget
    token_limit_exceeded = token_quota > 0 and estimated_tokens > token_quota
    runtime_limit_exceeded = runtime_quota_minutes > 0 and estimated_runtime_minutes > runtime_quota_minutes

    warning_threshold_cost = goal_budget * budget_warning_threshold if goal_budget > 0 else 0.0
    pause_at_warning = goal_budget > 0 and estimated_cost >= warning_threshold_cost

    recommended_action = "review_before_live_execution"
    if budgetless_spend_blocked:
        recommended_action = "do_not_run_budget_required"
    elif over_budget:
        recommended_action = "do_not_run_over_budget"
    elif token_limit_exceeded:
        recommended_action = "do_not_run_token_quota_exceeded"
    elif runtime_limit_exceeded:
        recommended_action = "do_not_run_runtime_quota_exceeded"
    elif pause_at_warning:
        recommended_action = "pause_for_budget_review"

    return {
        "schema_version": GOAL_ENGINE_RESOURCE_COST_GOVERNANCE_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or merged.get("run_id") or "",
        "node_id": node_id,
        "goal_budget": goal_budget,
        "estimated_cost": estimated_cost,
        "budget_remaining": budget_remaining,
        "budget_warning_threshold": budget_warning_threshold,
        "provider_cost_quota": provider_cost_quota,
        "connector_cost_quota": connector_cost_quota,
        "token_quota": token_quota,
        "estimated_tokens": estimated_tokens,
        "runtime_quota_minutes": runtime_quota_minutes,
        "estimated_runtime_minutes": estimated_runtime_minutes,
        "external_write_quota": external_write_quota,
        "parallel_run_quota": parallel_run_quota,
        "external_write_allowed": external_write_quota > 0,
        "budgetless_spend_blocked": budgetless_spend_blocked,
        "over_budget": over_budget,
        "token_limit_exceeded": token_limit_exceeded,
        "runtime_limit_exceeded": runtime_limit_exceeded,
        "pause_at_warning_threshold": True,
        "warning_threshold_reached": pause_at_warning,
        "hard_stop_at_limit": True,
        "recommended_action": recommended_action,
        "dry_run_only": True,
        "external_write_performed": False,
        "grants_permission": False,
        "would_grant_permission": False,
    }


_aion_previous_build_goal_engine_step_trace_rows_resource_cost_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_resource_cost_v1(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        preview = build_goal_engine_resource_cost_governance_preview(row, run_id=run_id)
        row["resource_cost_governance_preview"] = preview

        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        row["payload"] = {
            **payload,
            "resource_cost_governance_preview": preview,
        }

        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine human feedback preview v1
GOAL_ENGINE_HUMAN_FEEDBACK_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.human_feedback_preview.v1"


def build_goal_engine_human_feedback_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}

    merged = {
        **contract,
        **config,
        **source_config,
        **nested,
        **payload,
    }

    node_id = str(
        merged.get("node_id")
        or merged.get("id")
        or merged.get("goal_id")
        or merged.get("experiment_id")
        or merged.get("loop_id")
        or "goal_engine_feedback"
    )

    feedback_rating = merged.get("feedback_rating")
    if feedback_rating is not None:
        try:
            feedback_rating = int(feedback_rating)
        except Exception:
            feedback_rating = None

    allow_learning = merged.get("allow_learning") is True
    do_not_learn = merged.get("do_not_learn_from_this") is True

    return {
        "schema_version": GOAL_ENGINE_HUMAN_FEEDBACK_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or str(merged.get("run_id") or ""),
        "node_id": node_id,
        "node_kind": str(merged.get("node_kind") or merged.get("kind") or merged.get("step_type") or ""),
        "feedback_required": merged.get("feedback_required") is True,
        "attach_feedback_to_run_id": run_id or str(merged.get("run_id") or ""),
        "attach_feedback_to_goal_id": str(merged.get("goal_id") or node_id),
        "feedback_rating": feedback_rating,
        "feedback_category": str(merged.get("feedback_category") or ""),
        "feedback_comment": str(merged.get("feedback_comment") or ""),
        "allow_learning": allow_learning,
        "do_not_learn_from_this": do_not_learn,
        "bridge_feedback_to_prior_bank": allow_learning and not do_not_learn,
        "bridge_feedback_to_outcome_score": True,
        "negative_feedback_grants_permission": False,
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
        "external_write_performed": False,
        "recommended_action": "collect_human_feedback_before_learning"
        if merged.get("feedback_required") is True
        else "review_before_live_execution",
    }


_aion_previous_build_goal_engine_step_trace_rows_human_feedback_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_human_feedback_v1(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        if isinstance(row, dict):
            preview = build_goal_engine_human_feedback_preview(row, run_id=run_id)
            row = {
                **row,
                "human_feedback_preview": preview,
            }
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row["payload"] = {
                **payload,
                "human_feedback_preview": preview,
            }
        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine human feedback source-config repair v2
_aion_previous_build_goal_engine_human_feedback_preview_source_config_v2 = build_goal_engine_human_feedback_preview


def build_goal_engine_human_feedback_preview(row, *, run_id=None):
    preview = _aion_previous_build_goal_engine_human_feedback_preview_source_config_v2(
        row,
        run_id=run_id,
    )

    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}

    merged = {
        **contract,
        **config,
        **source_config,
        **nested,
        **payload,
    }

    feedback_required = merged.get("feedback_required")
    if feedback_required is not None:
        preview["feedback_required"] = feedback_required is True

    if merged.get("feedback_category") is not None:
        preview["feedback_category"] = str(merged.get("feedback_category") or "")

    if merged.get("feedback_comment") is not None:
        preview["feedback_comment"] = str(merged.get("feedback_comment") or "")

    if merged.get("feedback_rating") is not None:
        try:
            preview["feedback_rating"] = int(merged.get("feedback_rating"))
        except Exception:
            preview["feedback_rating"] = None

    if merged.get("allow_learning") is not None:
        preview["allow_learning"] = merged.get("allow_learning") is True

    if merged.get("do_not_learn_from_this") is not None:
        preview["do_not_learn_from_this"] = merged.get("do_not_learn_from_this") is True

    preview["bridge_feedback_to_prior_bank"] = (
        preview.get("allow_learning") is True
        and preview.get("do_not_learn_from_this") is not True
    )

    preview["negative_feedback_grants_permission"] = False
    preview["grants_permission"] = False
    preview["would_grant_permission"] = False
    preview["dry_run_only"] = True
    preview["external_write_performed"] = False

    preview["recommended_action"] = (
        "collect_human_feedback_before_learning"
        if preview.get("feedback_required") is True
        else "review_before_live_execution"
    )

    return preview

# AION PATCH: Goal Engine human feedback step-trace hard repair v3
_aion_previous_build_goal_engine_step_trace_rows_human_feedback_v3 = build_goal_engine_step_trace_rows


def _aion_goal_engine_merge_row_payload_v3(row):
    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}

    return {
        **contract,
        **config,
        **source_config,
        **nested,
        **payload,
    }


def _aion_goal_engine_apply_human_feedback_preview_v3(row, *, run_id=None):
    if not isinstance(row, dict):
        return row

    merged = _aion_goal_engine_merge_row_payload_v3(row)

    existing = row.get("human_feedback_preview")
    preview = existing if isinstance(existing, dict) else {}

    feedback_required = (
        merged.get("feedback_required")
        if merged.get("feedback_required") is not None
        else preview.get("feedback_required", False)
    )

    allow_learning = (
        merged.get("allow_learning")
        if merged.get("allow_learning") is not None
        else preview.get("allow_learning", False)
    )

    do_not_learn = (
        merged.get("do_not_learn_from_this")
        if merged.get("do_not_learn_from_this") is not None
        else preview.get("do_not_learn_from_this", False)
    )

    rating = merged.get("feedback_rating", preview.get("feedback_rating"))
    try:
        rating = int(rating) if rating is not None else None
    except Exception:
        rating = None

    preview = {
        **preview,
        "schema_version": preview.get("schema_version") or "aion.goal_engine.human_feedback_preview.v1",
        "runtime": "aion_goal_engine",
        "run_id": run_id or row.get("run_id") or "",
        "node_id": str(row.get("node_id") or row.get("id") or merged.get("node_id") or ""),
        "feedback_required": feedback_required is True,
        "feedback_rating": rating,
        "feedback_category": str(merged.get("feedback_category") or preview.get("feedback_category") or ""),
        "feedback_comment": str(merged.get("feedback_comment") or preview.get("feedback_comment") or ""),
        "allow_learning": allow_learning is True,
        "do_not_learn_from_this": do_not_learn is True,
        "bridge_feedback_to_prior_bank": allow_learning is True and do_not_learn is not True,
        "bridge_feedback_to_outcome_score": True,
        "negative_feedback_grants_permission": False,
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
        "external_write_performed": False,
    }

    preview["recommended_action"] = (
        "collect_human_feedback_before_learning"
        if preview["feedback_required"] is True
        else "review_before_live_execution"
    )

    row["human_feedback_preview"] = preview

    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    row["payload"] = {
        **payload,
        "human_feedback_preview": preview,
    }

    return row


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_human_feedback_v3(
        manifest,
        run_id=run_id,
    )

    return [
        _aion_goal_engine_apply_human_feedback_preview_v3(row, run_id=run_id)
        for row in rows
    ]

# AION PATCH: Goal Engine human feedback manifest-source repair v4
_aion_previous_build_goal_engine_step_trace_rows_human_feedback_v4 = build_goal_engine_step_trace_rows


def _aion_goal_engine_bool_v4(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on", "required"}:
        return True
    if text in {"0", "false", "no", "n", "off", "none", ""}:
        return False
    return default


def _aion_goal_engine_feedback_source_map_v4(manifest):
    if not isinstance(manifest, dict):
        return {}

    source_map = {}

    def add_source(step):
        if not isinstance(step, dict):
            return

        config = step.get("config") if isinstance(step.get("config"), dict) else {}
        source_config = step.get("source_config") if isinstance(step.get("source_config"), dict) else {}
        payload = step.get("payload") if isinstance(step.get("payload"), dict) else {}
        contract = step.get("contract") if isinstance(step.get("contract"), dict) else {}

        merged = {
            **contract,
            **config,
            **source_config,
            **payload,
            **step,
        }

        node_id = (
            step.get("node_id")
            or step.get("id")
            or payload.get("node_id")
            or payload.get("id")
            or contract.get("node_id")
            or contract.get("goal_id")
            or contract.get("experiment_id")
            or contract.get("loop_id")
        )

        if node_id:
            source_map[str(node_id)] = merged

    for key in ("source_steps", "steps", "goal_engine_steps", "manifest_steps"):
        value = manifest.get(key)
        if isinstance(value, list):
            for step in value:
                add_source(step)

    return source_map


def _aion_goal_engine_apply_human_feedback_preview_v4(row, source, *, run_id=None):
    if not isinstance(row, dict):
        return row

    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    existing = row.get("human_feedback_preview")
    preview = existing if isinstance(existing, dict) else {}

    merged = {
        **(source if isinstance(source, dict) else {}),
        **payload,
        **row,
    }

    feedback_required = _aion_goal_engine_bool_v4(
        merged.get("feedback_required", preview.get("feedback_required")),
        False,
    )
    allow_learning = _aion_goal_engine_bool_v4(
        merged.get("allow_learning", preview.get("allow_learning")),
        False,
    )
    do_not_learn = _aion_goal_engine_bool_v4(
        merged.get("do_not_learn_from_this", preview.get("do_not_learn_from_this")),
        False,
    )

    rating = merged.get("feedback_rating", preview.get("feedback_rating"))
    try:
        rating = int(rating) if rating is not None else None
    except Exception:
        rating = None

    next_preview = {
        **preview,
        "schema_version": preview.get("schema_version") or "aion.goal_engine.human_feedback_preview.v1",
        "runtime": "aion_goal_engine",
        "run_id": run_id or row.get("run_id") or "",
        "node_id": str(row.get("node_id") or row.get("id") or ""),
        "feedback_required": feedback_required,
        "feedback_rating": rating,
        "feedback_category": str(merged.get("feedback_category") or preview.get("feedback_category") or ""),
        "feedback_comment": str(merged.get("feedback_comment") or preview.get("feedback_comment") or ""),
        "allow_learning": allow_learning,
        "do_not_learn_from_this": do_not_learn,
        "bridge_feedback_to_prior_bank": allow_learning and not do_not_learn,
        "bridge_feedback_to_outcome_score": True,
        "negative_feedback_grants_permission": False,
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
        "external_write_performed": False,
        "recommended_action": (
            "collect_human_feedback_before_learning"
            if feedback_required
            else "review_before_live_execution"
        ),
    }

    row["human_feedback_preview"] = next_preview
    row["payload"] = {
        **payload,
        "human_feedback_preview": next_preview,
    }

    return row


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_human_feedback_v4(
        manifest,
        run_id=run_id,
    )

    source_map = _aion_goal_engine_feedback_source_map_v4(manifest)

    repaired = []
    for row in rows:
        if not isinstance(row, dict):
            repaired.append(row)
            continue

        node_id = str(row.get("node_id") or row.get("id") or "")
        source = source_map.get(node_id, {})
        repaired.append(
            _aion_goal_engine_apply_human_feedback_preview_v4(
                row,
                source,
                run_id=run_id,
            )
        )

    return repaired

# AION PATCH: Goal Engine learning / dreaming advisory preview v1
GOAL_ENGINE_LEARNING_REFLECTION_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.learning_reflection_preview.v1"


def _aion_goal_engine_bool_learning_v1(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _aion_goal_engine_float_learning_v1(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _aion_goal_engine_list_learning_v1(value):
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def _aion_goal_engine_deep_merge_learning_v1(row):
    if not isinstance(row, dict):
        return {}

    merged = {}

    def absorb(value):
        if isinstance(value, dict):
            merged.update(value)

    absorb(row)
    absorb(row.get("source_config"))
    absorb(row.get("config"))
    absorb(row.get("payload"))

    contract = row.get("contract")
    if isinstance(contract, dict):
        absorb(contract)
        absorb(contract.get("source_config"))
        absorb(contract.get("config"))
        absorb(contract.get("payload"))

    payload = row.get("payload")
    if isinstance(payload, dict):
        absorb(payload.get("source_config"))
        absorb(payload.get("config"))
        absorb(payload.get("payload"))

    return merged


def build_goal_engine_learning_reflection_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    merged = _aion_goal_engine_deep_merge_learning_v1(payload)

    node_id = (
        merged.get("node_id")
        or merged.get("id")
        or merged.get("reflection_id")
        or payload.get("node_id")
        or payload.get("id")
        or "goal_engine_reflection"
    )

    allow_learn = _aion_goal_engine_bool_learning_v1(merged.get("allow_learn"), False)
    adr_active = _aion_goal_engine_bool_learning_v1(merged.get("adr_active"), False)

    would_write_memory = allow_learn and not adr_active

    if adr_active:
        blocked_reason = "adr_active"
    elif not allow_learn:
        blocked_reason = "allow_learn_false"
    else:
        blocked_reason = ""

    memory_confidence = max(
        0.0,
        min(
            _aion_goal_engine_float_learning_v1(
                merged.get("memory_confidence")
                if merged.get("memory_confidence") is not None
                else merged.get("confidence"),
                0.0,
            ),
            1.0,
        ),
    )

    return {
        "schema_version": GOAL_ENGINE_LEARNING_REFLECTION_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or merged.get("run_id") or "",
        "node_id": str(node_id),
        "reflection_summary": str(
            merged.get("reflection_summary")
            or merged.get("summary")
            or "Reflection pending."
        ),
        "winning_patterns": _aion_goal_engine_list_learning_v1(merged.get("winning_patterns")),
        "failed_patterns": _aion_goal_engine_list_learning_v1(merged.get("failed_patterns")),
        "episodic_memory": str(merged.get("episodic_memory") or ""),
        "semantic_glyph_memory": str(merged.get("semantic_glyph_memory") or ""),
        "allow_learn": allow_learn,
        "adr_active": adr_active,
        "would_write_memory": would_write_memory,
        "bridge_to_prior_bank": would_write_memory,
        "bridge_to_habit_capsule": would_write_memory,
        "learned_memory_grants_permission": False,
        "can_execute_from_memory": False,
        "memory_write_guard": True,
        "memory_read_guard": True,
        "memory_confidence": memory_confidence,
        "memory_provenance": str(
            merged.get("memory_provenance")
            or merged.get("provenance")
            or merged.get("source")
            or ""
        ),
        "retention_policy": str(merged.get("retention_policy") or "advisory_reviewable"),
        "forgetting_policy": str(merged.get("forgetting_policy") or "retain_until_review_or_expiry"),
        "learning_blocked_reason": blocked_reason,
        "external_write_performed": False,
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
        "recommended_action": "review_learning_preview" if would_write_memory else "do_not_write_learning_memory",
    }


_aion_previous_build_goal_engine_step_trace_rows_learning_reflection_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_learning_reflection_v1(
        manifest,
        run_id=run_id,
    )

    source_steps = []
    if isinstance(manifest, dict) and isinstance(manifest.get("source_steps"), list):
        source_steps = [item for item in manifest.get("source_steps") if isinstance(item, dict)]

    source_by_id = {}
    for source in source_steps:
        sid = str(source.get("id") or source.get("node_id") or "")
        if sid:
            source_by_id[sid] = source

    enriched = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        kind = str(row.get("node_kind") or row.get("kind") or row.get("step_type") or "").strip()
        action_id = str(row.get("action_id") or row.get("payload", {}).get("action_id") if isinstance(row.get("payload"), dict) else "").strip()
        node_id = str(row.get("node_id") or row.get("id") or "")

        should_preview = (
            kind in {"reflect_learn", "reflection", "learn"}
            or action_id == "goal_engine.reflect_learn"
        )

        if should_preview:
            source = source_by_id.get(node_id, {})
            source_config = source.get("config") if isinstance(source.get("config"), dict) else {}
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            merged_row = {
                **row,
                **source_config,
                "source_config": {**source_config, **(row.get("source_config") if isinstance(row.get("source_config"), dict) else {})},
                "payload": {**source_config, **payload},
            }

            preview = build_goal_engine_learning_reflection_preview(merged_row, run_id=run_id)
            row["learning_reflection_preview"] = preview
            row["learned_memory_grants_permission"] = False
            row["can_execute_from_memory"] = False
            row["payload"] = {
                **payload,
                "learning_reflection_preview": preview,
                "learned_memory_grants_permission": False,
                "can_execute_from_memory": False,
            }

        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine red-team safety simulation preview v1
GOAL_ENGINE_RED_TEAM_SAFETY_PREVIEW_SCHEMA_VERSION = "aion.goal_engine.red_team_safety_preview.v1"


def _aion_goal_engine_bool_red_team_v1(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on", "unsafe", "blocked"}:
        return True
    if text in {"false", "0", "no", "n", "off", "safe", "allowed"}:
        return False
    return default


def _aion_goal_engine_float_red_team_v1(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def build_goal_engine_red_team_safety_preview(row, *, run_id=None):
    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
    source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}

    merged = {
        **contract,
        **config,
        **source_config,
        **nested,
        **payload,
    }

    node_id = (
        merged.get("node_id")
        or merged.get("id")
        or contract.get("goal_id")
        or contract.get("experiment_id")
        or contract.get("loop_id")
        or "goal_engine_step"
    )

    node_kind = str(
        merged.get("node_kind")
        or merged.get("kind")
        or merged.get("step_type")
        or ""
    )

    risk_score = max(0.0, min(_aion_goal_engine_float_red_team_v1(merged.get("risk_score"), 0.0), 1.0))
    safety_classification = str(merged.get("safety_classification") or "safe").strip().lower()

    blocked_reasons = _aion_goal_engine_list(
        merged.get("blocked_reasons")
        or merged.get("safety_blocked_reasons")
        or []
    )

    unsafe_goal = (
        _aion_goal_engine_bool_red_team_v1(merged.get("unsafe_goal"), False)
        or safety_classification in {"unsafe", "blocked", "high_risk"}
        or risk_score >= 0.8
        or bool(blocked_reasons)
    )

    red_team_checks = _aion_goal_engine_list(
        merged.get("red_team_checks")
        or [
            "goal_interpretation",
            "loop_bounds",
            "experiment_budget_abuse",
            "resume_stale_state",
            "learned_memory_policy_bypass",
            "adversarial_prompt_checks",
        ]
    )

    unbounded_execution_blocked = (
        merged.get("unbounded_execution_blocked") is not False
        and merged.get("bounded_execution") is not False
    )

    recommended_action = "block_before_execution" if unsafe_goal else "review_before_live_execution"

    return {
        "schema_version": GOAL_ENGINE_RED_TEAM_SAFETY_PREVIEW_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "run_id": run_id or str(merged.get("run_id") or ""),
        "node_id": str(node_id),
        "node_kind": node_kind or "goal_engine",
        "red_team_checks": red_team_checks,
        "risk_score": risk_score,
        "safety_classification": "unsafe" if unsafe_goal else "safe",
        "unsafe_goal_blocked": unsafe_goal,
        "unbounded_execution_blocked": unbounded_execution_blocked,
        "budget_abuse_blocked": True,
        "resume_stale_state_blocked": True,
        "learned_memory_policy_bypass_blocked": True,
        "adversarial_prompt_checks_enabled": True,
        "blocked_reasons": blocked_reasons,
        "recommended_action": recommended_action,
        "dry_run_only": True,
        "external_write_performed": False,
        "grants_permission": False,
        "would_grant_permission": False,
    }


_aion_previous_build_goal_engine_step_trace_rows_red_team_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_red_team_v1(
        manifest,
        run_id=run_id,
    )

    enriched = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        preview = build_goal_engine_red_team_safety_preview(row, run_id=run_id)
        row["red_team_safety_preview"] = preview
        row["external_write_performed"] = False
        row["grants_permission"] = False
        row["would_grant_permission"] = False

        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        row["payload"] = {
            **payload,
            "red_team_safety_preview": preview,
        }

        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine red-team safety source-config repair v2
_aion_previous_build_goal_engine_red_team_safety_preview_source_config_v2 = build_goal_engine_red_team_safety_preview


def build_goal_engine_red_team_safety_preview(row, *, run_id=None):
    preview = _aion_previous_build_goal_engine_red_team_safety_preview_source_config_v2(
        row,
        run_id=run_id,
    )

    payload = row if isinstance(row, dict) else {}
    nested = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
    source_config = payload.get("source_config") if isinstance(payload.get("source_config"), dict) else {}
    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}

    merged = {
        **contract,
        **config,
        **source_config,
        **nested,
        **payload,
    }

    risk_score = max(
        0.0,
        min(
            _aion_goal_engine_float_red_team_v1(
                merged.get("risk_score"),
                preview.get("risk_score", 0.0),
            ),
            1.0,
        ),
    )

    blocked_reasons = _aion_goal_engine_list(
        merged.get("blocked_reasons")
        or merged.get("safety_blocked_reasons")
        or preview.get("blocked_reasons")
        or []
    )

    safety_classification = str(
        merged.get("safety_classification")
        or preview.get("safety_classification")
        or "safe"
    ).strip().lower()

    unsafe_goal = (
        _aion_goal_engine_bool_red_team_v1(merged.get("unsafe_goal"), False)
        or safety_classification in {"unsafe", "blocked", "high_risk"}
        or risk_score >= 0.8
        or bool(blocked_reasons)
    )

    preview["risk_score"] = risk_score
    preview["blocked_reasons"] = blocked_reasons
    preview["safety_classification"] = "unsafe" if unsafe_goal else "safe"
    preview["unsafe_goal_blocked"] = unsafe_goal
    preview["recommended_action"] = (
        "block_before_execution" if unsafe_goal else "review_before_live_execution"
    )
    preview["dry_run_only"] = True
    preview["external_write_performed"] = False
    preview["grants_permission"] = False
    preview["would_grant_permission"] = False

    return preview


_aion_previous_build_goal_engine_step_trace_rows_red_team_source_config_v2 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_red_team_source_config_v2(
        manifest,
        run_id=run_id,
    )

    source_steps = []
    if isinstance(manifest, dict) and isinstance(manifest.get("source_steps"), list):
        source_steps = [item for item in manifest.get("source_steps") if isinstance(item, dict)]

    source_by_id = {}
    for source in source_steps:
        source_id = source.get("id") or source.get("node_id")
        if source_id:
            source_by_id[str(source_id)] = source

    enriched = []
    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        source = source_by_id.get(str(row.get("node_id") or row.get("id") or ""))
        if isinstance(source, dict):
            source_config = source.get("config") if isinstance(source.get("config"), dict) else {}
            row = {
                **row,
                "source_config": {
                    **source_config,
                    **(row.get("source_config") if isinstance(row.get("source_config"), dict) else {}),
                },
            }
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            row["payload"] = {
                **source_config,
                **payload,
                "source_config": row["source_config"],
            }

        preview = build_goal_engine_red_team_safety_preview(row, run_id=run_id)
        row["red_team_safety_preview"] = preview
        row["external_write_performed"] = False
        row["grants_permission"] = False
        row["would_grant_permission"] = False

        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        row["payload"] = {
            **payload,
            "red_team_safety_preview": preview,
        }

        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine preview-builder registry v1
def _aion_goal_engine_safe_preview_builder_v1(builder):
    def wrapped(row, *, run_id=None):
        try:
            result = builder(row, run_id=run_id)
            return result if isinstance(result, dict) else {}
        except Exception as exc:
            return {
                "schema_version": "aion.goal_engine.preview_error.v1",
                "runtime": "aion_goal_engine",
                "error": str(exc),
                "dry_run_only": True,
                "external_write_performed": False,
                "grants_permission": False,
                "would_grant_permission": False,
            }

    return wrapped


def _aion_goal_engine_noop_preview_v1(row, *, run_id=None):
    return {}


def _aion_goal_engine_kind_for_registry_v1(row):
    if not isinstance(row, dict):
        return "unknown"

    raw = (
        row.get("node_kind")
        or row.get("kind")
        or row.get("step_type")
        or row.get("action_id")
        or ""
    )

    raw = str(raw).strip()

    if raw.startswith("goal_engine."):
        raw = raw.split(".", 1)[1]

    aliases = {
        "outcome": "outcome_evaluation",
        "outcomeevaluation": "outcome_evaluation",
        "reflect": "reflect_learn",
        "reflection": "reflect_learn",
        "learn": "reflect_learn",
        "state_delta": "state_delta_accumulator",
        "environment": "environment_revalidation",
    }

    return aliases.get(raw, raw or "unknown")


GOAL_ENGINE_PREVIEW_BUILDERS = {
    "goal": [
        build_goal_engine_simulation_what_if_preview,
        build_goal_engine_resource_cost_governance_preview,
        build_goal_engine_human_feedback_preview,
        build_goal_engine_red_team_safety_preview,
    ],
    "experiment": [
        build_goal_engine_experiment_variant_preview,
        build_goal_engine_simulation_what_if_preview,
        build_goal_engine_resource_cost_governance_preview,
        build_goal_engine_red_team_safety_preview,
    ],
    "loop": [
        build_goal_engine_loop_iteration_preview,
        build_goal_engine_checkpoint_resume_preview,
        build_goal_engine_simulation_what_if_preview,
        build_goal_engine_resource_cost_governance_preview,
        build_goal_engine_red_team_safety_preview,
    ],
    "outcome_evaluation": [
        build_goal_engine_outcome_score_preview,
        build_goal_engine_human_feedback_preview,
        build_goal_engine_red_team_safety_preview,
    ],
    "reflect_learn": [
        build_goal_engine_learning_reflection_preview,
        build_goal_engine_human_feedback_preview,
        build_goal_engine_red_team_safety_preview,
    ],
    "state_delta_accumulator": [
        build_goal_engine_state_delta_preview,
        build_goal_engine_red_team_safety_preview,
    ],
    "environment_revalidation": [
        build_goal_engine_environment_revalidation_preview,
        build_goal_engine_red_team_safety_preview,
    ],
}


def _aion_goal_engine_preview_name_v1(preview):
    if not isinstance(preview, dict):
        return ""

    schema = str(preview.get("schema_version") or "")
    if schema.startswith("aion.goal_engine.") and schema.endswith(".v1"):
        return schema.replace("aion.goal_engine.", "").replace(".v1", "")

    return str(preview.get("preview_type") or "")


def build_goal_engine_preview_bundle_for_row(row, *, run_id=None):
    row = row if isinstance(row, dict) else {}
    node_kind = _aion_goal_engine_kind_for_registry_v1(row)
    builders = GOAL_ENGINE_PREVIEW_BUILDERS.get(node_kind, [])

    previews = {}
    for builder in builders:
        preview = _aion_goal_engine_safe_preview_builder_v1(builder)(row, run_id=run_id)
        name = _aion_goal_engine_preview_name_v1(preview)
        if name:
            previews[name] = preview

    node_id = str(row.get("node_id") or row.get("id") or "")

    return {
        "schema_version": "aion.goal_engine.preview_bundle.v1",
        "runtime": "aion_goal_engine",
        "run_id": run_id or row.get("run_id") or "",
        "node_id": node_id,
        "node_kind": node_kind,
        "preview_names": sorted(previews.keys()),
        "previews": previews,
        "dry_run_only": True,
        "external_write_performed": False,
        "grants_permission": False,
        "would_grant_permission": False,
    }


_aion_previous_build_goal_engine_step_trace_rows_preview_registry_v1 = build_goal_engine_step_trace_rows


def build_goal_engine_step_trace_rows(manifest, *, run_id=None):
    rows = _aion_previous_build_goal_engine_step_trace_rows_preview_registry_v1(
        manifest,
        run_id=run_id,
    )

    enriched = []

    for row in rows:
        if not isinstance(row, dict):
            enriched.append(row)
            continue

        bundle = build_goal_engine_preview_bundle_for_row(row, run_id=run_id)

        row["goal_engine_preview_bundle"] = bundle
        row["dry_run_only"] = True
        row["external_write_performed"] = False
        row["grants_permission"] = False
        row["would_grant_permission"] = False

        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        row["payload"] = {
            **payload,
            "goal_engine_preview_bundle": bundle,
        }

        enriched.append(row)

    return enriched

# AION PATCH: Goal Engine canonical preview bundle bridge final override v13
# Reason:
# - GoalEnginePreviewBundle is now the single source of truth for Goal Engine dry-run output.
# - Legacy fields remain as compatibility mirrors only.
# - This final EOF override wins over older appended attach wrappers.
# - A2A machine trace stays present but deferred until Sprint 1 is stable.

from backend.modules.aion.goal_engine.preview_bundle import build_goal_engine_preview_bundle


def _aion_goal_engine_contracts_from_capsule_v13(capsule):
    contracts = []
    for step in _workflow_steps_from_capsule(capsule):
        if not is_goal_engine_step(step):
            continue
        contract = _contract_for_goal_engine_step(step)
        if contract is not None:
            contracts.append(contract)
    return contracts


def attach_goal_engine_manifest_to_dry_result(dry_result, capsule, *, run_id=None):
    """
    Attach canonical GoalEnginePreviewBundle to final WorkflowDryRunResult.

    Contract:
    - GoalEnginePreviewBundle is the single source of truth.
    - outcome_evidence_summary validator rows are owned by the bundle.
    - the bridge only mirrors canonical payload fields for legacy UI compatibility.
    - Legacy fields are compatibility mirrors from the bundle.
    - advisory only
    - dry-run only
    - grants no permission
    - performs no external writes
    """
    contracts = _aion_goal_engine_contracts_from_capsule_v13(capsule)
    if not contracts:
        return dry_result

    workflow_id = _workflow_id_from_capsule(capsule)
    safe_run_id = str(run_id or getattr(dry_result, "run_id", "") or "goal_engine_dry_run")

    bundle = build_goal_engine_preview_bundle(
        run_id=safe_run_id,
        workflow_id=workflow_id,
        contracts=contracts,
    )

    bundle_payload = bundle.to_dict()

    canonical_goal_runtime_summary = bundle_payload.get("goal_runtime_summary")
    if not isinstance(canonical_goal_runtime_summary, dict):
        canonical_goal_runtime_summary = {}

    canonical_checkpoint_runtime_summary = bundle_payload.get("checkpoint_runtime_summary")
    if not isinstance(canonical_checkpoint_runtime_summary, dict):
        canonical_checkpoint_runtime_summary = {}

    canonical_resume_revalidation_summary = bundle_payload.get("resume_revalidation_summary")
    if not isinstance(canonical_resume_revalidation_summary, dict):
        canonical_resume_revalidation_summary = {}

    canonical_experiment_runtime_summary = bundle_payload.get("experiment_runtime_summary")
    if not isinstance(canonical_experiment_runtime_summary, dict):
        canonical_experiment_runtime_summary = {}

    canonical_orchestrator_runtime_summary = bundle_payload.get("orchestrator_runtime_summary")
    if not isinstance(canonical_orchestrator_runtime_summary, dict):
        canonical_orchestrator_runtime_summary = {}
    canonical_goal_decomposition_runtime_summary = bundle_payload.get("goal_decomposition_runtime_summary")
    if not isinstance(canonical_goal_decomposition_runtime_summary, dict):
        canonical_goal_decomposition_runtime_summary = {}

    canonical_memory_runtime_summary = bundle_payload.get("memory_runtime_summary")
    if not isinstance(canonical_memory_runtime_summary, dict):
        canonical_memory_runtime_summary = {}


    canonical_manifest = dict(bundle_payload.get("manifest") or {})
    canonical_step_trace = list(bundle_payload.get("step_trace") or [])
    canonical_boardroom_trace = dict(bundle_payload.get("boardroom_trace") or {})
    canonical_machine_trace = dict(bundle_payload.get("machine_trace") or {})

    canonical_manifest.setdefault("runtime", "aion_goal_engine")
    canonical_manifest.setdefault("run_id", safe_run_id)
    canonical_manifest.setdefault("workflow_id", workflow_id)
    canonical_manifest.setdefault("dry_run_only", True)
    canonical_manifest.setdefault("would_execute", False)
    canonical_manifest.setdefault("would_write_external", False)
    canonical_manifest.setdefault("would_grant_permission", False)

    safety = canonical_manifest.get("safety_contract")
    if not isinstance(safety, dict):
        safety = {}

    safety.update({
        "goals_grant_permission": False,
        "experiments_grant_permission": False,
        "loops_grant_permission": False,
        "learning_grants_permission": False,
        "external_writes_require_approval": True,
        "unbounded_loops_allowed": False,
        "resume_requires_environment_revalidation": True,
    })
    canonical_manifest["safety_contract"] = safety

    canonical_boardroom_trace.setdefault("dry_run_only", True)
    canonical_boardroom_trace.setdefault("would_execute", False)
    canonical_boardroom_trace.setdefault("would_write_external", False)
    canonical_boardroom_trace.setdefault("would_grant_permission", False)
    canonical_boardroom_trace.setdefault("grants_permission", False)
    canonical_boardroom_trace.setdefault("external_writes_require_approval", True)

    canonical_machine_trace.setdefault("runtime", "aion_goal_engine")
    canonical_machine_trace.setdefault("trace_type", "goal_engine_preview")
    canonical_machine_trace.setdefault("agent_ready", False)
    canonical_machine_trace.setdefault("a2a_deferred", True)
    canonical_machine_trace.setdefault("commercial_interface_ready", False)

    setattr(dry_result, "goal_engine_preview_bundle", bundle_payload)
    setattr(dry_result, "goal_engine_manifest", canonical_manifest)
    setattr(dry_result, "goal_engine", canonical_manifest)
    setattr(dry_result, "goal_engine_step_trace", canonical_step_trace)
    setattr(dry_result, "goal_engine_boardroom_trace", canonical_boardroom_trace)
    setattr(dry_result, "goal_engine_machine_trace", canonical_machine_trace)
    setattr(dry_result, "goal_engine_goal_runtime_summary", canonical_goal_runtime_summary)
    setattr(dry_result, "goal_runtime_summary", canonical_goal_runtime_summary)
    setattr(dry_result, "goal_engine_checkpoint_runtime_summary", canonical_checkpoint_runtime_summary)
    setattr(dry_result, "checkpoint_runtime_summary", canonical_checkpoint_runtime_summary)
    setattr(dry_result, "goal_engine_resume_revalidation_summary", canonical_resume_revalidation_summary)
    setattr(dry_result, "resume_revalidation_summary", canonical_resume_revalidation_summary)
    setattr(dry_result, "goal_engine_experiment_runtime_summary", canonical_experiment_runtime_summary)
    setattr(dry_result, "experiment_runtime_summary", canonical_experiment_runtime_summary)
    setattr(dry_result, "goal_engine_orchestrator_runtime_summary", canonical_orchestrator_runtime_summary)
    setattr(dry_result, "orchestrator_runtime_summary", canonical_orchestrator_runtime_summary)
    setattr(dry_result, "goal_engine_goal_decomposition_runtime_summary", canonical_goal_decomposition_runtime_summary)
    setattr(dry_result, "goal_decomposition_runtime_summary", canonical_goal_decomposition_runtime_summary)
    setattr(dry_result, "goal_engine_memory_runtime_summary", canonical_memory_runtime_summary)
    setattr(dry_result, "memory_runtime_summary", canonical_memory_runtime_summary)

    original_to_dict = getattr(dry_result, "to_dict", None)

    if callable(original_to_dict):
        def to_dict_with_goal_engine_preview_bundle():
            payload = original_to_dict()
            if not isinstance(payload, dict):
                return payload

            payload["goal_engine_preview_bundle"] = bundle_payload

            # Legacy compatibility mirrors.
            payload["goal_engine_manifest"] = canonical_manifest
            payload["goal_engine"] = canonical_manifest
            payload["goal_engine_step_trace"] = canonical_step_trace
            payload["goal_engine_boardroom_trace"] = canonical_boardroom_trace
            payload["goal_engine_machine_trace"] = canonical_machine_trace
            payload["goal_engine_goal_runtime_summary"] = canonical_goal_runtime_summary
            payload["goal_runtime_summary"] = canonical_goal_runtime_summary
            payload["goal_engine_checkpoint_runtime_summary"] = canonical_checkpoint_runtime_summary
            payload["checkpoint_runtime_summary"] = canonical_checkpoint_runtime_summary
            payload["goal_engine_resume_revalidation_summary"] = canonical_resume_revalidation_summary
            payload["resume_revalidation_summary"] = canonical_resume_revalidation_summary
            payload["goal_engine_experiment_runtime_summary"] = canonical_experiment_runtime_summary
            payload["experiment_runtime_summary"] = canonical_experiment_runtime_summary
            payload["goal_engine_orchestrator_runtime_summary"] = canonical_orchestrator_runtime_summary
            payload["orchestrator_runtime_summary"] = canonical_orchestrator_runtime_summary
            payload["goal_engine_goal_decomposition_runtime_summary"] = canonical_goal_decomposition_runtime_summary
            payload["goal_decomposition_runtime_summary"] = canonical_goal_decomposition_runtime_summary
            payload["goal_engine_memory_runtime_summary"] = canonical_memory_runtime_summary
            payload["memory_runtime_summary"] = canonical_memory_runtime_summary

            existing_trace = payload.get("trace")
            if isinstance(existing_trace, list):
                existing_keys = {
                    (
                        str(row.get("runtime") or ""),
                        str(row.get("node_id") or ""),
                        str(row.get("step_index") or ""),
                    )
                    for row in existing_trace
                    if isinstance(row, dict)
                }

                merged_trace = list(existing_trace)
                for row in canonical_step_trace:
                    if not isinstance(row, dict):
                        continue

                    key = (
                        str(row.get("runtime") or ""),
                        str(row.get("node_id") or ""),
                        str(row.get("step_index") or ""),
                    )

                    if key not in existing_keys:
                        merged_trace.append(row)
                        existing_keys.add(key)

                payload["trace"] = merged_trace
            else:
                payload["trace"] = canonical_step_trace

            return payload

        dry_result.to_dict = to_dict_with_goal_engine_preview_bundle

    return dry_result
