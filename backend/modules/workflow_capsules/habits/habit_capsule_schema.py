from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import hashlib
import json
import re


SCHEMA_VERSION = "aion.habit_capsule.v1"
DEFAULT_SIGNER = "Tessaris-Core"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _stable_hash(payload: Dict[str, Any]) -> str:
    return hashlib.sha3_256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_.:-]+", ".", str(value or "").strip()).strip(".")
    return slug or "habit.untitled.v1"


@dataclass
class HabitCapsule:
    """
    Habit Capsule v1.

    A Habit Capsule is not a live executable replacement yet.
    It is a CAU-approved reinforcement record proving that a workflow has
    repeatedly succeeded under policy and may later be resolved as a stable habit.
    """

    habit_key: str
    source_workflow_key: str
    display_name: str
    meaning: str

    trigger_tags: List[str] = field(default_factory=list)
    promotion_policy: Dict[str, Any] = field(default_factory=dict)
    evidence: Dict[str, Any] = field(default_factory=dict)
    resonance: Dict[str, Any] = field(default_factory=dict)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        meta = data.setdefault("meta", {})
        meta.setdefault("schema_version", SCHEMA_VERSION)
        meta.setdefault("signed_by", DEFAULT_SIGNER)
        meta.setdefault("created_at", _utc_now_iso())
        meta.setdefault("version", "1.0")
        return data

    def stable_dict(self) -> Dict[str, Any]:
        data = self.to_dict()
        meta = dict(data.get("meta") or {})
        meta.pop("checksum", None)
        data["meta"] = meta
        return data

    def checksum(self) -> str:
        return _stable_hash(self.stable_dict())

    def finalize(self) -> "HabitCapsule":
        self.meta.setdefault("schema_version", SCHEMA_VERSION)
        self.meta.setdefault("signed_by", DEFAULT_SIGNER)
        self.meta.setdefault("created_at", _utc_now_iso())
        self.meta.setdefault("version", "1.0")
        self.meta["checksum"] = self.checksum()
        return self

    def save(self, path: str | Path) -> Path:
        self.finalize()
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return p

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HabitCapsule":
        return cls(
            habit_key=str(data.get("habit_key") or ""),
            source_workflow_key=str(data.get("source_workflow_key") or ""),
            display_name=str(data.get("display_name") or ""),
            meaning=str(data.get("meaning") or ""),
            trigger_tags=list(data.get("trigger_tags") or []),
            promotion_policy=dict(data.get("promotion_policy") or {}),
            evidence=dict(data.get("evidence") or {}),
            resonance=dict(data.get("resonance") or {}),
            meta=dict(data.get("meta") or {}),
        ).finalize()

    @classmethod
    def load(cls, path: str | Path) -> "HabitCapsule":
        p = Path(path)
        return cls.from_dict(json.loads(p.read_text(encoding="utf-8")))


def make_habit_key(source_workflow_key: str) -> str:
    source = _safe_slug(source_workflow_key.replace("workflow:", ""))
    return f"habit:{source}"
