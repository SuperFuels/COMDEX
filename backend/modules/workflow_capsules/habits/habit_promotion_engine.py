from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import json
import os
import uuid

from backend.modules.workflow_capsules.foundations.workflow_capsule_schema import WorkflowCapsule
from backend.modules.workflow_capsules.habits.habit_capsule_schema import (
    HabitCapsule,
    make_habit_key,
)
from backend.modules.workflow_capsules.habits.habit_capsule_repository import (
    HabitCapsuleRepository,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore
from backend.modules.aion_agents.runtime.vault_repository_backend import (
    AgentVaultRepositoryBackend,
    configured_agent_domain_store,
)


DEFAULT_HABIT_DIR = Path(".runtime/workflow_capsules/habits")
DEFAULT_PROMOTION_LOG = Path(".runtime/workflow_capsules/habits/habit_promotion_log.jsonl")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _clamp01(value: Any, default: float = 0.0) -> float:
    try:
        x = float(value)
    except Exception:
        x = default
    return max(0.0, min(1.0, x))


class HabitPromotionEngine:
    """
    CAU-gated promotion engine.

    This does not change workflow execution.
    It only creates a HabitCapsule candidate when policy and CAU allow it.
    """

    def __init__(
        self,
        *,
        habit_dir: Path | str | None = None,
        promotion_log: Path | str | None = None,
        repository: HabitCapsuleRepository | None = None,
        domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
        min_successful_runs: int = 3,
        min_avg_quality: float = 0.70,
    ) -> None:
        explicit_legacy = habit_dir is not None or promotion_log is not None
        self.habit_dir = Path(habit_dir or DEFAULT_HABIT_DIR)
        self.promotion_log = Path(promotion_log or DEFAULT_PROMOTION_LOG)
        store = domain_store or (
            configured_agent_domain_store() if not explicit_legacy else None
        )
        self.workspace_id = str(
            workspace_id
            or os.environ.get("TESSARIS_BUSINESS_STABLE_ID")
            or ""
        ).strip()
        self.repository = repository or HabitCapsuleRepository(
            habit_dir=(self.habit_dir if explicit_legacy else None),
            domain_store=store,
            workspace_id=self.workspace_id or None,
        )
        self.log_vault = (
            AgentVaultRepositoryBackend(
                store,
                kind="workflow_capsule_habit_promotion_events",
                audit=True,
            )
            if store
            else None
        )
        if self.log_vault is not None and not self.workspace_id:
            raise ValueError("workflow_capsule_habit_promotion_workspace_id_required")
        self.min_successful_runs = max(1, int(min_successful_runs))
        self.min_avg_quality = _clamp01(min_avg_quality, 0.70)

    def evaluate_and_promote(
        self,
        *,
        capsule: WorkflowCapsule,
        run_evidence: List[Dict[str, Any]],
        cau_state: Optional[Dict[str, Any]] = None,
        persist: bool = True,
    ) -> Dict[str, Any]:
        cau_state = dict(cau_state or {})
        allow_learn = bool(cau_state.get("allow_learn") is True)
        adr_active = bool(cau_state.get("adr_active") is True)

        successful = [
            e for e in list(run_evidence or [])
            if isinstance(e, dict) and bool(e.get("run_ok", e.get("ok", False)))
        ]

        qualities = [
            _clamp01(e.get("quality"), 0.0)
            for e in successful
            if isinstance(e, dict)
        ]
        avg_quality = round(sum(qualities) / len(qualities), 6) if qualities else 0.0

        eligible_by_evidence = (
            len(successful) >= self.min_successful_runs
            and avg_quality >= self.min_avg_quality
        )

        mutation_allowed = allow_learn and not adr_active
        promoted = False
        habit_path = None
        habit = None

        reasons: List[str] = []
        if not allow_learn:
            reasons.append("cau_allow_learn_false")
        if adr_active:
            reasons.append("adr_active")
        if len(successful) < self.min_successful_runs:
            reasons.append("insufficient_successful_runs")
        if avg_quality < self.min_avg_quality:
            reasons.append("avg_quality_below_threshold")

        if eligible_by_evidence and mutation_allowed:
            habit_key = make_habit_key(capsule.canonical_key)
            habit = HabitCapsule(
                habit_key=habit_key,
                source_workflow_key=capsule.canonical_key,
                display_name=f"Habit: {capsule.display_name}",
                meaning=(
                    "CAU-approved habit candidate promoted from repeated "
                    f"successful workflow runs for {capsule.canonical_key}."
                ),
                trigger_tags=list(capsule.tags or []),
                promotion_policy={
                    "min_successful_runs": self.min_successful_runs,
                    "min_avg_quality": self.min_avg_quality,
                    "requires_cau_allow_learn": True,
                    "adr_blocks_promotion": True,
                },
                evidence={
                    "successful_runs": len(successful),
                    "avg_quality": avg_quality,
                    "run_ids": [str(e.get("run_id") or "") for e in successful if e.get("run_id")],
                },
                resonance={
                    "sqi_score": avg_quality,
                    "ρ": min(1.0, len(successful) / max(1, self.min_successful_runs)),
                    "Ī": avg_quality,
                },
                meta={
                    "source": "HabitPromotionEngine",
                    "promoted_at": _utc_now_iso(),
                },
            ).finalize()

            if persist:
                saved = self.repository.save(habit)
                habit_path = saved["path"]

            promoted = True

        record = {
            "schema_version": "aion.habit_promotion_result.v1",
            "ts": _utc_now_iso(),
            "source_workflow_key": capsule.canonical_key,
            "display_name": capsule.display_name,
            "eligible_by_evidence": eligible_by_evidence,
            "mutation_allowed": mutation_allowed,
            "promoted": promoted,
            "habit_key": habit.habit_key if habit else None,
            "habit_path": str(habit_path) if habit_path else None,
            "successful_runs": len(successful),
            "avg_quality": avg_quality,
            "thresholds": {
                "min_successful_runs": self.min_successful_runs,
                "min_avg_quality": self.min_avg_quality,
            },
            "cau": {
                "allow_learn": allow_learn,
                "adr_active": adr_active,
                "deny_reason": cau_state.get("deny_reason"),
            },
            "blocked_reasons": reasons,
        }

        self._append_log(record)

        return record

    def _append_log(self, record: Dict[str, Any]) -> None:
        if self.log_vault is not None:
            source_key = str(record.get("source_workflow_key") or "workflow")
            self.log_vault.put(
                workspace_id=self.workspace_id,
                item_id=f"{source_key.replace('/', '_')}-{uuid.uuid4().hex}",
                payload=record,
            )
            return
        self.promotion_log.parent.mkdir(parents=True, exist_ok=True)
        with self.promotion_log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
