from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import hashlib
import json
import time


DEFAULT_FEEDBACK_PATH = Path(".runtime/workflow_capsules/feedback/workflow_capsule_feedback.jsonl")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


def _stable_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha3_256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
    except Exception:
        x = default
    return max(0.0, min(1.0, x))


class WorkflowCapsuleFeedbackEngine:
    """
    CAU-gated workflow capsule feedback.

    Important boundary:
      - This engine may log feedback attempts at any time.
      - It MUST NOT mutate capsule resonance/SQI unless CAU allow_learn=true
        and ADR is not active.
    """

    def __init__(
        self,
        path: Path | str = DEFAULT_FEEDBACK_PATH,
        *,
        learning_runtime: Optional[Any] = None,
        emit_learning_events: bool = True,
    ) -> None:
        self.path = Path(path)
        self.learning_runtime = learning_runtime
        self.emit_learning_events = bool(emit_learning_events)

    def apply(
        self,
        *,
        capsule: Any,
        run_result: Any,
        cau_state: Optional[Dict[str, Any]] = None,
        source: str = "workflow_capsule_feedback",
        persist_capsule: bool = False,
    ) -> Dict[str, Any]:
        cau_state = dict(cau_state or {})
        allow_learn = bool(cau_state.get("allow_learn") is True)
        adr_active = bool(cau_state.get("adr_active") is True)

        capsule_key = getattr(capsule, "canonical_key", None)
        display_name = getattr(capsule, "display_name", None)
        meta = getattr(capsule, "meta", {}) or {}
        capsule_checksum_before = meta.get("checksum") if isinstance(meta, dict) else None

        run_payload = _jsonable(run_result)
        run_ok = bool(run_payload.get("ok")) if isinstance(run_payload, dict) else False

        steps = run_payload.get("steps", []) if isinstance(run_payload, dict) else []
        total_steps = len(steps) if isinstance(steps, list) else 0

        blocked_steps = [
            s for s in steps
            if isinstance(s, dict) and s.get("status") == "blocked"
        ]
        simulated_steps = [
            s for s in steps
            if isinstance(s, dict) and s.get("status") == "simulated"
        ]

        blocked_count = len(blocked_steps)
        simulated_count = len(simulated_steps)

        if total_steps <= 0:
            quality = 0.0
        else:
            quality = simulated_count / total_steps
            if run_ok:
                quality += 0.15
            quality -= min(0.35, blocked_count * 0.08)

        quality = _clamp01(quality)

        mutation_allowed = allow_learn and not adr_active
        mutation_applied = False

        if mutation_allowed:
            resonance = getattr(capsule, "resonance", None)
            if not isinstance(resonance, dict):
                resonance = {}
                setattr(capsule, "resonance", resonance)

            old_sqi = _clamp01(resonance.get("sqi_score", 0.0))
            old_rho = _clamp01(resonance.get("ρ", 0.0))
            old_i = _clamp01(resonance.get("Ī", 0.0))

            alpha = 0.25
            new_sqi = round((1 - alpha) * old_sqi + alpha * quality, 6)
            new_rho = round((1 - alpha) * old_rho + alpha * (1.0 if run_ok else 0.25), 6)
            new_i = round((1 - alpha) * old_i + alpha * quality, 6)

            resonance["sqi_score"] = new_sqi
            resonance["ρ"] = new_rho
            resonance["Ī"] = new_i
            resonance["last_feedback_at"] = _utc_now_iso()
            resonance["last_feedback_quality"] = quality

            capsule.meta["sqi_score"] = new_sqi
            capsule.meta["ρ"] = new_rho
            capsule.meta["Ī"] = new_i
            capsule.finalize()

            if persist_capsule:
                source_path = capsule.meta.get("source_path")
                if source_path:
                    capsule.save(source_path)

            mutation_applied = True

        error_code = None
        if not run_ok:
            error_code = "workflow_run_failed"
        elif blocked_count > 0:
            error_code = "workflow_steps_blocked"

        record: Dict[str, Any] = {
            "schema_version": "aion.workflow_capsule_feedback.v1",
            "ts": _utc_now_iso(),
            "source": source,
            "canonical_key": capsule_key,
            "display_name": display_name,
            "run_id": run_payload.get("run_id") if isinstance(run_payload, dict) else None,
            "run_ok": run_ok,
            "error_code": error_code,
            "total_steps": total_steps,
            "blocked_count": blocked_count,
            "simulated_count": simulated_count,
            "quality": quality,
            "cau": {
                "allow_learn": allow_learn,
                "adr_active": adr_active,
                "deny_reason": cau_state.get("deny_reason"),
            },
            "mutation_allowed": mutation_allowed,
            "mutation_applied": mutation_applied,
            "capsule_checksum_before": capsule_checksum_before,
            "capsule_checksum_after": getattr(capsule, "meta", {}).get("checksum", None),
        }

        record["feedback_hash"] = _stable_hash({
            k: v for k, v in record.items() if k != "feedback_hash"
        })

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

        learning_event = self._emit_learning_event(
            capsule_key=str(capsule_key or "workflow:unknown.v1"),
            run_id=str(record.get("run_id") or ""),
            run_ok=run_ok,
            error_code=error_code,
            quality=quality,
            total_steps=total_steps,
            blocked_count=blocked_count,
            simulated_count=simulated_count,
            feedback_hash=record["feedback_hash"],
            cau_state=cau_state,
        )

        return {
            "ok": True,
            "path": str(self.path),
            "canonical_key": capsule_key,
            "run_id": record["run_id"],
            "quality": quality,
            "mutation_allowed": mutation_allowed,
            "mutation_applied": mutation_applied,
            "feedback_hash": record["feedback_hash"],
            "learning_event": learning_event,
        }

    def _emit_learning_event(
        self,
        *,
        capsule_key: str,
        run_id: str,
        run_ok: bool,
        error_code: Optional[str],
        quality: float,
        total_steps: int,
        blocked_count: int,
        simulated_count: int,
        feedback_hash: str,
        cau_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Optional non-breaking bridge into AionLearningRuntime.

        Uses record_skill_run(...) because the current Phase D runtime already
        treats executable observations as skill_run-style learning events.
        Metadata marks these as workflow capsule runs.
        """

        if not self.emit_learning_events:
            return {"ok": True, "emitted": False, "reason": "disabled"}

        runtime = self.learning_runtime
        if runtime is None:
            try:
                from backend.modules.aion_learning.runtime import AionLearningRuntime
                runtime = AionLearningRuntime()
            except Exception as exc:
                return {
                    "ok": False,
                    "emitted": False,
                    "non_blocking": True,
                    "error": f"{type(exc).__name__}: {exc}",
                }

        try:
            event = runtime.record_skill_run(
                skill_id=capsule_key,
                skill_run_id=run_id or f"workflow_run_{int(time.time())}",
                ok=bool(run_ok),
                error_code=error_code,
                latency_ms=0,
                metadata={
                    "kind": "workflow_capsule_run",
                    "source": "workflow_capsule_feedback",
                    "feedback_hash": feedback_hash,
                    "quality": quality,
                    "total_steps": _safe_int(total_steps, 0),
                    "blocked_count": _safe_int(blocked_count, 0),
                    "simulated_count": _safe_int(simulated_count, 0),
                    "dry_run": True,
                    "cau": dict(cau_state or {}),
                },
            )
            return {
                "ok": True,
                "emitted": True,
                "event_id": event.get("event_id"),
                "skill_id": event.get("skill_id"),
                "event_type": event.get("event_type"),
                "path": getattr(getattr(runtime, "paths", None), "events_path", None),
            }
        except Exception as exc:
            return {
                "ok": False,
                "emitted": False,
                "non_blocking": True,
                "error": f"{type(exc).__name__}: {exc}",
            }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default

