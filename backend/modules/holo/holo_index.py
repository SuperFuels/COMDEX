# backend/modules/holo/holo_index.py
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

# On-disk global index for all holos, across containers.
# Kept next to the .holo exports under holo_exports/.
HOLO_INDEX_PATH = (
    Path("backend/modules/dimensions/containers/holo_exports") / "holo_index.json"
)


@dataclass
class HoloIndexEntry:
    container_id: str
    holo_id: str
    revision: int
    tick: int
    created_at: str  # ISO-8601
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _load_holo_index() -> List[Dict[str, Any]]:
    """
    Load the global holo index from disk.

    Returns [] if the file does not exist or is unreadable.
    """
    if not HOLO_INDEX_PATH.exists():
        return []
    try:
        return json.loads(HOLO_INDEX_PATH.read_text())
    except Exception:
        # Corrupt index should not crash callers – just treat as empty.
        return []


def _write_holo_index(entries: List[Dict[str, Any]]) -> None:
    """
    Persist the full index back to disk.
    """
    HOLO_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    HOLO_INDEX_PATH.write_text(json.dumps(entries, indent=2, sort_keys=True))


def add_to_holo_index(entry: HoloIndexEntry) -> None:
    """
    Upsert a single HoloIndexEntry by holo_id into the global index.
    """
    entries = _load_holo_index()
    entries = [e for e in entries if e.get("holo_id") != entry.holo_id]
    entries.append(entry.to_dict())
    _write_holo_index(entries)


def load_holo_history_for_container(container_id: str) -> List[Dict[str, Any]]:
    """
    Return all global-index entries for a given container, newest → oldest.

    Shape (per entry):
      {
        "container_id": "...",
        "holo_id": "...",
        "revision": int,
        "tick": int,
        "created_at": "...",
        "tags": [...],
      }
    """
    entries = _load_holo_index()
    entries = [e for e in entries if e.get("container_id") == container_id]

    entries.sort(
        key=lambda e: (
            e.get("tick", 0),
            e.get("revision", 0),
            e.get("created_at", ""),
        ),
        reverse=True,
    )
    return entries


def search_holo_index(
    container_id: Optional[str] = None,
    tag: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Global search over holo_index.json.

    Filters:
      - container_id (optional)
      - tag (optional, must be present in entry["tags"])
    Returns newest → oldest.
    """
    entries = _load_holo_index()

    if container_id:
        entries = [e for e in entries if e.get("container_id") == container_id]

    if tag:
        entries = [e for e in entries if tag in (e.get("tags") or [])]

    entries.sort(
        key=lambda e: (
            e.get("tick", 0),
            e.get("revision", 0),
            e.get("created_at", ""),
        ),
        reverse=True,
    )
    return entries