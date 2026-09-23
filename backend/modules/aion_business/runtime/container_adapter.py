from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.aion_business.contracts.containers import ContainerBindingSpec
from backend.modules.aion_business.runtime.container_binding_repository import (
    ContainerBindingRepository,
)
from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime


class BusinessContainerAdapter:
    """
    Thin adapter between Aion Business and the existing AION/UCS container layer.

    v1 goal:
    - resolve runtime container
    - read snapshot/state
    - register/save if needed
    - avoid fighting existing UCS/container runtime conventions
    """

    def __init__(
        self,
        binding_repository: Optional[ContainerBindingRepository] = None,
    ):
        self.binding_repository = binding_repository or ContainerBindingRepository()

    def get_binding(self, binding_id: str) -> ContainerBindingSpec:
        return self.binding_repository.get(binding_id)

    def resolve_container(self, binding: ContainerBindingSpec) -> Dict[str, Any]:
        container_id = binding.runtime_container_id

        if binding.runtime_backend in {"ucs", "container_runtime", "dc_json", "vault", "generated"}:
            try:
                container = ucs_runtime.get_container(container_id)
                if isinstance(container, dict) and container:
                    return container
            except Exception:
                pass

            try:
                container = ucs_runtime.load_container(container_id)
                if isinstance(container, dict) and container:
                    return container
            except Exception:
                pass

        return {}

    def ensure_container(self, binding: ContainerBindingSpec) -> Dict[str, Any]:
        """
        Ensure a minimal runtime-side container exists and is registered.
        """
        existing = self.resolve_container(binding)
        if existing:
            return existing

        payload = {
            "id": binding.runtime_container_id,
            "name": binding.name,
            "type": "container",
            "geometry": binding.geometry or "business_container",
            "state": "active",
            "meta": {
                "address": binding.address or f"ucs://local/{binding.runtime_container_id}#container",
                "workspace_id": binding.workspace_id,
                "business_binding_id": binding.id,
                "category": binding.category,
                "tags": list(binding.tags),
                "source_ref": binding.source_ref,
                "runtime_backend": binding.runtime_backend,
                "kg_container_id": binding.kg_container_id,
                "kg_graph": binding.kg_graph,
                "kg_topic_wa": binding.kg_topic_wa,
                "writable": binding.writable,
                "semantic_writes_enabled": binding.semantic_writes_enabled,
            },
            "atoms": {},
            "glyphs": [],
            "glyph_grid": [],
            "nodes": [],
            "links": [],
            "wormholes": ["ucs_hub"],
        }

        ucs_runtime.register_container(binding.runtime_container_id, payload)
        ucs_runtime.save_container(binding.runtime_container_id, payload)
        resolved = self.resolve_container(binding)
        return resolved if resolved else payload

    def get_container(self, binding_id: str) -> Dict[str, Any]:
        binding = self.get_binding(binding_id)
        container = self.resolve_container(binding)
        if container:
            return container
        return self.ensure_container(binding)

    def get_container_for_binding(self, binding: ContainerBindingSpec) -> Dict[str, Any]:
        container = self.resolve_container(binding)
        if container:
            return container
        return self.ensure_container(binding)

    def save_container(self, binding: ContainerBindingSpec, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save/merge a runtime container state.
        """
        payload = dict(data or {})
        payload.setdefault("id", binding.runtime_container_id)
        payload.setdefault("name", binding.name)
        payload.setdefault("type", "container")
        payload.setdefault("geometry", binding.geometry or "business_container")
        payload.setdefault("state", "active")
        payload.setdefault("meta", {})
        payload["meta"].setdefault("workspace_id", binding.workspace_id)
        payload["meta"].setdefault("business_binding_id", binding.id)
        payload["meta"].setdefault("category", binding.category)
        payload["meta"].setdefault("tags", list(binding.tags))
        payload["meta"].setdefault("source_ref", binding.source_ref)
        payload["meta"].setdefault("runtime_backend", binding.runtime_backend)
        payload["meta"].setdefault("kg_container_id", binding.kg_container_id)
        payload["meta"].setdefault("kg_graph", binding.kg_graph)
        payload["meta"].setdefault("kg_topic_wa", binding.kg_topic_wa)
        payload["meta"].setdefault("writable", binding.writable)
        payload["meta"].setdefault("semantic_writes_enabled", binding.semantic_writes_enabled)

        ucs_runtime.save_container(binding.runtime_container_id, payload)
        resolved = self.resolve_container(binding)
        return resolved if resolved else payload

    def get_address(self, binding: ContainerBindingSpec) -> Optional[str]:
        container = self.resolve_container(binding)
        if not container:
            return binding.address

        meta = container.get("meta") or {}
        return meta.get("address") or binding.address