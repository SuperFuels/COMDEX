from __future__ import annotations

from typing import Any, Dict, List

from backend.modules.aion_business.contracts.skills import SkillRunRequest, SkillRunResult
from backend.modules.aion_business.runtime.container_adapter import BusinessContainerAdapter
from backend.modules.aion_business.skills.base import (
    BaseSkill,
    SkillExecutionError,
    SkillValidationError,
)


class ReadContainerSkill(BaseSkill):
    """
    Read a business container through the Aion Business container adapter.

    Expected input_payload:
    {
        "binding_id": "offers-binding"
    }

    Optional:
    {
        "include_full_container": true
    }
    """

    def __init__(self, container_adapter: BusinessContainerAdapter | None = None):
        self.container_adapter = container_adapter or BusinessContainerAdapter()

    @property
    def skill_id(self) -> str:
        return "read_container"

    def validate_request(self, request: SkillRunRequest) -> None:
        super().validate_request(request)

        binding_id = request.input_payload.get("binding_id")
        if not binding_id or not isinstance(binding_id, str):
            raise SkillValidationError("missing_binding_id")

        if binding_id not in request.allowed_containers:
            raise SkillValidationError(f"container_not_allowed:{binding_id}")

    def run(self, request: SkillRunRequest) -> SkillRunResult:
        binding_id = str(request.input_payload["binding_id"])
        include_full_container = bool(request.input_payload.get("include_full_container", False))

        try:
            container = self.container_adapter.get_container(binding_id)
        except Exception as exc:
            raise SkillExecutionError(f"container_read_failed:{binding_id}:{exc}") from exc

        if not isinstance(container, dict):
            raise SkillExecutionError(f"invalid_container_payload:{binding_id}")

        output_payload: Dict[str, Any] = {
            "binding_id": binding_id,
            "container_id": container.get("id"),
            "name": container.get("name"),
            "type": container.get("type"),
            "geometry": container.get("geometry"),
            "state": container.get("state"),
            "meta": container.get("meta", {}),
            "summary": self._build_summary(container),
        }

        if include_full_container:
            output_payload["container"] = container

        return SkillRunResult(
            ok=True,
            skill_id=self.skill_id,
            output_payload=output_payload,
            artifacts=[],
            warnings=[],
            error_code=None,
            trace={
                "binding_id": binding_id,
                "container_id": container.get("id"),
                "included_full_container": include_full_container,
            },
            side_effects_applied=False,
        )

    def _build_summary(self, container: Dict[str, Any]) -> Dict[str, Any]:
        atoms = container.get("atoms")
        glyphs = container.get("glyphs")
        nodes = container.get("nodes")
        links = container.get("links")

        return {
            "has_atoms": bool(atoms),
            "has_glyphs": bool(glyphs),
            "has_nodes": bool(nodes),
            "has_links": bool(links),
            "atom_count": self._safe_count(atoms),
            "glyph_count": self._safe_count(glyphs),
            "node_count": self._safe_count(nodes),
            "link_count": self._safe_count(links),
            "top_level_keys": sorted(container.keys()),
        }

    @staticmethod
    def _safe_count(value: Any) -> int:
        if isinstance(value, dict):
            return len(value)
        if isinstance(value, list):
            return len(value)
        return 0