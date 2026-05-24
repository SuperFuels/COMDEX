"""
Workflow Capsule Runner - AION Workflow Glyph Capsules v1
─────────────────────────────────────────────────────────
Single high-level orchestration path for capsule-native workflow glyphs.

Flow:
  glyph/intention key
    -> registry resolve
    -> capsule load
    -> compiled glyph expansion
    -> policy / vault / CAU evaluation
    -> dry-run preview
    -> optional approval request
    -> append execution trace
    -> CAU-gated feedback

This runner intentionally starts with dry-run-first semantics.

Approval/resume validates the gate and connector readiness. The only real
external-write path currently allowed is approval-gated Gmail draft creation.
Live Gmail send/reply/send-draft/delete remain intentionally unwired.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
import time

from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
)
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    WorkflowGlyphRegistry,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_expander import (
    WorkflowCapsuleExpander,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_policy import (
    WorkflowCapsulePolicyGate,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_dry_run import (
    WorkflowCapsuleDryRunExecutor,
)
from backend.modules.workflow_capsules.execution.workflow_capsule_trace import (
    WorkflowCapsuleTraceWriter,
)
from backend.modules.workflow_capsules.resonance.workflow_capsule_feedback import (
    WorkflowCapsuleFeedbackEngine,
)
from backend.modules.workflow_capsules.approval.workflow_capsule_approval_store import (
    WorkflowCapsuleApprovalStore,
)
from backend.modules.workflow_capsules.connectors.workflow_connector_adapter import (
    WorkflowConnectorAdapter,
)
from backend.modules.workflow_capsules.permissions.permission_evaluator import (
    PermissionEvaluator,
)
from backend.modules.workflow_capsules.permissions.permission_modes import (
    PermissionDecision,
    PermissionMode,
    RiskTier,
)
from backend.modules.workflow_capsules.permissions.permission_policy import (
    AgentPermissionProfile,
    PermissionEvaluationContext,
    WorkflowPermissionPolicy,
)
from backend.modules.workflow_capsules.call_workflow_glyph_runtime import (
    execute_call_workflow_glyph_dry_run,
)
from backend.modules.workflow_capsules.glyph_store.workflow_glyph_repository import (
    WorkflowGlyphRepository,
)


SCHEMA_VERSION = "aion.workflow_capsule_runner_result.v1"
RESUME_SCHEMA_VERSION = "aion.workflow_capsule_resume_result.v1"

EXECUTION_MODE_CONNECTOR_READY = "connector_ready"
EXECUTION_MODE_LIVE_EXECUTE = "live_execute"


@dataclass
class WorkflowCapsuleRunnerResult:
    ok: bool
    schema_version: str = SCHEMA_VERSION
    mode: str = "dry_run"

    query: str = ""
    canonical_key: Optional[str] = None
    display_name: Optional[str] = None
    run_id: Optional[str] = None

    capsule: Dict[str, Any] = field(default_factory=dict)
    expansion: Dict[str, Any] = field(default_factory=dict)
    policy: Dict[str, Any] = field(default_factory=dict)
    run: Dict[str, Any] = field(default_factory=dict)
    trace: Dict[str, Any] = field(default_factory=dict)
    feedback: Dict[str, Any] = field(default_factory=dict)
    approval: Dict[str, Any] = field(default_factory=dict)

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    t: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorkflowCapsuleRunner:
    """
    Unified dry-run runner for workflow capsules.

    Stable entrypoint for conversation/orchestrator layers once intent has
    resolved to a workflow glyph/display glyph/canonical key.
    """

    def __init__(
        self,
        *,
        registry: Optional[WorkflowGlyphRegistry] = None,
        expander: Optional[WorkflowCapsuleExpander] = None,
        policy_gate: Optional[WorkflowCapsulePolicyGate] = None,
        dry_run_executor: Optional[WorkflowCapsuleDryRunExecutor] = None,
        trace_writer: Optional[WorkflowCapsuleTraceWriter] = None,
        feedback_engine: Optional[WorkflowCapsuleFeedbackEngine] = None,
        approval_store: Optional[WorkflowCapsuleApprovalStore] = None,
        connector_adapter: Optional[WorkflowConnectorAdapter] = None,
        workflow_glyph_repository: Optional[WorkflowGlyphRepository] = None,
        persist_feedback_capsule: bool = False,
    ) -> None:
        self.registry = registry or WorkflowGlyphRegistry()
        self.expander = expander or WorkflowCapsuleExpander()
        self.policy_gate = policy_gate or WorkflowCapsulePolicyGate()
        self.dry_run_executor = dry_run_executor or WorkflowCapsuleDryRunExecutor()
        self.trace_writer = trace_writer or WorkflowCapsuleTraceWriter()
        self.feedback_engine = feedback_engine or WorkflowCapsuleFeedbackEngine()
        self.approval_store = approval_store or WorkflowCapsuleApprovalStore()
        self.connector_adapter = connector_adapter or WorkflowConnectorAdapter()
        self.workflow_glyph_repository = workflow_glyph_repository or WorkflowGlyphRepository()
        self.persist_feedback_capsule = persist_feedback_capsule

    def run_dry(
        self,
        value: str,
        *,
        inputs: Optional[Dict[str, Any]] = None,
        available_vault_requirements: Optional[List[str]] = None,
        cau_state: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
        rebuild_registry: bool = True,
        create_approval: bool = True,
    ) -> WorkflowCapsuleRunnerResult:
        """
        Resolve and dry-run a workflow capsule.

        Parameters:
          value:
            canonical_key, display_glyph, tag, alias, or semantic query.
          inputs:
            runtime inputs, e.g. {"gmail_message_id": "..."}.
          available_vault_requirements:
            vault handles currently available to this runtime.
          cau_state:
            CAU state. Learning/reinforcement only mutates when allow_learn=true.
        """

        query = str(value or "").strip()
        inputs = inputs or {}
        available_vault_requirements = available_vault_requirements or []
        cau_state = cau_state or {
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "missing_cau_state_default_deny",
        }

        errors: List[str] = []
        warnings: List[str] = []

        try:
            if rebuild_registry:
                self.registry.rebuild_and_save()

            capsule = self.registry.require(query)
            expansion = self.expander.expand(capsule)

            if not expansion.ok:
                errors.extend(expansion.errors)

            policy = self.policy_gate.evaluate(
                capsule,
                expansion,
                available_vault_requirements=available_vault_requirements,
                cau_state=cau_state,
                phase="dry_run",
            )

            if policy.warnings:
                warnings.extend(policy.warnings)
            if policy.errors:
                errors.extend(policy.errors)

            dry = self.dry_run_executor.run(
                capsule,
                expansion,
                available_vault_requirements=available_vault_requirements,
                cau_state=cau_state,
                inputs=inputs,
            )

            nested_call_workflow_glyph = self._execute_call_workflow_glyph_steps_for_dry_run(
                capsule=capsule,
                expansion=expansion,
                dry=dry,
                inputs=inputs,
                available_vault_requirements=available_vault_requirements,
                extra=extra or {},
            )

            if nested_call_workflow_glyph:
                self._attach_call_workflow_glyph_results_to_dry_run(
                    dry=dry,
                    nested_results=nested_call_workflow_glyph,
                )

            if dry.warnings:
                warnings.extend(dry.warnings)
            if dry.errors:
                errors.extend(dry.errors)

            approval = (
                self._maybe_create_approval(
                    capsule=capsule,
                    expansion=expansion,
                    policy=policy,
                    dry=dry,
                    extra=extra or {},
                )
                if create_approval
                else {}
            )

            trace = self.trace_writer.append(
                event_type="workflow_runner_dry_run_completed",
                capsule=capsule,
                expansion_result=expansion,
                policy_result=policy,
                run_result=dry,
                cau_state=cau_state,
                extra={**(extra or {}), "approval": approval},
            )

            feedback = self.feedback_engine.apply(
                capsule=capsule,
                run_result=dry,
                cau_state=cau_state,
                persist_capsule=self.persist_feedback_capsule,
            )

            warnings = list(dict.fromkeys(warnings))
            errors = list(dict.fromkeys(errors))

            ok = bool(expansion.ok and policy.ok and dry.ok and not errors)

            return WorkflowCapsuleRunnerResult(
                ok=ok,
                query=query,
                canonical_key=capsule.canonical_key,
                display_name=capsule.display_name,
                run_id=dry.run_id,
                capsule={
                    "canonical_key": capsule.canonical_key,
                    "display_name": capsule.display_name,
                    "display_glyph": capsule.display_glyph,
                    "tags": list(capsule.tags or []),
                    "vault_requirements": list(capsule.vault_requirements or []),
                    "checksum": capsule.meta.get("checksum"),
                },
                expansion=expansion.to_dict(),
                policy=policy.to_dict(),
                run={
                    **dry.to_dict(),
                    "call_workflow_glyph_runs": self._call_workflow_glyph_runs_from_dry(dry, parent_inputs=inputs),
                },
                trace=trace,
                feedback=feedback,
                approval=approval,
                errors=errors,
                warnings=warnings,
            )

        except Exception as exc:
            return WorkflowCapsuleRunnerResult(
                ok=False,
                query=query,
                errors=[f"{type(exc).__name__}: {exc}"],
                warnings=list(dict.fromkeys(warnings)),
            )

    def approve(
        self,
        approval_id: str,
        *,
        decided_by: str = "human",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.approval_store.decide(
            approval_id,
            decision="approved",
            decided_by=decided_by,
            reason=reason,
        )

    def reject(
        self,
        approval_id: str,
        *,
        decided_by: str = "human",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.approval_store.decide(
            approval_id,
            decision="rejected",
            decided_by=decided_by,
            reason=reason,
        )

    def resume_after_approval(
        self,
        approval_id: str,
        *,
        available_vault_requirements: Optional[List[str]] = None,
        cau_state: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
        rebuild_registry: bool = True,
        execution_mode: str = EXECUTION_MODE_CONNECTOR_READY,
    ) -> Dict[str, Any]:
        """
        MVP resume gate.

        This does not perform real Gmail/API send. It verifies:
          - approval exists,
          - approval is approved,
          - capsule can be loaded,
          - compiled glyph can be expanded,
          - approved external-write step exists,
          - vault requirement is available,
          - connector adapter says external write is ready.

        If all checks pass, it returns a simulated external-write-ready result.
        """

        available_vault_requirements = available_vault_requirements or []
        cau_state = cau_state or {
            "allow_learn": False,
            "adr_active": False,
            "deny_reason": "resume_after_approval_default_no_learning",
        }

        execution_mode = str(execution_mode or EXECUTION_MODE_CONNECTOR_READY).strip()

        approval = self.approval_store.get(approval_id)
        if not approval:
            return {
                "ok": False,
                "schema_version": RESUME_SCHEMA_VERSION,
                "approval_id": approval_id,
                "error": "approval_not_found",
            }

        if approval.get("status") != "approved":
            return {
                "ok": False,
                "schema_version": RESUME_SCHEMA_VERSION,
                "approval_id": approval_id,
                "status": approval.get("status"),
                "error": "approval_not_approved",
            }

        try:
            if rebuild_registry:
                self.registry.rebuild_and_save()

            capsule = self.registry.require(str(approval.get("canonical_key") or ""))

            required = list(capsule.vault_requirements or [])
            available = set(available_vault_requirements or [])
            missing = [r for r in required if r not in available]

            if missing:
                return {
                    "ok": False,
                    "schema_version": RESUME_SCHEMA_VERSION,
                    "approval_id": approval_id,
                    "canonical_key": capsule.canonical_key,
                    "error": "missing_vault_requirements",
                    "missing_vault_requirements": missing,
                }

            expansion = self.expander.expand(capsule)
            if not expansion.ok:
                return {
                    "ok": False,
                    "schema_version": RESUME_SCHEMA_VERSION,
                    "approval_id": approval_id,
                    "canonical_key": capsule.canonical_key,
                    "error": "expansion_failed",
                    "errors": list(expansion.errors or []),
                    "warnings": list(expansion.warnings or []),
                }

            send_step = self._resolve_external_write_step(
                expansion=expansion,
                preferred_step_id=approval.get("external_write_step_id"),
            )

            if send_step is None:
                return {
                    "ok": False,
                    "schema_version": RESUME_SCHEMA_VERSION,
                    "approval_id": approval_id,
                    "canonical_key": capsule.canonical_key,
                    "error": "external_write_step_not_found",
                }

            permission_result = self._evaluate_resume_permission(
                capsule=capsule,
                step=send_step,
                execution_mode=execution_mode,
            )
            if permission_result.decision == PermissionDecision.BLOCK:
                return {
                    "ok": False,
                    "schema_version": RESUME_SCHEMA_VERSION,
                    "approval_id": approval_id,
                    "canonical_key": capsule.canonical_key,
                    "execution_mode": execution_mode,
                    "connector_ready": False,
                    "error": "permission_blocked",
                    "permission": permission_result.to_dict(),
                    "risk_tier": permission_result.audit.get("risk_tier"),
                    "decision": permission_result.to_dict().get("decision"),
                }

            raw_step = getattr(send_step, "raw", {}) or {}
            allow_real_gmail_draft = bool((extra or {}).get("allow_real_gmail_draft") is True)

            if (
                self._is_gmail_create_draft_step(send_step)
                and execution_mode == EXECUTION_MODE_LIVE_EXECUTE
            ):
                if not allow_real_gmail_draft:
                    return {
                        "ok": False,
                        "schema_version": RESUME_SCHEMA_VERSION,
                        "phase": "resume_after_approval",
                        "execution_mode": execution_mode,
                        "approval_id": approval_id,
                        "canonical_key": capsule.canonical_key,
                        "executed_external_step": getattr(send_step, "step_id", None),
                        "status": "blocked_real_gmail_draft_not_requested",
                        "error": "real_gmail_draft_requires_explicit_request",
                        "message": "Real Gmail draft creation requires explicit allow_real_gmail_draft=true.",
                        "connector_ready": False,
                    }

                if not self._approval_has_prior_dry_run(approval):
                    return {
                        "ok": False,
                        "schema_version": RESUME_SCHEMA_VERSION,
                        "phase": "resume_after_approval",
                        "execution_mode": execution_mode,
                        "approval_id": approval_id,
                        "canonical_key": capsule.canonical_key,
                        "executed_external_step": getattr(send_step, "step_id", None),
                        "status": "blocked_missing_prior_dry_run",
                        "error": "dry_run_required_before_real_gmail_draft",
                        "message": "A dry-run approval payload is required before creating a real Gmail draft.",
                        "connector_ready": False,
                    }

                connector_result = self.connector_adapter.create_draft(
                    connector=raw_step.get("connector", "gmail"),
                    step=raw_step,
                    inputs={
                        **((approval.get("payload") or {}).get("inputs") or {}),
                        **((extra or {}).get("inputs") or {}),
                    },
                    approval=approval,
                    available_vault_requirements=available_vault_requirements,
                    execution_mode=execution_mode,
                ).to_dict()
            else:
                connector_result = self.connector_adapter.external_write_ready(
                    connector=raw_step.get("connector", "gmail"),
                    step=raw_step,
                    approval=approval,
                    available_vault_requirements=available_vault_requirements,
                    execution_mode=execution_mode,
                ).to_dict()

            ok = bool(connector_result.get("ok"))
            return {
                "ok": ok,
                "schema_version": RESUME_SCHEMA_VERSION,
                "phase": "resume_after_approval",
                "execution_mode": execution_mode,
                "approval_id": approval_id,
                "run_id": approval.get("run_id"),
                "canonical_key": capsule.canonical_key,
                "display_name": capsule.display_name,
                "executed_external_step": getattr(send_step, "step_id", None),
                "status": connector_result.get("status"),
                "error": None if ok else connector_result.get("status"),
                "message": (connector_result.get("payload") or {}).get(
                    "message",
                    "Connector resume check completed.",
                ),
                "audit_event": {
                    "event_type": "workflow_runner_connector_resume_completed",
                    "connector": connector_result.get("connector"),
                    "action": connector_result.get("action"),
                    "status": connector_result.get("status"),
                    "sent": bool((connector_result.get("payload") or {}).get("sent") is True),
                    "must_not_send": bool((connector_result.get("payload") or {}).get("must_not_send") is True),
                    "live_send_enabled": False,
                    "approval_id": approval_id,
                    "step_id": getattr(send_step, "step_id", None),
                },
                "connector_result": connector_result,
                "permission": permission_result.to_dict(),
                "risk_tier": permission_result.audit.get("risk_tier"),
                "decision": permission_result.to_dict().get("decision"),
                "connector_ready": bool(connector_result.get("ok")),
                "cau": cau_state or {},
                "extra": extra or {},
            }

        except Exception as exc:
            return {
                "ok": False,
                "schema_version": RESUME_SCHEMA_VERSION,
                "approval_id": approval_id,
                "error": f"{type(exc).__name__}: {exc}",
            }

    @staticmethod
    def _step_action(step: Any) -> str:
        raw = step.raw if isinstance(getattr(step, "raw", None), dict) else {}
        permission = raw.get("permission") if isinstance(raw.get("permission"), dict) else {}
        return str(
            permission.get("action")
            or raw.get("action")
            or raw.get("kind")
            or getattr(step, "kind", "")
            or getattr(step, "step_id", "")
            or ""
        ).strip()

    @staticmethod
    def _is_gmail_create_draft_step(step: Any) -> bool:
        action = WorkflowCapsuleRunner._step_action(step)
        raw = step.raw if isinstance(getattr(step, "raw", None), dict) else {}
        return bool(
            action == "gmail.create_draft"
            or action == "create_draft"
            or raw.get("kind") == "create_draft"
            or getattr(step, "kind", None) == "create_draft"
        )

    @staticmethod
    def _approval_has_prior_dry_run(approval: Dict[str, Any]) -> bool:
        payload = approval.get("payload") if isinstance(approval.get("payload"), dict) else {}
        run = payload.get("run") if isinstance(payload.get("run"), dict) else {}
        return bool(
            run.get("dry_run") is True
            or run.get("mode") == "dry_run"
            or run.get("schema_version") == "aion.workflow_capsule_dry_run_result.v1"
            or run.get("run_id")
        )

    def _permission_mode_from_capsule(self, capsule: WorkflowCapsule) -> PermissionMode:
        raw = (
            (capsule.meta or {}).get("permission_mode")
            or (capsule.workflow_graph or {}).get("permission_mode")
            or (capsule.compiled_glyph or {}).get("permission_mode")
            or PermissionMode.REVIEW.value
        )
        try:
            return PermissionMode(str(raw))
        except Exception:
            return PermissionMode.REVIEW

    def _risk_tier_from_step(self, step: Any) -> RiskTier:
        raw = None
        try:
            raw = step.raw.get("risk_tier")
            if raw is None and isinstance(step.raw.get("permission"), dict):
                raw = step.raw.get("permission", {}).get("risk_tier")
        except Exception:
            raw = None

        try:
            return RiskTier(str(raw or RiskTier.MEDIUM.value))
        except Exception:
            return RiskTier.MEDIUM

    def _permission_context_for_resume(
        self,
        *,
        capsule: WorkflowCapsule,
        step: Any,
        execution_mode: str,
    ) -> PermissionEvaluationContext:
        raw = step.raw if isinstance(getattr(step, "raw", None), dict) else {}
        permission = raw.get("permission") if isinstance(raw.get("permission"), dict) else {}

        action = str(
            raw.get("kind")
            or getattr(step, "kind", "")
            or raw.get("action")
            or getattr(step, "step_id", "")
            or "external_write"
        )

        return PermissionEvaluationContext(
            workspace_id=str(
                (capsule.meta or {}).get("workspace_id")
                or (capsule.workflow_graph or {}).get("workspace_id")
                or ""
            ),
            agent_id=str(
                (capsule.meta or {}).get("agent_id")
                or raw.get("agent_id")
                or permission.get("agent_id")
                or "agent.default"
            ),
            workflow_id=str(capsule.workflow_id or capsule.canonical_key),
            node_id=str(raw.get("node_id") or getattr(step, "step_id", "")),
            action=action,
            connector=raw.get("connector"),
            risk_tier=self._risk_tier_from_step(step),
            is_external_write=True,
            is_draft_action=action in {"draft", "draft_content", "create_draft"},
            requires_approval=True,
            confidence=permission.get("confidence"),
            risk_flags=list(permission.get("risk_flags") or raw.get("risk_flags") or []),
            execution_mode=execution_mode,
            metadata={
                "canonical_key": capsule.canonical_key,
                "step_id": getattr(step, "step_id", None),
                "permission": permission,
            },
        )

    def _evaluate_resume_permission(
        self,
        *,
        capsule: WorkflowCapsule,
        step: Any,
        execution_mode: str,
    ) -> Any:
        policy = WorkflowPermissionPolicy(
            workflow_id=str(capsule.workflow_id or capsule.canonical_key),
            mode=self._permission_mode_from_capsule(capsule),
            allow_live_execute=bool(
                execution_mode == EXECUTION_MODE_LIVE_EXECUTE
                and self._is_gmail_create_draft_step(step)
            ),
        )

        agent = AgentPermissionProfile(
            agent_id=str(
                (capsule.meta or {}).get("agent_id")
                or "agent.default"
            ),
            can_self_authorise_external_writes=False,
        )

        context = self._permission_context_for_resume(
            capsule=capsule,
            step=step,
            execution_mode=execution_mode,
        )

        return PermissionEvaluator().evaluate(
            policy=policy,
            agent=agent,
            context=context,
        )

    @staticmethod
    def _is_call_workflow_glyph_step(step: Any) -> bool:
        raw = step.raw if isinstance(getattr(step, "raw", None), dict) else {}
        permission = raw.get("permission") if isinstance(raw.get("permission"), dict) else {}
        action = str(
            raw.get("kind")
            or raw.get("type")
            or raw.get("action")
            or permission.get("action")
            or getattr(step, "kind", "")
            or getattr(step, "step_id", "")
            or ""
        ).strip()
        return action == "call_workflow_glyph"

    @staticmethod
    def _call_workflow_glyph_node_from_step(step: Any) -> Dict[str, Any]:
        raw = step.raw if isinstance(getattr(step, "raw", None), dict) else {}
        config = raw.get("config") if isinstance(raw.get("config"), dict) else {}

        glyph_code = (
            raw.get("glyph_code")
            or config.get("glyph_code")
            or raw.get("code")
            or config.get("code")
            or raw.get("display_glyph")
            or config.get("display_glyph")
        )

        return {
            **raw,
            "id": raw.get("id") or raw.get("node_id") or getattr(step, "step_id", ""),
            "kind": "call_workflow_glyph",
            "glyph_code": glyph_code,
            "glyph_version": raw.get("glyph_version") or config.get("glyph_version"),
            "version_hash": raw.get("version_hash") or config.get("version_hash"),
            "child_workflow_id": raw.get("child_workflow_id") or config.get("child_workflow_id"),
            "input_schema": raw.get("input_schema") or config.get("input_schema"),
            "output_schema": raw.get("output_schema") or config.get("output_schema"),
            "required_connectors": raw.get("required_connectors") or config.get("required_connectors"),
            "approval_policy": raw.get("approval_policy") or config.get("approval_policy"),
            "config": config,
        }

    def _workflow_glyph_registry_for_call_runtime(self) -> Dict[str, Any]:
        glyphs = []

        # Prefer callable glyphs from the persisted backend WorkflowGlyphRepository.
        # This is the real backend registry path used by /api/workflow-glyphs.
        try:
            search = getattr(self.workflow_glyph_repository, "search", None)
            if callable(search):
                for glyph in search("", callable_only=True):
                    if hasattr(glyph, "to_dict"):
                        glyphs.append(glyph.to_dict())
                    elif isinstance(glyph, dict):
                        glyphs.append(dict(glyph))
        except TypeError:
            try:
                for glyph in self.workflow_glyph_repository.search("gmail", callable_only=True):
                    if hasattr(glyph, "to_dict"):
                        glyphs.append(glyph.to_dict())
                    elif isinstance(glyph, dict):
                        glyphs.append(dict(glyph))
            except Exception:
                pass
        except Exception:
            pass

        return {
            "source": "backend_workflow_glyph_repository",
            "glyphs": glyphs,
        }

    def _execute_call_workflow_glyph_steps_for_dry_run(
        self,
        *,
        capsule: WorkflowCapsule,
        expansion: Any,
        dry: Any,
        inputs: Dict[str, Any],
        available_vault_requirements: List[str],
        extra: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        steps = list(getattr(expansion, "steps", []) or [])
        call_steps = [step for step in steps if self._is_call_workflow_glyph_step(step)]

        if not call_steps:
            return []

        parent_run_id = str(getattr(dry, "run_id", "") or f"{capsule.canonical_key}:dry_run")
        registry = self._workflow_glyph_registry_for_call_runtime()

        results: List[Dict[str, Any]] = []
        parent_payload: Dict[str, Any] = {
            **(inputs or {}),
            "canonical_key": capsule.canonical_key,
            "workflow_id": str(capsule.workflow_id or capsule.canonical_key),
            "parent_run_id": parent_run_id,
        }

        for index, step in enumerate(call_steps, start=1):
            node = self._call_workflow_glyph_node_from_step(step)

            result = execute_call_workflow_glyph_dry_run(
                parent_run_id=parent_run_id,
                call_node=node,
                parent_payload=parent_payload,
                glyph_registry=registry,
                available_connectors=available_vault_requirements,
                parent_approval_policy={
                    "approval_before_external_write": True,
                    "requires_approval": True,
                    "source": "WorkflowCapsuleRunner.run_dry",
                },
            ).to_dict()

            result["runner_integration"] = {
                "source": "WorkflowCapsuleRunner.run_dry",
                "step_id": getattr(step, "step_id", None),
                "step_index": index,
                "backend_registry_source": registry.get("source"),
                "real_runtime_path": True,
                "dry_run_only": True,
            }

            results.append(result)

            if result.get("ok") and isinstance(result.get("child_output"), dict):
                parent_payload.update(result["child_output"])

        return results

    @staticmethod
    def _attach_call_workflow_glyph_results_to_dry_run(
        *,
        dry: Any,
        nested_results: List[Dict[str, Any]],
    ) -> None:
        if not nested_results:
            return

        dry_dict = dry.to_dict() if hasattr(dry, "to_dict") else {}

        existing_trace = list(getattr(dry, "trace", []) or dry_dict.get("trace") or [])
        existing_boardroom = list(getattr(dry, "boardroom_events", []) or dry_dict.get("boardroom_events") or [])

        nested_trace = []
        nested_boardroom = []

        for result in nested_results:
            nested_trace.append({
                "kind": "call_workflow_glyph",
                "status": result.get("status"),
                "ok": result.get("ok"),
                "glyph_code": result.get("glyph_code"),
                "glyph_version": result.get("glyph_version"),
                "child_workflow_id": result.get("child_workflow_id"),
                "parent_run_id": result.get("parent_run_id"),
                "child_run_id": result.get("child_run_id"),
                "validation": result.get("validation"),
                "provenance": result.get("provenance"),
                "metrics": result.get("metrics"),
                "runner_integration": result.get("runner_integration"),
            })

            provenance = result.get("provenance") if isinstance(result.get("provenance"), dict) else {}
            for event in provenance.get("boardroom_events") or []:
                if isinstance(event, dict):
                    nested_boardroom.append(event)

        setattr(dry, "call_workflow_glyph_runs", nested_results)
        setattr(dry, "nested_call_workflow_glyph_runs", nested_results)
        setattr(dry, "trace", existing_trace + nested_trace)
        setattr(dry, "boardroom_events", existing_boardroom + nested_boardroom)


    @staticmethod
    def _call_workflow_glyph_runs_from_dry(
        dry: Any,
        *,
        parent_inputs: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        trace = list(getattr(dry, "trace", []) or [])
        parent_inputs = dict(parent_inputs or {})

        runs: List[Dict[str, Any]] = []
        for item in trace:
            if not (
                isinstance(item, dict)
                and item.get("kind") == "call_workflow_glyph"
            ):
                continue

            run = dict(item)

            # E5 result-panel contract: the promoted nested run must expose
            # explicit parent->child input and child->parent output, not just
            # provenance metadata buried in trace.
            run.setdefault("child_input", dict(parent_inputs))
            run.setdefault("child_output", {
                **dict(parent_inputs),
                "child_workflow_id": run.get("child_workflow_id"),
                "glyph_code": run.get("glyph_code"),
                "dry_run": True,
                "runtime_plan_completed": run.get("status") == "dry_run_completed",
            })

            runs.append(run)

        return runs

    def _maybe_create_approval(
        self,
        *,
        capsule: WorkflowCapsule,
        expansion: Any,
        policy: Any,
        dry: Any,
        extra: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not bool(getattr(dry, "approval_required", False)):
            return {}

        external_step = self._resolve_external_write_step(expansion=expansion)

        external_step_id = None
        approval_ref = None
        reason = "Workflow requires human approval before external write."

        if external_step is not None:
            external_step_id = getattr(external_step, "step_id", None)
            raw = getattr(external_step, "raw", {}) or {}
            guard = raw.get("guard") or {}
            approval_ref = guard.get("requires_approval_ref")
            reason = (
                (raw.get("approval") or {}).get("reason")
                or guard.get("reason")
                or reason
            )

        return self.approval_store.create(
            run_id=str(getattr(dry, "run_id", "")),
            canonical_key=capsule.canonical_key,
            display_name=capsule.display_name,
            reason=reason,
            external_write_step_id=external_step_id,
            approval_ref=approval_ref,
            payload={
                "run": dry.to_dict(),
                "policy": policy.to_dict(),
                "external_step_id": external_step_id,
            },
            meta={
                "source": "WorkflowCapsuleRunner",
                "extra": extra,
            },
        )

    @staticmethod
    def _resolve_external_write_step(
        *,
        expansion: Any,
        preferred_step_id: Optional[str] = None,
    ) -> Any:
        steps = list(getattr(expansion, "steps", []) or [])

        if preferred_step_id:
            for step in steps:
                if getattr(step, "step_id", None) == preferred_step_id:
                    return step

        for step in steps:
            if bool(getattr(step, "external_write", False)):
                return step

        for step in steps:
            if getattr(step, "kind", None) == "external_write":
                return step

        return None


def run_workflow_capsule_dry(
    value: str,
    *,
    inputs: Optional[Dict[str, Any]] = None,
    available_vault_requirements: Optional[List[str]] = None,
    cau_state: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return WorkflowCapsuleRunner().run_dry(
        value,
        inputs=inputs,
        available_vault_requirements=available_vault_requirements,
        cau_state=cau_state,
        extra=extra,
    ).to_dict()
