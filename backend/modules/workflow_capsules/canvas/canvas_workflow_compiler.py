from __future__ import annotations

"""
Canvas Workflow Compiler - AION Workflow Capsules v1
────────────────────────────────────────────────────

Compiles visual workflow canvas nodes/edges into WorkflowCapsule objects.

This is the backend contract for:

  visual canvas
    -> nodes / edges
    -> compiled_glyph.steps
    -> WorkflowCapsule
    -> .workflow.wiki.phn

Important safety rules:
  - canvas payloads must not contain raw credentials,
  - canvas display glyphs must not collide with reserved GlyphOS primitives,
  - canonical_key is the executable identity,
  - display_glyph is UI shorthand only,
  - compiled output must be compatible with WorkflowCapsuleExpander.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re

from backend.modules.workflow_capsules.execution.workflow_capsule_expander import (
    COMPILED_GLYPH_SCHEMA_VERSION,
)
from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
    WorkflowCapsulePolicy,
)
from backend.modules.workflow_capsules.registry.workflow_glyph_registry import (
    is_reserved_glyph,
    is_valid_workflow_key,
)
from backend.modules.workflow_capsules.permissions.permission_modes import (
    PermissionMode,
    RiskTier,
)


CANVAS_COMPILER_SCHEMA_VERSION = "aion.workflow_canvas_compiler.v1"

SECRET_FIELD_NAMES = {
    "password",
    "secret",
    "client_secret",
    "access_token",
    "refresh_token",
    "id_token",
    "authorization",
    "token",
    "api_key",
    "private_key",
}


@dataclass
class CanvasCompileResult:
    ok: bool
    capsule: Optional[WorkflowCapsule] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    schema_version: str = CANVAS_COMPILER_SCHEMA_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "schema_version": self.schema_version,
            "capsule": self.capsule.to_dict() if self.capsule else None,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "metadata": dict(self.metadata),
        }


def _safe_step_id(value: Any, fallback: str) -> str:
    raw = str(value or fallback).strip() or fallback
    safe = re.sub(r"[^a-zA-Z0-9_.:-]+", "_", raw).strip("_")
    return safe or fallback


def _norm_kind(value: Any) -> str:
    kind = str(value or "").strip()
    return kind or "task"


def _contains_secret_key(value: Any) -> bool:
    if isinstance(value, dict):
        for k, v in value.items():
            if str(k).strip().lower() in SECRET_FIELD_NAMES:
                return True
            if _contains_secret_key(v):
                return True
    elif isinstance(value, list):
        return any(_contains_secret_key(v) for v in value)
    return False


def _node_data(node: Dict[str, Any]) -> Dict[str, Any]:
    data = node.get("data")
    return data if isinstance(data, dict) else {}


def _valid_permission_mode(value: Any) -> bool:
    if value is None:
        return True
    try:
        PermissionMode(str(value))
        return True
    except Exception:
        return False


def _valid_risk_tier(value: Any) -> bool:
    if value is None:
        return True
    try:
        RiskTier(str(value))
        return True
    except Exception:
        return False


def _normalise_permission_block(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


class CanvasWorkflowCompiler:
    """
    Converts canvas graph payloads into WorkflowCapsule objects.

    Expected canvas payload:

      {
        "canonical_key": "workflow:gmail.enquiry_reply.v1",
        "display_name": "Handle Gmail Enquiry",
        "meaning": "...",
        "display_glyph": "WG-001",
        "tags": [...],
        "vault_requirements": [...],
        "nodes": [...],
        "edges": [...]
      }
    """

    def compile(self, canvas: Dict[str, Any]) -> CanvasCompileResult:
        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(canvas, dict):
            return CanvasCompileResult(
                ok=False,
                errors=["canvas_payload_must_be_object"],
            )

        if _contains_secret_key(canvas):
            errors.append("canvas_payload_must_not_contain_secret_fields")

        canonical_key = str(canvas.get("canonical_key") or "").strip()
        if not is_valid_workflow_key(canonical_key):
            errors.append("invalid_or_missing_canonical_key")

        workflow_permission_mode = canvas.get("permission_mode")
        if not _valid_permission_mode(workflow_permission_mode):
            errors.append(f"invalid_workflow_permission_mode:{workflow_permission_mode}")

        display_glyph = canvas.get("display_glyph")
        if display_glyph is not None and is_reserved_glyph(str(display_glyph)):
            errors.append("display_glyph_collides_with_reserved_glyphos_primitive")

        nodes = canvas.get("nodes") or []
        edges = canvas.get("edges") or []

        if not isinstance(nodes, list):
            errors.append("canvas.nodes_must_be_list")
            nodes = []

        if not isinstance(edges, list):
            errors.append("canvas.edges_must_be_list")
            edges = []

        if not nodes:
            warnings.append("canvas_has_no_nodes")

        node_ids = set()
        for idx, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(f"node[{idx}]_must_be_object")
                continue

            node_id = str(node.get("id") or "").strip()
            if not node_id:
                errors.append(f"node[{idx}]_missing_id")
                continue

            if node_id in node_ids:
                errors.append(f"duplicate_node_id:{node_id}")
            node_ids.add(node_id)

            data = _node_data(node)
            node_permission_mode = data.get("permission_mode") or _normalise_permission_block(data.get("permission")).get("node_mode")
            node_risk_tier = data.get("risk_tier") or _normalise_permission_block(data.get("permission")).get("risk_tier")

            if not _valid_permission_mode(node_permission_mode):
                errors.append(f"node[{idx}]_invalid_permission_mode:{node_permission_mode}")

            if not _valid_risk_tier(node_risk_tier):
                errors.append(f"node[{idx}]_invalid_risk_tier:{node_risk_tier}")

        for idx, edge in enumerate(edges):
            if not isinstance(edge, dict):
                errors.append(f"edge[{idx}]_must_be_object")
                continue

            source = str(edge.get("source") or "").strip()
            target = str(edge.get("target") or "").strip()

            if source not in node_ids:
                errors.append(f"edge[{idx}]_source_missing:{source}")
            if target not in node_ids:
                errors.append(f"edge[{idx}]_target_missing:{target}")

        if errors:
            return CanvasCompileResult(
                ok=False,
                errors=sorted(set(errors)),
                warnings=warnings,
                metadata={
                    "node_count": len(nodes),
                    "edge_count": len(edges),
                },
            )

        node_to_step_id: Dict[str, str] = {}
        for idx, node in enumerate(nodes):
            data = _node_data(node)
            node_id = str(node.get("id") or "").strip()
            node_to_step_id[node_id] = _safe_step_id(
                data.get("step_id") or node_id,
                f"step_{idx + 1}",
            )

        incoming: Dict[str, List[str]] = {node_id: [] for node_id in node_ids}
        outgoing: Dict[str, List[str]] = {node_id: [] for node_id in node_ids}

        for edge in edges:
            source = str(edge.get("source") or "").strip()
            target = str(edge.get("target") or "").strip()
            outgoing.setdefault(source, []).append(target)
            incoming.setdefault(target, []).append(source)

        steps: List[Dict[str, Any]] = []

        for idx, node in enumerate(nodes):
            data = _node_data(node)
            node_id = str(node.get("id") or "").strip()
            step_id = node_to_step_id.get(node_id) or _safe_step_id(data.get("step_id") or node_id, f"step_{idx + 1}")
            kind = _norm_kind(data.get("kind") or node.get("type"))
            label = str(data.get("label") or data.get("name") or step_id)

            input_refs = [
                node_to_step_id.get(src) or _safe_step_id(src, src)
                for src in incoming.get(node_id, [])
            ]

            output_ref = str(data.get("output_ref") or f"{step_id}.output")

            raw_step = {
                "id": step_id,
                "kind": kind,
                "label": label,
                "input_refs": input_refs,
                "output_ref": output_ref,
            }

            for key in [
                "connector",
                "requires",
                "guard",
                "approval",
                "external_write",
                "requires_approval",
                "permission_mode",
                "risk_tier",
                "permission",
                "limits",
                "agent_id",
                "action",
                "confidence",
                "risk_flags",
                "action_id",
                "capability_id",
                "skill_id",
                "skill_hash",
                "department_id",
                "required_inputs",
                "output_contract",
            ]:
                if key in data:
                    raw_step[key] = data[key]

            if "permission" in raw_step and not isinstance(raw_step["permission"], dict):
                raw_step["permission"] = {}

            steps.append(raw_step)

        capsule = WorkflowCapsule(
            canonical_key=canonical_key,
            display_name=str(canvas.get("display_name") or canonical_key),
            meaning=str(canvas.get("meaning") or ""),
            display_glyph=(str(display_glyph) if display_glyph is not None else None),
            tags=[str(x) for x in list(canvas.get("tags") or [])],
            allowed_use_cases=[str(x) for x in list(canvas.get("allowed_use_cases") or [])],
            policy=WorkflowCapsulePolicy.from_any(canvas.get("policy") or {}),
            vault_requirements=[str(x) for x in list(canvas.get("vault_requirements") or [])],
            workflow_id=str(canvas.get("workflow_id") or canonical_key),
            workflow_graph={
                "schema_version": "aion.workflow_canvas_graph.v1",
                "permission_mode": workflow_permission_mode or "review",
                "permission_policy": dict(canvas.get("permission_policy") or {}),
                "nodes": nodes,
                "edges": edges,
            },
            compiled_glyph={
                "schema_version": COMPILED_GLYPH_SCHEMA_VERSION,
                "source": "canvas_workflow_compiler",
                "steps": steps,
            },
            audit_rules=dict(canvas.get("audit_rules") or {}),
            resonance=dict(canvas.get("resonance") or {}),
            entangled_links=dict(canvas.get("entangled_links") or {}),
            meta={
                **dict(canvas.get("meta") or {}),
                "source": "CanvasWorkflowCompiler",
                "canvas_compiler_schema_version": CANVAS_COMPILER_SCHEMA_VERSION,
                "workflow_permission_mode": workflow_permission_mode or "review",
            },
        ).finalize()

        return CanvasCompileResult(
            ok=True,
            capsule=capsule,
            errors=[],
            warnings=warnings,
            metadata={
                "node_count": len(nodes),
                "edge_count": len(edges),
                "step_count": len(steps),
                "canonical_key": canonical_key,
            },
        )
