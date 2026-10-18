#!/usr/bin/env python3
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from backend.modules.aion_business.runtime.business_vault_runtime import guardian_mode_requested
from backend.modules.aion_learning.vault_store import AionLearningVaultStore

DEFAULT_TEACHING_MEMORY_FILE = Path("data/logs/phase0_learning_memory.json")


class TeachingMemoryStore:
    def __init__(
        self,
        path: Path | str | None = None,
        *,
        vault_store: AionLearningVaultStore | None = None,
        workspace_id: str | None = None,
    ) -> None:
        explicit_path = path is not None
        self.path = Path(path or DEFAULT_TEACHING_MEMORY_FILE)
        self.vault_store = vault_store
        if vault_store is None and not explicit_path and guardian_mode_requested():
            self.vault_store = AionLearningVaultStore(workspace_id=workspace_id)

    def load(self) -> Dict[str, Any]:
        if self.vault_store is not None:
            data = self.vault_store.get_state("teaching_memory", {"concepts": {}})
            if not isinstance(data, dict):
                return {"concepts": {}}
            data.setdefault("concepts", {})
            if not isinstance(data["concepts"], dict):
                data["concepts"] = {}
            return data
        if not self.path.exists():
            return {"concepts": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"concepts": {}}
            data.setdefault("concepts", {})
            if not isinstance(data["concepts"], dict):
                data["concepts"] = {}
            return data
        except Exception:
            return {"concepts": {}}

    def save(self, mem: Dict[str, Any]) -> None:
        if self.vault_store is not None:
            self.vault_store.put_state("teaching_memory", mem)
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(mem, indent=2), encoding="utf-8")

    def clear(self) -> None:
        if self.vault_store is not None:
            self.vault_store.delete_state("teaching_memory")
            return
        if self.path.exists():
            self.path.unlink()

    def upsert_concept(
        self,
        *,
        concept_label: str,
        corrected_response: str,
        target_confidence: float,
        tags: Optional[list[str]] = None,
        notes: Optional[str] = None,
        correction_reason: Optional[str] = None,
        routing_hints: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        mem = self.load()
        concepts = mem.setdefault("concepts", {})

        rec = {
            "concept_label": concept_label,
            "corrected_response": corrected_response,
            "target_confidence": float(target_confidence),
            "tags": list(tags or []),
            "notes": notes,
            "correction_reason": correction_reason,
            "routing_hints": routing_hints or {},
            "updated_at": time.time(),
        }
        concepts[concept_label] = rec
        self.save(mem)
        return rec

    def get_concept(self, concept_label: str) -> Optional[Dict[str, Any]]:
        mem = self.load()
        concepts = mem.get("concepts", {}) or {}
        rec = concepts.get(concept_label)
        return rec if isinstance(rec, dict) else None

    def all_concepts(self) -> Dict[str, Dict[str, Any]]:
        mem = self.load()
        concepts = mem.get("concepts", {}) or {}
        return {k: v for k, v in concepts.items() if isinstance(v, dict)}
