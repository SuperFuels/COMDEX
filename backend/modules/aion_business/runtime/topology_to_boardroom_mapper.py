from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set


DEPARTMENT_ORDER = [
    "ceo",
    "coo",
    "marketing",
    "sales",
    "operations",
    "finance",
    "support",
    "hr",
    "aion",
    "openai",
]

SEAT_ID_MAP = {
    "ceo": "seat_ceo",
    "coo": "seat_coo",
    "marketing": "seat_marketing",
    "sales": "seat_sales",
    "operations": "seat_ops",
    "finance": "seat_finance",
    "support": "seat_support",
    "hr": "seat_hr",
    "aion": "seat_aion",
    "openai": "seat_openai",
}

DEPARTMENT_LABELS = {
    "ceo": "CEO",
    "coo": "COO",
    "marketing": "Marketing",
    "sales": "Sales",
    "operations": "Operations",
    "finance": "Finance",
    "support": "Support",
    "hr": "HR",
    "aion": "Aion",
    "openai": "OpenAI",
}


@dataclass(slots=True)
class TopologyBoardroomMapperResult:
    workspace: Dict[str, Any]
    departments: List[Dict[str, Any]]
    seats: List[Dict[str, Any]]
    pulse: Dict[str, Any]
    center: Dict[str, Any]
    active_zone: str
    selected_seat_id: Optional[str]
    floors: Dict[str, Any]
    runtime: Dict[str, Any]
    metadata: Dict[str, Any]


