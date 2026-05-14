from __future__ import annotations

from typing import Any, Dict, List

from backend.modules.aion_business.contracts.skills import SkillRunRequest, SkillRunResult
from backend.modules.aion_business.runtime.container_guard import ContainerGuard
from backend.modules.aion_business.skills.base import (
    BaseSkill,
    SkillExecutionError,
    SkillValidationError,
)


class SummarizeDocsSkill(BaseSkill):
    """
    v1 deterministic summarizer.

    Expected input_payload:
    {
        "binding_id": "offers-binding"
    }

    Optional:
    {
        "max_items": 10,
        "include_keys": ["nodes", "links", "glyphs", "meta"]
    }

    This first version does not call any external model.
    It produces a structured summary from the container snapshot.
    """

    def __init__(self, container_guard: ContainerGuard | None = None):
        self.container_guard = container_guard or ContainerGuard()

    @property
    def skill_id(self) -> str:
        return "summarize_docs"

    def validate_request(self, request: SkillRunRequest) -> None:
        super().validate_request(request)

        binding_id = request.input_payload.get("binding_id")
        if not binding_id or not isinstance(binding_id, str):
            raise SkillValidationError("missing_binding_id")

        if binding_id not in request.allowed_containers:
            raise SkillValidationError(f"container_not_allowed:{binding_id}")

        max_items = request.input_payload.get("max_items", 10)
        if not isinstance(max_items, int) or max_items <= 0:
            raise SkillValidationError("invalid_max_items")

        include_keys = request.input_payload.get("include_keys")
        if include_keys is not None and not isinstance(include_keys, list):
            raise SkillValidationError("include_keys_must_be_list")

    def run(self, request: SkillRunRequest) -> SkillRunResult:
        binding_id = str(request.input_payload["binding_id"])
        max_items = int(request.input_payload.get("max_items", 10))
        include_keys = request.input_payload.get("include_keys") or [
            "nodes",
            "links",
            "glyphs",
            "glyph_grid",
            "meta",
        ]

        workspace = request.input_payload.get("workspace")
        role = request.input_payload.get("role")
        agent = request.input_payload.get("agent")
        task = request.input_payload.get("task")

        if workspace is None or role is None or agent is None:
            raise SkillExecutionError("missing_runtime_context_for_guarded_read")

        guarded = self.container_guard.read_container(
            workspace=workspace,
            role=role,
            agent=agent,
            binding_id=binding_id,
            task=task,
        )
        if not guarded.ok or not guarded.container:
            raise SkillExecutionError(f"guarded_container_read_failed:{guarded.reason}")

        container = guarded.container
        summary = self._summarize_container(
            container=container,
            max_items=max_items,
            include_keys=include_keys,
        )

        return SkillRunResult(
            ok=True,
            skill_id=self.skill_id,
            output_payload={
                "binding_id": binding_id,
                "container_id": container.get("id"),
                "summary": summary,
            },
            artifacts=[],
            warnings=[],
            error_code=None,
            trace={
                "binding_id": binding_id,
                "container_id": container.get("id"),
                "max_items": max_items,
                "include_keys": include_keys,
            },
            side_effects_applied=False,
        )

    def _summarize_container(
        self,
        *,
        container: Dict[str, Any],
        max_items: int,
        include_keys: List[str],
    ) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "container_name": container.get("name"),
            "container_type": container.get("type"),
            "geometry": container.get("geometry"),
            "state": container.get("state"),
            "top_level_keys": sorted(container.keys()),
        }

        if "meta" in include_keys:
            out["meta"] = dict(container.get("meta") or {})

        if "nodes" in include_keys:
            nodes = container.get("nodes") or []
            out["node_count"] = self._safe_count(nodes)
            out["node_preview"] = self._preview_items(nodes, max_items=max_items)

        if "links" in include_keys:
            links = container.get("links") or []
            out["link_count"] = self._safe_count(links)
            out["link_preview"] = self._preview_items(links, max_items=max_items)

        if "glyphs" in include_keys:
            glyphs = container.get("glyphs") or []
            out["glyph_count"] = self._safe_count(glyphs)
            out["glyph_preview"] = self._preview_items(glyphs, max_items=max_items)

        if "glyph_grid" in include_keys:
            glyph_grid = container.get("glyph_grid") or []
            out["glyph_grid_count"] = self._safe_count(glyph_grid)
            out["glyph_grid_preview"] = self._preview_items(glyph_grid, max_items=max_items)

        return out

    @staticmethod
    def _safe_count(value: Any) -> int:
        if isinstance(value, dict):
            return len(value)
        if isinstance(value, list):
            return len(value)
        return 0

    @staticmethod
    def _preview_items(items: Any, *, max_items: int) -> List[Any]:
        if isinstance(items, dict):
            preview = []
            for idx, (key, value) in enumerate(items.items()):
                if idx >= max_items:
                    break
                preview.append({"key": key, "value": value})
            return preview

        if isinstance(items, list):
            return items[:max_items]

        return []