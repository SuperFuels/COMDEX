from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Set

from backend.modules.aion_business.contracts.sovereign_brain import (
    assert_provider_adapter_boundary,
)


ALLOWED_NODE_TYPES = {
    "aion_ingress",
    "context",
    "retrieval",
    "model",
    "compute",
    "harness",
    "consensus",
    "policy",
    "approval",
    "capability",
    "verification",
    "learning",
    "aion_receipt",
}


@dataclass(slots=True)
class SovereignFlowCompileResult:
    ok: bool
    manifest: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class SovereignFlowCompiler:
    """Validates an intelligence graph. Compilation never executes a node."""

    def compile(self, spec: Mapping[str, Any]) -> SovereignFlowCompileResult:
        nodes = [dict(item) for item in spec.get("nodes", [])]
        edges = [dict(item) for item in spec.get("edges", [])]
        errors: List[str] = []
        by_id: Dict[str, Dict[str, Any]] = {}

        for node in nodes:
            node_id = str(node.get("id") or "").strip()
            node_type = str(node.get("type") or "").strip()
            if not node_id or node_id in by_id:
                errors.append("node_id_missing_or_duplicate")
                continue
            by_id[node_id] = node
            if node_type not in ALLOWED_NODE_TYPES:
                errors.append(f"node_type_not_allowed:{node_id}:{node_type}")
            if node_type == "model":
                try:
                    assert_provider_adapter_boundary(node)
                except ValueError as exc:
                    errors.append(f"{node_id}:{exc}")
                if node.get("writes_canonical_state") or node.get("grants_authority"):
                    errors.append(f"model_is_not_authority:{node_id}")
            if node_type in {"model", "retrieval"} and node.get("location") == "external":
                for key in ("provider", "data_classification", "disclosure_destination", "residency"):
                    if not str(node.get(key) or "").strip():
                        errors.append(f"external_node_missing_{key}:{node_id}")
            if node_type == "consensus":
                limit = int(node.get("max_iterations") or 0)
                if limit < 1 or limit > 8:
                    errors.append(f"consensus_iteration_limit_required:{node_id}")
                if not node.get("exit_criteria"):
                    errors.append(f"consensus_exit_criteria_required:{node_id}")
                if not node.get("budget"):
                    errors.append(f"consensus_budget_required:{node_id}")

        graph: Dict[str, List[str]] = {node_id: [] for node_id in by_id}
        reverse: Dict[str, List[str]] = {node_id: [] for node_id in by_id}
        for edge in edges:
            source, target = str(edge.get("source") or ""), str(edge.get("target") or "")
            if source not in by_id or target not in by_id:
                errors.append(f"edge_endpoint_missing:{source}:{target}")
                continue
            graph[source].append(target)
            reverse[target].append(source)
            if by_id[target].get("location") == "external" and not edge.get("encryption_required"):
                errors.append(f"external_edge_requires_encryption:{source}:{target}")

        ingress = [node_id for node_id, node in by_id.items() if node.get("type") == "aion_ingress"]
        receipts = [node_id for node_id, node in by_id.items() if node.get("type") == "aion_receipt"]
        if len(ingress) != 1:
            errors.append("exactly_one_aion_ingress_required")
        if len(receipts) != 1:
            errors.append("exactly_one_aion_receipt_required")

        if len(ingress) == 1 and len(receipts) == 1:
            reachable = self._walk(graph, ingress[0])
            can_reach_receipt = self._walk(reverse, receipts[0])
            for node_id in by_id:
                if node_id not in reachable or node_id not in can_reach_receipt:
                    errors.append(f"node_outside_aion_boundary:{node_id}")

        for node_id, node in by_id.items():
            if node.get("type") != "capability":
                continue
            ancestors = self._walk(reverse, node_id)
            if not any(by_id[item].get("type") == "policy" for item in ancestors if item in by_id):
                errors.append(f"capability_missing_policy:{node_id}")
            if node.get("consequential") and not any(
                by_id[item].get("type") == "approval" for item in ancestors if item in by_id
            ):
                errors.append(f"consequential_capability_missing_approval:{node_id}")

        if errors:
            return SovereignFlowCompileResult(ok=False, errors=sorted(set(errors)))

        canonical = {
            "schema_version": "aion.sovereign_intelligence_flow.v1",
            "flow_id": str(spec.get("flow_id") or "unnamed-flow"),
            "nodes": nodes,
            "edges": edges,
            "execution_state": "compiled_not_executed",
            "aion_boundary": {"ingress": ingress[0], "receipt": receipts[0]},
        }
        canonical["manifest_hash"] = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return SovereignFlowCompileResult(ok=True, manifest=canonical)

    @staticmethod
    def _walk(graph: Mapping[str, Iterable[str]], start: str) -> Set[str]:
        seen: Set[str] = set()
        pending = [start]
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            pending.extend(item for item in graph.get(current, []) if item not in seen)
        return seen


def reference_flow() -> Dict[str, Any]:
    """A provider-neutral, non-executing example used by the public explainer and tests."""
    return {
        "flow_id": "public.second-brain.explainer",
        "nodes": [
            {"id": "admit", "type": "aion_ingress"},
            {"id": "evidence", "type": "retrieval", "location": "local"},
            {"id": "specialist_a", "type": "model", "location": "local", "authorities": []},
            {"id": "specialist_b", "type": "model", "location": "local", "authorities": []},
            {
                "id": "compare",
                "type": "consensus",
                "max_iterations": 3,
                "exit_criteria": "evidence-supported agreement or explicit disagreement",
                "budget": {"seconds": 60, "iterations": 3},
            },
            {"id": "govern", "type": "policy"},
            {"id": "approve", "type": "approval"},
            {"id": "act", "type": "capability", "consequential": True},
            {"id": "verify", "type": "verification"},
            {"id": "receipt", "type": "aion_receipt"},
        ],
        "edges": [
            {"source": "admit", "target": "evidence"},
            {"source": "evidence", "target": "specialist_a"},
            {"source": "evidence", "target": "specialist_b"},
            {"source": "specialist_a", "target": "compare"},
            {"source": "specialist_b", "target": "compare"},
            {"source": "compare", "target": "govern"},
            {"source": "govern", "target": "approve"},
            {"source": "approve", "target": "act"},
            {"source": "act", "target": "verify"},
            {"source": "verify", "target": "receipt"},
        ],
    }
