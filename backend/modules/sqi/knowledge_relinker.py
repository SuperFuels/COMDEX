from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional
import os
from datetime import datetime, timezone


def _deterministic_time_enabled() -> bool:
    return os.getenv("TESSARIS_DETERMINISTIC_TIME") == "1"


def _now_iso() -> str:
    # Deterministic mode: fixed timestamp (no wall clock).
    if _deterministic_time_enabled():
        return "0000-00-00T00:00:00.000Z"
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class KnowledgeRelinker:
    """
    Watches knowledge changes and proposes/executes relinks.
    MVP: pure functions over provided edges, no I/O coupling.
    """

    def relink_projects_for_updated_fact(
        self, *, fact_id: str, projects: Iterable[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Given a fact update, return patched project metas:
        - ensure project.meta.links.facts includes fact_id
        - bump project.meta.last_link_refresh (deterministic when enabled)
        """
        fid = str(fact_id)
        ts = _now_iso()

        patches: List[Dict[str, Any]] = []
        for proj in projects:
            if not isinstance(proj, dict):
                continue

            meta = proj.setdefault("meta", {})
            if not isinstance(meta, dict):
                meta = {}
                proj["meta"] = meta

            links = meta.setdefault("links", {})
            if not isinstance(links, dict):
                links = {}
                meta["links"] = links

            facts = links.setdefault("facts", [])
            if not isinstance(facts, list):
                facts = []
                links["facts"] = facts

            if fid and fid not in facts:
                facts.append(fid)

            meta["last_link_refresh"] = ts
            patches.append({"id": proj.get("id"), "meta": meta})

        return patches


# ─────────────────────────────────────────────
# Lazy singleton (avoid import-time runtime bring-up)
# ─────────────────────────────────────────────
_RELINKER: Optional[KnowledgeRelinker] = None


def get_relinker() -> KnowledgeRelinker:
    global _RELINKER
    if _RELINKER is None:
        _RELINKER = KnowledgeRelinker()
    return _RELINKER


class _RelinkerProxy:
    def __getattr__(self, name: str):
        return getattr(get_relinker(), name)


relinker = _RelinkerProxy()
