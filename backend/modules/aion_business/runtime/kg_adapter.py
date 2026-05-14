from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.aion_business.contracts.containers import ContainerBindingSpec
from backend.modules.knowledge_graph.kg_writer_singleton import get_kg_writer


class BusinessKGAdapter:
    """
    Semantic journaling bridge for Aion Business.

    Use this for:
    - business events
    - task traces
    - rationale
    - outcomes
    - learning signals
    - object links

    Do not bypass this for semantic writes unless there is a very good reason.
    """

    def __init__(self) -> None:
        self.kg = get_kg_writer()

    def inject_business_event(
        self,
        binding: ContainerBindingSpec,
        *,
        glyph_type: str,
        content: Any,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: str = "aion_business",
        tags: Optional[list[str]] = None,
        plugin: str = "AionBusiness",
    ) -> str:
        md = dict(metadata or {})
        md.setdefault("container_id", binding.kg_container_id or binding.runtime_container_id)
        md.setdefault("workspace_id", binding.workspace_id)
        md.setdefault("business_binding_id", binding.id)
        md.setdefault("category", binding.category)

        if binding.kg_topic_wa:
            md.setdefault("topic", binding.kg_topic_wa)
        if binding.kg_graph:
            md.setdefault("graph", binding.kg_graph)

        return self.kg.inject_glyph(
            content=content,
            glyph_type=glyph_type,
            metadata=md,
            agent_id=agent_id,
            tags=tags or ["aion_business", binding.category],
            plugin=plugin,
        )

    def link_objects(self, src_id: str, dst_id: str, relation: str) -> str:
        return self.kg.add_edge(src_id, dst_id, relation)

    def write_task_event(
        self,
        binding: ContainerBindingSpec,
        *,
        task_id: str,
        status: str,
        objective: str,
        owned_by_role: str,
        assigned_agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.inject_business_event(
            binding,
            glyph_type="business_task_event",
            content=f"Task:{task_id} status={status} objective={objective}",
            metadata={
                "task_id": task_id,
                "status": status,
                "objective": objective,
                "owned_by_role": owned_by_role,
                "assigned_agent_id": assigned_agent_id,
                **(metadata or {}),
            },
            tags=["task", "business"],
        )

    def write_learning_signal(
        self,
        binding: ContainerBindingSpec,
        *,
        source_id: str,
        signal_type: str,
        summary: str,
        confidence: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.inject_business_event(
            binding,
            glyph_type="business_learning_signal",
            content=summary,
            metadata={
                "source_id": source_id,
                "signal_type": signal_type,
                "confidence": confidence,
                **(metadata or {}),
            },
            tags=["learning", "business"],
        )