from __future__ import annotations

import json
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

from backend.modules.hexcore.first_class_cognitive_control_plane import (
    FirstClassCognitiveControlPlane,
)


SCHEMA_VERSION = "aion.hexcore.standalone_task_governance.v1"
_CURRENT_TASK_INTELLIGENCE: ContextVar[Dict[str, Any]] = ContextVar(
    "aion_current_task_intelligence", default={}
)
ACTIVE_SERVICE_MIGRATION = {
    "general_apprentice": {
        "path": "backend/AION/system/aion_general_apprentice_service.py",
        "mode": "standalone_wrapper",
    },
    "north_star_mastery": {
        "path": "backend/AION/system/aion_north_star_mastery_service.py",
        "mode": "standalone_wrapper",
    },
    "mastery_curriculum": {
        "path": "backend/AION/system/aion_mastery_curriculum_service.py",
        "mode": "standalone_wrapper",
    },
    "open_mission_compounding": {
        "path": "backend/AION/system/aion_open_mission_compounding_service.py",
        "mode": "standalone_wrapper",
    },
    "open_mission_executor": {
        "path": "backend/AION/system/aion_open_mission_executor_service.py",
        "mode": "standalone_wrapper",
    },
    "long_duration_campaign": {
        "path": "backend/AION/system/aion_long_duration_real_outcome_campaign_service.py",
        "mode": "standalone_wrapper",
    },
    "outcome_learning": {
        "path": "backend/AION/system/aion_real_outcome_learning_service.py",
        "mode": "standalone_wrapper",
    },
    "cognitive_runtime": {
        "path": "backend/AION/system/aion_cognitive_runtime_service.py",
        "mode": "native_governed_runtime",
    },
}


def _status_text(outcome: Any) -> str:
    if isinstance(outcome, Mapping):
        for key in ("status", "outcome", "result", "action"):
            value = outcome.get(key)
            if isinstance(value, str) and value:
                return value
        return json.dumps(
            {str(k): v for k, v in list(outcome.items())[:12]},
            sort_keys=True,
            default=str,
        )[:1000]
    return str(outcome or "completed")[:1000]


@dataclass
class GovernedStandaloneTask:
    repo_root: Path
    service_id: str
    task_text: str
    operation_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict, init=False)
    completed: bool = field(default=False, init=False)
    _context_token: Optional[Token] = field(default=None, init=False, repr=False)

    def __enter__(self) -> "GovernedStandaloneTask":
        root = Path(self.repo_root).resolve()
        self.control = FirstClassCognitiveControlPlane(
            repo_root=root,
            canonical_state_path=root / "data/hexcore/persistent_learning_state.json",
            state_path=root / "data/hexcore/first_class_cognitive_control_plane.json",
        )
        self.context = self.control.prepare_task(
            self.task_text,
            metadata={
                **self.metadata,
                "session_id": f"service:{self.service_id}",
                "service_id": self.service_id,
                "operation_id": self.operation_id,
            },
        )
        self._context_token = _CURRENT_TASK_INTELLIGENCE.set(dict(self.context))
        return self

    def finish(
        self,
        outcome: Any,
        *,
        verified: bool = False,
        verifier: Optional[str] = None,
        evidence_refs: Sequence[str] = (),
        used_memory_ids: Optional[Sequence[str]] = None,
        used_skill_ids: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        retrieved = self.context
        # Retrieval and use are deliberately separate. A migrated deterministic
        # engine may receive context without proving that a specific memory
        # changed its result, so only caller-acknowledged IDs count as used.
        memories = list(used_memory_ids or [])
        skills = list(used_skill_ids or [])
        result = self.control.record_task_outcome(
            trace_id=str(retrieved.get("trace_id") or ""),
            used_memory_ids=memories,
            used_skill_ids=skills,
            outcome=_status_text(outcome),
            verified=bool(verified),
            verifier=verifier or (self.service_id if verified else None),
            evidence_refs=evidence_refs,
        )
        self.completed = bool(result.get("recorded"))
        return result

    def __exit__(self, exc_type, exc, _traceback) -> bool:
        if not self.completed:
            self.finish(
                {"status": "failed" if exc is not None else "completed_without_verification",
                 "error": type(exc).__name__ if exc is not None else None},
                verified=False,
            )
        if self._context_token is not None:
            _CURRENT_TASK_INTELLIGENCE.reset(self._context_token)
            self._context_token = None
        return False


def governed_standalone_task(
    *,
    repo_root: Path,
    service_id: str,
    task_text: str,
    operation_id: Optional[str] = None,
    metadata: Optional[Mapping[str, Any]] = None,
) -> GovernedStandaloneTask:
    return GovernedStandaloneTask(
        repo_root=Path(repo_root),
        service_id=str(service_id),
        task_text=str(task_text),
        operation_id=str(operation_id or f"operation_{uuid.uuid4().hex}"),
        metadata=dict(metadata or {}),
    )


def migration_status(repo_root: Path) -> Dict[str, Any]:
    root = Path(repo_root).resolve()
    control_state_path = root / "data/hexcore/first_class_cognitive_control_plane.json"
    try:
        control_state = json.loads(control_state_path.read_text(encoding="utf-8"))
    except Exception:
        control_state = {}
    observed_sessions = {
        str(row.get("session_id") or "")
        for row in control_state.get("task_traces") or []
    }
    rows = []
    for service_id, contract in ACTIVE_SERVICE_MIGRATION.items():
        path = root / contract["path"]
        source = path.read_text(encoding="utf-8") if path.exists() else ""
        mode = contract["mode"]
        integrated = (
            "governed_standalone_task(" in source
            if mode == "standalone_wrapper"
            else "CanonicalAionCognitiveRuntime" in source
        )
        rows.append({
            "service_id": service_id,
            "path": str(path),
            "mode": mode,
            "integrated": integrated,
            "live_task_trace_observed": (
                f"service:{service_id}" in observed_sessions
                if mode == "standalone_wrapper" else None
            ),
        })
    migrated = sum(row["integrated"] for row in rows)
    standalone_rows = [row for row in rows if row["mode"] == "standalone_wrapper"]
    live_traces = sum(row["live_task_trace_observed"] is True for row in standalone_rows)
    return {
        "schema_version": "aion.hexcore.standalone_task_migration_status.v1",
        "status": "fully_migrated" if migrated == len(rows) else "migration_incomplete",
        "active_service_entrypoints": len(rows),
        "migrated_entrypoints": migrated,
        "unmigrated_entrypoints": len(rows) - migrated,
        "standalone_entrypoints": len(standalone_rows),
        "live_standalone_task_traces": live_traces,
        "standalone_trace_gaps": len(standalone_rows) - live_traces,
        "services": rows,
        "historical_nonexecuting_files_in_scope": False,
        "claim_boundary": (
            "All active supervised learning/cognitive service entrypoints are in scope; "
            "archived benchmarks and nonexecuting historical artifacts are not runtime paths."
        ),
    }


def current_task_intelligence() -> Dict[str, Any]:
    """Return the governed parent-task context visible to nested legacy code."""
    return dict(_CURRENT_TASK_INTELLIGENCE.get() or {})


def write_migration_status(repo_root: Path, result_path: Optional[Path] = None) -> Dict[str, Any]:
    root = Path(repo_root).resolve()
    result = migration_status(root)
    target = Path(result_path or root / "results/hexcore_active_runtime_cognitive_migration.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(target)
    return result


__all__ = [
    "ACTIVE_SERVICE_MIGRATION",
    "GovernedStandaloneTask",
    "governed_standalone_task",
    "current_task_intelligence",
    "migration_status",
    "write_migration_status",
]
