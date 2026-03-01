from __future__ import annotations

from typing import Any, Dict, List, Optional

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


class AIONEquitiesKGBridge:
    """
    Bridge from AION Equities domain payloads into first-class KG nodes/edges.

    This does not try to be clever about inference. It simply:
    - normalizes domain payloads into KG node payloads
    - writes them through knowledge_graph_writer
    - adds the canonical edges needed for traversal
    """

    def __init__(self, writer: Any = None):
        self.writer = writer or kg_writer

    def write_company(self, company: Dict[str, Any]) -> Dict[str, Any]:
        company_id = company["company_id"]
        node = _node(
            node_id=company_id,
            label=company.get("name") or company.get("ticker") or company_id,
            domain="equities_company",
            kind="fact",
            payload=company,
            tags=["aion_equities", "equities_company", "company"],
        )
        self.writer.inject_node(container_id=company_id, node=node)
        return node

    def write_assessment(self, assessment: Dict[str, Any]) -> Dict[str, Any]:
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
        self.writer.inject_node(container_id=assessment_id, node=node)
        self.writer.add_edge(entity_id, assessment_id, "evidence_source")
        return node

    def write_thesis(self, thesis: Dict[str, Any]) -> Dict[str, Any]:
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
        self.writer.inject_node(container_id=thesis_id, node=node)

        company_ref = thesis.get("company_ref")
        if company_ref:
            self.writer.add_edge(company_ref, thesis_id, "supports_thesis")

        for assessment_ref in thesis.get("assessment_refs", []) or []:
            if assessment_ref:
                self.writer.add_edge(assessment_ref, thesis_id, "evidence_source")

        return node

    def write_trigger_map(self, trigger_map: Dict[str, Any]) -> Dict[str, Any]:
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
        self.writer.inject_node(container_id=trigger_map_id, node=node)
        self.writer.add_edge(company_ref, trigger_map_id, "confidence_modifier")
        return node

    def write_pre_earnings_estimate(self, estimate: Dict[str, Any]) -> Dict[str, Any]:
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
        self.writer.inject_node(container_id=estimate_id, node=node)
        self.writer.add_edge(company_ref, estimate_id, "supports_thesis")
        return node

    def write_bundle(
        self,
        *,
        company: Optional[Dict[str, Any]] = None,
        assessment: Optional[Dict[str, Any]] = None,
        thesis: Optional[Dict[str, Any]] = None,
        trigger_map: Optional[Dict[str, Any]] = None,
        pre_earnings_estimate: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[str]]:
        written: Dict[str, List[str]] = {
            "nodes": [],
            "edges": [],
        }

        if company:
            node = self.write_company(company)
            written["nodes"].append(node["id"])

        if assessment:
            node = self.write_assessment(assessment)
            written["nodes"].append(node["id"])
            written["edges"].append(
                f"{assessment['entity_id']}->evidence_source->{assessment['assessment_id']}"
            )

        if thesis:
            node = self.write_thesis(thesis)
            written["nodes"].append(node["id"])
            company_ref = thesis.get("company_ref")
            if company_ref:
                written["edges"].append(f"{company_ref}->supports_thesis->{thesis['thesis_id']}")
            for assessment_ref in thesis.get("assessment_refs", []) or []:
                written["edges"].append(f"{assessment_ref}->evidence_source->{thesis['thesis_id']}")

        if trigger_map:
            node = self.write_trigger_map(trigger_map)
            written["nodes"].append(node["id"])
            written["edges"].append(
                f"{trigger_map['company_ref']}->confidence_modifier->{trigger_map['company_trigger_map_id']}"
            )

        if pre_earnings_estimate:
            node = self.write_pre_earnings_estimate(pre_earnings_estimate)
            written["nodes"].append(node["id"])
            written["edges"].append(
                f"{pre_earnings_estimate['company_ref']}->supports_thesis->{pre_earnings_estimate['pre_earnings_estimate_id']}"
            )

        return written


__all__ = ["AIONEquitiesKGBridge"]