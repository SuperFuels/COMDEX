from __future__ import annotations

import time
import uuid
from typing import Any, Dict, Optional, Tuple

from backend.modules.aion_skills.contracts import SkillRunRequest, SkillRunResult
from backend.modules.aion_skills.registry import SkillRegistry, get_global_skill_registry
from backend.modules.aion_skills.telemetry import SkillTelemetryStore, get_global_skill_telemetry

# Phase D Sprint 1 (learning runtime hooks) - additive / non-breaking
from backend.modules.aion_learning.runtime import AionLearningRuntime, get_aion_learning_runtime


class SkillExecutionAdapter:
    """
    Unified execution adapter/runtime for AION skills (Phase C).

    Adds policy gating / hardening while remaining backward compatible with the
    original Phase C Sprint 1 request/response contracts.

    Phase D Sprint 1 (additive):
      - records skill execution learning events (non-breaking)
      - does NOT alter success/failure semantics of skill execution
    """

    def __init__(
        self,
        registry: Optional[SkillRegistry] = None,
        telemetry: Optional[SkillTelemetryStore] = None,
        learning_runtime: Optional[AionLearningRuntime] = None,
    ) -> None:
        self.registry = registry or get_global_skill_registry()
        self.telemetry = telemetry or get_global_skill_telemetry()
        self.learning_runtime = learning_runtime or get_aion_learning_runtime()

    # ------------------------------------------------------------------
    # Phase D learning hook (non-breaking)
    # ------------------------------------------------------------------

    def _record_learning(self, req: SkillRunRequest, res: SkillRunResult) -> None:
        """
        Record a Phase D learning event for each completed adapter result.

        Non-breaking by design: any learning runtime error is swallowed so skill
        execution behavior remains unchanged.
        """
        try:
            self.learning_runtime.record_skill_run(
                skill_id=str(res.skill_id or req.skill_id or ""),
                skill_run_id=str(res.skill_run_id or ""),
                ok=bool(res.ok),
                error_code=(str(res.error_code) if res.error_code else None),
                latency_ms=int(res.latency_ms or 0),
                session_id=req.session_id,
                turn_id=req.turn_id,
                metadata={
                    "safety_class": getattr(res, "safety_class", None),
                    "status": getattr(res, "status", None),
                    "telemetry_ref": getattr(res, "telemetry_ref", None),
                    "request_id": getattr(req, "request_id", None),
                    "dry_run": bool(getattr(req, "dry_run", False)),
                },
            )
        except Exception:
            # Phase D Sprint 1 must never break Phase C runtime execution.
            pass

    # ------------------------------------------------------------------
    # Policy / guardrails (Phase C hardening)
    # ------------------------------------------------------------------

    def _is_skill_allowed(self, skill_id: str, request: Any) -> Tuple[bool, str]:
        """
        Registry + policy gate before execution.

        Uses registry metadata when available. Falls back safely if metadata is missing.
        """
        meta = None
        try:
            meta = self.registry.get_metadata(skill_id)
        except Exception:
            meta = None

        if meta is None:
            # If the skill exists but metadata was not attached, allow legacy behavior.
            # If it doesn't exist, the main run() path will handle skill_not_found.
            if hasattr(self.registry, "has") and callable(getattr(self.registry, "has")):
                try:
                    if not self.registry.has(skill_id):
                        return False, "skill_not_registered"
                except Exception:
                    pass
            return True, "ok"

        if not bool(getattr(meta, "enabled", True)):
            return False, "skill_disabled"

        # Phase C hardening: external side-effect skills blocked by default unless explicitly allowed.
        allow_external = False
        try:
            allow_external = bool(getattr(request, "allow_external_side_effects", False))
        except Exception:
            allow_external = False

        if str(getattr(meta, "safety_class", "")) == "external_side_effect" and not allow_external:
            return False, "external_side_effect_not_allowed"

        # Optional stricter mode: only verified/core skills allowed.
        require_verified = False
        try:
            require_verified = bool(getattr(request, "require_verified_skill", False))
        except Exception:
            require_verified = False

        stage = str(getattr(meta, "stage", "experimental") or "experimental")
        if require_verified and stage not in {"verified", "core"}:
            return False, f"skill_stage_not_verified:{stage}"

        return True, "ok"

    def _emit_telemetry_for_result(
        self,
        req: SkillRunRequest,
        res: SkillRunResult,
        extra_meta: Optional[Dict[str, Any]] = None,
    ) -> SkillRunResult:
        """
        Emit telemetry and attach telemetry_ref to the result.
        Safe even if telemetry store errors (result still returns).
        """
        meta = {"request_id": req.request_id}
        if extra_meta:
            meta.update(dict(extra_meta))

        try:
            ev = self.telemetry.emit(
                skill_run_id=res.skill_run_id,
                skill_id=res.skill_id,
                ok=res.ok,
                latency_ms=res.latency_ms,
                session_id=req.session_id,
                turn_id=req.turn_id,
                safety_class=res.safety_class,
                status=res.status,
                error_code=res.error_code,
                metadata=meta,
            )
            res.telemetry_ref = getattr(ev, "telemetry_id", None)
        except Exception:
            # Do not fail the skill result because telemetry failed.
            pass
        return res

    def _finalize_result(
        self,
        req: SkillRunRequest,
        res: SkillRunResult,
        extra_telemetry_meta: Optional[Dict[str, Any]] = None,
    ) -> SkillRunResult:
        """
        Common finalization path:
          1) emit telemetry
          2) record learning (Phase D)
          3) return result
        """
        res = self._emit_telemetry_for_result(req, res, extra_meta=extra_telemetry_meta)
        self._record_learning(req, res)
        return res

    def _deny_result(
        self,
        *,
        req: SkillRunRequest,
        skill_run_id: str,
        started: float,
        deny_reason: str,
        skill_id: Optional[str] = None,
        safety_class: str = "internal_safe",
        status: str = "experimental",
        trace_extra: Optional[Dict[str, Any]] = None,
    ) -> SkillRunResult:
        latency_ms = int((time.time() - started) * 1000)

        # ------------------------------------------------------------------
        # Normalize to contract-valid enums (deny paths often use placeholders)
        # ------------------------------------------------------------------
        status_norm = str(status or "experimental").strip()
        if status_norm not in {"experimental", "verified", "core"}:
            status_norm = "experimental"

        safety_norm = str(safety_class or "internal_safe").strip()
        allowed_safety = {
            "internal_safe",
            "read_only",
            "external_network",
            "side_effecting",
            "restricted",
            "safe_read",
            "safe_transform",
            "internal_state",
            "external_side_effect",
        }
        if safety_norm not in allowed_safety:
            safety_norm = "internal_safe"

        res = SkillRunResult(
            ok=False,
            skill_id=str(skill_id or req.skill_id),
            skill_run_id=skill_run_id,
            output={},
            error=deny_reason,
            error_code="skill_policy_blocked" if deny_reason != "skill_not_found" else "skill_not_found",
            latency_ms=latency_ms,
            safety_class=safety_norm,
            status=status_norm,
            trace={
                "adapter": "SkillExecutionAdapter",
                "phase": "phase_c_hardened_phase_d_hooked",
                "dry_run": bool(req.dry_run),
                **(trace_extra or {}),
            },
            metadata={
                "policy_blocked": True,
                "request": req.to_dict(),
                "status_source": "registry_metadata" if str(status or "").strip() in {"experimental", "verified", "core"} else "deny_default",
                "requested_status": str(status) if status is not None else None,
                "safety_source": "registry_metadata" if str(safety_class or "").strip() in allowed_safety else "deny_default",
                "requested_safety_class": str(safety_class) if safety_class is not None else None,
            },
        ).validate()

        return self._finalize_result(
            req,
            res,
            extra_telemetry_meta={
                "reason": deny_reason,
                "policy_blocked": True,
                "status_source": "registry_metadata" if str(status or "").strip() in {"experimental", "verified", "core"} else "deny_default",
                "safety_source": "registry_metadata" if str(safety_class or "").strip() in allowed_safety else "deny_default",
            },
        )
    # ------------------------------------------------------------------
    # Main execution path
    # ------------------------------------------------------------------

    def run(self, req: SkillRunRequest) -> SkillRunResult:
        req = req.validate()
        started = time.time()
        skill_run_id = f"skillrun_{uuid.uuid4().hex[:16]}"

        # Policy gate before resolution/execution (uses metadata if present)
        allowed, deny_reason = self._is_skill_allowed(req.skill_id, req)
        if not allowed and deny_reason != "skill_not_registered":
            # Try to enrich with metadata if available
            meta = None
            try:
                meta = self.registry.get_metadata(req.skill_id)
            except Exception:
                meta = None

            # IMPORTANT: pass contract-safe placeholders if metadata is missing
            meta_safety = "internal_safe"
            meta_stage = "experimental"
            if meta is not None:
                try:
                    meta_safety = str(getattr(meta, "safety_class", "internal_safe") or "internal_safe")
                except Exception:
                    meta_safety = "internal_safe"
                try:
                    meta_stage = str(getattr(meta, "stage", "experimental") or "experimental")
                except Exception:
                    meta_stage = "experimental"

            return self._deny_result(
                req=req,
                skill_run_id=skill_run_id,
                started=started,
                deny_reason=deny_reason,
                skill_id=req.skill_id,
                safety_class=meta_safety,
                status=meta_stage,
                trace_extra={"policy_gate": True},
            )

        resolved = self.registry.resolve(req.skill_id)
        if not resolved:
            # IMPORTANT: use contract-safe placeholders here (not "unknown")
            return self._deny_result(
                req=req,
                skill_run_id=skill_run_id,
                started=started,
                deny_reason="skill_not_found",
                skill_id=req.skill_id,
                safety_class="internal_safe",
                status="experimental",
                trace_extra={"policy_gate": False},
            )

        spec, handler = resolved
        timeout_ms = int(req.timeout_ms_override or spec.timeout_ms)

        # Dry run path
        if req.dry_run:
            latency_ms = int((time.time() - started) * 1000)
            res = SkillRunResult(
                ok=True,
                skill_id=spec.skill_id,
                skill_run_id=skill_run_id,
                output={
                    "dry_run": True,
                    "would_execute": spec.skill_id,
                    "timeout_ms": timeout_ms,
                    "input_keys": sorted(list((req.inputs or {}).keys())),
                },
                latency_ms=latency_ms,
                safety_class=spec.safety_class,
                status=spec.status,
                trace={
                    "adapter": "SkillExecutionAdapter",
                    "phase": "phase_c_hardened_phase_d_hooked",
                    "dry_run": True,
                    "handler_name": getattr(handler, "__name__", "unknown"),
                },
                metadata={"request_id": req.request_id},
            ).validate()

            return self._finalize_result(req, res, extra_telemetry_meta={"dry_run": True})

        # Live execution path
        try:
            output = handler(dict(req.inputs or {}))
            if not isinstance(output, dict):
                output = {"result": output}

            latency_ms = int((time.time() - started) * 1000)
            res = SkillRunResult(
                ok=True,
                skill_id=spec.skill_id,
                skill_run_id=skill_run_id,
                output=output,
                latency_ms=latency_ms,
                safety_class=spec.safety_class,
                status=spec.status,
                trace={
                    "adapter": "SkillExecutionAdapter",
                    "phase": "phase_c_hardened_phase_d_hooked",
                    "timeout_ms": timeout_ms,
                    "handler_name": getattr(handler, "__name__", "unknown"),
                },
                metadata={"request_id": req.request_id},
            ).validate()

        except Exception as e:
            latency_ms = int((time.time() - started) * 1000)
            res = SkillRunResult(
                ok=False,
                skill_id=spec.skill_id,
                skill_run_id=skill_run_id,
                output={},
                error=str(e),
                error_code="skill_execution_error",
                latency_ms=latency_ms,
                safety_class=spec.safety_class,
                status=spec.status,
                trace={
                    "adapter": "SkillExecutionAdapter",
                    "phase": "phase_c_hardened_phase_d_hooked",
                    "timeout_ms": timeout_ms,
                    "handler_name": getattr(handler, "__name__", "unknown"),
                },
                metadata={"request_id": req.request_id},
            ).validate()

        return self._finalize_result(req, res)