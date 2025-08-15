from __future__ import annotations
from typing import Dict, Any, Iterable, List

class KnowledgeRelinker:
    """
    Watches knowledge changes and proposes/executes relinks.
    MVP: pure functions over provided edges, no I/O coupling.
    """
    def relink_projects_for_updated_fact(
        self, *, fact_id: str, projects: Iterable[Dict[str,Any]]
    ) -> List[Dict[str,Any]]:
        """
        Given a fact update, return patched project metas:
        - ensure project.meta.links.facts includes fact_id
        - bump project.meta.last_link_refresh
        """
        patches = []
        for proj in projects:
            meta = proj.setdefault("meta", {})
            links = meta.setdefault("links", {})
            facts = links.setdefault("facts", [])
            if fact_id not in facts:
                facts.append(fact_id)
            meta["last_link_refresh"] = "now"
            patches.append({"id": proj.get("id"), "meta": meta})
        return patches

relinker = KnowledgeRelinker()