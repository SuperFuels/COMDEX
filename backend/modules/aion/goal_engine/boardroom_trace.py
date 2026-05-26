from __future__ import annotations

from typing import Any, Dict, List


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def build_goal_engine_boardroom_trace(manifest: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Convert a Goal Engine dry-run manifest into a compact Boardroom-facing trace.

    This is advisory visibility only:
    - no execution
    - no permission grant
    - no external write
    - no learning bypass
    """
    manifest = _as_dict(manifest)
    steps = _as_list(manifest.get("steps"))

    if not manifest:
        return {
            "runtime": "aion_goal_engine",
            "available": False,
            "summary": "No Goal Engine manifest attached.",
            "active_goals": [],
            "safety": {
                "dry_run_only": True,
                "would_execute": False,
                "would_write_external": False,
                "would_grant_permission": False,
            },
            "events": [],
        }

    active_goals = []
    events = []
    blocked_reasons = []

    for step in steps:
        step = _as_dict(step)
        payload = _as_dict(step.get("payload") or step.get("contract") or step)

        contract_type = str(
            step.get("contract_type")
            or payload.get("contract_type")
            or step.get("node_type")
            or step.get("action_id")
            or ""
        )

        validation_errors = _as_list(step.get("validation_errors") or payload.get("validation_errors"))
        blocked_reasons.extend(str(item) for item in validation_errors if item)

        if "GoalNodeContract" in contract_type or step.get("action_id") == "goal_engine.goal":
            active_goals.append({
                "goal_id": payload.get("goal_id") or step.get("goal_id") or "",
                "goal_name": payload.get("goal_name") or step.get("goal_name") or "Goal",
                "target_metric": payload.get("target_metric") or step.get("target_metric") or "",
                "target_value": payload.get("target_value") or step.get("target_value"),
            })

        events.append({
            "event_type": "goal_engine.dry_run_step_visible",
            "contract_type": contract_type or "goal_engine_step",
            "dry_run_only": step.get("dry_run_only", True) is not False,
            "would_execute": step.get("would_execute", False) is True,
            "would_write_external": step.get("would_write_external", False) is True,
            "would_grant_permission": step.get("would_grant_permission", False) is True,
            "validation_errors": validation_errors,
        })

    safety_contract = _as_dict(manifest.get("safety_contract"))

    return {
        "runtime": "aion_goal_engine",
        "available": True,
        "run_id": manifest.get("run_id") or "",
        "workflow_id": manifest.get("workflow_id") or "",
        "valid": manifest.get("valid", not bool(blocked_reasons)),
        "summary": "Goal Engine dry-run trace attached. Advisory only; grants no permission.",
        "active_goals": active_goals,
        "blocked_reasons": blocked_reasons,
        "safety": {
            "dry_run_only": manifest.get("dry_run_only", True) is not False,
            "would_execute": manifest.get("would_execute", False) is True,
            "would_write_external": manifest.get("would_write_external", False) is True,
            "would_grant_permission": manifest.get("would_grant_permission", False) is True,
            "external_writes_require_approval": safety_contract.get("external_writes_require_approval", True) is not False,
            "unbounded_loops_allowed": safety_contract.get("unbounded_loops_allowed", False) is True,
            "resume_requires_environment_revalidation": safety_contract.get("resume_requires_environment_revalidation", True) is not False,
        },
        "events": events,
    }

# AION PATCH: Goal Engine Boardroom Trace / Manifest alignment v1
def _aion_goal_engine_manifest_steps(manifest):
    if not isinstance(manifest, dict):
        return []

    steps = manifest.get("steps")
    if isinstance(steps, list):
        return [step for step in steps if isinstance(step, dict)]

    rows = []
    for key in (
        "goals",
        "experiments",
        "loops",
        "outcome_evaluations",
        "reflections",
        "state_delta_accumulators",
        "environment_revalidations",
    ):
        value = manifest.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    rows.append(item)
    return rows


def _aion_goal_engine_step_kind(step):
    if not isinstance(step, dict):
        return "unknown"

    raw = (
        step.get("step_type")
        or step.get("node_kind")
        or step.get("kind")
        or step.get("type")
        or step.get("action_id")
        or step.get("id")
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


_aion_previous_build_goal_engine_boardroom_trace_alignment_v1 = build_goal_engine_boardroom_trace


def build_goal_engine_boardroom_trace(manifest):
    trace = _aion_previous_build_goal_engine_boardroom_trace_alignment_v1(manifest)

    if not isinstance(trace, dict):
        trace = {}

    if not isinstance(manifest, dict):
        return trace

    safety = manifest.get("safety_contract") if isinstance(manifest.get("safety_contract"), dict) else {}

    trace.setdefault("runtime", manifest.get("runtime") or "aion_goal_engine")
    trace["dry_run_only"] = manifest.get("dry_run_only") is not False
    trace["grants_permission"] = False
    trace["would_grant_permission"] = bool(manifest.get("would_grant_permission")) is True
    trace["would_execute"] = bool(manifest.get("would_execute")) is True
    trace["would_write_external"] = bool(manifest.get("would_write_external")) is True
    trace["requires_approval_before_live_write"] = manifest.get("requires_approval_before_live_write") is not False

    trace["safety_contract"] = {
        **safety,
        "goals_grant_permission": False,
        "experiments_grant_permission": False,
        "loops_grant_permission": False,
        "learning_grants_permission": False,
        "external_writes_require_approval": True,
        "unbounded_loops_allowed": False,
        "resume_requires_environment_revalidation": True,
    }

    manifest_steps = _aion_goal_engine_manifest_steps(manifest)
    kinds = []
    rows = []

    for index, step in enumerate(manifest_steps):
        kind = _aion_goal_engine_step_kind(step)
        if kind and kind not in kinds:
            kinds.append(kind)

        contract = step.get("contract") if isinstance(step.get("contract"), dict) else {}
        node_id = (
            step.get("node_id")
            or step.get("id")
            or contract.get("node_id")
            or contract.get("goal_id")
            or contract.get("experiment_id")
            or contract.get("loop_id")
            or f"goal_engine_step_{index + 1}"
        )

        rows.append({
            "index": step.get("index", index),
            "node_id": str(node_id),
            "node_kind": kind,
            "step_type": kind,
            "contract_type": step.get("contract_type") or contract.get("contract_type") or "",
            "dry_run_only": True,
            "grants_permission": False,
            "would_grant_permission": False,
            "would_execute": False,
            "would_write_external": False,
            "status": "dry_run_simulated",
            "validation_errors": step.get("validation_errors") or contract.get("validation_errors") or [],
        })

    trace["manifest_step_kinds"] = kinds
    trace["manifest_steps"] = rows
    trace["goal_engine_steps"] = rows

    # Keep human-readable trace text so simple drift tests can verify coverage.
    trace["manifest_alignment_summary"] = " ".join(kinds)

    return trace

# AION PATCH: Goal Engine Boardroom visibility preview fields v2
_aion_previous_build_goal_engine_boardroom_trace_visibility_v2 = build_goal_engine_boardroom_trace


def _aion_goal_engine_first_preview_value(rows, preview_key, value_key, default=None):
    for row in rows:
        if not isinstance(row, dict):
            continue
        preview = row.get(preview_key)
        if isinstance(preview, dict) and value_key in preview:
            return preview.get(value_key)
    return default


def _aion_goal_engine_collect_preview_values(rows, preview_key, value_key):
    values = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        preview = row.get(preview_key)
        if not isinstance(preview, dict):
            continue

        raw = preview.get(value_key)
        if isinstance(raw, list):
            for item in raw:
                if item not in values:
                    values.append(item)
        elif raw not in (None, "") and raw not in values:
            values.append(raw)

    return values


def _aion_goal_engine_preview_rows_from_manifest(manifest):
    if not isinstance(manifest, dict):
        return []

    rows = manifest.get("goal_engine_step_trace")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]

    rows = manifest.get("step_trace")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]

    return []


def build_goal_engine_boardroom_trace(manifest):
    trace = _aion_previous_build_goal_engine_boardroom_trace_visibility_v2(manifest)

    if not isinstance(trace, dict):
        trace = {}

    if not isinstance(manifest, dict):
        return trace

    preview_rows = _aion_goal_engine_preview_rows_from_manifest(manifest)

    if not preview_rows:
        return trace

    experiment_variants = _aion_goal_engine_collect_preview_values(
        preview_rows,
        "experiment_variant_preview",
        "variants",
    )
    evidence_refs = _aion_goal_engine_collect_preview_values(
        preview_rows,
        "outcome_score_preview",
        "evidence_refs",
    )

    loop_iteration_count = _aion_goal_engine_first_preview_value(
        preview_rows,
        "loop_iteration_preview",
        "would_run_iterations",
        0,
    )

    outcome_score_preview = {}
    checkpoint_resume_state = {}
    state_delta_summary = {}

    for row in preview_rows:
        if not isinstance(row, dict):
            continue

        if not outcome_score_preview and isinstance(row.get("outcome_score_preview"), dict):
            outcome_score_preview = dict(row["outcome_score_preview"])

        if not checkpoint_resume_state and isinstance(row.get("checkpoint_resume_preview"), dict):
            checkpoint_resume_state = dict(row["checkpoint_resume_preview"])

        if not state_delta_summary and isinstance(row.get("state_delta_preview"), dict):
            state_delta_summary = dict(row["state_delta_preview"])

    blocked_reasons = list(trace.get("blocked_reasons") or [])
    if not blocked_reasons:
        blocked_reasons.append("dry_run_only_no_external_write")

    preview_fields = {
        "schema_version": "aion.goal_engine.boardroom_visibility_preview_fields.v1",
        "runtime": "aion_goal_engine",
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
        "would_write_external": False,
        "external_write_performed": False,
        "loop_iteration_count": loop_iteration_count,
        "experiment_variants": experiment_variants,
        "outcome_score": outcome_score_preview,
        "checkpoint_resume_state": checkpoint_resume_state,
        "state_delta_summary": state_delta_summary,
        "evidence_refs": evidence_refs,
        "blocked_reasons": blocked_reasons,
    }

    trace["preview_fields"] = preview_fields
    trace["preview_rows"] = preview_rows
    trace["loop_iteration_count"] = loop_iteration_count
    trace["experiment_variants"] = experiment_variants
    trace["outcome_score_preview"] = outcome_score_preview
    trace["checkpoint_resume_state"] = checkpoint_resume_state
    trace["state_delta_summary"] = state_delta_summary
    trace["evidence_refs"] = evidence_refs

    trace["dry_run_only"] = True
    trace["grants_permission"] = False
    trace["would_grant_permission"] = False
    trace["would_write_external"] = False

    return trace

# AION PATCH: Goal Engine Boardroom experiment variant label normalisation v1
_aion_previous_build_goal_engine_boardroom_trace_variant_labels_v1 = build_goal_engine_boardroom_trace


def _aion_goal_engine_variant_labels_v1(values):
    labels = []

    for value in values if isinstance(values, list) else []:
        label = None

        if isinstance(value, dict):
            label = (
                value.get("label")
                or value.get("variant_label")
                or value.get("name")
                or value.get("variant_id")
            )
        else:
            label = value

        if label not in (None, "") and label not in labels:
            labels.append(label)

    return labels


def build_goal_engine_boardroom_trace(manifest):
    trace = _aion_previous_build_goal_engine_boardroom_trace_variant_labels_v1(manifest)

    if not isinstance(trace, dict):
        return trace

    preview_fields = trace.get("preview_fields")
    if isinstance(preview_fields, dict):
        preview_fields["experiment_variants"] = _aion_goal_engine_variant_labels_v1(
            preview_fields.get("experiment_variants")
        )
        trace["experiment_variants"] = list(preview_fields["experiment_variants"])
    elif isinstance(trace.get("experiment_variants"), list):
        trace["experiment_variants"] = _aion_goal_engine_variant_labels_v1(
            trace.get("experiment_variants")
        )

    return trace

# AION PATCH: Goal Engine Boardroom resource + cost governance visibility v1
def _aion_goal_engine_float_v1(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _aion_goal_engine_int_v1(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _aion_goal_engine_collect_step_trace_v1(manifest):
    if not isinstance(manifest, dict):
        return []

    rows = manifest.get("goal_engine_step_trace")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]

    rows = manifest.get("step_trace")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]

    rows = manifest.get("trace")
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]

    return []


def _aion_goal_engine_resource_cost_rows_v1(manifest):
    rows = []

    for row in _aion_goal_engine_collect_step_trace_v1(manifest):
        preview = row.get("resource_cost_governance_preview")
        if not isinstance(preview, dict):
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            preview = payload.get("resource_cost_governance_preview")

        if not isinstance(preview, dict):
            continue

        rows.append({
            "node_id": str(preview.get("node_id") or row.get("node_id") or ""),
            "node_kind": str(row.get("node_kind") or row.get("kind") or ""),
            "goal_budget": _aion_goal_engine_float_v1(preview.get("goal_budget"), 0.0),
            "estimated_cost": _aion_goal_engine_float_v1(preview.get("estimated_cost"), 0.0),
            "budget_remaining": _aion_goal_engine_float_v1(preview.get("budget_remaining"), 0.0),
            "token_quota": _aion_goal_engine_int_v1(preview.get("token_quota"), 0),
            "estimated_tokens": _aion_goal_engine_int_v1(preview.get("estimated_tokens"), 0),
            "runtime_quota_minutes": _aion_goal_engine_float_v1(preview.get("runtime_quota_minutes"), 0.0),
            "estimated_runtime_minutes": _aion_goal_engine_float_v1(preview.get("estimated_runtime_minutes"), 0.0),
            "provider_cost_quota": _aion_goal_engine_float_v1(preview.get("provider_cost_quota"), 0.0),
            "connector_cost_quota": _aion_goal_engine_float_v1(preview.get("connector_cost_quota"), 0.0),
            "external_write_quota": _aion_goal_engine_int_v1(preview.get("external_write_quota"), 0),
            "parallel_run_quota": _aion_goal_engine_int_v1(preview.get("parallel_run_quota"), 0),
            "external_write_allowed": preview.get("external_write_allowed") is True,
            "budgetless_spend_blocked": preview.get("budgetless_spend_blocked") is True,
            "over_budget": preview.get("over_budget") is True,
            "token_limit_exceeded": preview.get("token_limit_exceeded") is True,
            "runtime_limit_exceeded": preview.get("runtime_limit_exceeded") is True,
            "warning_threshold_reached": preview.get("warning_threshold_reached") is True,
            "recommended_action": str(preview.get("recommended_action") or "review_before_live_execution"),
            "dry_run_only": True,
            "grants_permission": False,
        })

    return rows


def _aion_goal_engine_resource_cost_summary_v1(manifest):
    rows = _aion_goal_engine_resource_cost_rows_v1(manifest)

    goal_budget_total = sum(row["goal_budget"] for row in rows if row["goal_budget"] > 0)
    estimated_cost_total = sum(row["estimated_cost"] for row in rows)
    token_quota_total = sum(row["token_quota"] for row in rows)
    estimated_tokens_total = sum(row["estimated_tokens"] for row in rows)
    runtime_quota_minutes_total = sum(row["runtime_quota_minutes"] for row in rows)
    estimated_runtime_minutes_total = sum(row["estimated_runtime_minutes"] for row in rows)

    budgetless_spend_blocked = any(row["budgetless_spend_blocked"] for row in rows)
    over_budget = any(row["over_budget"] for row in rows)
    token_limit_exceeded = any(row["token_limit_exceeded"] for row in rows)
    runtime_limit_exceeded = any(row["runtime_limit_exceeded"] for row in rows)
    external_write_allowed = any(row["external_write_allowed"] for row in rows)

    recommended_action = "review_before_live_execution"
    if budgetless_spend_blocked:
        recommended_action = "do_not_run_budget_required"
    elif over_budget:
        recommended_action = "do_not_run_over_budget"
    elif token_limit_exceeded:
        recommended_action = "do_not_run_token_quota_exceeded"
    elif runtime_limit_exceeded:
        recommended_action = "do_not_run_runtime_quota_exceeded"
    elif any(row["warning_threshold_reached"] for row in rows):
        recommended_action = "pause_for_budget_review"

    return {
        "schema_version": "aion.goal_engine.boardroom_resource_cost_governance.v1",
        "runtime": "aion_goal_engine",
        "rows": rows,
        "goal_budget_total": round(goal_budget_total, 6),
        "estimated_cost_total": round(estimated_cost_total, 6),
        "budget_remaining_total": round(goal_budget_total - estimated_cost_total, 6),
        "token_quota_total": token_quota_total,
        "estimated_tokens_total": estimated_tokens_total,
        "runtime_quota_minutes_total": round(runtime_quota_minutes_total, 6),
        "estimated_runtime_minutes_total": round(estimated_runtime_minutes_total, 6),
        "external_write_allowed": external_write_allowed,
        "budgetless_spend_blocked": budgetless_spend_blocked,
        "over_budget": over_budget,
        "token_limit_exceeded": token_limit_exceeded,
        "runtime_limit_exceeded": runtime_limit_exceeded,
        "hard_stop_at_limit": True,
        "pause_at_warning_threshold": True,
        "recommended_action": recommended_action,
        "dry_run_only": True,
        "grants_permission": False,
        "would_grant_permission": False,
    }


_aion_previous_build_goal_engine_boardroom_trace_resource_cost_v1 = build_goal_engine_boardroom_trace


def build_goal_engine_boardroom_trace(manifest):
    trace = _aion_previous_build_goal_engine_boardroom_trace_resource_cost_v1(manifest)

    if not isinstance(trace, dict):
        trace = {}

    if not isinstance(manifest, dict):
        return trace

    governance = _aion_goal_engine_resource_cost_summary_v1(manifest)
    if not governance["rows"]:
        return trace

    trace["resource_cost_governance"] = governance
    trace["budget_status"] = {
        "estimated_cost_total": governance["estimated_cost_total"],
        "goal_budget_total": governance["goal_budget_total"],
        "budget_remaining_total": governance["budget_remaining_total"],
        "budgetless_spend_blocked": governance["budgetless_spend_blocked"],
        "over_budget": governance["over_budget"],
        "token_limit_exceeded": governance["token_limit_exceeded"],
        "runtime_limit_exceeded": governance["runtime_limit_exceeded"],
        "external_write_allowed": governance["external_write_allowed"],
        "recommended_action": governance["recommended_action"],
        "dry_run_only": True,
        "grants_permission": False,
    }

    fields = trace.get("boardroom_visibility_fields")
    if not isinstance(fields, list):
        fields = []
    for field in ("budget_status", "resource_cost_governance"):
        if field not in fields:
            fields.append(field)
    trace["boardroom_visibility_fields"] = fields

    events = trace.get("events")
    if not isinstance(events, list):
        events = []
    for row in governance["rows"]:
        events.append({
            "event_type": "goal_engine.resource_cost_governance_visible",
            "node_id": row["node_id"],
            "node_kind": row["node_kind"],
            "estimated_cost": row["estimated_cost"],
            "goal_budget": row["goal_budget"],
            "budgetless_spend_blocked": row["budgetless_spend_blocked"],
            "recommended_action": row["recommended_action"],
            "dry_run_only": True,
            "grants_permission": False,
        })
    trace["events"] = events

    return trace

# AION PATCH: Goal Engine Boardroom learning + human feedback visibility v1
def _aion_goal_engine_trace_rows_learning_feedback_v1(trace, manifest):
    rows = []

    if isinstance(trace, dict):
        for key in ("goal_engine_steps", "manifest_steps", "trace", "goal_engine_step_trace"):
            value = trace.get(key)
            if isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))

    if isinstance(manifest, dict):
        for key in ("goal_engine_step_trace", "trace", "steps"):
            value = manifest.get(key)
            if isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))

    deduped = []
    seen = set()
    for row in rows:
        marker = (
            str(row.get("node_id") or row.get("id") or ""),
            str(row.get("node_kind") or row.get("step_type") or row.get("kind") or ""),
            str(row.get("index") or ""),
        )
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(row)

    return deduped


def _aion_goal_engine_preview_from_row_v1(row, key):
    if not isinstance(row, dict):
        return {}

    preview = row.get(key)
    if isinstance(preview, dict):
        return preview

    payload = row.get("payload")
    if isinstance(payload, dict) and isinstance(payload.get(key), dict):
        return payload.get(key)

    return {}


def _aion_goal_engine_list_unique_v1(values):
    out = []
    for value in values:
        if isinstance(value, list):
            nested = value
        else:
            nested = [value]

        for item in nested:
            if item is None:
                continue
            safe = str(item).strip()
            if safe and safe not in out:
                out.append(safe)

    return out


_aion_previous_build_goal_engine_boardroom_trace_learning_feedback_v1 = build_goal_engine_boardroom_trace


def build_goal_engine_boardroom_trace(manifest):
    trace = _aion_previous_build_goal_engine_boardroom_trace_learning_feedback_v1(manifest)

    if not isinstance(trace, dict):
        trace = {}

    rows = _aion_goal_engine_trace_rows_learning_feedback_v1(trace, manifest)

    learning_previews = [
        _aion_goal_engine_preview_from_row_v1(row, "learning_reflection_preview")
        for row in rows
    ]
    learning_previews = [item for item in learning_previews if item]

    feedback_previews = [
        _aion_goal_engine_preview_from_row_v1(row, "human_feedback_preview")
        for row in rows
    ]
    feedback_previews = [item for item in feedback_previews if item]

    reflection_summaries = _aion_goal_engine_list_unique_v1(
        item.get("reflection_summary") for item in learning_previews
    )
    winning_patterns = _aion_goal_engine_list_unique_v1(
        item.get("winning_patterns") for item in learning_previews
    )
    failed_patterns = _aion_goal_engine_list_unique_v1(
        item.get("failed_patterns") for item in learning_previews
    )
    blocked_reasons = _aion_goal_engine_list_unique_v1(
        item.get("learning_blocked_reason") for item in learning_previews
    )

    confidence_values = []
    for item in learning_previews:
        try:
            confidence_values.append(float(item.get("memory_confidence", 0.0)))
        except Exception:
            pass

    learning_summary = {
        "schema_version": "aion.goal_engine.boardroom_learning_summary.v1",
        "preview_count": len(learning_previews),
        "would_write_memory_count": sum(1 for item in learning_previews if item.get("would_write_memory") is True),
        "bridge_to_prior_bank_count": sum(1 for item in learning_previews if item.get("bridge_to_prior_bank") is True),
        "reflection_summaries": reflection_summaries,
        "winning_patterns": winning_patterns,
        "failed_patterns": failed_patterns,
        "learning_blocked_reasons": blocked_reasons,
        "memory_confidence_max": max(confidence_values) if confidence_values else 0.0,
        "learned_memory_grants_permission": False,
        "can_execute_from_memory": False,
        "dry_run_only": True,
        "grants_permission": False,
    }

    feedback_categories = _aion_goal_engine_list_unique_v1(
        item.get("feedback_category") for item in feedback_previews
    )

    human_feedback_summary = {
        "schema_version": "aion.goal_engine.boardroom_human_feedback_summary.v1",
        "preview_count": len(feedback_previews),
        "feedback_required_count": sum(1 for item in feedback_previews if item.get("feedback_required") is True),
        "feedback_categories": feedback_categories,
        "allow_learning_count": sum(1 for item in feedback_previews if item.get("allow_learning") is True),
        "do_not_learn_count": sum(1 for item in feedback_previews if item.get("do_not_learn_from_this") is True),
        "negative_feedback_grants_permission": False,
        "dry_run_only": True,
        "grants_permission": False,
    }

    trace["learning_summary"] = learning_summary
    trace["human_feedback_summary"] = human_feedback_summary

    fields = trace.get("boardroom_visibility_fields")
    if not isinstance(fields, list):
        fields = []

    for field in ("learning_summary", "human_feedback_summary"):
        if field not in fields:
            fields.append(field)

    trace["boardroom_visibility_fields"] = fields

    events = trace.get("events")
    if not isinstance(events, list):
        events = []

    events.append({
        "event_type": "goal_engine.learning_visible",
        "would_write_memory_count": learning_summary["would_write_memory_count"],
        "learned_memory_grants_permission": False,
        "can_execute_from_memory": False,
    })
    events.append({
        "event_type": "goal_engine.human_feedback_visible",
        "feedback_required_count": human_feedback_summary["feedback_required_count"],
        "negative_feedback_grants_permission": False,
    })

    trace["events"] = events

    return trace

# AION PATCH: Goal Engine Boardroom human feedback source-config fallback v2
_aion_previous_build_goal_engine_boardroom_trace_feedback_source_v2 = build_goal_engine_boardroom_trace


def _aion_goal_engine_bool_feedback_v2(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return default


def _aion_goal_engine_feedback_config_from_row_v2(row):
    if not isinstance(row, dict):
        return {}

    merged = {}

    for key in ("source_config", "config", "payload", "contract"):
        value = row.get(key)
        if isinstance(value, dict):
            merged.update(value)
            nested_source = value.get("source_config")
            if isinstance(nested_source, dict):
                merged.update(nested_source)
            nested_config = value.get("config")
            if isinstance(nested_config, dict):
                merged.update(nested_config)

    merged.update({
        key: value
        for key, value in row.items()
        if key in {
            "feedback_required",
            "feedback_category",
            "allow_learning",
            "do_not_learn_from_this",
            "rating",
            "feedback_comment",
        }
    })

    return merged


def build_goal_engine_boardroom_trace(manifest):
    trace = _aion_previous_build_goal_engine_boardroom_trace_feedback_source_v2(manifest)

    if not isinstance(trace, dict):
        trace = {}

    rows = _aion_goal_engine_trace_rows_learning_feedback_v1(trace, manifest)

    existing = trace.get("human_feedback_summary")
    if not isinstance(existing, dict):
        existing = {
            "schema_version": "aion.goal_engine.boardroom_human_feedback_summary.v1",
            "preview_count": 0,
            "feedback_required_count": 0,
            "feedback_categories": [],
            "allow_learning_count": 0,
            "do_not_learn_count": 0,
            "negative_feedback_grants_permission": False,
            "dry_run_only": True,
            "grants_permission": False,
        }

    feedback_required_count = int(existing.get("feedback_required_count") or 0)
    allow_learning_count = int(existing.get("allow_learning_count") or 0)
    do_not_learn_count = int(existing.get("do_not_learn_count") or 0)

    categories = list(existing.get("feedback_categories") or [])

    for row in rows:
        preview = _aion_goal_engine_preview_from_row_v1(row, "human_feedback_preview")
        config = _aion_goal_engine_feedback_config_from_row_v2(row)

        feedback_required = (
            preview.get("feedback_required")
            if isinstance(preview, dict) and preview.get("feedback_required") is not None
            else config.get("feedback_required")
        )

        allow_learning = (
            preview.get("allow_learning")
            if isinstance(preview, dict) and preview.get("allow_learning") is not None
            else config.get("allow_learning")
        )

        do_not_learn = (
            preview.get("do_not_learn_from_this")
            if isinstance(preview, dict) and preview.get("do_not_learn_from_this") is not None
            else config.get("do_not_learn_from_this")
        )

        category = (
            preview.get("feedback_category")
            if isinstance(preview, dict) and preview.get("feedback_category")
            else config.get("feedback_category")
        )

        if _aion_goal_engine_bool_feedback_v2(feedback_required, False):
            feedback_required_count += 1

        if _aion_goal_engine_bool_feedback_v2(allow_learning, False):
            allow_learning_count += 1

        if _aion_goal_engine_bool_feedback_v2(do_not_learn, False):
            do_not_learn_count += 1

        if category:
            safe_category = str(category).strip()
            if safe_category and safe_category not in categories:
                categories.append(safe_category)

    existing["feedback_required_count"] = feedback_required_count
    existing["allow_learning_count"] = allow_learning_count
    existing["do_not_learn_count"] = do_not_learn_count
    existing["feedback_categories"] = categories
    existing["negative_feedback_grants_permission"] = False
    existing["dry_run_only"] = True
    existing["grants_permission"] = False

    trace["human_feedback_summary"] = existing

    fields = trace.get("boardroom_visibility_fields")
    if not isinstance(fields, list):
        fields = []
    if "human_feedback_summary" not in fields:
        fields.append("human_feedback_summary")
    trace["boardroom_visibility_fields"] = fields

    return trace

# AION PATCH: Goal Engine Boardroom human feedback deep scan repair v3
_aion_previous_build_goal_engine_boardroom_trace_feedback_deep_v3 = build_goal_engine_boardroom_trace


def _aion_goal_engine_deep_find_feedback_configs_v3(value, *, _depth=0):
    if _depth > 8:
        return []

    found = []

    if isinstance(value, dict):
        has_feedback_keys = any(
            key in value
            for key in (
                "feedback_required",
                "feedback_category",
                "allow_learning",
                "do_not_learn_from_this",
                "rating",
                "feedback_comment",
                "human_feedback_preview",
            )
        )

        if has_feedback_keys:
            found.append(value)

        for child in value.values():
            found.extend(_aion_goal_engine_deep_find_feedback_configs_v3(child, _depth=_depth + 1))

    elif isinstance(value, list):
        for item in value:
            found.extend(_aion_goal_engine_deep_find_feedback_configs_v3(item, _depth=_depth + 1))

    return found


def _aion_goal_engine_bool_feedback_v3(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return default


def build_goal_engine_boardroom_trace(manifest):
    trace = _aion_previous_build_goal_engine_boardroom_trace_feedback_deep_v3(manifest)

    if not isinstance(trace, dict):
        trace = {}

    existing = trace.get("human_feedback_summary")
    if not isinstance(existing, dict):
        existing = {}

    configs = []
    configs.extend(_aion_goal_engine_deep_find_feedback_configs_v3(manifest))
    configs.extend(_aion_goal_engine_deep_find_feedback_configs_v3(trace))

    feedback_required_count = int(existing.get("feedback_required_count") or 0)
    allow_learning_count = int(existing.get("allow_learning_count") or 0)
    do_not_learn_count = int(existing.get("do_not_learn_count") or 0)
    categories = list(existing.get("feedback_categories") or [])

    seen = set()

    for config in configs:
        if not isinstance(config, dict):
            continue

        preview = config.get("human_feedback_preview")
        if isinstance(preview, dict):
            merged = {**config, **preview}
        else:
            merged = dict(config)

        key = (
            str(merged.get("feedback_category") or ""),
            str(merged.get("feedback_required") or ""),
            str(merged.get("allow_learning") or ""),
            str(merged.get("do_not_learn_from_this") or ""),
            str(merged.get("rating") or ""),
        )

        if key in seen:
            continue
        seen.add(key)

        if _aion_goal_engine_bool_feedback_v3(merged.get("feedback_required"), False):
            feedback_required_count += 1

        if _aion_goal_engine_bool_feedback_v3(merged.get("allow_learning"), False):
            allow_learning_count += 1

        if _aion_goal_engine_bool_feedback_v3(merged.get("do_not_learn_from_this"), False):
            do_not_learn_count += 1

        category = merged.get("feedback_category")
        if category:
            safe_category = str(category).strip()
            if safe_category and safe_category not in categories:
                categories.append(safe_category)

    trace["human_feedback_summary"] = {
        "schema_version": "aion.goal_engine.boardroom_human_feedback_summary.v1",
        **existing,
        "preview_count": max(int(existing.get("preview_count") or 0), len(seen)),
        "feedback_required_count": feedback_required_count,
        "feedback_categories": categories,
        "allow_learning_count": allow_learning_count,
        "do_not_learn_count": do_not_learn_count,
        "negative_feedback_grants_permission": False,
        "dry_run_only": True,
        "grants_permission": False,
    }

    fields = trace.get("boardroom_visibility_fields")
    if not isinstance(fields, list):
        fields = []
    if "human_feedback_summary" not in fields:
        fields.append("human_feedback_summary")
    trace["boardroom_visibility_fields"] = fields

    events = trace.get("events")
    if not isinstance(events, list):
        events = []

    if not any(isinstance(event, dict) and event.get("event_type") == "goal_engine.human_feedback_visible" for event in events):
        events.append({
            "event_type": "goal_engine.human_feedback_visible",
            "dry_run_only": True,
            "grants_permission": False,
            "feedback_required_count": feedback_required_count,
        })

    trace["events"] = events

    return trace

# AION PATCH: Goal Engine Boardroom red-team safety visibility v1
_aion_previous_build_goal_engine_boardroom_trace_red_team_visibility_v1 = build_goal_engine_boardroom_trace


def _aion_goal_engine_float_red_team_boardroom_v1(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _aion_goal_engine_bool_red_team_boardroom_v1(value, default=False):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "unsafe", "blocked"}
    if value is None:
        return default
    return bool(value)


def _aion_goal_engine_list_red_team_boardroom_v1(value):
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        return [value] if value.strip() else []
    if value is None:
        return []
    return [value]


def _aion_goal_engine_deep_find_red_team_configs_v1(value, *, _depth=0):
    if _depth > 8:
        return []

    found = []

    if isinstance(value, dict):
        preview = value.get("red_team_safety_preview")
        if isinstance(preview, dict):
            found.append(preview)

        has_red_team_shape = any(
            key in value
            for key in (
                "unsafe_goal",
                "unsafe_goal_blocked",
                "safety_classification",
                "risk_score",
                "blocked_reasons",
                "safety_blocked_reasons",
            )
        )

        if has_red_team_shape:
            found.append(value)

        for child in value.values():
            found.extend(_aion_goal_engine_deep_find_red_team_configs_v1(child, _depth=_depth + 1))

    elif isinstance(value, list):
        for item in value:
            found.extend(_aion_goal_engine_deep_find_red_team_configs_v1(item, _depth=_depth + 1))

    return found


def _aion_goal_engine_node_id_from_red_team_item_v1(item, fallback_index=0):
    if not isinstance(item, dict):
        return f"goal_engine_red_team_{fallback_index + 1}"

    return str(
        item.get("node_id")
        or item.get("id")
        or item.get("goal_id")
        or item.get("loop_id")
        or item.get("experiment_id")
        or f"goal_engine_red_team_{fallback_index + 1}"
    )


def build_goal_engine_boardroom_trace(manifest):
    trace = _aion_previous_build_goal_engine_boardroom_trace_red_team_visibility_v1(manifest)

    if not isinstance(trace, dict):
        trace = {}

    configs = []
    configs.extend(_aion_goal_engine_deep_find_red_team_configs_v1(manifest))
    configs.extend(_aion_goal_engine_deep_find_red_team_configs_v1(trace))

    rows = []
    blocked_reasons = []
    highest_risk_score = 0.0
    unsafe_goal_blocked_count = 0

    seen = set()

    for index, item in enumerate(configs):
        if not isinstance(item, dict):
            continue

        node_id = _aion_goal_engine_node_id_from_red_team_item_v1(item, index)
        risk_score = max(
            0.0,
            min(
                _aion_goal_engine_float_red_team_boardroom_v1(item.get("risk_score"), 0.0),
                1.0,
            ),
        )

        item_blocked_reasons = _aion_goal_engine_list_red_team_boardroom_v1(
            item.get("blocked_reasons") or item.get("safety_blocked_reasons") or []
        )

        safety_classification = str(
            item.get("safety_classification") or "safe"
        ).strip().lower()

        unsafe_goal_blocked = (
            _aion_goal_engine_bool_red_team_boardroom_v1(item.get("unsafe_goal_blocked"), False)
            or _aion_goal_engine_bool_red_team_boardroom_v1(item.get("unsafe_goal"), False)
            or safety_classification in {"unsafe", "blocked", "high_risk"}
            or risk_score >= 0.8
            or bool(item_blocked_reasons)
        )

        signature = (
            node_id,
            risk_score,
            safety_classification,
            tuple(str(reason) for reason in item_blocked_reasons),
            unsafe_goal_blocked,
        )
        if signature in seen:
            continue
        seen.add(signature)

        if unsafe_goal_blocked:
            unsafe_goal_blocked_count += 1

        highest_risk_score = max(highest_risk_score, risk_score)

        for reason in item_blocked_reasons:
            reason_text = str(reason)
            if reason_text and reason_text not in blocked_reasons:
                blocked_reasons.append(reason_text)

        rows.append({
            "node_id": node_id,
            "risk_score": risk_score,
            "safety_classification": "unsafe" if unsafe_goal_blocked else safety_classification,
            "unsafe_goal_blocked": unsafe_goal_blocked,
            "blocked_reasons": [str(reason) for reason in item_blocked_reasons],
            "recommended_action": "block_before_execution" if unsafe_goal_blocked else "review_before_live_execution",
            "dry_run_only": True,
            "external_write_performed": False,
            "grants_permission": False,
            "would_grant_permission": False,
        })

    recommended_action = (
        "block_before_execution"
        if unsafe_goal_blocked_count > 0 or highest_risk_score >= 0.8
        else "review_before_live_execution"
    )

    summary = {
        "schema_version": "aion.goal_engine.boardroom_red_team_safety_summary.v1",
        "runtime": "aion_goal_engine",
        "unsafe_goal_blocked_count": unsafe_goal_blocked_count,
        "highest_risk_score": highest_risk_score,
        "blocked_reasons": blocked_reasons,
        "recommended_action": recommended_action,
        "rows": rows,
        "dry_run_only": True,
        "external_write_performed": False,
        "grants_permission": False,
        "would_grant_permission": False,
    }

    trace["red_team_safety_summary"] = summary

    fields = trace.get("boardroom_visibility_fields")
    if not isinstance(fields, list):
        fields = []
    if "red_team_safety_summary" not in fields:
        fields.append("red_team_safety_summary")
    trace["boardroom_visibility_fields"] = fields

    events = trace.get("events")
    if not isinstance(events, list):
        events = []

    if not any(isinstance(event, dict) and event.get("event_type") == "goal_engine.red_team_safety_visible" for event in events):
        events.append({
            "event_type": "goal_engine.red_team_safety_visible",
            "unsafe_goal_blocked_count": unsafe_goal_blocked_count,
            "highest_risk_score": highest_risk_score,
            "recommended_action": recommended_action,
            "dry_run_only": True,
            "external_write_performed": False,
            "grants_permission": False,
        })

    trace["events"] = events

    return trace
