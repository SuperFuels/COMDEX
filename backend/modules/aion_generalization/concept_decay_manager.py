#!/usr/bin/env python3
"""Governed decay of customer-learned AION concepts."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import time
from typing import Any
from uuid import uuid4

from backend.modules.aion_business.runtime.business_vault_runtime import (
    guardian_mode_requested,
)
from backend.modules.aion_knowledge.knowledge_graph_core import (
    AionKnowledgeGraphStore,
)
from backend.modules.aion_learning.vault_store import AionLearningVaultStore


REINFORCE_LOG = Path("data/feedback/concept_reinforcement.log")
SNAPSHOT_PATH = Path("data/feedback/concept_evolution_snapshot.jsonl")
DECAY_INTERVAL = 3600 * 4
DECAY_FACTOR = 0.97
MIN_STRENGTH = 0.25
EXPORT_LIMIT = 1000


def parse_reinforcement_log(
    path: str | Path | None = None,
) -> dict[str, float]:
    """Read an explicit retained legacy reinforcement source.

    Guardian mode refuses an implicit application-relative source. The live
    protected caller must supply governed reinforcement evidence instead.
    """
    if path is None and guardian_mode_requested():
        raise RuntimeError("concept_decay_guardian_reinforcement_input_required")
    source = Path(path or REINFORCE_LOG)
    if not source.is_file():
        return {}
    last_seen: dict[str, float] = {}
    for line in source.read_text(encoding="utf-8").splitlines():
        try:
            timestamp, message = line.strip().split(" ", 1)
            if message.startswith("reinforce"):
                last_seen[message.split()[1]] = float(timestamp)
        except (IndexError, TypeError, ValueError):
            continue
    return last_seen


def decay_stale_links(
    last_seen: dict[str, float],
    *,
    store: AionKnowledgeGraphStore | None = None,
    now: float | None = None,
) -> tuple[int, int]:
    graph = store or AionKnowledgeGraphStore()
    current_time = float(now if now is not None else time.time())
    updates = 0
    deletions = 0
    for row in graph.search(predicate="is_a"):
        concept_name = row["object"].removeprefix("concept:")
        age = current_time - float(last_seen.get(concept_name, 0.0))
        if age <= DECAY_INTERVAL:
            continue
        next_strength = float(row["strength"]) * DECAY_FACTOR
        if next_strength < MIN_STRENGTH:
            if graph.delete(row["subject"], row["predicate"], row["object"]):
                deletions += 1
            continue
        graph.put(
            row["subject"],
            row["predicate"],
            row["object"],
            vec=row.get("vec"),
            strength=next_strength,
            reinforce_existing=False,
            provenance_class=str(
                row.get("provenance_class") or "customer_derived"
            ),
        )
        updates += 1
    return updates, deletions


def export_snapshot(
    *,
    store: AionKnowledgeGraphStore | None = None,
    learning_store: AionLearningVaultStore | None = None,
    legacy_snapshot_path: str | Path | None = None,
) -> dict[str, Any]:
    graph = store or AionKnowledgeGraphStore()
    concepts: dict[str, int] = {}
    for row in graph.search(predicate="is_a")[:EXPORT_LIMIT]:
        concept = row["object"].removeprefix("concept:")
        concepts[concept] = concepts.get(concept, 0) + 1
    event_id = f"concept-evolution-{uuid4().hex}"
    payload = {
        "event_id": event_id,
        "event_type": "concept_evolution_snapshot",
        "ts_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "vault_order_ns": time.time_ns(),
        "concepts": concepts,
    }
    audit = learning_store or AionLearningVaultStore()
    if audit.enabled:
        audit.append_event(event_id, payload)
        return payload
    destination = Path(legacy_snapshot_path or SNAPSHOT_PATH)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def main() -> None:
    last_seen = parse_reinforcement_log()
    updates, deletions = decay_stale_links(last_seen)
    snapshot = export_snapshot()
    print(
        "AION concept decay complete:",
        {"updated": updates, "deleted": deletions, "snapshot": snapshot["event_id"]},
    )


if __name__ == "__main__":
    main()
