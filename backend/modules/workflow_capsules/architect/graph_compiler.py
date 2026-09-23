from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from backend.modules.workflow_capsules.architect.builder_spec import WorkflowBuilderSpec
from backend.modules.workflow_capsules.architect.node_registry import ArchitectNodeRegistry
from backend.modules.workflow_capsules.architect.spec_validator import (
    WorkflowBuilderSpecValidator,
)
from backend.modules.workflow_capsules.canvas.canvas_workflow_compiler import (
    CanvasWorkflowCompiler,
)


@dataclass(slots=True)
class WorkflowBuilderGraphCompileResult:
    ok: bool
    canvas: Dict[str, Any] = field(default_factory=dict)
    capsule: Any = None
    validation: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "canvas": self.canvas,
            "capsule": self.capsule.to_dict() if hasattr(self.capsule, "to_dict") else None,
            "validation": self.validation,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


class WorkflowBuilderGraphCompiler:
    def __init__(self, registry: ArchitectNodeRegistry | None = None) -> None:
        self.registry = registry or ArchitectNodeRegistry()
        self.validator = WorkflowBuilderSpecValidator(self.registry)

    def compile(
        self,
        spec: WorkflowBuilderSpec,
        *,
        connected_credentials: List[str] | None = None,
    ) -> WorkflowBuilderGraphCompileResult:
        validation = self.validator.validate(
            spec,
            connected_credentials=connected_credentials or [],
        )

        if not validation.ok:
            return WorkflowBuilderGraphCompileResult(
                ok=False,
                validation=validation.to_dict(),
                errors=list(validation.errors),
                warnings=list(validation.warnings),
            )

        canvas = self._to_canvas(spec)
        compiled = CanvasWorkflowCompiler().compile(canvas)

        return WorkflowBuilderGraphCompileResult(
            ok=bool(compiled.ok),
            canvas=canvas,
            capsule=compiled.capsule,
            validation=validation.to_dict(),
            errors=list(compiled.errors or []),
            warnings=list(validation.warnings) + list(compiled.warnings or []),
        )

    def _to_canvas(self, spec: WorkflowBuilderSpec) -> Dict[str, Any]:
        nodes = []

        for index, step in enumerate(spec.steps):
            node_def = self.registry.require(step.node_type)

            kind = self._kind_for_node_type(step.node_type)
            node_data = {
                "step_id": step.step_id,
                "kind": kind,
                "label": step.label,
                "risk_tier": step.risk_tier,
                "requires_approval": bool(step.requires_approval or node_def.requires_approval),
                "permission": {
                    "risk_tier": step.risk_tier,
                    "action": step.node_type,
                },
                "output_ref": f"{step.step_id}.output",
                **dict(step.config or {}),
            }

            if node_def.connector:
                node_data["connector"] = node_def.connector

            if node_def.external_write:
                node_data["external_write"] = True

            if step.missing_connector:
                node_data["missing_connector"] = True

            nodes.append(
                {
                    "id": step.step_id,
                    "type": kind,
                    "position": {"x": 140 + (index * 260), "y": 160},
                    "data": node_data,
                }
            )

        edges = [
            {
                "id": f"edge_{edge.source}_{edge.target}",
                "source": edge.source,
                "target": edge.target,
                **({"condition": edge.condition} if edge.condition else {}),
            }
            for edge in spec.edges
        ]

        return {
            "canonical_key": f"workflow:architect.{self._slug(spec.workflow_name)}.v1",
            "display_name": spec.workflow_name,
            "meaning": spec.goal,
            "display_glyph": "ARCH-WF-001",
            "tags": ["architect", "ai_generated", "workflow_builder"],
            "vault_requirements": self._vault_requirements(spec),
            "permission_mode": "review",
            "nodes": nodes,
            "edges": edges,
        }

    @staticmethod
    def _kind_for_node_type(node_type: str) -> str:
        mapping = {
            "gmail.read": "read_email",
            "extract_fields": "extract",
            "set_variable": "set_variable",
            "get_variable": "get_variable",
            "compose_string": "draft_content",
            "human_approval": "approval_checkpoint",
            "gmail.create_draft": "create_draft",
            "hubspot.upsert_contact": "external_write",
            "router": "router",
            "if_else": "if_else",
            "missing_connector_placeholder": "missing_connector_placeholder",
        }
        return mapping.get(node_type, node_type.replace(".", "_"))

    @staticmethod
    def _slug(value: str) -> str:
        out = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
        while "__" in out:
            out = out.replace("__", "_")
        return out.strip("_") or "generated"

    @staticmethod
    def _vault_requirements(spec: WorkflowBuilderSpec) -> List[str]:
        out = []
        for connector in spec.connectors_required:
            if connector:
                out.append(f"vault.{connector}.credentials")
        return sorted(set(out))