class TopologyToBoardroomMapper:
    """
    Converts persisted/generated business topology into a boardroom-friendly shape.

    Supports either:
    - BusinessTopology pydantic models
    - plain dict payloads

    Also accepts optional runtime summary input so the boardroom can project:
    - operators
    - workflows
    - triggers
    - recent runs
    - approvals
    - blocked / failed states
    """

    def map_topology(
        self,
        topology: Any,
        *,
        runtime_summary: Optional[Dict[str, Any]] = None,
        active_zone: str = "coo",
        selected_seat_id: Optional[str] = None,
    ) -> TopologyBoardroomMapperResult:
        topology_dict = self._to_dict(topology)
        runtime_payload = self._normalize_runtime_summary(runtime_summary)

        nodes = topology_dict.get("nodes", []) or []
        edges = topology_dict.get("edges", []) or []

        node_by_id = {node["id"]: node for node in nodes if node.get("id")}
        nodes_by_type = self._group_nodes_by_type(nodes)
        edge_index = self._build_edge_index(edges)

        workspace_node = self._pick_workspace_node(nodes_by_type)
        workspace = self._map_workspace(workspace_node)

        departments = self._map_departments(
            topology=topology_dict,
            nodes_by_type=nodes_by_type,
            edge_index=edge_index,
            node_by_id=node_by_id,
            runtime_summary=runtime_payload,
        )

        seats = self._map_seats(
            topology=topology_dict,
            departments=departments,
            nodes_by_type=nodes_by_type,
            edge_index=edge_index,
            node_by_id=node_by_id,
            runtime_summary=runtime_payload,
        )

        pulse = self._build_pulse(
            topology=topology_dict,
            nodes_by_type=nodes_by_type,
            edge_index=edge_index,
        )
        center = self._build_center_metrics(pulse=pulse, topology=topology_dict)

        floors = self._build_floors(
            topology=topology_dict,
            departments=departments,
            seats=seats,
            nodes_by_type=nodes_by_type,
            edge_index=edge_index,
            node_by_id=node_by_id,
            runtime_summary=runtime_payload,
        )

        runtime_projection = self._build_runtime_projection(
            departments=departments,
            seats=seats,
            runtime_summary=runtime_payload,
        )

        resolved_selected_seat_id = selected_seat_id or self._default_selected_seat_id(seats)
        resolved_active_zone = active_zone if active_zone in SEAT_ID_MAP else "coo"

        return TopologyBoardroomMapperResult(
            workspace=workspace,
            departments=departments,
            seats=seats,
            pulse=pulse,
            center=center,
            active_zone=resolved_active_zone,
            selected_seat_id=resolved_selected_seat_id,
            floors=floors,
            runtime=runtime_projection,
            metadata={
                "workspace_id": topology_dict.get("workspace_id"),
                "node_count": len(nodes),
                "edge_count": len(edges),
                "department_count": len(departments),
                "seat_count": len(seats),
                "floor_count": len(floors),
                "operator_count": runtime_projection.get("counts", {}).get("operators", 0),
                "workflow_count": runtime_projection.get("counts", {}).get("workflows", 0),
                "trigger_count": runtime_projection.get("counts", {}).get("triggers", 0),
                "run_count": runtime_projection.get("counts", {}).get("runs", 0),
                "pending_approval_count": runtime_projection.get("counts", {}).get(
                    "pending_approvals",
                    0,
                ),
            },
        )

    @staticmethod
    def _to_dict(topology: Any) -> Dict[str, Any]:
        if isinstance(topology, dict):
            return topology
        if hasattr(topology, "model_dump"):
            return topology.model_dump(mode="json")
        if hasattr(topology, "dict"):
            return topology.dict()
        raise TypeError(f"Unsupported topology type: {type(topology).__name__}")

    @staticmethod
    def _normalize_runtime_summary(runtime_summary: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(runtime_summary, dict):
            return {}

        if isinstance(runtime_summary.get("summary"), dict):
            runtime_summary = dict(runtime_summary["summary"])

        normalized = dict(runtime_summary)

        normalized.setdefault("operators", [])
        normalized.setdefault("workflows", [])
        normalized.setdefault("triggers", [])
        normalized.setdefault("runs", [])
        normalized.setdefault("approvals", [])
        normalized.setdefault("counts", {})

        return normalized

    def _group_nodes_by_type(self, nodes: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for node in nodes:
            grouped.setdefault(node.get("node_type", "unknown"), []).append(node)
        return grouped

    def _build_edge_index(
        self,
        edges: List[Dict[str, Any]],
    ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
        out: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
            "from": {},
            "to": {},
        }
        for edge in edges:
            from_node_id = edge.get("from_node_id")
            to_node_id = edge.get("to_node_id")
            if from_node_id:
                out["from"].setdefault(from_node_id, []).append(edge)
            if to_node_id:
                out["to"].setdefault(to_node_id, []).append(edge)
        return out

    @staticmethod
    def _pick_workspace_node(nodes_by_type: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        workspaces = nodes_by_type.get("workspace", [])
        if not workspaces:
            return {
                "ref_id": "workspace",
                "label": "Workspace",
                "metadata": {},
            }
        return workspaces[0]

    def _map_workspace(self, workspace_node: Dict[str, Any]) -> Dict[str, Any]:
        metadata = workspace_node.get("metadata", {}) or {}
        return {
            "id": workspace_node.get("ref_id") or workspace_node.get("workspace_id") or "workspace",
            "slug": workspace_node.get("ref_id") or workspace_node.get("workspace_id") or "workspace",
            "name": workspace_node.get("label") or "Workspace",
            "currency": metadata.get("currency", "EUR"),
            "timezone": metadata.get("timezone"),
            "industry": metadata.get("business_type"),
        }

    def _map_departments(
        self,
        *,
        topology: Dict[str, Any],
        nodes_by_type: Dict[str, List[Dict[str, Any]]],
        edge_index: Dict[str, Dict[str, List[Dict[str, Any]]]],
        node_by_id: Dict[str, Dict[str, Any]],
        runtime_summary: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        department_nodes = nodes_by_type.get("department", [])
        function_nodes = nodes_by_type.get("function", [])

        functions_by_department: Dict[str, List[Dict[str, Any]]] = {}
        department_owner_by_key: Dict[str, Optional[str]] = {}

        teams_by_department = self._teams_by_department(nodes_by_type)
        humans_by_department = self._agents_by_department(nodes_by_type, "human_agent")
        ais_by_department = self._agents_by_department(nodes_by_type, "ai_agent")

        runtime_index = self._build_runtime_index(runtime_summary)

        for function_node in function_nodes:
            metadata = function_node.get("metadata", {}) or {}
            department_key = metadata.get("department_key")
            if not department_key:
                continue

            functions_by_department.setdefault(department_key, []).append(
                {
                    "id": function_node.get("ref_id") or function_node.get("id"),
                    "departmentId": f"dept_{department_key}",
                    "key": metadata.get("function_key")
                    or metadata.get("key")
                    or function_node.get("ref_id")
                    or function_node.get("id"),
                    "name": function_node.get("label")
                    or metadata.get("function_key")
                    or metadata.get("key")
                    or "Function",
                    "description": function_node.get("description"),
                    "isEnabled": True,
                }
            )

        for department_key in functions_by_department.keys():
            owner = self._pick_department_owner(
                department_key=department_key,
                teams=teams_by_department.get(department_key, []),
                humans=humans_by_department.get(department_key, []),
                ai_agents=ais_by_department.get(department_key, []),
            )
            department_owner_by_key[department_key] = owner

        out: List[Dict[str, Any]] = []

        existing_keys: Set[str] = set()
        for department_node in department_nodes:
            metadata = department_node.get("metadata", {}) or {}
            department_key = metadata.get("department_key") or department_node.get("ref_id")
            if not department_key:
                continue
            existing_keys.add(department_key)

            runtime_for_department = self._build_department_runtime_payload(
                department_key=department_key,
                runtime_index=runtime_index,
            )

            out.append(
                {
                    "id": f"dept_{department_key}",
                    "key": department_key,
                    "name": department_node.get("label")
                    or DEPARTMENT_LABELS.get(department_key, department_key.title()),
                    "owner": department_owner_by_key.get(department_key),
                    "functions": sorted(
                        functions_by_department.get(department_key, []),
                        key=lambda item: item["name"].lower(),
                    ),
                    "operators": runtime_for_department["operators"],
                    "workflows": runtime_for_department["workflows"],
                    "triggers": runtime_for_department["triggers"],
                    "recentRuns": runtime_for_department["recent_runs"],
                    "pendingApprovals": runtime_for_department["pending_approvals"],
                    "automationState": runtime_for_department["automation_state"],
                }
            )

        for synthetic_key in ["ceo", "coo", "aion"]:
            if synthetic_key in existing_keys:
                continue

            runtime_for_department = self._build_department_runtime_payload(
                department_key=synthetic_key,
                runtime_index=runtime_index,
            )

            out.append(
                {
                    "id": f"dept_{synthetic_key}",
                    "key": synthetic_key,
                    "name": DEPARTMENT_LABELS[synthetic_key],
                    "owner": None,
                    "functions": [],
                    "operators": runtime_for_department["operators"],
                    "workflows": runtime_for_department["workflows"],
                    "triggers": runtime_for_department["triggers"],
                    "recentRuns": runtime_for_department["recent_runs"],
                    "pendingApprovals": runtime_for_department["pending_approvals"],
                    "automationState": runtime_for_department["automation_state"],
                }
            )

        out.sort(
            key=lambda item: DEPARTMENT_ORDER.index(item["key"])
            if item["key"] in DEPARTMENT_ORDER
            else 999
        )
        return out

    def _map_seats(
        self,
        *,
        topology: Dict[str, Any],
        departments: List[Dict[str, Any]],
        nodes_by_type: Dict[str, List[Dict[str, Any]]],
        edge_index: Dict[str, Dict[str, List[Dict[str, Any]]]],
        node_by_id: Dict[str, Dict[str, Any]],
        runtime_summary: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        teams_by_department = self._teams_by_department(nodes_by_type)
        humans_by_department = self._agents_by_department(nodes_by_type, "human_agent")
        ais_by_department = self._agents_by_department(nodes_by_type, "ai_agent")
        channels_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="channel",
        )
        services_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="service",
        )
        revenue_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="revenue_stream",
        )
        fulfillment_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="fulfillment_process",
        )
        payment_terms_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="payment_terms",
        )

        runtime_index = self._build_runtime_index(runtime_summary)

        functions_by_department: Dict[str, List[Dict[str, Any]]] = {
            dept["key"]: dept.get("functions", []) or []
            for dept in departments
        }

        seats: List[Dict[str, Any]] = []

        for department in departments:
            department_key = department["key"]
            seat_id = SEAT_ID_MAP.get(department_key, f"seat_{department_key}")

            department_functions = functions_by_department.get(department_key, [])
            human_agents = humans_by_department.get(department_key, [])
            ai_agents = ais_by_department.get(department_key, [])
            teams = teams_by_department.get(department_key, [])

            runtime_for_department = self._build_department_runtime_payload(
                department_key=department_key,
                runtime_index=runtime_index,
            )

            kpis = self._build_seat_kpis(
                department_key=department_key,
                department_functions=department_functions,
                human_agents=human_agents,
                ai_agents=ai_agents,
                teams=teams,
                channels_by_function=channels_by_function,
                services_by_function=services_by_function,
                revenue_by_function=revenue_by_function,
                fulfillment_by_function=fulfillment_by_function,
                payment_terms_by_function=payment_terms_by_function,
                runtime_for_department=runtime_for_department,
            )

            tasks = self._build_seat_tasks(
                department_key=department_key,
                department_functions=department_functions,
                human_agents=human_agents,
                ai_agents=ai_agents,
                runtime_for_department=runtime_for_department,
            )

            open_tasks = sum(1 for task in tasks if task["state"] in {"todo", "in_progress"})
            blocked_tasks = sum(1 for task in tasks if task["state"] == "blocked")
            due_today = sum(1 for task in tasks if task.get("dueAt"))

            seats.append(
                {
                    "id": seat_id,
                    "departmentKey": department_key,
                    "label": department["name"],
                    "shortLabel": department["name"][:3].upper(),
                    "owner": department.get("owner"),
                    "state": self._derive_seat_state(
                        department_key=department_key,
                        open_tasks=open_tasks,
                        blocked_tasks=blocked_tasks,
                        automation_state=runtime_for_department["automation_state"],
                    ),
                    "openTasks": open_tasks,
                    "blockedTasks": blocked_tasks,
                    "dueToday": due_today,
                    "goals": [],
                    "kpis": kpis,
                    "tasks": tasks,
                    "operators": runtime_for_department["operators"],
                    "workflows": runtime_for_department["workflows"],
                    "triggers": runtime_for_department["triggers"],
                    "recentRuns": runtime_for_department["recent_runs"],
                    "pendingApprovals": runtime_for_department["pending_approvals"],
                    "automationState": runtime_for_department["automation_state"],
                    "inspector": {
                        "seatId": seat_id,
                        "departmentKey": department_key,
                        "operators": runtime_for_department["operators"],
                        "workflows": runtime_for_department["workflows"],
                        "triggers": runtime_for_department["triggers"],
                        "recentRuns": runtime_for_department["recent_runs"],
                        "pendingApprovals": runtime_for_department["pending_approvals"],
                        "automationState": runtime_for_department["automation_state"],
                    },
                }
            )

        return seats

    def _build_seat_kpis(
        self,
        *,
        department_key: str,
        department_functions: List[Dict[str, Any]],
        human_agents: List[Dict[str, Any]],
        ai_agents: List[Dict[str, Any]],
        teams: List[Dict[str, Any]],
        channels_by_function: Dict[str, List[Dict[str, Any]]],
        services_by_function: Dict[str, List[Dict[str, Any]]],
        revenue_by_function: Dict[str, List[Dict[str, Any]]],
        fulfillment_by_function: Dict[str, List[Dict[str, Any]]],
        payment_terms_by_function: Dict[str, List[Dict[str, Any]]],
        runtime_for_department: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        function_count = len(department_functions)
        human_count = len(human_agents)
        ai_count = len(ai_agents)
        team_count = len(teams)

        channel_refs: Set[str] = set()
        service_refs: Set[str] = set()
        revenue_refs: Set[str] = set()
        fulfillment_refs: Set[str] = set()
        payment_refs: Set[str] = set()

        for fn in department_functions:
            function_id = fn["id"]
            channel_refs.update(item["ref_id"] for item in channels_by_function.get(function_id, []))
            service_refs.update(item["ref_id"] for item in services_by_function.get(function_id, []))
            revenue_refs.update(item["ref_id"] for item in revenue_by_function.get(function_id, []))
            fulfillment_refs.update(
                item["ref_id"] for item in fulfillment_by_function.get(function_id, [])
            )
            payment_refs.update(
                item["ref_id"] for item in payment_terms_by_function.get(function_id, [])
            )

        seat_id = SEAT_ID_MAP.get(department_key, f"seat_{department_key}")

        kpis: List[Dict[str, Any]] = [
            {
                "id": f"kpi::{department_key}::functions",
                "seatId": seat_id,
                "label": "Functions",
                "value": function_count,
            },
            {
                "id": f"kpi::{department_key}::teams",
                "seatId": seat_id,
                "label": "Teams",
                "value": team_count,
            },
            {
                "id": f"kpi::{department_key}::humans",
                "seatId": seat_id,
                "label": "Humans",
                "value": human_count,
            },
            {
                "id": f"kpi::{department_key}::ai_agents",
                "seatId": seat_id,
                "label": "AI Agents",
                "value": ai_count,
            },
            {
                "id": f"kpi::{department_key}::operators",
                "seatId": seat_id,
                "label": "Operators",
                "value": len(runtime_for_department.get("operators") or []),
            },
            {
                "id": f"kpi::{department_key}::workflows",
                "seatId": seat_id,
                "label": "Workflows",
                "value": len(runtime_for_department.get("workflows") or []),
            },
            {
                "id": f"kpi::{department_key}::triggers",
                "seatId": seat_id,
                "label": "Triggers",
                "value": len(runtime_for_department.get("triggers") or []),
            },
            {
                "id": f"kpi::{department_key}::runs_waiting_approval",
                "seatId": seat_id,
                "label": "Waiting Approval",
                "value": runtime_for_department.get("automation_state", {}).get(
                    "waitingApprovalCount",
                    0,
                ),
            },
        ]

        if channel_refs:
            kpis.append(
                {
                    "id": f"kpi::{department_key}::channels",
                    "seatId": seat_id,
                    "label": "Channels",
                    "value": len(channel_refs),
                }
            )

        if service_refs:
            kpis.append(
                {
                    "id": f"kpi::{department_key}::services",
                    "seatId": seat_id,
                    "label": "Services",
                    "value": len(service_refs),
                }
            )

        if revenue_refs:
            kpis.append(
                {
                    "id": f"kpi::{department_key}::revenue_streams",
                    "seatId": seat_id,
                    "label": "Revenue Streams",
                    "value": len(revenue_refs),
                }
            )

        if fulfillment_refs:
            kpis.append(
                {
                    "id": f"kpi::{department_key}::fulfillment",
                    "seatId": seat_id,
                    "label": "Fulfillment Paths",
                    "value": len(fulfillment_refs),
                }
            )

        if payment_refs:
            kpis.append(
                {
                    "id": f"kpi::{department_key}::payment_terms",
                    "seatId": seat_id,
                    "label": "Payment Terms",
                    "value": len(payment_refs),
                }
            )

        return kpis

    def _build_seat_tasks(
        self,
        *,
        department_key: str,
        department_functions: List[Dict[str, Any]],
        human_agents: List[Dict[str, Any]],
        ai_agents: List[Dict[str, Any]],
        runtime_for_department: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = []

        for fn in department_functions[:4]:
            tasks.append(
                {
                    "id": f"task::{department_key}::{fn['id']}",
                    "seatId": SEAT_ID_MAP.get(department_key, f"seat_{department_key}"),
                    "title": f"Run {fn['name']}",
                    "state": "todo",
                    "priority": "medium",
                }
            )

        if department_key == "operations" and department_functions:
            tasks.append(
                {
                    "id": f"task::{department_key}::review_delivery",
                    "seatId": SEAT_ID_MAP.get(department_key, f"seat_{department_key}"),
                    "title": "Review delivery queue",
                    "state": "in_progress",
                    "priority": "high",
                }
            )

        if department_key == "finance" and department_functions:
            tasks.append(
                {
                    "id": f"task::{department_key}::collections",
                    "seatId": SEAT_ID_MAP.get(department_key, f"seat_{department_key}"),
                    "title": "Check billing and collections",
                    "state": "todo",
                    "priority": "high",
                }
            )

        if department_key == "support" and ai_agents:
            tasks.append(
                {
                    "id": f"task::{department_key}::triage",
                    "seatId": SEAT_ID_MAP.get(department_key, f"seat_{department_key}"),
                    "title": "Triage business support requests",
                    "state": "todo",
                    "priority": "medium",
                }
            )

        if department_key == "sales" and human_agents:
            tasks.append(
                {
                    "id": f"task::{department_key}::followup",
                    "seatId": SEAT_ID_MAP.get(department_key, f"seat_{department_key}"),
                    "title": "Follow up live opportunities",
                    "state": "in_progress",
                    "priority": "high",
                }
            )

        automation_state = runtime_for_department.get("automation_state", {})
        if automation_state.get("waitingApprovalCount", 0) > 0:
            tasks.append(
                {
                    "id": f"task::{department_key}::approvals",
                    "seatId": SEAT_ID_MAP.get(department_key, f"seat_{department_key}"),
                    "title": "Review waiting approvals",
                    "state": "blocked",
                    "priority": "high",
                }
            )

        if automation_state.get("failedCount", 0) > 0:
            tasks.append(
                {
                    "id": f"task::{department_key}::failed_runs",
                    "seatId": SEAT_ID_MAP.get(department_key, f"seat_{department_key}"),
                    "title": "Inspect failed automation runs",
                    "state": "blocked",
                    "priority": "high",
                }
            )

        if runtime_for_department.get("workflows"):
            tasks.append(
                {
                    "id": f"task::{department_key}::launch_workflow",
                    "seatId": SEAT_ID_MAP.get(department_key, f"seat_{department_key}"),
                    "title": "Launch workflow",
                    "state": "todo",
                    "priority": "medium",
                    "action": "launch_workflow",
                }
            )

        return tasks[:8]

    def _build_pulse(
        self,
        *,
        topology: Dict[str, Any],
        nodes_by_type: Dict[str, List[Dict[str, Any]]],
        edge_index: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ) -> Dict[str, Any]:
        revenue_count = len(nodes_by_type.get("revenue_stream", []))
        cost_count = len(nodes_by_type.get("cost_item", []))
        service_count = len(nodes_by_type.get("service", []))
        channel_count = len(nodes_by_type.get("channel", []))
        team_count = len(nodes_by_type.get("team", []))
        function_count = len(nodes_by_type.get("function", []))

        runway_days = max(30, 30 + (revenue_count * 20) - (cost_count * 5))
        gross_margin_pct = max(15, min(85, 40 + (revenue_count * 4) - cost_count))

        return {
            "cash": {
                "onHand": revenue_count * 2500,
                "incoming30d": revenue_count * 1800,
                "outgoing30d": max(500, cost_count * 700),
                "runwayDays": runway_days,
            },
            "sales": {
                "revenue": revenue_count * 3000,
                "orders": max(1, service_count * 8),
                "conversionRate": round(min(0.95, 0.12 + (channel_count * 0.03)), 2),
                "sellThroughRate": round(min(0.98, 0.25 + (service_count * 0.05)), 2),
            },
            "stock": {
                "units": 0,
                "value": 0,
                "daysCover": 0,
                "slowStockValue": 0,
                "inTransitValue": 0,
            },
            "ops": {
                "backlog": max(0, function_count * 3),
                "fulfilmentRate": round(min(0.99, 0.7 + (team_count * 0.04)), 2),
                "blockedJobs": max(0, cost_count - 1),
                "avgTurnaroundDays": max(1, 8 - min(5, team_count)),
            },
            "finance": {
                "creditorDays": 30,
                "debtorDays": 14 if revenue_count > 1 else 7,
                "grossMarginPct": gross_margin_pct,
            },
            "risk": {
                "cash": "low" if revenue_count >= cost_count else "medium",
                "stock": "low",
                "demand": "low" if channel_count >= 3 else "medium",
                "operations": "low" if team_count >= 2 else "medium",
            },
        }

    def _build_center_metrics(
        self,
        *,
        pulse: Dict[str, Any],
        topology: Dict[str, Any],
    ) -> Dict[str, Any]:
        revenue = pulse["sales"]["revenue"]
        cash = pulse["cash"]["onHand"]
        orders = pulse["sales"]["orders"]
        margin = pulse["finance"]["grossMarginPct"]
        risk = pulse["risk"]

        health = "Healthy"
        if "high" in risk.values():
            health = "High Risk"
        elif "medium" in risk.values():
            health = "Watch"

        return {
            "revenue": f"€{revenue:,.0f}",
            "cash": f"€{cash:,.0f}",
            "pipeline": str(orders),
            "profit": f"{margin}%",
            "health": health,
        }

    def _build_floors(
        self,
        *,
        topology: Dict[str, Any],
        departments: List[Dict[str, Any]],
        seats: List[Dict[str, Any]],
        nodes_by_type: Dict[str, List[Dict[str, Any]]],
        edge_index: Dict[str, Dict[str, List[Dict[str, Any]]]],
        node_by_id: Dict[str, Dict[str, Any]],
        runtime_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        floors: Dict[str, Any] = {}

        floor_departments = ["sales", "finance", "operations", "support", "marketing", "hr"]

        teams_by_department = self._teams_by_department(nodes_by_type)
        humans_by_department = self._agents_by_department(nodes_by_type, "human_agent")
        ais_by_department = self._agents_by_department(nodes_by_type, "ai_agent")
        functions_by_department = self._functions_by_department(nodes_by_type)

        channels_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="channel",
        )
        services_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="service",
        )
        revenue_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="revenue_stream",
        )
        fulfillment_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="fulfillment_process",
        )
        payment_terms_by_function = self._linked_targets_by_function(
            nodes_by_type,
            edge_index,
            node_by_id,
            target_type="payment_terms",
        )

        runtime_index = self._build_runtime_index(runtime_summary)
        seat_by_department = {seat["departmentKey"]: seat for seat in seats}

        for department_key in floor_departments:
            department_functions = functions_by_department.get(department_key, [])
            teams = teams_by_department.get(department_key, [])
            humans = humans_by_department.get(department_key, [])
            ai_agents = ais_by_department.get(department_key, [])
            seat = seat_by_department.get(department_key)
            runtime_for_department = self._build_department_runtime_payload(
                department_key=department_key,
                runtime_index=runtime_index,
            )

            if (
                not department_functions
                and not teams
                and not humans
                and not ai_agents
                and not runtime_for_department["operators"]
                and not runtime_for_department["workflows"]
            ):
                continue

            stages = self._build_floor_stages(
                department_key=department_key,
                seat=seat,
                department_functions=department_functions,
                channels_by_function=channels_by_function,
                services_by_function=services_by_function,
                revenue_by_function=revenue_by_function,
                fulfillment_by_function=fulfillment_by_function,
                payment_terms_by_function=payment_terms_by_function,
                runtime_for_department=runtime_for_department,
            )

            agents = self._build_floor_agents(
                department_key=department_key,
                teams=teams,
                humans=humans,
                ai_agents=ai_agents,
                seat=seat,
                runtime_for_department=runtime_for_department,
            )

            flows = self._build_floor_flows(
                department_key=department_key,
                stages=stages,
            )

            floors[department_key] = {
                "departmentKey": department_key,
                "agents": agents,
                "stages": stages,
                "flows": flows,
                "operators": runtime_for_department["operators"],
                "workflows": runtime_for_department["workflows"],
                "triggers": runtime_for_department["triggers"],
                "recentRuns": runtime_for_department["recent_runs"],
                "pendingApprovals": runtime_for_department["pending_approvals"],
                "automationState": runtime_for_department["automation_state"],
            }

        return floors

    def _build_floor_stages(
        self,
        *,
        department_key: str,
        seat: Optional[Dict[str, Any]],
        department_functions: List[Dict[str, Any]],
        channels_by_function: Dict[str, List[Dict[str, Any]]],
        services_by_function: Dict[str, List[Dict[str, Any]]],
        revenue_by_function: Dict[str, List[Dict[str, Any]]],
        fulfillment_by_function: Dict[str, List[Dict[str, Any]]],
        payment_terms_by_function: Dict[str, List[Dict[str, Any]]],
        runtime_for_department: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        stage_defs = self._stage_definitions_for_department(department_key)

        function_count = len(department_functions)
        open_tasks = (seat or {}).get("openTasks", 0)

        total_channels: Set[str] = set()
        total_services: Set[str] = set()
        total_revenue: Set[str] = set()
        total_fulfillment: Set[str] = set()
        total_payment_terms: Set[str] = set()

        for fn in department_functions:
            function_id = fn["id"]
            total_channels.update(item["ref_id"] for item in channels_by_function.get(function_id, []))
            total_services.update(item["ref_id"] for item in services_by_function.get(function_id, []))
            total_revenue.update(item["ref_id"] for item in revenue_by_function.get(function_id, []))
            total_fulfillment.update(
                item["ref_id"] for item in fulfillment_by_function.get(function_id, [])
            )
            total_payment_terms.update(
                item["ref_id"] for item in payment_terms_by_function.get(function_id, [])
            )

        density = max(
            1,
            function_count
            + len(total_channels)
            + len(total_services)
            + len(total_revenue)
            + len(total_fulfillment)
            + len(total_payment_terms)
            + len(runtime_for_department.get("operators") or [])
            + len(runtime_for_department.get("workflows") or []),
        )

        stages: List[Dict[str, Any]] = []
        automation_state = runtime_for_department.get("automation_state", {})

        for idx, label in enumerate(stage_defs):
            base_count = max(1, density - idx)
            if idx == len(stage_defs) - 1:
                base_count = max(1, len(total_services) or len(total_revenue) or function_count)
            if department_key == "operations":
                base_count += open_tasks
            if department_key == "support" and idx == 0:
                base_count += open_tasks
            if department_key == "finance" and idx == len(stage_defs) - 1:
                base_count += len(total_payment_terms)
            if department_key == "marketing" and idx == 0:
                base_count += automation_state.get("queuedCount", 0)
                base_count += automation_state.get("runningCount", 0)

            stage_state = "healthy"
            if automation_state.get("failedCount", 0) > 0 and idx <= 1:
                stage_state = "warning"
            elif automation_state.get("waitingApprovalCount", 0) > 0 and idx <= 2:
                stage_state = "warning"
            elif open_tasks >= 5 and idx <= 1:
                stage_state = "warning"
            elif open_tasks >= 3 and idx == 0:
                stage_state = "warning"

            stages.append(
                {
                    "id": f"{department_key}_stage_{idx + 1}",
                    "departmentKey": department_key,
                    "entityType": "stage",
                    "label": label,
                    "count": base_count,
                    "value": base_count * 100,
                    "state": stage_state,
                }
            )

        return stages

    def _build_floor_agents(
        self,
        *,
        department_key: str,
        teams: List[Dict[str, Any]],
        humans: List[Dict[str, Any]],
        ai_agents: List[Dict[str, Any]],
        seat: Optional[Dict[str, Any]],
        runtime_for_department: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        agents: List[Dict[str, Any]] = []

        open_tasks = (seat or {}).get("openTasks", 0)
        team_count = max(1, len(teams) or len(humans) or len(ai_agents) or 1)

        for idx, human in enumerate(humans):
            agents.append(
                {
                    "id": f"{department_key}_human_{idx + 1}",
                    "departmentKey": department_key,
                    "entityType": "agent",
                    "label": human.get("label")
                    or human.get("ref_id")
                    or f"{department_key.title()} Human",
                    "role": human.get("description") or "Human Operator",
                    "state": "healthy" if open_tasks < 5 else "warning",
                    "workload": min(100, 45 + (open_tasks * 8)),
                    "displayTag": "Human",
                    "throughput": max(1, 8 - idx),
                    "assignedCount": open_tasks,
                }
            )

        for idx, agent in enumerate(ai_agents):
            agents.append(
                {
                    "id": f"{department_key}_ai_{idx + 1}",
                    "departmentKey": department_key,
                    "entityType": "agent",
                    "label": agent.get("label")
                    or agent.get("ref_id")
                    or f"{department_key.title()} AI",
                    "role": agent.get("description") or "AI Agent",
                    "state": "healthy",
                    "workload": min(100, 35 + (open_tasks * 5)),
                    "displayTag": "AI",
                    "throughput": max(1, 12 - idx),
                    "assignedCount": max(1, open_tasks // team_count if open_tasks else 1),
                }
            )

        runtime_operators = runtime_for_department.get("operators") or []
        runtime_state = runtime_for_department.get("automation_state", {})

        for idx, operator in enumerate(runtime_operators[:4]):
            operator_id = operator.get("id") or operator.get("operator_id") or f"{department_key}_operator_{idx+1}"
            agents.append(
                {
                    "id": operator_id,
                    "departmentKey": department_key,
                    "entityType": "agent",
                    "label": operator.get("name") or operator.get("label") or "Operator",
                    "role": operator.get("description") or "Managed Operator",
                    "state": self._runtime_status_to_agent_state(
                        runtime_state.get("latestStatus"),
                    ),
                    "displayTag": "Operator",
                    "workload": min(
                        100,
                        25
                        + (runtime_state.get("queuedCount", 0) * 8)
                        + (runtime_state.get("runningCount", 0) * 15)
                        + (runtime_state.get("waitingApprovalCount", 0) * 12),
                    ),
                    "throughput": max(1, 10 - idx),
                    "assignedCount": runtime_state.get("totalRuns", 0),
                    "runtimeStatus": runtime_state.get("latestStatus"),
                    "queuedCount": runtime_state.get("queuedCount", 0),
                    "runningCount": runtime_state.get("runningCount", 0),
                    "waitingApprovalCount": runtime_state.get("waitingApprovalCount", 0),
                    "failedCount": runtime_state.get("failedCount", 0),
                    "completedCount": runtime_state.get("completedCount", 0),
                    "seatId": SEAT_ID_MAP.get(department_key, f"seat_{department_key}"),
                }
            )

        if not agents:
            for idx, team in enumerate(teams[:2]):
                agents.append(
                    {
                        "id": f"{department_key}_team_{idx + 1}",
                        "departmentKey": department_key,
                        "entityType": "agent",
                        "label": team.get("label")
                        or team.get("ref_id")
                        or f"{department_key.title()} Team",
                        "role": "Team",
                        "state": "healthy",
                        "workload": 40 + (open_tasks * 6),
                        "displayTag": "Team",
                        "throughput": max(1, 10 - idx),
                        "assignedCount": open_tasks,
                    }
                )

        return agents[:6]

    def _build_floor_flows(
        self,
        *,
        department_key: str,
        stages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        flows: List[Dict[str, Any]] = []

        for idx in range(len(stages) - 1):
            from_stage = stages[idx]
            to_stage = stages[idx + 1]
            count = max(1, min(from_stage.get("count", 1), to_stage.get("count", 1)))

            state = "healthy"
            if from_stage.get("state") == "warning" or to_stage.get("state") == "warning":
                state = "warning"

            flows.append(
                {
                    "id": f"{department_key}_flow_{idx + 1}",
                    "departmentKey": department_key,
                    "label": f"{from_stage['label']} → {to_stage['label']}",
                    "fromStageId": from_stage["id"],
                    "toStageId": to_stage["id"],
                    "count": count,
                    "value": count * 100,
                    "state": state,
                }
            )

        return flows

    def _stage_definitions_for_department(self, department_key: str) -> List[str]:
        stage_map = {
            "sales": ["Lead Intake", "Qualification", "Proposal", "Conversion"],
            "finance": ["Invoice Queue", "Payments", "Reconciliation", "Collections"],
            "operations": ["Queued Work", "In Progress", "QA / Review", "Completed"],
            "support": ["Inbox", "Triage", "Resolution", "Closed"],
            "marketing": ["Campaign Prep", "Publishing", "Response", "Attribution"],
            "hr": ["Hiring Queue", "Screening", "Onboarding", "Retention"],
        }
        return stage_map.get(department_key, ["Stage 1", "Stage 2", "Stage 3", "Stage 4"])

    def _functions_by_department(
        self,
        nodes_by_type: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {}
        for node in nodes_by_type.get("function", []):
            department_key = (node.get("metadata", {}) or {}).get("department_key")
            if department_key:
                out.setdefault(department_key, []).append(node)
        return out

    def _teams_by_department(
        self,
        nodes_by_type: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {}
        for node in nodes_by_type.get("team", []):
            department_key = (node.get("metadata", {}) or {}).get("department_key")
            if department_key:
                out.setdefault(department_key, []).append(node)
        return out

    def _agents_by_department(
        self,
        nodes_by_type: Dict[str, List[Dict[str, Any]]],
        node_type: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {}
        for node in nodes_by_type.get(node_type, []):
            department_key = (node.get("metadata", {}) or {}).get("department_key")
            if department_key:
                out.setdefault(department_key, []).append(node)
        return out

    def _linked_targets_by_function(
        self,
        nodes_by_type: Dict[str, List[Dict[str, Any]]],
        edge_index: Dict[str, Dict[str, List[Dict[str, Any]]]],
        node_by_id: Dict[str, Dict[str, Any]],
        *,
        target_type: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {}

        for fn in nodes_by_type.get("function", []):
            fn_ref_id = fn.get("ref_id") or fn.get("id")
            fn_node_id = fn.get("id")
            if not fn_node_id or not fn_ref_id:
                continue

            targets: List[Dict[str, Any]] = []
            for edge in edge_index["from"].get(fn_node_id, []):
                target = node_by_id.get(edge.get("to_node_id", ""))
                if not target:
                    continue
                if target.get("node_type") == target_type:
                    targets.append(target)

            out[fn_ref_id] = targets

        return out

    def _pick_department_owner(
        self,
        *,
        department_key: str,
        teams: List[Dict[str, Any]],
        humans: List[Dict[str, Any]],
        ai_agents: List[Dict[str, Any]],
    ) -> Optional[str]:
        if humans:
            return humans[0].get("label")
        if teams:
            return teams[0].get("label")
        if ai_agents:
            return ai_agents[0].get("label")
        return None

    def _derive_seat_state(
        self,
        *,
        department_key: str,
        open_tasks: int,
        blocked_tasks: int,
        automation_state: Optional[Dict[str, Any]] = None,
    ) -> str:
        automation_state = automation_state or {}

        if blocked_tasks > 0:
            return "warning"
        if automation_state.get("failedCount", 0) > 0:
            return "warning"
        if automation_state.get("waitingApprovalCount", 0) > 0:
            return "warning"
        if open_tasks >= 5:
            return "warning"
        if department_key in {"ceo", "coo", "aion"}:
            return "healthy"
        return "healthy"

    def _default_selected_seat_id(self, seats: List[Dict[str, Any]]) -> Optional[str]:
        for preferred in ["seat_coo", "seat_marketing", "seat_sales", "seat_ops", "seat_finance"]:
            if any(seat["id"] == preferred for seat in seats):
                return preferred
        return seats[0]["id"] if seats else None

    def _build_runtime_index(self, runtime_summary: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        operators = self._normalize_operator_items(runtime_summary.get("operators") or [])
        workflows = self._normalize_workflow_items(runtime_summary.get("workflows") or [])
        triggers = self._normalize_trigger_items(runtime_summary.get("triggers") or [])
        runs = self._normalize_run_items(runtime_summary)
        approvals = self._normalize_approval_items(runtime_summary)

        return {
            "operators_by_department": self._group_by_department(operators),
            "workflows_by_department": self._group_by_department(workflows),
            "triggers_by_department": self._group_by_department(triggers),
            "runs_by_department": self._group_by_department(runs),
            "approvals_by_department": self._group_by_department(approvals),
        }

    def _build_department_runtime_payload(
        self,
        *,
        department_key: str,
        runtime_index: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        operators = list(runtime_index["operators_by_department"].get(department_key, []))
        workflows = list(runtime_index["workflows_by_department"].get(department_key, []))
        triggers = list(runtime_index["triggers_by_department"].get(department_key, []))
        recent_runs = sorted(
            list(runtime_index["runs_by_department"].get(department_key, [])),
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )[:10]
        approvals = sorted(
            list(runtime_index["approvals_by_department"].get(department_key, [])),
            key=lambda item: item.get("requested_at") or "",
            reverse=True,
        )
        pending_approvals = [item for item in approvals if item.get("status") == "pending"][:10]

        queued_count = sum(1 for item in recent_runs if item.get("status") == "queued")
        running_count = sum(1 for item in recent_runs if item.get("status") == "running")
        waiting_approval_count = sum(
            1 for item in recent_runs if item.get("status") == "waiting_approval"
        )
        failed_count = sum(1 for item in recent_runs if item.get("status") == "failed")
        completed_count = sum(1 for item in recent_runs if item.get("status") == "completed")
        blocked_count = sum(
            1
            for item in recent_runs
            if item.get("status") in {"blocked", "waiting_approval", "failed"}
        )
        latest_status = recent_runs[0].get("status") if recent_runs else None

        return {
            "operators": operators,
            "workflows": workflows,
            "triggers": triggers,
            "recent_runs": recent_runs,
            "pending_approvals": pending_approvals,
            "automation_state": {
                "status": self._derive_automation_status(
                    queued_count=queued_count,
                    running_count=running_count,
                    waiting_approval_count=waiting_approval_count,
                    failed_count=failed_count,
                    completed_count=completed_count,
                ),
                "queuedCount": queued_count,
                "runningCount": running_count,
                "waitingApprovalCount": waiting_approval_count,
                "failedCount": failed_count,
                "completedCount": completed_count,
                "blockedCount": blocked_count,
                "totalRuns": len(recent_runs),
                "latestStatus": latest_status,
                "latestUpdatedAt": recent_runs[0].get("updated_at") if recent_runs else None,
            },
        }

    def _build_runtime_projection(
        self,
        *,
        departments: List[Dict[str, Any]],
        seats: List[Dict[str, Any]],
        runtime_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        runs = self._normalize_run_items(runtime_summary)
        approvals = self._normalize_approval_items(runtime_summary)
        operators = self._normalize_operator_items(runtime_summary.get("operators") or [])
        workflows = self._normalize_workflow_items(runtime_summary.get("workflows") or [])
        triggers = self._normalize_trigger_items(runtime_summary.get("triggers") or [])

        return {
            "operators": operators,
            "workflows": workflows,
            "triggers": triggers,
            "runs": runs[:20],
            "approvals": approvals[:20],
            "counts": {
                "operators": len(operators),
                "workflows": len(workflows),
                "triggers": len(triggers),
                "runs": len(runs),
                "pending_approvals": sum(
                    1 for item in approvals if item.get("status") == "pending"
                ),
            },
            "departments": [
                {
                    "departmentKey": dept["key"],
                    "operatorCount": len(dept.get("operators") or []),
                    "workflowCount": len(dept.get("workflows") or []),
                    "triggerCount": len(dept.get("triggers") or []),
                    "waitingApprovalCount": len(dept.get("pendingApprovals") or []),
                    "automationState": dept.get("automationState") or {},
                }
                for dept in departments
            ],
            "seats": [
                {
                    "seatId": seat["id"],
                    "departmentKey": seat.get("departmentKey"),
                    "automationState": seat.get("automationState") or {},
                }
                for seat in seats
            ],
        }

    @staticmethod
    def _group_by_department(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {}
        for item in items:
            department_key = (
                item.get("department_key")
                or item.get("departmentKey")
                or item.get("department")
                or item.get("metadata", {}).get("department_key")
            )
            if department_key:
                out.setdefault(str(department_key), []).append(item)
        return out

    def _normalize_operator_items(self, items: List[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for raw in items:
            item = self._to_plain_dict(raw)
            if not item:
                continue
            operator_id = item.get("id") or item.get("agent_id") or item.get("operator_id")
            normalized.append(
                {
                    "id": operator_id,
                    "operator_id": operator_id,
                    "name": item.get("name") or item.get("label") or operator_id or "Operator",
                    "department_key": item.get("department_key")
                    or item.get("departmentKey")
                    or item.get("metadata", {}).get("department_key"),
                    "description": item.get("description"),
                    "agent_type": item.get("agent_type") or item.get("type") or "operator",
                    "workflow_ids": list(item.get("workflow_ids") or []),
                    "trigger_ids": list(item.get("trigger_ids") or []),
                    "active": bool(item.get("active", True)),
                    "metadata": dict(item.get("metadata") or {}),
                }
            )
        return normalized

    def _normalize_workflow_items(self, items: List[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for raw in items:
            item = self._to_plain_dict(raw)
            if not item:
                continue
            workflow_id = item.get("workflow_id") or item.get("id")
            normalized.append(
                {
                    "id": workflow_id,
                    "workflow_id": workflow_id,
                    "name": item.get("name") or workflow_id or "Workflow",
                    "department_key": item.get("department_key")
                    or item.get("departmentKey")
                    or item.get("metadata", {}).get("department_key"),
                    "description": item.get("description"),
                    "execution_mode": item.get("execution_mode"),
                    "active": bool(item.get("active", True)),
                    "tags": list(item.get("tags") or []),
                }
            )
        return normalized

    def _normalize_trigger_items(self, items: List[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for raw in items:
            item = self._to_plain_dict(raw)
            if not item:
                continue
            trigger_id = item.get("trigger_id") or item.get("id")
            config = dict(item.get("config") or {})
            normalized.append(
                {
                    "id": trigger_id,
                    "trigger_id": trigger_id,
                    "name": item.get("name") or trigger_id or "Trigger",
                    "trigger_type": item.get("trigger_type") or item.get("type"),
                    "workflow_id": item.get("workflow_id") or item.get("workflow_definition_id"),
                    "agent_id": item.get("agent_id"),
                    "department_key": item.get("department_key")
                    or config.get("department_key")
                    or item.get("metadata", {}).get("department_key"),
                    "active": bool(item.get("active", True)),
                    "config": config,
                }
            )
        return normalized

    def _normalize_run_items(self, runtime_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        source_items = runtime_summary.get("runs") or []
        if not source_items and isinstance(runtime_summary.get("marketing_summary"), dict):
            source_items = runtime_summary["marketing_summary"].get("runs") or []

        normalized: List[Dict[str, Any]] = []
        for raw in source_items:
            item = self._to_plain_dict(raw)
            if not item:
                continue

            run_id = item.get("id") or item.get("run_id")
            operator_id = item.get("operator_id") or item.get("agent_id")
            payload = dict(item.get("payload") or {})
            context = dict(item.get("context") or {})
            output = dict(item.get("output") or {})
            step_runs = list(item.get("step_runs") or [])

            normalized.append(
                {
                    "id": run_id,
                    "run_id": run_id,
                    "workflow_id": item.get("workflow_id"),
                    "workflow_name": item.get("workflow_name") or item.get("name"),
                    "operator_id": operator_id,
                    "agent_id": operator_id,
                    "department_key": item.get("department_key")
                    or payload.get("department_key")
                    or context.get("department_key"),
                    "status": item.get("status") or "queued",
                    "trigger_kind": item.get("trigger_kind"),
                    "execution_mode": item.get("execution_mode"),
                    "approval_request_id": item.get("approval_request_id"),
                    "failure_reason": item.get("failure_reason"),
                    "current_step_index": item.get("current_step_index"),
                    "payload": payload,
                    "context": context,
                    "output": output,
                    "step_runs": step_runs,
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at") or item.get("created_at"),
                    "completed_at": item.get("completed_at"),
                }
            )

        normalized.sort(
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )
        return normalized

    def _normalize_approval_items(self, runtime_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        source_items = runtime_summary.get("approvals") or []
        if not source_items and isinstance(runtime_summary.get("marketing_summary"), dict):
            marketing_summary = runtime_summary["marketing_summary"]
            source_items = (
                list(marketing_summary.get("pending_approvals") or [])
                + list(marketing_summary.get("resolved_approvals") or [])
            )

        normalized: List[Dict[str, Any]] = []
        for raw in source_items:
            item = self._to_plain_dict(raw)
            if not item:
                continue

            normalized.append(
                {
                    "id": item.get("id"),
                    "workflow_run_id": item.get("workflow_run_id"),
                    "operator_id": item.get("operator_id") or item.get("agent_id"),
                    "department_key": item.get("department_key"),
                    "title": item.get("title") or item.get("name") or "Approval",
                    "summary": item.get("summary"),
                    "status": item.get("status") or "pending",
                    "payload": dict(item.get("payload") or {}),
                    "requested_at": item.get("requested_at"),
                    "resolved_at": item.get("resolved_at"),
                    "resolved_by": item.get("resolved_by"),
                    "resolution_note": item.get("resolution_note"),
                }
            )

        normalized.sort(key=lambda item: item.get("requested_at") or "", reverse=True)
        return normalized

    @staticmethod
    def _to_plain_dict(value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return dict(value)
        if hasattr(value, "model_dump"):
            dumped = value.model_dump(mode="json")
            if isinstance(dumped, dict):
                return dumped
        if hasattr(value, "dict"):
            dumped = value.dict()
            if isinstance(dumped, dict):
                return dumped
        if hasattr(value, "to_dict"):
            dumped = value.to_dict()
            if isinstance(dumped, dict):
                return dumped
        return {}

    @staticmethod
    def _derive_automation_status(
        *,
        queued_count: int,
        running_count: int,
        waiting_approval_count: int,
        failed_count: int,
        completed_count: int,
    ) -> str:
        if failed_count > 0:
            return "failed"
        if waiting_approval_count > 0:
            return "waiting_approval"
        if running_count > 0:
            return "running"
        if queued_count > 0:
            return "queued"
        if completed_count > 0:
            return "completed"
        return "idle"

    @staticmethod
    def _runtime_status_to_agent_state(status: Optional[str]) -> str:
        if status in {"failed", "blocked", "waiting_approval"}:
            return "warning"
        return "healthy"