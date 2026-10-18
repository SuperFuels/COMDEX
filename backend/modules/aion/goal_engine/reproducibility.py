from __future__ import annotations

import hashlib
import json
from typing import Any


GOAL_ENGINE_REPRODUCIBILITY_SCHEMA_VERSION = "aion.goal_engine.reproducibility.v1"

GOAL_VERSION = "goal.v1"
EXPERIMENT_VERSION = "experiment.v1"
LOOP_VERSION = "loop.v1"
OUTCOME_SCHEMA_VERSION = "outcome.v1"
MEMORY_SCHEMA_VERSION = "memory.v1"
CHECKPOINT_SCHEMA_VERSION_REF = "checkpoint.v1"


def canonical_json(value: Any) -> str:
    return json.dumps(value or {}, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_checksum(value: Any) -> str:
    payload = canonical_json(value).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def build_goal_engine_reproducibility_block(
    *,
    source_capsule: dict[str, Any] | None = None,
    goal_contract: dict[str, Any] | None = None,
    child_glyph_versions: list[dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_capsule = dict(source_capsule or {})
    goal_contract = dict(goal_contract or {})

    block = {
        "schema_version": GOAL_ENGINE_REPRODUCIBILITY_SCHEMA_VERSION,
        "trace_type": "goal_engine_reproducibility",
        "goal_version": GOAL_VERSION,
        "experiment_version": EXPERIMENT_VERSION,
        "loop_version": LOOP_VERSION,
        "outcome_schema_version": OUTCOME_SCHEMA_VERSION,
        "memory_schema_version": MEMORY_SCHEMA_VERSION,
        "checkpoint_schema_version": CHECKPOINT_SCHEMA_VERSION_REF,
        "source_capsule_checksum": stable_checksum(source_capsule),
        "goal_contract_checksum": stable_checksum(goal_contract),
        "child_glyph_versions": list(child_glyph_versions or []),
        "versions_pinned": True,
        "rollback_supported": False,
        "preserve_old_versions": True,
        "dry_run_only": True,
    }

    if extra:
        block.update(dict(extra))

    return block
