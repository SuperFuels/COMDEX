from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Dict, List, Optional

from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import (
    WorkflowCapsule,
    WorkflowCapsulePolicy,
)
from backend.modules.workflow_capsules.global_registry.industry_pack_schema import (
    GlobalWorkflowPattern,
    IndustryWorkflowPack,
)
from backend.modules.workflow_capsules.global_registry.local_binding_schema import (
    LocalWorkflowBinding,
)


COMPILED_GLYPH_SCHEMA_VERSION = "aion.workflow_glyph.v1"
MATERIALIZER_SCHEMA_VERSION = "aion.global_pattern_materializer.v1"


_SECRET_FIELD_NAMES = {
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


def _contains_secret_field(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            normalized = str(key or "").strip().lower()
            if normalized in _SECRET_FIELD_NAMES:
                return True
            if _contains_secret_field(item):
                return True

    if isinstance(value, list):
        return any(_contains_secret_field(item) for item in value)

    return False


def _as_dict(value: Any) -> Dict[str, Any]:
    if is_dataclass(value):
        return asdict(value)
    return value if isinstance(value, dict) else {}


def _list_of_str(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value or "").strip()
    return [text] if text else []


def _step_id_from_index(index: int) -> str:
    return f"step_{index + 1}"


def _normalise_step(raw: Dict[str, Any], *, index: int) -> Dict[str, Any]:
    step_id = str(
        raw.get("id")
        or raw.get("step_id")
        or raw.get("output_ref")
        or _step_id_from_index(index)
    )

    kind = str(raw.get("kind") or raw.get("type") or "task")
    label = str(raw.get("label") or raw.get("name") or kind.replace("_", " ").title())

    output_ref = str(raw.get("output_ref") or f"{step_id}.output")

    step: Dict[str, Any] = {
        "id": step_id,
        "kind": kind,
        "label": label,
        "input_refs": _list_of_str(raw.get("input_refs") or raw.get("inputs")),
        "output_ref": output_ref,
    }

    for key in (
        "connector",
        "requires",
        "external_write",
        "requires_approval",
        "approval_required",
        "guard",
        "approval",
        "purpose",
    ):
        if key in raw:
            step[key] = raw[key]

    if kind in {"approval_checkpoint", "send_email", "external_write"}:
        step["requires_approval"] = True

    if kind in {"send_email", "external_write", "post_social", "update_crm"}:
        step["external_write"] = True

    return step


def _compile_pattern_template_to_glyph(
    *,
    pattern: GlobalWorkflowPattern,
    binding: LocalWorkflowBinding,
) -> Dict[str, Any]:
    template = _as_dict(pattern.template)
    raw_steps = template.get("steps") or []

    if not isinstance(raw_steps, list):
        raise ValueError("global_pattern_template_steps_must_be_list")

    steps = [
        _normalise_step(raw, index=index)
        for index, raw in enumerate(raw_steps)
        if isinstance(raw, dict)
    ]

    return {
        "schema_version": COMPILED_GLYPH_SCHEMA_VERSION,
        "namespace": "aion.workflow_capsules.global_registry",
        "op": "sequence",
        "workflow": {
            "workflow_id": binding.workflow_canonical_key,
            "name": pattern.display_name,
            "workspace_id": binding.workspace_id,
            "business_id": binding.business_id,
            "pattern_key": binding.pattern_key,
        },
        "policy": {
            "dry_run_first": True,
            "approval_before_external_write": True,
            "external_writes_allowed": False,
            "allow_autonomous_execution": False,
        },
        "steps": steps,
        "flow_links": [],
        "materialized_from": {
            "pattern_key": pattern.pattern_key,
            "pack_industry": pattern.industry,
            "binding_key": binding.binding_key,
        },
    }


class GlobalPatternMaterializer:
    """
    Materialises a reusable global workflow pattern into a local Workflow Capsule.

    Boundary:
      global pattern = reusable template
      local binding = workspace/business connector + vault handles
      materialised capsule = executable local capsule

    This class never accepts or persists raw credentials.
    """

    def find_pattern(
        self,
        *,
        pack: IndustryWorkflowPack,
        binding: LocalWorkflowBinding,
    ) -> GlobalWorkflowPattern:
        for pattern in pack.patterns:
            if pattern.pattern_key == binding.pattern_key:
                return pattern

        raise ValueError(f"global_pattern_not_found:{binding.pattern_key}")

    def materialize(
        self,
        *,
        pack: IndustryWorkflowPack,
        binding: LocalWorkflowBinding,
        display_name: Optional[str] = None,
    ) -> WorkflowCapsule:
        pack.finalize()
        binding.finalize()

        pattern = self.find_pattern(pack=pack, binding=binding)
        pattern.finalize()

        combined_boundary = {
            "pack": pack.to_dict(),
            "binding": binding.to_dict(),
            "pattern": pattern.to_dict(),
        }
        if _contains_secret_field(combined_boundary):
            raise ValueError("materializer_input_must_not_contain_secret_fields")

        vault_requirements = sorted(
            set(
                list(pattern.required_vault_handles or [])
                + list(binding.vault_bindings.values() or [])
            )
        )

        compiled_glyph = _compile_pattern_template_to_glyph(
            pattern=pattern,
            binding=binding,
        )

        capsule = WorkflowCapsule(
            canonical_key=binding.workflow_canonical_key,
            display_name=display_name or pattern.display_name,
            meaning=(
                f"Materialised local Workflow Capsule from global pattern "
                f"{pattern.pattern_key} for workspace {binding.workspace_id}."
            ),
            display_glyph=pattern.display_glyph,
            tags=sorted(set(list(pattern.tags or []) + list(pack.tags or []) + ["materialized", "global-pattern"])),
            allowed_use_cases=list(pattern.local_binding_slots or []),
            policy=WorkflowCapsulePolicy(
                dry_run_first=True,
                approval_before_external_write=True,
                external_writes_allowed=False,
                allow_autonomous_execution=False,
            ),
            vault_requirements=vault_requirements,
            workflow_id=binding.workflow_canonical_key,
            workflow_graph={
                "schema_version": "aion.materialized_workflow_graph.v1",
                "pattern_key": pattern.pattern_key,
                "binding_key": binding.binding_key,
                "workspace_id": binding.workspace_id,
                "business_id": binding.business_id,
                "connector_bindings": dict(binding.connector_bindings or {}),
                "vault_bindings": dict(binding.vault_bindings or {}),
                "business_context": dict(binding.business_context or {}),
            },
            compiled_glyph=compiled_glyph,
            audit_rules={
                "source": "global_pattern_materializer",
                "schema_version": MATERIALIZER_SCHEMA_VERSION,
                "no_raw_credentials": True,
                "execution_requires_runner": True,
            },
            resonance={
                "sqi_score": 0.0,
                "ρ": 0.0,
                "Ī": 0.0,
            },
            entangled_links={
                "global_pattern": [pattern.pattern_key],
                "industry_pack": [pack.pack_key],
                "local_binding": [binding.binding_key],
            },
            meta={
                "schema_version": "aion.workflow_capsule.v1",
                "materializer_schema_version": MATERIALIZER_SCHEMA_VERSION,
                "source_pack_key": pack.pack_key,
                "source_pattern_key": pattern.pattern_key,
                "source_binding_key": binding.binding_key,
                "workspace_id": binding.workspace_id,
                "business_id": binding.business_id,
            },
        )

        capsule.finalize()

        if _contains_secret_field(capsule.to_dict()):
            raise ValueError("materialized_capsule_must_not_contain_secret_fields")

        return capsule


def materialize_global_pattern_to_capsule(
    *,
    pack: IndustryWorkflowPack,
    binding: LocalWorkflowBinding,
    display_name: Optional[str] = None,
) -> WorkflowCapsule:
    return GlobalPatternMaterializer().materialize(
        pack=pack,
        binding=binding,
        display_name=display_name,
    )
