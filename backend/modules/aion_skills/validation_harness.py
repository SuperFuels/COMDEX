from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.aion_skills.contracts import (
    SkillRunRequest,
    SkillValidationCase,
    SkillValidationResult,
)
from backend.modules.aion_skills.execution_adapter import SkillExecutionAdapter


class SkillValidationHarness:
    """
    Minimal validation harness for Phase C Sprint 1.
    Deterministic checks only.
    """

    def __init__(self, adapter: Optional[SkillExecutionAdapter] = None) -> None:
        self.adapter = adapter or SkillExecutionAdapter()

    def run_case(self, case: SkillValidationCase) -> SkillValidationResult:
        case = case.validate()

        req = SkillRunRequest.from_dict(case.request).validate()
        if req.skill_id != case.skill_id:
            req.skill_id = case.skill_id

        res = self.adapter.run(req)

        checks: Dict[str, Any] = {
            "skill_run_ok": bool(res.ok),
            "skill_id_match": res.skill_id == case.skill_id,
        }

        expected = dict(case.expected or {})

        # Optional deterministic expectations
        if "expect_ok" in expected:
            checks["expect_ok"] = bool(res.ok) == bool(expected.get("expect_ok"))

        if "require_output_keys" in expected:
            required_keys = [str(x) for x in list(expected.get("require_output_keys") or [])]
            checks["require_output_keys"] = all(k in (res.output or {}) for k in required_keys)

        if "max_latency_ms" in expected:
            try:
                max_latency = int(expected.get("max_latency_ms"))
                checks["max_latency_ms"] = int(res.latency_ms) <= max_latency
            except Exception:
                checks["max_latency_ms"] = False

        total_checks = len(checks)
        passed_checks = sum(1 for v in checks.values() if bool(v))
        pass_rate = (passed_checks / total_checks) if total_checks else 0.0
        ok = passed_checks == total_checks

        return SkillValidationResult(
            ok=ok,
            case_id=case.case_id,
            skill_id=case.skill_id,
            pass_rate=pass_rate,
            checks=checks,
            details={
                "request": req.to_dict(),
                "result": res.to_dict(),
                "expected": expected,
                "passed_checks": passed_checks,
                "total_checks": total_checks,
            },
        ).validate()