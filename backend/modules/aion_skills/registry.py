from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from backend.modules.aion_skills.contracts import SkillMetadata, SkillSpec

SkillHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class _RegistryEntry:
    """
    Internal registry record.

    Keeps the original Phase C shape (spec + handler), and adds normalized metadata
    for enable/disable, promotion, topic tagging, and validation policy workflows.
    """
    spec: SkillSpec
    handler: SkillHandler
    metadata: SkillMetadata


class SkillRegistry:
    """
    In-memory unified skill registry (Phase C).

    Backward compatible with the original registry API:
      - register(spec, handler) -> SkillSpec
      - resolve(skill_id) -> (SkillSpec, handler)
      - list_specs(status=..., tag=...)

    Additive capabilities:
      - metadata access (get_metadata / list_metadata)
      - enabled flag filtering
      - stage promotion (experimental -> verified -> core)
      - enable/disable toggles
    """

    def __init__(self) -> None:
        self._entries: Dict[str, _RegistryEntry] = {}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_metadata_from_spec(self, spec: SkillSpec) -> SkillMetadata:
        """
        Derive normalized metadata from a SkillSpec.
        """
        spec = spec.validate()

        # Map legacy safety labels to newer normalized metadata labels.
        safety_map = {
            "internal_safe": "internal_state",
            "read_only": "safe_read",
            "external_network": "external_side_effect",
            "side_effecting": "external_side_effect",
            "restricted": "external_side_effect",
            # already-normalized labels passthrough:
            "safe_read": "safe_read",
            "safe_transform": "safe_transform",
            "internal_state": "internal_state",
            "external_side_effect": "external_side_effect",
        }

        meta = SkillMetadata(
            skill_id=spec.skill_id,
            title=spec.name or spec.skill_id,
            description=spec.description or "",
            safety_class=safety_map.get(str(spec.safety_class or "").strip(), "safe_read"),
            stage=str(spec.status or "experimental"),
            tags=list(spec.tags or []),
            topics=list(getattr(spec, "topics", []) or []),
            enabled=bool(getattr(spec, "enabled", True)),
            validation_policy=getattr(spec, "validation_policy", None) or None,
            extra={
                "skill_spec_version": spec.version,
                "timeout_ms": int(spec.timeout_ms),
                "retry_policy": dict(spec.retry_policy or {}),
                **dict(spec.metadata or {}),
            },
        ).validate()
        return meta

    def _sync_spec_from_metadata(self, spec: SkillSpec, meta: SkillMetadata) -> SkillSpec:
        """
        Keep spec fields aligned with metadata changes (enabled/promote etc.).
        """
        spec.status = meta.stage
        spec.tags = list(meta.tags or [])

        # These fields are additive in the updated contracts.py
        if hasattr(spec, "topics"):
            spec.topics = list(meta.topics or [])
        if hasattr(spec, "enabled"):
            spec.enabled = bool(meta.enabled)
        if hasattr(spec, "validation_policy"):
            spec.validation_policy = meta.validation_policy

        return spec

    # ------------------------------------------------------------------
    # Core registration / retrieval
    # ------------------------------------------------------------------

    def register(
        self,
        spec: SkillSpec,
        handler: SkillHandler,
        metadata: Optional[SkillMetadata] = None,
    ) -> SkillSpec:
        """
        Register a skill using the canonical SkillSpec + handler path.

        Optional `metadata` can override derived metadata. If omitted, metadata is
        derived from the spec so older callers continue to work unchanged.
        """
        spec = spec.validate()
        if not callable(handler):
            raise TypeError("handler must be callable")

        meta = (metadata or self._build_metadata_from_spec(spec)).validate()
        if meta.skill_id != spec.skill_id:
            raise ValueError("metadata.skill_id must match spec.skill_id")

        # Sync spec with metadata in case metadata overrides status/enabled/topics/etc.
        spec = self._sync_spec_from_metadata(spec, meta).validate()

        self._entries[spec.skill_id] = _RegistryEntry(spec=spec, handler=handler, metadata=meta)
        return spec

    def register_skill(
        self,
        skill_id: str,
        handler: SkillHandler,
        metadata: Optional[SkillMetadata] = None,
        **metadata_kwargs: Any,
    ) -> SkillSpec:
        """
        Convenience registration path (additive).

        Builds a minimal SkillSpec + SkillMetadata so you can register quickly when
        you don't want to manually construct SkillSpec.
        """
        sid = str(skill_id or "").strip()
        if not sid:
            raise ValueError("skill_id is required")
        if not callable(handler):
            raise TypeError(f"handler for {sid} must be callable")

        if metadata is None:
            metadata = SkillMetadata(
                skill_id=sid,
                title=str(metadata_kwargs.get("title") or sid),
                description=str(metadata_kwargs.get("description") or ""),
                safety_class=str(metadata_kwargs.get("safety_class") or "safe_read"),
                stage=str(metadata_kwargs.get("stage") or "experimental"),
                tags=list(metadata_kwargs.get("tags") or []),
                topics=list(metadata_kwargs.get("topics") or []),
                enabled=bool(metadata_kwargs.get("enabled", True)),
                validation_policy=metadata_kwargs.get("validation_policy"),
                extra=dict(metadata_kwargs.get("extra") or {}),
            ).validate()
        else:
            metadata = metadata.validate()

        spec = SkillSpec(
            skill_id=sid,
            name=metadata.title or sid,
            version=str(metadata_kwargs.get("version") or "0.1.0"),
            description=metadata.description or "",
            input_schema=dict(metadata_kwargs.get("input_schema") or {"type": "object"}),
            output_schema=dict(metadata_kwargs.get("output_schema") or {"type": "object"}),
            # Keep legacy SkillSpec safety labels unless explicitly overridden
            safety_class=str(metadata_kwargs.get("spec_safety_class") or "internal_safe"),
            timeout_ms=int(metadata_kwargs.get("timeout_ms") or 5000),
            retry_policy=dict(metadata_kwargs.get("retry_policy") or {"max_retries": 0}),
            status=metadata.stage,
            tags=list(metadata.tags or []),
            metadata=dict(metadata_kwargs.get("spec_metadata") or {}),
            topics=list(metadata.topics or []),
            enabled=bool(metadata.enabled),
            validation_policy=metadata.validation_policy,
        ).validate()

        return self.register(spec=spec, handler=handler, metadata=metadata)

    def unregister(self, skill_id: str) -> bool:
        return self._entries.pop(str(skill_id), None) is not None

    def has(self, skill_id: str) -> bool:
        return str(skill_id) in self._entries

    def get_spec(self, skill_id: str) -> Optional[SkillSpec]:
        entry = self._entries.get(str(skill_id))
        return entry.spec if entry else None

    def get_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        entry = self._entries.get(str(skill_id))
        return entry.metadata if entry else None

    def get_handler(self, skill_id: str) -> Optional[SkillHandler]:
        """
        Enabled-only handler lookup (safe default).
        """
        entry = self._entries.get(str(skill_id))
        if not entry:
            return None
        if not bool(entry.metadata.enabled):
            return None
        return entry.handler

    def get_handler_raw(self, skill_id: str) -> Optional[SkillHandler]:
        """
        Returns the handler even if disabled (useful for admin/testing).
        """
        entry = self._entries.get(str(skill_id))
        return entry.handler if entry else None

    def resolve(self, skill_id: str) -> Optional[Tuple[SkillSpec, SkillHandler]]:
        """
        Enabled-only resolution (safe default for runtime adapter).
        """
        entry = self._entries.get(str(skill_id))
        if not entry or not bool(entry.metadata.enabled):
            return None
        return entry.spec, entry.handler

    def resolve_with_metadata(self, skill_id: str) -> Optional[Tuple[SkillSpec, SkillMetadata, SkillHandler]]:
        """
        Additive helper for richer admin/runtime introspection.
        """
        entry = self._entries.get(str(skill_id))
        if not entry or not bool(entry.metadata.enabled):
            return None
        return entry.spec, entry.metadata, entry.handler

    # ------------------------------------------------------------------
    # Listing / filtering
    # ------------------------------------------------------------------

    def list_specs(
        self,
        *,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        topic: Optional[str] = None,
        enabled_only: bool = False,
    ) -> List[SkillSpec]:
        specs: List[SkillSpec] = []
        for entry in self._entries.values():
            if enabled_only and not bool(entry.metadata.enabled):
                continue
            specs.append(entry.spec)

        if status:
            specs = [s for s in specs if str(getattr(s, "status", "")) == status]
        if tag:
            specs = [s for s in specs if tag in (s.tags or [])]
        if topic:
            specs = [s for s in specs if topic in (getattr(s, "topics", []) or [])]

        specs.sort(key=lambda s: (str(getattr(s, "status", "")), str(getattr(s, "skill_id", ""))))
        return specs

    def list_skill_ids(self, *, enabled_only: bool = False) -> List[str]:
        ids = sorted(self._entries.keys())
        if not enabled_only:
            return ids

        out: List[str] = []
        for sid in ids:
            entry = self._entries.get(sid)
            if entry and bool(entry.metadata.enabled):
                out.append(sid)
        return out

    def list_metadata(
        self,
        *,
        enabled_only: bool = False,
        stage: Optional[str] = None,
        tag: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        metas: List[SkillMetadata] = []
        for sid in self.list_skill_ids(enabled_only=False):
            entry = self._entries[sid]
            m = entry.metadata

            if enabled_only and not bool(m.enabled):
                continue
            if stage and str(m.stage) != stage:
                continue
            if tag and tag not in (m.tags or []):
                continue
            if topic and topic not in (m.topics or []):
                continue

            metas.append(m)

        metas.sort(key=lambda m: (str(m.stage), str(m.skill_id)))
        return [m.to_dict() for m in metas]

    # ------------------------------------------------------------------
    # Lifecycle controls (Phase C completion helpers)
    # ------------------------------------------------------------------

    def set_enabled(self, skill_id: str, enabled: bool) -> bool:
        entry = self._entries.get(str(skill_id))
        if entry is None:
            return False
        entry.metadata.enabled = bool(enabled)
        self._sync_spec_from_metadata(entry.spec, entry.metadata)
        return True

    def promote(self, skill_id: str, target_stage: str) -> bool:
        """
        Controlled promotion path:
          experimental -> verified -> core

        Allows same-stage no-op (returns True).
        """
        entry = self._entries.get(str(skill_id))
        if entry is None:
            return False

        target = str(target_stage or "").strip()
        order = {"experimental": 0, "verified": 1, "core": 2}
        if target not in order:
            return False

        current = entry.metadata.stage if entry.metadata.stage in order else "experimental"

        # no downgrades
        if order[target] < order[current]:
            return False

        # only allow same-stage or +1 step promotion
        if order[target] > order[current] + 1:
            return False

        entry.metadata.stage = target
        self._sync_spec_from_metadata(entry.spec, entry.metadata)
        return True

    def update_metadata(self, skill_id: str, **changes: Any) -> bool:
        """
        Small convenience patcher for metadata (additive).
        """
        entry = self._entries.get(str(skill_id))
        if entry is None:
            return False

        meta = entry.metadata
        for k, v in changes.items():
            if hasattr(meta, k):
                setattr(meta, k, v)

        meta.validate()
        self._sync_spec_from_metadata(entry.spec, meta)
        return True

    # ------------------------------------------------------------------
    # Snapshots / introspection
    # ------------------------------------------------------------------

    def to_snapshot(self) -> Dict[str, Any]:
        return {
            "count": len(self._entries),
            "enabled_count": sum(1 for e in self._entries.values() if bool(e.metadata.enabled)),
            "skills": [s.to_dict() for s in self.list_specs()],
            "metadata": self.list_metadata(),
        }

    def telemetry_summary(self) -> Dict[str, Any]:
        """
        Registry-only summary (not execution telemetry). Safe helper for smoke tests/admin.
        """
        by_stage: Dict[str, int] = {"experimental": 0, "verified": 1 - 1, "core": 2 - 2}
        by_safety: Dict[str, int] = {}
        enabled_count = 0

        for entry in self._entries.values():
            m = entry.metadata
            if m.enabled:
                enabled_count += 1
            by_stage[m.stage] = by_stage.get(m.stage, 0) + 1
            by_safety[m.safety_class] = by_safety.get(m.safety_class, 0) + 1

        return {
            "total_skills": len(self._entries),
            "enabled_skills": enabled_count,
            "disabled_skills": len(self._entries) - enabled_count,
            "by_stage": by_stage,
            "by_safety_class": by_safety,
        }


_GLOBAL_REGISTRY: Optional[SkillRegistry] = None


def get_global_skill_registry() -> SkillRegistry:
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = SkillRegistry()
    return _GLOBAL_REGISTRY


def register_builtin_demo_skills(registry: Optional[SkillRegistry] = None) -> SkillRegistry:
    """
    Minimal built-ins so Phase C can be tested immediately.
    """
    reg = registry or get_global_skill_registry()

    def _echo_skill(inputs: Dict[str, Any]) -> Dict[str, Any]:
        text = str(inputs.get("text") or "")
        return {"echo": text, "length": len(text)}

    def _roadmap_priority_skill(inputs: Dict[str, Any]) -> Dict[str, Any]:
        topic = str(inputs.get("topic") or "AION roadmap")
        return {
            "topic": topic,
            "priority_order": [
                "response_quality_and_followup_handling",
                "planner_and_context_routing",
                "skill_runtime_registry_adapter",
                "learning_loop_integration",
            ],
            "summary": (
                f"For {topic}, prioritize user-visible conversational quality first, "
                "then strengthen routing/planning, then expand execution capability."
            ),
        }

    # Idempotent-ish registration for repeated smoke runs
    if not reg.has("skill.echo_text"):
        reg.register_skill(
            "skill.echo_text",
            handler=_echo_skill,
            metadata=SkillMetadata(
                skill_id="skill.echo_text",
                title="Echo Text",
                description="Echoes input text for testing adapter/telemetry plumbing.",
                safety_class="safe_transform",
                stage="experimental",
                tags=["test", "debug"],
                topics=["general", "testing", "utilities"],
                validation_policy=None,
            ),
            version="0.1.0",
            input_schema={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            output_schema={"type": "object"},
            timeout_ms=1000,
            retry_policy={"max_retries": 0},
            spec_safety_class="internal_safe",
        )

    if not reg.has("skill.aion_roadmap_priority"):
        reg.register_skill(
            "skill.aion_roadmap_priority",
            handler=_roadmap_priority_skill,
            metadata=SkillMetadata(
                skill_id="skill.aion_roadmap_priority",
                title="AION Roadmap Priority",
                description="Returns deterministic roadmap prioritization guidance for AION.",
                safety_class="safe_read",
                stage="experimental",
                tags=["aion", "roadmap", "planning"],
                topics=["AION roadmap", "planning", "aion", "roadmap"],
                validation_policy=None,
            ),
            version="0.1.0",
            input_schema={
                "type": "object",
                "properties": {"topic": {"type": "string"}},
            },
            output_schema={"type": "object"},
            timeout_ms=1000,
            retry_policy={"max_retries": 0},
            spec_safety_class="internal_safe",
        )

    # Optional trading skill pack (non-breaking) -- LAZY IMPORT avoids circular import
    try:
        from backend.modules.aion_trading.skill_pack import register_aion_trading_skills
        register_aion_trading_skills(reg)
    except Exception:
        # non-breaking startup
        pass

    return reg