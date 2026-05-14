from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .contracts_workflow_glyph import (
    AION_WORKFLOW_OP_ACTION,
    AION_WORKFLOW_OP_APPROVAL,
    AION_WORKFLOW_OP_CLASSIFY,
    AION_WORKFLOW_OP_EXTRACT,
    AION_WORKFLOW_OP_ROUTE,
    AION_WORKFLOW_OP_SEQUENCE,
    AION_WORKFLOW_OP_TRIGGER,
    AION_WORKFLOW_OP_WAIT,
    WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION,
    WORKFLOW_GLYPH_SCHEMA_VERSION,
    WORKFLOW_NAMESPACE,
    WorkflowPolicy,
    assert_safe_workflow_glyph,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _node_id(node: dict[str, Any], index: int) -> str:
    return str(node.get("id") or node.get("node_id") or f"node_{index}")


def normalise_node_to_workflow_step(node: dict[str, Any], index: int = 0) -> dict[str, Any]:
    title = str(node.get("title") or "").lower()
    node_type = str(node.get("type") or node.get("node_type") or "").lower()
    node_id = _node_id(node, index)

    op = AION_WORKFLOW_OP_ACTION

    if (
        "trigger" in node_type
        or "trigger" in title
        or "gmail new email" in title
        or "webhook" in title
    ):
        op = AION_WORKFLOW_OP_TRIGGER
    elif "extract" in title or "parser" in node_type:
        op = AION_WORKFLOW_OP_EXTRACT
    elif "classify" in title or "router" in title or "router" in node_type or "route" in title:
        op = AION_WORKFLOW_OP_CLASSIFY
    elif "approval" in title or "gate" in node_type:
        op = AION_WORKFLOW_OP_APPROVAL
    elif "wait" in title or "delay" in title or "schedule" in title:
        op = AION_WORKFLOW_OP_WAIT
    elif "if" in title or "else" in title or "fork" in title:
        op = AION_WORKFLOW_OP_ROUTE

    return {
        "op": op,
        "node_id": node_id,
        "ref": node_id,
        "title": str(node.get("title") or "Untitled step"),
        "node_type": str(node.get("type") or node.get("node_type") or "Action"),
        "status": str(node.get("status") or "draft"),
        "meta": str(node.get("meta") or ""),
        "position": {
            "x": float(node.get("x") or 0),
            "y": float(node.get("y") or 0),
        },
        "config": node.get("config") if isinstance(node.get("config"), dict) else {},
    }


def order_nodes_for_workflow_glyph(graph: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])

    if not nodes:
        return []

    node_by_id = {_node_id(node, i): node for i, node in enumerate(nodes)}
    incoming = {node_id: 0 for node_id in node_by_id}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in node_by_id}

    for edge in edges:
        from_id = str(edge.get("from") or "")
        to_id = str(edge.get("to") or "")
        if from_id not in node_by_id or to_id not in node_by_id:
            continue
        incoming[to_id] += 1
        outgoing[from_id].append(to_id)

    queue = sorted(
        [node for node_id, node in node_by_id.items() if incoming.get(node_id, 0) == 0],
        key=lambda n: float(n.get("x") or 0),
    )

    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()

    while queue:
        node = queue.pop(0)
        node_id = str(node.get("id") or node.get("node_id") or "")
        if not node_id or node_id in seen:
            continue

        seen.add(node_id)
        ordered.append(node)

        next_ids = sorted(
            [next_id for next_id in outgoing.get(node_id, []) if next_id not in seen],
            key=lambda next_id: float((node_by_id.get(next_id) or {}).get("x") or 0),
        )

        for next_id in next_ids:
            incoming[next_id] = max(0, incoming.get(next_id, 0) - 1)
            if incoming[next_id] == 0 and next_id in node_by_id:
                queue.append(node_by_id[next_id])

    remaining = sorted(
        [node for node in nodes if str(node.get("id") or node.get("node_id") or "") not in seen],
        key=lambda n: float(n.get("x") or 0),
    )

    return ordered + remaining


def build_canvas_layout(graph: dict[str, Any]) -> dict[str, Any]:
    nodes = list(graph.get("nodes") or [])
    edges = list(graph.get("edges") or [])

    return {
        "schema_version": WORKFLOW_CANVAS_LAYOUT_SCHEMA_VERSION,
        "coordinate_space": "absolute_canvas_px",
        "nodes": [
            {
                "node_id": _node_id(node, index),
                "x": float(node.get("x") or 0),
                "y": float(node.get("y") or 0),
            }
            for index, node in enumerate(nodes)
        ],
        "edges": [
            {
                "from": str(edge.get("from") or ""),
                "to": str(edge.get("to") or ""),
                "condition": str(edge.get("condition") or "success"),
            }
            for edge in edges
        ],
    }


def compile_workflow_graph_to_glyph(payload: dict[str, Any]) -> dict[str, Any]:
    graph = payload.get("graph") or {}
    ordered_nodes = order_nodes_for_workflow_glyph(graph)

    business_container = (
        payload.get("business_container")
        or payload.get("workflow", {}).get("business_container")
        or "costa-conexion"
    )

    workflow_id = (
        payload.get("workflow_id")
        or payload.get("workflow", {}).get("workflow_id")
        or "workflow_draft_1"
    )

    name = payload.get("name") or payload.get("workflow", {}).get("name") or "Untitled workflow 1"
    status = payload.get("status") or payload.get("workflow", {}).get("status") or "draft"

    compiled = {
        "schema_version": WORKFLOW_GLYPH_SCHEMA_VERSION,
        "namespace": WORKFLOW_NAMESPACE,
        "op": AION_WORKFLOW_OP_SEQUENCE,
        "workflow": {
            "workflow_id": str(workflow_id),
            "name": str(name),
            "business_container": str(business_container),
            "status": str(status),
        },
        "policy": WorkflowPolicy().to_dict(),
        "steps": [
            normalise_node_to_workflow_step(node, index)
            for index, node in enumerate(ordered_nodes)
        ],
        "flow_links": [
            {
                "from": str(edge.get("from") or ""),
                "to": str(edge.get("to") or ""),
                "condition": str(edge.get("condition") or "success"),
            }
            for edge in (graph.get("edges") or [])
        ],
        "compiled_at": utc_now_iso(),
    }

    assert_safe_workflow_glyph(compiled)
    return compiled
