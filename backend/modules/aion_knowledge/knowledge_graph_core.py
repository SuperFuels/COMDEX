#!/usr/bin/env python3
"""Workspace-scoped AION knowledge graph.

Customer-learned triplets use encrypted Guardian domain records when the
Business Vault is authoritative. An explicit SQLite path remains available
for legacy operation, tests and source-retaining migration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
import json
import logging
import os
from pathlib import Path
import sqlite3
import sys
import time
from typing import Any, Iterable, Optional
import uuid

from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


logger = logging.getLogger(__name__)
DATA_PATH = Path("data/knowledge")
DB_PATH = DATA_PATH / "aion_knowledge_graph.db"


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _triplet_entity_id(subject: str, predicate: str, obj: str) -> str:
    digest = sha256(f"{subject}\0{predicate}\0{obj}".encode("utf-8")).hexdigest()
    return f"aion-knowledge-triplet-{digest}"


class AionKnowledgeGraphStore:
    """Encrypted per-workspace graph with explicit legacy SQLite support."""

    DOMAIN_ID = "business.knowledge"
    RECORD_TYPE = "aion_knowledge_triplet"

    def __init__(
        self,
        *,
        domain_store: VaultDomainStore | None = None,
        workspace_id: str | None = None,
        legacy_db_path: str | Path | None = None,
        auto_configure: bool = True,
    ) -> None:
        if domain_store is None and auto_configure and legacy_db_path is None:
            if guardian_mode_requested():
                runtime = configured_business_vault_runtime()
                domain_store = VaultDomainStore(
                    runtime.guardian,
                    actor_id="aion-knowledge-graph-runtime",
                )
        self.domain_store = domain_store
        self.workspace_id = str(
            workspace_id
            or os.environ.get("TESSARIS_BUSINESS_STABLE_ID")
            or ""
        ).strip()
        if self.domain_store is not None and not self.workspace_id:
            raise ValueError("aion_knowledge_graph_workspace_id_required")
        self.legacy_db_path = Path(legacy_db_path or DB_PATH)

    @property
    def guardian_enabled(self) -> bool:
        return self.domain_store is not None

    def _legacy_connection(self) -> sqlite3.Connection:
        self.legacy_db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.legacy_db_path)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT,
                predicate TEXT,
                object TEXT,
                strength REAL,
                vec TEXT,
                timestamp TEXT
            )
            """
        )
        connection.commit()
        return connection

    def list_triplets(self) -> list[dict[str, Any]]:
        if self.domain_store is not None:
            output = [
                dict(row["payload"])
                for row in self.domain_store.list(
                    self.DOMAIN_ID,
                    workspace_id=self.workspace_id,
                )
                if row["payload"].get("record_type") == self.RECORD_TYPE
            ]
            return sorted(
                output,
                key=lambda row: (
                    str(row.get("subject") or ""),
                    str(row.get("predicate") or ""),
                    str(row.get("object") or ""),
                ),
            )
        connection = self._legacy_connection()
        try:
            rows = connection.execute(
                "SELECT subject,predicate,object,strength,vec,timestamp "
                "FROM knowledge ORDER BY subject,predicate,object"
            ).fetchall()
        finally:
            connection.close()
        return [
            {
                "record_type": self.RECORD_TYPE,
                "subject": row[0],
                "predicate": row[1],
                "object": row[2],
                "strength": float(row[3] or 0.0),
                "vec": json.loads(row[4]) if row[4] else None,
                "timestamp": row[5],
                "provenance_class": "legacy_unclassified",
            }
            for row in rows
        ]

    def get(self, subject: str, predicate: str, obj: str) -> dict[str, Any] | None:
        entity_id = _triplet_entity_id(subject, predicate, obj)
        if self.domain_store is not None:
            row = self.domain_store.get_optional(
                self.DOMAIN_ID,
                workspace_id=self.workspace_id,
                entity_id=entity_id,
            )
            if row is None or row["payload"].get("record_type") != self.RECORD_TYPE:
                return None
            return {**dict(row["payload"]), "_version": int(row["version"])}
        connection = self._legacy_connection()
        try:
            row = connection.execute(
                "SELECT subject,predicate,object,strength,vec,timestamp FROM knowledge "
                "WHERE subject=? AND predicate=? AND object=? ORDER BY id LIMIT 1",
                (subject, predicate, obj),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            return None
        return {
            "record_type": self.RECORD_TYPE,
            "subject": row[0],
            "predicate": row[1],
            "object": row[2],
            "strength": float(row[3] or 0.0),
            "vec": json.loads(row[4]) if row[4] else None,
            "timestamp": row[5],
            "provenance_class": "legacy_unclassified",
        }

    def put(
        self,
        subject: str,
        predicate: str,
        obj: Any,
        *,
        vec: Optional[list[Any]] = None,
        strength: float = 1.0,
        reinforce_existing: bool = True,
        provenance_class: str = "customer_derived",
    ) -> dict[str, Any]:
        subject_text = str(subject)
        predicate_text = str(predicate)
        object_text = str(obj)
        existing = self.get(subject_text, predicate_text, object_text)
        next_strength = float(strength)
        if existing is not None and reinforce_existing:
            next_strength = float(existing.get("strength") or 0.0) + 0.1 * float(
                strength
            )
        payload = {
            "schema_version": "aion.knowledge-triplet.v1",
            "record_type": self.RECORD_TYPE,
            "subject": subject_text,
            "predicate": predicate_text,
            "object": object_text,
            "strength": next_strength,
            "vec": list(vec) if vec is not None else existing.get("vec") if existing else None,
            "timestamp": _now(),
            "provenance_class": str(provenance_class),
        }
        if self.domain_store is not None:
            self.domain_store.put(
                self.DOMAIN_ID,
                workspace_id=self.workspace_id,
                entity_id=_triplet_entity_id(subject_text, predicate_text, object_text),
                payload=payload,
                expected_version=(int(existing["_version"]) if existing else None),
                actor_id="aion-knowledge-graph-runtime",
            )
            return payload
        connection = self._legacy_connection()
        try:
            if existing is None:
                connection.execute(
                    "INSERT INTO knowledge(subject,predicate,object,strength,vec,timestamp) "
                    "VALUES(?,?,?,?,?,?)",
                    (
                        subject_text,
                        predicate_text,
                        object_text,
                        next_strength,
                        json.dumps(payload["vec"]) if payload["vec"] is not None else None,
                        payload["timestamp"],
                    ),
                )
            else:
                connection.execute(
                    "UPDATE knowledge SET strength=?,vec=?,timestamp=? "
                    "WHERE subject=? AND predicate=? AND object=?",
                    (
                        next_strength,
                        json.dumps(payload["vec"]) if payload["vec"] is not None else None,
                        payload["timestamp"],
                        subject_text,
                        predicate_text,
                        object_text,
                    ),
                )
            connection.commit()
        finally:
            connection.close()
        return payload

    def delete(self, subject: str, predicate: str, obj: str) -> bool:
        if self.domain_store is not None:
            return self.domain_store.delete(
                self.DOMAIN_ID,
                workspace_id=self.workspace_id,
                entity_id=_triplet_entity_id(subject, predicate, obj),
                reason_code="customer_knowledge_triplet_deleted",
                actor_id="aion-knowledge-graph-runtime",
            )
        connection = self._legacy_connection()
        try:
            cursor = connection.execute(
                "DELETE FROM knowledge WHERE subject=? AND predicate=? AND object=?",
                (subject, predicate, obj),
            )
            connection.commit()
            return int(cursor.rowcount or 0) > 0
        finally:
            connection.close()

    def search(
        self,
        *,
        subject: str | None = None,
        predicate: str | None = None,
        obj: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            row
            for row in self.list_triplets()
            if (subject is None or row["subject"] == subject)
            and (predicate is None or row["predicate"] == predicate)
            and (obj is None or row["object"] == obj)
        ]


def _store() -> AionKnowledgeGraphStore:
    return AionKnowledgeGraphStore()


def _connect() -> sqlite3.Connection:
    """Legacy-only compatibility hook.

    Direct SQL callers are rejected while Guardian is authoritative because a
    raw connection would bypass workspace isolation and audit controls.
    """
    store = _store()
    if store.guardian_enabled:
        raise RuntimeError("aion_knowledge_direct_sql_forbidden_in_guardian_mode")
    return store._legacy_connection()


triplets: dict[tuple[str, str, str], float] = {}
disable_auto_merge = False
auto_merge_cooldown_until = 0.0


def add_triplet(
    subject: str,
    predicate: str,
    obj: Any,
    vec: Optional[list[Any]] = None,
    strength: float = 1.0,
    provenance_class: str = "customer_derived",
) -> None:
    payload = _store().put(
        subject,
        predicate,
        obj,
        vec=vec,
        strength=strength,
        reinforce_existing=True,
        provenance_class=provenance_class,
    )
    triplets[(str(subject), str(predicate), str(obj))] = float(payload["strength"])


def search(
    subject: Optional[str] = None,
    predicate: Optional[str] = None,
    obj: Optional[str] = None,
) -> list[dict[str, Any]]:
    return _store().search(subject=subject, predicate=predicate, obj=obj)


def reinforce(subject: str, predicate: str, obj: str, gain: float = 0.05) -> None:
    store = _store()
    existing = store.get(subject, predicate, obj)
    if existing is None:
        return
    payload = store.put(
        subject,
        predicate,
        obj,
        vec=existing.get("vec"),
        strength=float(existing["strength"]) + float(gain),
        reinforce_existing=False,
        provenance_class=str(existing.get("provenance_class") or "customer_derived"),
    )
    triplets[(subject, predicate, obj)] = float(payload["strength"])


def related(node: str, depth: int = 1) -> list[dict[str, Any]]:
    del depth
    rows = [
        row
        for row in _store().list_triplets()
        if row["subject"] == node or row["object"] == node
    ]
    return sorted(rows, key=lambda row: float(row["strength"]), reverse=True)[:100]


def get_related(node: str, depth: int = 1) -> list[dict[str, Any]]:
    return related(node, depth=depth)


def load_knowledge() -> None:
    global triplets
    triplets = {
        (row["subject"], row["predicate"], row["object"]): float(row["strength"])
        for row in _store().list_triplets()
    }


def save_knowledge() -> None:
    store = _store()
    wanted = set(triplets)
    existing = {
        (row["subject"], row["predicate"], row["object"]): row
        for row in store.list_triplets()
    }
    for key, strength in triplets.items():
        row = existing.get(key)
        store.put(
            *key,
            vec=row.get("vec") if row else None,
            strength=float(strength),
            reinforce_existing=False,
            provenance_class=str(
                row.get("provenance_class") if row else "customer_derived"
            ),
        )
    for key in set(existing) - wanted:
        store.delete(*key)


def dump_concepts(limit: int = 20) -> None:
    rows = sorted(
        _store().search(predicate="is_a"),
        key=lambda row: float(row["strength"]),
        reverse=True,
    )[:limit]
    print("🌐 Concept Field Relations:")
    for row in rows:
        print(
            f"  {row['subject']} -[{row['predicate']}:{row['strength']:.3f}]-> "
            f"{row['object']}"
        )


try:
    from backend.bridges.photon_AKG_bridge import PhotonAKGBridge
except ModuleNotFoundError:
    try:
        from backend.modules.aion_photon.photon_AKG_bridge import PhotonAKGBridge
    except ModuleNotFoundError:
        PhotonAKGBridge = None

_photon_bridge = PhotonAKGBridge() if PhotonAKGBridge else None


def create_concept_node(
    name: str,
    symbols: list[str],
    meta: dict[str, Any] | None = None,
) -> str:
    concept_id = f"concept:{name}_{uuid.uuid4().hex[:8]}"
    add_triplet(concept_id, "type", "concept")
    add_triplet(concept_id, "created_at", str(time.time()))
    for symbol in symbols or []:
        add_triplet(f"symbol:{symbol}", "is_a", concept_id)
    for key, value in (meta or {}).items():
        add_triplet(concept_id, f"meta:{key}", str(value))
    add_triplet(concept_id, "meta:origin_system", "AION.ConceptEvolution")
    try:
        if _photon_bridge:
            _photon_bridge.export_concept(concept_id)
    except Exception as exc:
        logger.warning("[AKG->Photon] Failed to export %s: %s", concept_id, exc)
    return concept_id


def merge_concepts(a: str, b: str) -> str | None:
    if disable_auto_merge or time.time() < auto_merge_cooldown_until:
        return None
    return f"{a}_{b}_merged"


def start_auto_merge_cooldown(seconds: int = 60) -> None:
    global disable_auto_merge, auto_merge_cooldown_until
    disable_auto_merge = True
    auto_merge_cooldown_until = time.time() + seconds


def check_auto_merge_cooldown() -> None:
    global disable_auto_merge, auto_merge_cooldown_until
    if time.time() >= auto_merge_cooldown_until:
        disable_auto_merge = False
        auto_merge_cooldown_until = 0.0


def export_concepts() -> dict[str, list[str]]:
    if not triplets:
        load_knowledge()
    concept_map: dict[str, list[str]] = {}
    for subject, predicate, obj in triplets:
        if predicate == "is_a" and subject.startswith("symbol:") and obj.startswith(
            "concept:"
        ):
            concept_map.setdefault(obj.removeprefix("concept:"), []).append(
                subject.removeprefix("symbol:")
            )
    return concept_map


def inspect_node(concept_name: str) -> list[tuple[str, str, str, float]]:
    concept_id = (
        concept_name if concept_name.startswith("concept:") else f"concept:{concept_name}"
    )
    rows = related(concept_id)
    output = [
        (row["subject"], row["predicate"], row["object"], float(row["strength"]))
        for row in rows
    ]
    for subject, predicate, obj, strength in output:
        print(f"  {subject} -[{predicate}:{strength}]> {obj}")
    return output


def print_concept_tree(limit: int = 50, indent: int = 0) -> None:
    del indent
    if not triplets:
        load_knowledge()
    tree: dict[str, list[str]] = {}
    for (subject, predicate, obj), _strength in triplets.items():
        if predicate == "subclass_of":
            tree.setdefault(obj.removeprefix("concept:"), []).append(
                subject.removeprefix("concept:")
            )
    roots = [node for node in tree if not any(node in children for children in tree.values())]

    def emit(node: str, depth: int, seen: set[str]) -> None:
        if node in seen:
            return
        seen.add(node)
        print("  " * depth + ("↳ " if depth else "") + node)
        for child in tree.get(node, []):
            emit(child, depth + 1, seen)

    for root in roots[:limit]:
        emit(root, 0, set())


def adjust_concept_strength(
    concept_name: str,
    delta: float,
    mode: str = "add",
) -> None:
    store = _store()
    target = f"concept:{concept_name}"
    for row in store.search(predicate="is_a", obj=target):
        current = float(row["strength"])
        strength = current + float(delta) if mode == "add" else current * float(delta)
        store.put(
            row["subject"],
            row["predicate"],
            row["object"],
            vec=row.get("vec"),
            strength=strength,
            reinforce_existing=False,
            provenance_class=str(row.get("provenance_class") or "customer_derived"),
        )


def update_self_accuracy(concept_name: str, meta_accuracy: float) -> None:
    try:
        value = round(float(meta_accuracy), 4)
    except (TypeError, ValueError):
        value = 0.0
    add_triplet(f"concept:{concept_name}", "self_accuracy", value)


def dump_summary(limit: int = 10) -> None:
    rows = sorted(
        _store().list_triplets(),
        key=lambda row: float(row["strength"]),
        reverse=True,
    )[:limit]
    print("🧩 Top Knowledge Links:")
    for row in rows:
        print(
            f"  {row['subject']} -[{row['predicate']}:{row['strength']:.3f}]-> "
            f"{row['object']}"
        )


if __name__ == "__main__":
    print(export_concepts())
