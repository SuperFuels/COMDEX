#!/usr/bin/env python3
"""Business-scoped PAL learning snapshots.

Guardian mode stores longitudinal learning evidence in the external Business
Vault and refuses to read undeclared application-relative legacy sources.
Explicit paths remain available for legacy operation and copy migration.
"""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path
import sqlite3
from statistics import mean
import time
from typing import Any, Iterable, Mapping
from uuid import uuid4

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


DATA_DIR = Path("data")
PAL_FILE = DATA_DIR / "perception" / "exemplars.jsonl"
KG_DB = DATA_DIR / "knowledge" / "aion_knowledge_graph.db"
SNAPSHOT_LOG = DATA_DIR / "analysis" / "pal_snapshots.jsonl"


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


class PalSnapshotStore:
    """Persist customer-derived PAL evidence outside the update boundary."""

    EVENT_TYPE = "pal_learning_snapshot"

    def __init__(
        self,
        *,
        vault_store: AionLearningVaultStore | None = None,
        legacy_log_path: str | Path | None = None,
        auto_configure: bool = True,
    ) -> None:
        self.vault_store = vault_store or AionLearningVaultStore(
            auto_configure=auto_configure
        )
        self.legacy_log_path = Path(legacy_log_path or SNAPSHOT_LOG)

    @property
    def guardian_enabled(self) -> bool:
        return self.vault_store.enabled

    def append(self, snapshot: Mapping[str, Any]) -> dict[str, Any]:
        payload = dict(snapshot)
        event_id = str(payload.get("event_id") or f"pal-snapshot-{uuid4().hex}")
        payload.setdefault("event_id", event_id)
        payload.setdefault("event_type", self.EVENT_TYPE)
        payload.setdefault("ts_utc", str(payload.get("timestamp") or _timestamp()))
        payload.setdefault("vault_order_ns", time.time_ns())
        if self.guardian_enabled:
            self.vault_store.append_event(event_id, payload)
            return payload
        self.legacy_log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.legacy_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
        return payload

    def list(self) -> list[dict[str, Any]]:
        if self.guardian_enabled:
            return self.vault_store.list_events(kind=self.EVENT_TYPE)
        if not self.legacy_log_path.is_file():
            return []
        output: list[dict[str, Any]] = []
        for raw in self.legacy_log_path.read_text(encoding="utf-8").splitlines():
            if raw.strip():
                output.append(json.loads(raw))
        return output


def read_pal_memory(path: str | Path = PAL_FILE) -> list[dict[str, Any]]:
    """Load a retained legacy PAL source for summarisation."""
    source = Path(path)
    if not source.is_file():
        return []
    exemplars: list[dict[str, Any]] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            exemplars.append(value)
    return exemplars


def read_knowledge_graph(path: str | Path = KG_DB) -> list[dict[str, Any]]:
    """Read a retained legacy knowledge graph without creating a database."""
    source = Path(path)
    if not source.is_file():
        return []
    connection = sqlite3.connect(f"file:{source.resolve()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT subject,predicate,object,strength FROM knowledge "
            "ORDER BY strength DESC LIMIT 20"
        ).fetchall()
    finally:
        connection.close()
    return [
        {
            "subject": subject,
            "predicate": predicate,
            "object": object_,
            "strength": strength,
        }
        for subject, predicate, object_, strength in rows
    ]


def summarize_pal(exemplars: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    entries = list(exemplars)
    if not entries:
        return {
            "count": 0,
            "avg_reward": 0.0,
            "unique_prompts": 0,
            "unique_options": 0,
        }
    rewards = [float(entry.get("reward") or 0.0) for entry in entries]
    prompts = {entry.get("prompt") for entry in entries}
    options = {entry.get("option") for entry in entries}
    return {
        "count": len(entries),
        "avg_reward": mean(rewards),
        "unique_prompts": len(prompts),
        "unique_options": len(options),
    }


def plot_progress(
    log_entries: list[Mapping[str, Any]],
    *,
    output_path: str | Path = DATA_DIR / "analysis" / "pal_snapshot_plot.png",
) -> Path:
    """Render a rebuildable legacy diagnostic to an explicitly chosen path."""
    import matplotlib.pyplot as plt

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    rounds = list(range(1, len(log_entries) + 1))
    accuracy = [entry["accuracy"] for entry in log_entries]
    epsilon = [entry["epsilon"] for entry in log_entries]
    figure, first_axis = plt.subplots()
    first_axis.set_xlabel("Rounds")
    first_axis.set_ylabel("Accuracy", color="black")
    first_axis.plot(rounds, accuracy, marker="o", color="black")
    first_axis.tick_params(axis="y", labelcolor="black")
    second_axis = first_axis.twinx()
    second_axis.set_ylabel("Epsilon (exploration)", color="gray")
    second_axis.plot(rounds, epsilon, marker="x", linestyle="--", color="gray")
    figure.tight_layout()
    plt.title("Aion PAL Learning Dynamics")
    plt.savefig(destination, dpi=300)
    plt.close(figure)
    return destination


def create_snapshot(
    *,
    exemplars: list[Mapping[str, Any]] | None = None,
    knowledge_links: list[Mapping[str, Any]] | None = None,
    store: PalSnapshotStore | None = None,
    legacy_pal_path: str | Path | None = None,
    legacy_kg_path: str | Path | None = None,
) -> dict[str, Any]:
    """Summarise supplied customer learning and persist encrypted evidence.

    Guardian mode deliberately requires caller-supplied inputs. This prevents
    an update from silently reading an undeclared application-local knowledge
    source. Legacy paths must be explicit when the Vault is authoritative.
    """
    snapshot_store = store or PalSnapshotStore()
    if exemplars is None:
        if snapshot_store.guardian_enabled and legacy_pal_path is None:
            raise RuntimeError("pal_snapshot_guardian_exemplars_required")
        exemplars = read_pal_memory(legacy_pal_path or PAL_FILE)
    if knowledge_links is None:
        if snapshot_store.guardian_enabled and legacy_kg_path is None:
            raise RuntimeError("pal_snapshot_guardian_knowledge_links_required")
        knowledge_links = read_knowledge_graph(legacy_kg_path or KG_DB)
    snapshot = {
        "timestamp": _timestamp(),
        "pal_summary": summarize_pal(exemplars),
        "top_kg_links": [dict(item) for item in knowledge_links[:10]],
    }
    return snapshot_store.append(snapshot)


def take_snapshot(**kwargs: Any) -> dict[str, Any]:
    """Compatibility entrypoint used by PAL equilibrium training."""
    return create_snapshot(**kwargs)


if __name__ == "__main__":
    create_snapshot()
