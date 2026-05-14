from __future__ import annotations

from typing import Any, Dict, Optional

from backend.modules.dimensions.universal_container_system.ucs_runtime import ucs_runtime


class AIONEquitiesContainerAdapter:
    def __init__(self, runtime: Optional[Any] = None):
        self.runtime = runtime or ucs_runtime

    def _save(self, container: Dict[str, Any]) -> Dict[str, Any]:
        self.runtime.save_container(container["id"], container)
        return container

    def company_container(self, company: Dict[str, Any]) -> Dict[str, Any]:
        cid = f"equities/company/{company.get('ticker', company['company_id'])}"
        container = {
            "id": cid,
            "name": company.get("name", cid),
            "type": "container",
            "kind": "equities_company",
            "domain": "aion_equities",
            "meta": {
                "source_ref": company["company_id"],
                "topic": "ucs://local/aion_equities",
            },
            "payload": company,
            "glyph_grid": [],
            "nodes": [],
            "wormholes": ["ucs_hub"],
        }
        return self._save(container)

    def assessment_container(
        self,
        assessment: Dict[str, Any],
        *,
        sqi_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cid = f"equities/assessment/{assessment['assessment_id'].replace('/', '__')}"
        container = {
            "id": cid,
            "name": assessment.get("assessment_id", cid),
            "type": "container",
            "kind": "equities_assessment",
            "domain": "aion_equities",
            "meta": {
                "source_ref": assessment["assessment_id"],
                "topic": "ucs://local/aion_equities",
            },
            "payload": assessment,
            "sqi_payload": sqi_payload or {},
            "glyph_grid": [],
            "nodes": [],
            "wormholes": ["ucs_hub"],
        }
        return self._save(container)

    def thesis_container(
        self,
        thesis: Dict[str, Any],
        *,
        sqi_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cid = f"equities/thesis/{thesis['thesis_id'].replace('/', '__')}"
        container = {
            "id": cid,
            "name": thesis.get("thesis_id", cid),
            "type": "container",
            "kind": "equities_thesis",
            "domain": "aion_equities",
            "meta": {
                "source_ref": thesis["thesis_id"],
                "topic": "ucs://local/aion_equities",
            },
            "payload": thesis,
            "sqi_payload": sqi_payload or {},
            "glyph_grid": [],
            "nodes": [],
            "wormholes": ["ucs_hub"],
        }
        return self._save(container)

    def trigger_map_container(
        self,
        trigger_map: Dict[str, Any],
        *,
        sqi_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cid = f"equities/trigger_map/{trigger_map['company_trigger_map_id'].replace('/', '__')}"
        container = {
            "id": cid,
            "name": trigger_map["company_trigger_map_id"],
            "type": "container",
            "kind": "equities_trigger_map",
            "domain": "aion_equities",
            "meta": {
                "source_ref": trigger_map["company_trigger_map_id"],
                "topic": "ucs://local/aion_equities",
            },
            "payload": trigger_map,
            "sqi_payload": sqi_payload or {},
            "glyph_grid": [],
            "nodes": [],
            "wormholes": ["ucs_hub"],
        }
        return self._save(container)

    def pre_earnings_estimate_container(
        self,
        estimate: Dict[str, Any],
        *,
        sqi_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        cid = f"equities/pre_earnings/{estimate['pre_earnings_estimate_id'].replace('/', '__')}"
        container = {
            "id": cid,
            "name": estimate.get("pre_earnings_estimate_id", cid),
            "type": "container",
            "kind": "equities_pre_earnings_estimate",
            "domain": "aion_equities",
            "meta": {
                "source_ref": estimate["pre_earnings_estimate_id"],
                "topic": "ucs://local/aion_equities",
            },
            "payload": estimate,
            "sqi_payload": sqi_payload or {},
            "glyph_grid": [],
            "nodes": [],
            "wormholes": ["ucs_hub"],
        }
        return self._save(container)