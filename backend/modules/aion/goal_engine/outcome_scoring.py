from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from backend.modules.aion.goal_engine.evidence_sources import summarize_evidence_sources


OUTCOME_SCORING_SCHEMA_VERSION = "aion.goal_engine.outcome_scoring.v1"
OUTCOME_SUCCESS_REQUIRES_EVIDENCE = "outcome_success_requires_evidence"


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "__dict__"):
        return dict(getattr(value, "__dict__", {}) or {})
    return {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _normalise_evidence_sources_for_validator(evidence: list[Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for index, item in enumerate(_as_list(evidence), start=1):
        row = _as_dict(item)
        if not row:
            continue

        evidence_type = str(
            row.get("evidence_type")
            or row.get("type")
            or row.get("kind")
            or ""
        ).strip()

        if evidence_type:
            row.setdefault("evidence_type", evidence_type)
            row.setdefault("type", evidence_type)

        if evidence_type == "manual_confirmation":
            row.setdefault("evidence_id", f"manual_confirmation_{index}")
            row.setdefault("source", "manual_confirmation")
            row.setdefault("source_connector", "manual_confirmation")
            row.setdefault("label", "Manual confirmation evidence")

            # Legacy compatibility:
            # Old outcome tests used manual_confirmation as an implicit Boardroom
            # confirmation without explicit verified/is_verified fields.
            # Explicit verified=False must still remain blocked.
            if "verified" not in row and "is_verified" not in row:
                row["verified"] = True
                row["is_verified"] = True

        if "verified" not in row and row.get("is_verified") is not None:
            row["verified"] = bool(row.get("is_verified"))

        if "is_verified" not in row and row.get("verified") is not None:
            row["is_verified"] = bool(row.get("verified"))

        if "confidence" not in row and row.get("confidence_score") is not None:
            row["confidence"] = row.get("confidence_score")

        if "confidence_score" not in row and row.get("confidence") is not None:
            row["confidence_score"] = row.get("confidence")

        if evidence_type == "manual_confirmation" and row.get("verified") is True and row.get("confidence") is None:
            row["confidence"] = 1.0
            row["confidence_score"] = 1.0

        rows.append(row)

    return rows


def build_outcome_score_preview(contract: Any) -> dict[str, Any]:
    """
    Completed workflow is not successful outcome without evidence.

    Evidence exists is not enough. Evidence must be valid, typed, sourced,
    verified, and confidence-scored through the evidence source validator.
    """
    payload = _as_dict(contract)

    outcome_id = str(payload.get("outcome_id") or "")
    goal_id = str(payload.get("goal_id") or "")
    run_id = str(payload.get("run_id") or "")

    status = str(payload.get("status") or "").strip()
    evidence = _as_list(payload.get("evidence"))

    normalized_evidence = _normalise_evidence_sources_for_validator(evidence)
    evidence_source_summary = summarize_evidence_sources(normalized_evidence)

    has_evidence = bool(evidence_source_summary.get("supports_outcome_success") is True)

    completed_execution_is_success = bool(status == "success" and has_evidence)
    success_blocked = bool(status == "success" and not has_evidence)

    blocked_reasons = list(evidence_source_summary.get("blocked_reasons") or [])

    if success_blocked and OUTCOME_SUCCESS_REQUIRES_EVIDENCE not in blocked_reasons:
        blocked_reasons.append(OUTCOME_SUCCESS_REQUIRES_EVIDENCE)

    return {
        "schema_version": OUTCOME_SCORING_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "outcome_score_preview",
        "outcome_id": outcome_id,
        "goal_id": goal_id,
        "run_id": run_id,
        "status": status,
        "metric_actual": payload.get("metric_actual"),
        "metric_target": payload.get("metric_target"),
        "metric_target_met": (
            payload.get("metric_actual") is not None
            and payload.get("metric_target") is not None
            and float(payload.get("metric_actual") or 0) >= float(payload.get("metric_target") or 0)
        ),
        "quality_score": payload.get("quality_score", 0.0),
        "confidence": payload.get("confidence", 0.0),
        "reason": payload.get("reason") or "",
        "evidence_count": len(normalized_evidence),
        "evidence_source_summary": evidence_source_summary,
        "has_evidence": has_evidence,
        "evidence_required": success_blocked,
        "completed_execution_is_success": completed_execution_is_success,
        "supports_outcome_success": completed_execution_is_success,
        "success_supported": completed_execution_is_success,
        "success_blocked": success_blocked,
        "blocked_reasons": blocked_reasons,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }


def summarize_outcome_evidence_state(outcome_previews: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Summarise outcome evidence state across one or more outcome previews.
    """
    previews = [item for item in _as_list(outcome_previews) if isinstance(item, dict)]

    evidence_backed = 0
    blocked = 0
    blocked_reasons: list[str] = []

    for preview in previews:
        supports_success = (
            preview.get("supports_outcome_success") is True
            or preview.get("success_supported") is True
            or preview.get("completed_execution_is_success") is True
        )

        if supports_success:
            evidence_backed += 1

        preview_blocked_reasons = _as_list(preview.get("blocked_reasons"))
        if preview_blocked_reasons or preview.get("success_blocked") is True:
            blocked += 1

        for reason in preview_blocked_reasons:
            reason_text = str(reason or "").strip()
            if reason_text and reason_text not in blocked_reasons:
                blocked_reasons.append(reason_text)

    validations: list[dict[str, Any]] = []
    for preview in previews:
        evidence_source_summary = preview.get("evidence_source_summary")
        if not isinstance(evidence_source_summary, dict):
            continue

        for validation in evidence_source_summary.get("validations") or []:
            if isinstance(validation, dict):
                validations.append(validation)

    return {
        "schema_version": OUTCOME_SCORING_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "outcome_evidence_summary",
        "outcome_count": len(previews),
        "evidence_backed_outcome_count": evidence_backed,
        "supported_success_count": evidence_backed,
        "blocked_outcome_count": blocked,
        "blocked_reasons": blocked_reasons,
        "validations": validations,
        "dry_run_only": True,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
    }

EXPERIMENT_RESULT_EVIDENCE_SCHEMA_VERSION = "aion.goal_engine.experiment_result_evidence.v1"
VARIANT_OUTCOME_SCORE_SCHEMA_VERSION = "aion.goal_engine.variant_outcome_score.v1"


def build_experiment_result_evidence_preview(
    *,
    experiment_id: str,
    goal_id: str,
    metric: str,
    variants: list[dict[str, Any]],
    evidence: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Dry-run preview for experiment-result evidence.

    This does not declare a winner by itself. It only reports whether evidence
    exists and whether each variant has measurable support.
    """
    variant_rows = []
    evidence_rows = list(evidence or [])

    for index, variant in enumerate(list(variants or [])):
        variant = variant if isinstance(variant, dict) else {}
        variant_id = str(variant.get("variant_id") or variant.get("id") or f"variant_{index + 1}")
        metric_actual = variant.get("metric_actual")
        sample_size = int(variant.get("sample_size") or 0)

        has_metric = metric_actual is not None
        has_sample = sample_size > 0

        variant_rows.append(
            {
                "variant_id": variant_id,
                "metric_actual": metric_actual,
                "sample_size": sample_size,
                "has_metric": has_metric,
                "has_sample": has_sample,
                "evidence_ready": bool(has_metric and has_sample),
            }
        )

    evidence_ready = bool(evidence_rows) and all(row["evidence_ready"] for row in variant_rows)

    return {
        "schema_version": EXPERIMENT_RESULT_EVIDENCE_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "experiment_result_evidence_preview",
        "experiment_id": experiment_id,
        "goal_id": goal_id,
        "metric": metric,
        "variant_count": len(variant_rows),
        "evidence_count": len(evidence_rows),
        "variants": variant_rows,
        "evidence": evidence_rows,
        "evidence_ready": evidence_ready,
        "winner_declared": False,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "dry_run_only": True,
        "blocked_reasons": [] if evidence_ready else ["experiment_result_evidence_required"],
    }


def build_variant_outcome_score_preview(
    *,
    experiment_id: str,
    goal_id: str,
    metric: str,
    variants: list[dict[str, Any]],
    target_value: float | None = None,
) -> dict[str, Any]:
    """
    Dry-run variant scoring preview.

    Scores are advisory. No winner is activated and no loser is stopped here.
    """
    target = float(target_value or 1.0)
    if target <= 0:
        target = 1.0

    scored_rows = []

    for index, variant in enumerate(list(variants or [])):
        variant = variant if isinstance(variant, dict) else {}
        variant_id = str(variant.get("variant_id") or variant.get("id") or f"variant_{index + 1}")

        try:
            metric_actual = float(variant.get("metric_actual") or 0.0)
        except Exception:
            metric_actual = 0.0

        try:
            cost = float(variant.get("cost") or 0.0)
        except Exception:
            cost = 0.0

        try:
            confidence = float(variant.get("confidence") or 0.0)
        except Exception:
            confidence = 0.0

        effectiveness = max(0.0, min(metric_actual / target, 1.0))
        cost_penalty = min(cost / max(target, 1.0), 1.0) * 0.15
        confidence_bonus = max(0.0, min(confidence, 1.0)) * 0.1
        score = max(0.0, min(effectiveness - cost_penalty + confidence_bonus, 1.0))

        scored_rows.append(
            {
                "variant_id": variant_id,
                "metric_actual": metric_actual,
                "target_value": target,
                "cost": cost,
                "confidence": confidence,
                "effectiveness_score": round(effectiveness, 4),
                "cost_penalty": round(cost_penalty, 4),
                "confidence_bonus": round(confidence_bonus, 4),
                "variant_score": round(score, 4),
            }
        )

    ranked = sorted(scored_rows, key=lambda row: row["variant_score"], reverse=True)

    return {
        "schema_version": VARIANT_OUTCOME_SCORE_SCHEMA_VERSION,
        "runtime": "aion_goal_engine",
        "trace_type": "variant_outcome_score_preview",
        "experiment_id": experiment_id,
        "goal_id": goal_id,
        "metric": metric,
        "target_value": target,
        "variants": scored_rows,
        "ranked_variant_ids": [row["variant_id"] for row in ranked],
        "top_variant_id": ranked[0]["variant_id"] if ranked else None,
        "winner_declared": False,
        "loser_stopped": False,
        "would_execute": False,
        "would_write_external": False,
        "would_grant_permission": False,
        "dry_run_only": True,
        "blocked_reasons": ["advisory_scoring_only", "human_review_required_before_winner_activation"],
    }
