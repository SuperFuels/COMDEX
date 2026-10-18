from __future__ import annotations

from typing import Any, Dict, List, Optional
import re

from backend.modules.knowledge_graph.knowledge_graph_writer import kg_writer


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _node(
    *,
    node_id: str,
    label: str,
    domain: str,
    kind: str,
    payload: Dict[str, Any],
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return {
        "id": node_id,
        "label": label,
        "domain": domain,
        "kind": kind,
        "payload": payload,
        "tags": list(tags or ["aion_equities", domain]),
    }


def _slug(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("/", "__")
    s = re.sub(r"[^a-zA-Z0-9_.\-]+", "_", s)
    s = s.replace(".", "_")
    return s


def _period_container_id(company_ref: str, fiscal_period_ref: str) -> str:
    # A real UCS container id / filename-safe id.
    # Example: equities__company_PAGE_L__2025_Q2
    return f"equities__{_slug(company_ref)}__{_slug(fiscal_period_ref)}"


class AIONEquitiesKGBridge:
    """
    Bridge from AION Equities domain payloads into first-class KG nodes/edges.

    NEW BEHAVIOR:
      - creates ONE visible .dc.json container per (company_ref, fiscal_period_ref)
      - injects trigger_map + variable_watch + assessment + thesis nodes into that container
      - writes edges into THAT SAME container's glyph_grid (kg_edge records)
    """

    def __init__(self, writer: Any = None):
        self.writer = writer or kg_writer

    # -----------------------------
    # Internal helpers
    # -----------------------------
    def _ensure_period_container(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
    ) -> str:
        cid = _period_container_id(company_ref, fiscal_period_ref)

        # Create/refresh a top-level "period snapshot" node (idempotent).
        snapshot_node = _node(
            node_id=f"{company_ref}/kg_period/{fiscal_period_ref}",
            label=f"{company_ref} {fiscal_period_ref} (Equities Snapshot)",
            domain="equities_period_snapshot",
            kind="fact",
            payload={
                "company_ref": company_ref,
                "fiscal_period_ref": fiscal_period_ref,
                "container_id": cid,
            },
            tags=["aion_equities", "equities_period_snapshot", "period", "snapshot"],
        )

        # IMPORTANT: inject into the PERIOD container, not into its own node_id container.
        self.writer.inject_node(container_id=cid, node=snapshot_node, allow_create=True, commit=True)
        return cid

    def _inject_edge(
        self,
        *,
        period_container_id: str,
        src: str,
        dst: str,
        relation: str,
    ) -> None:
        """
        Write a kg_edge into the SAME .dc.json container file (glyph_grid),
        so export_pack + UI traversal can see it.
        """
        # Use writer internals (already present in your KnowledgeGraphWriter)
        path = self.writer._container_path_for(period_container_id)  # type: ignore[attr-defined]
        container = self.writer._safe_load_container(path)  # type: ignore[attr-defined]
        container.setdefault("glyph_grid", [])

        # de-dupe exact edge
        gg = container["glyph_grid"]
        gg = [
            g for g in gg
            if not (
                isinstance(g, dict)
                and g.get("type") == "kg_edge"
                and (g.get("metadata") or {}).get("from") == src
                and (g.get("metadata") or {}).get("to") == dst
                and (g.get("metadata") or {}).get("relation") == relation
            )
        ]
        gg.append({
            "type": "kg_edge",
            "metadata": {"from": src, "to": dst, "relation": relation},
        })
        container["glyph_grid"] = gg

        self.writer._safe_save_container(path, container)  # type: ignore[attr-defined]

    # -----------------------------
    # Writers (period-aware)
    # -----------------------------
    def write_company(self, company: Dict[str, Any], *, period_container_id: str) -> Dict[str, Any]:
        company_id = company["company_id"]
        node = _node(
            node_id=company_id,
            label=company.get("name") or company.get("ticker") or company_id,
            domain="equities_company",
            kind="fact",
            payload=company,
            tags=["aion_equities", "equities_company", "company"],
        )
        self.writer.inject_node(container_id=period_container_id, node=node)
        return node

    def write_assessment(self, assessment: Dict[str, Any], *, period_container_id: str) -> Dict[str, Any]:
        assessment_id = assessment["assessment_id"]
        entity_id = assessment["entity_id"]

        node = _node(
            node_id=assessment_id,
            label=f"Assessment {assessment_id}",
            domain="equities_assessment",
            kind="fact",
            payload=assessment,
            tags=["aion_equities", "equities_assessment", "assessment"],
        )
        self.writer.inject_node(container_id=period_container_id, node=node)
        self._inject_edge(
            period_container_id=period_container_id,
            src=entity_id,
            dst=assessment_id,
            relation="evidence_source",
        )
        return node

    def write_thesis(self, thesis: Dict[str, Any], *, period_container_id: str) -> Dict[str, Any]:
        thesis_id = thesis["thesis_id"]
        ticker = _safe_str(thesis.get("ticker"))
        label = f"Theory {ticker}".strip() if ticker else thesis_id

        node = _node(
            node_id=thesis_id,
            label=label,
            domain="equities_thesis",
            kind="fact",
            payload=thesis,
            tags=["aion_equities", "equities_thesis", "thesis"],
        )
        self.writer.inject_node(container_id=period_container_id, node=node)

        company_ref = thesis.get("company_ref")
        if company_ref:
            self._inject_edge(
                period_container_id=period_container_id,
                src=company_ref,
                dst=thesis_id,
                relation="supports_thesis",
            )

        for assessment_ref in thesis.get("assessment_refs", []) or []:
            if assessment_ref:
                self._inject_edge(
                    period_container_id=period_container_id,
                    src=assessment_ref,
                    dst=thesis_id,
                    relation="evidence_source",
                )

        return node

    def write_trigger_map(self, trigger_map: Dict[str, Any], *, period_container_id: str) -> Dict[str, Any]:
        trigger_map_id = trigger_map["company_trigger_map_id"]
        company_ref = trigger_map["company_ref"]

        node = _node(
            node_id=trigger_map_id,
            label=f"TriggerMap {company_ref}",
            domain="equities_trigger_map",
            kind="fact",
            payload=trigger_map,
            tags=["aion_equities", "equities_trigger_map", "trigger_map"],
        )
        self.writer.inject_node(container_id=period_container_id, node=node)
        self._inject_edge(
            period_container_id=period_container_id,
            src=company_ref,
            dst=trigger_map_id,
            relation="confidence_modifier",
        )
        return node

    def write_variable_watch(self, variable_watch: Dict[str, Any], *, period_container_id: str) -> Dict[str, Any]:
        variable_watch_id = variable_watch["variable_watch_id"]
        company_ref = variable_watch["company_ref"]

        node = _node(
            node_id=variable_watch_id,
            label=f"VariableWatch {company_ref}",
            domain="equities_variable_watch",
            kind="fact",
            payload=variable_watch,
            tags=["aion_equities", "equities_variable_watch", "variable_watch"],
        )
        self.writer.inject_node(container_id=period_container_id, node=node)
        self._inject_edge(
            period_container_id=period_container_id,
            src=company_ref,
            dst=variable_watch_id,
            relation="watchlist",
        )
        return node

    def write_pre_earnings_estimate(self, estimate: Dict[str, Any], *, period_container_id: str) -> Dict[str, Any]:
        estimate_id = estimate["pre_earnings_estimate_id"]
        company_ref = estimate["company_ref"]

        node = _node(
            node_id=estimate_id,
            label=f"PreEarnings {company_ref}",
            domain="equities_pre_earnings",
            kind="fact",
            payload=estimate,
            tags=["aion_equities", "equities_pre_earnings", "pre_earnings_estimate"],
        )
        self.writer.inject_node(container_id=period_container_id, node=node)
        self._inject_edge(
            period_container_id=period_container_id,
            src=company_ref,
            dst=estimate_id,
            relation="supports_thesis",
        )
        return node

    def write_bundle(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
        company: Optional[Dict[str, Any]] = None,
        assessment: Optional[Dict[str, Any]] = None,
        thesis: Optional[Dict[str, Any]] = None,
        trigger_map: Optional[Dict[str, Any]] = None,
        variable_watch: Optional[Dict[str, Any]] = None,
        pre_earnings_estimate: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        NEW: requires company_ref + fiscal_period_ref so we can materialize a single container.

        Returns:
          { "period_container_id": "...", "written": {"nodes": [...], "edges": [...]} }
        """
        period_cid = self._ensure_period_container(
            company_ref=company_ref,
            fiscal_period_ref=fiscal_period_ref,
        )

        written: Dict[str, List[str]] = {"nodes": [], "edges": []}

        # Always link the period snapshot to company (nice traversal anchor)
        self._inject_edge(
            period_container_id=period_cid,
            src=company_ref,
            dst=f"{company_ref}/kg_period/{fiscal_period_ref}",
            relation="has_period",
        )

        if company:
            node = self.write_company(company, period_container_id=period_cid)
            written["nodes"].append(node["id"])

        if assessment:
            node = self.write_assessment(assessment, period_container_id=period_cid)
            written["nodes"].append(node["id"])
            written["edges"].append(f"{assessment['entity_id']}->evidence_source->{assessment['assessment_id']}")

        if thesis:
            node = self.write_thesis(thesis, period_container_id=period_cid)
            written["nodes"].append(node["id"])
            company_ref2 = thesis.get("company_ref")
            if company_ref2:
                written["edges"].append(f"{company_ref2}->supports_thesis->{thesis['thesis_id']}")
            for assessment_ref in thesis.get("assessment_refs", []) or []:
                written["edges"].append(f"{assessment_ref}->evidence_source->{thesis['thesis_id']}")

        if trigger_map:
            node = self.write_trigger_map(trigger_map, period_container_id=period_cid)
            written["nodes"].append(node["id"])
            written["edges"].append(f"{trigger_map['company_ref']}->confidence_modifier->{trigger_map['company_trigger_map_id']}")

        if variable_watch:
            node = self.write_variable_watch(variable_watch, period_container_id=period_cid)
            written["nodes"].append(node["id"])
            written["edges"].append(f"{variable_watch['company_ref']}->watchlist->{variable_watch['variable_watch_id']}")

        if pre_earnings_estimate:
            node = self.write_pre_earnings_estimate(pre_earnings_estimate, period_container_id=period_cid)
            written["nodes"].append(node["id"])
            written["edges"].append(f"{pre_earnings_estimate['company_ref']}->supports_thesis->{pre_earnings_estimate['pre_earnings_estimate_id']}")

        return {"period_container_id": period_cid, "written": written}


__all__ = ["AIONEquitiesKGBridge"]