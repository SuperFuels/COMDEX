from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Set
import time

from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
)


COMPILED_GLYPH_SCHEMA_VERSION = "aion.workflow_glyph.v1"


@dataclass
class WorkflowExpansionStep:
    index: int
    step_id: str
    kind: str
    label: str
    input_refs: List[str]
    output_ref: Optional[str]
    requires_approval: bool
    external_write: bool
    raw: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorkflowExpansionResult:
    ok: bool
    canonical_key: str
    display_name: str
    schema_version: str
    steps: List[WorkflowExpansionStep]
    trace: List[Dict[str, Any]]
    errors: List[str]
    warnings: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "canonical_key": self.canonical_key,
            "display_name": self.display_name,
            "schema_version": self.schema_version,
            "steps": [s.to_dict() for s in self.steps],
            "trace": self.trace,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class WorkflowCapsuleExpander:
    """
    Expands a capsule's compiled workflow glyph into an inspectable executable plan.

    This does NOT execute anything.
    It only validates and normalizes the compiled_glyph body.
    """

    def expand(self, capsule: WorkflowCapsule) -> WorkflowExpansionResult:
        trace: List[Dict[str, Any]] = []
        errors: List[str] = []
        warnings: List[str] = []

        compiled = capsule.compiled_glyph or {}
        schema_version = str(compiled.get("schema_version") or "")

        trace.append(
            {
                "t": time.time(),
                "event": "expansion_started",
                "canonical_key": capsule.canonical_key,
                "display_name": capsule.display_name,
            }
        )

        if schema_version != COMPILED_GLYPH_SCHEMA_VERSION:
            errors.append(
                f"Unsupported compiled_glyph schema_version: {schema_version!r}; expected {COMPILED_GLYPH_SCHEMA_VERSION!r}"
            )

        raw_steps = compiled.get("steps")
        if raw_steps is None:
            raw_steps = []
            warnings.append("compiled_glyph.steps missing; treating as empty list")

        if not isinstance(raw_steps, list):
            errors.append("compiled_glyph.steps must be a list")
            raw_steps = []

        steps: List[WorkflowExpansionStep] = []
        seen_ids: Set[str] = set()

        for idx, raw in enumerate(raw_steps):
            if not isinstance(raw, dict):
                errors.append(f"step[{idx}] must be an object")
                continue

            step_id = str(raw.get("id") or raw.get("step_id") or f"step_{idx + 1}")
            kind = str(raw.get("kind") or raw.get("type") or "unknown")
            label = str(raw.get("label") or raw.get("name") or step_id)

            if step_id in seen_ids:
                errors.append(f"duplicate step id: {step_id}")
            seen_ids.add(step_id)

            input_refs = raw.get("input_refs") or raw.get("inputs") or []
            if isinstance(input_refs, str):
                input_refs = [input_refs]
            if not isinstance(input_refs, list):
                errors.append(f"step[{idx}].input_refs must be list/string")
                input_refs = []

            input_refs = [str(x) for x in input_refs]

            output_ref = raw.get("output_ref") or raw.get("output")
            if output_ref is not None:
                output_ref = str(output_ref)

            requires_approval = bool(
                raw.get("requires_approval")
                or raw.get("approval_required")
                or kind in {"approval_checkpoint", "send_email", "external_write"}
            )

            external_write = bool(
                raw.get("external_write")
                or kind in {"send_email", "post_social", "update_crm", "external_write"}
            )

            step = WorkflowExpansionStep(
                index=idx,
                step_id=step_id,
                kind=kind,
                label=label,
                input_refs=input_refs,
                output_ref=output_ref,
                requires_approval=requires_approval,
                external_write=external_write,
                raw=raw,
            )
            steps.append(step)

            trace.append(
                {
                    "t": time.time(),
                    "event": "step_expanded",
                    "index": idx,
                    "step_id": step_id,
                    "kind": kind,
                    "requires_approval": requires_approval,
                    "external_write": external_write,
                }
            )

        missing_refs = self._find_missing_refs(steps)
        for ref in missing_refs:
            errors.append(f"missing input_ref: {ref}")

        if not steps:
            warnings.append("compiled_glyph has no executable steps yet")

        trace.append(
            {
                "t": time.time(),
                "event": "expansion_finished",
                "ok": not errors,
                "step_count": len(steps),
                "error_count": len(errors),
                "warning_count": len(warnings),
            }
        )

        return WorkflowExpansionResult(
            ok=not errors,
            canonical_key=capsule.canonical_key,
            display_name=capsule.display_name,
            schema_version=schema_version,
            steps=steps,
            trace=trace,
            errors=errors,
            warnings=warnings,
        )

    def _find_missing_refs(self, steps: List[WorkflowExpansionStep]) -> List[str]:
        produced: Set[str] = set()
        step_ids: Set[str] = {s.step_id for s in steps}

        for step in steps:
            if step.output_ref:
                produced.add(step.output_ref)

        missing: List[str] = []

        for step in steps:
            for ref in step.input_refs:
                # Allow references to prior step ids or output refs.
                if ref in step_ids or ref in produced:
                    continue

                # Allow runtime/system refs for now.
                if ref.startswith(("input.", "runtime.", "vault.", "ctx.", "user.")):
                    continue

                missing.append(ref)

        return sorted(set(missing))


def expand_workflow_capsule(capsule: WorkflowCapsule) -> Dict[str, Any]:
    return WorkflowCapsuleExpander().expand(capsule).to_dict()
