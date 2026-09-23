from __future__ import annotations

from typing import Iterable, List, Optional
import re

from backend.modules.aion_business.contracts.ai_agents import AIAgentSpec
from backend.modules.aion_business.contracts.business_identity import BusinessIdentity
from backend.modules.aion_business.contracts.channels import BusinessChannel
from backend.modules.aion_business.contracts.cost_structure import CostLineItem
from backend.modules.aion_business.contracts.fulfillment import FulfillmentProcess
from backend.modules.aion_business.contracts.functions import BusinessFunctionSpec
from backend.modules.aion_business.contracts.human_agents import HumanAgentSpec
from backend.modules.aion_business.contracts.payment_terms import PaymentTerms
from backend.modules.aion_business.contracts.revenue_streams import RevenueStream
from backend.modules.aion_business.contracts.services import ServiceOffer
from backend.modules.aion_business.contracts.teams import TeamSpec
from backend.modules.aion_business.contracts.business_identity import BusinessIdentity
from backend.modules.aion_business.contracts.channels import BusinessChannel
from backend.modules.aion_business.contracts.cost_structure import CostLineItem
from backend.modules.aion_business.contracts.fulfillment import FulfillmentProcess
from backend.modules.aion_business.contracts.functions import BusinessFunctionSpec
from backend.modules.aion_business.contracts.human_agents import HumanAgentSpec
from backend.modules.aion_business.contracts.payment_terms import PaymentTerms
from backend.modules.aion_business.contracts.revenue_streams import RevenueStream
from backend.modules.aion_business.contracts.services import ServiceOffer
from backend.modules.aion_business.contracts.teams import TeamSpec
from backend.modules.aion_business.contracts.ai_agents import AIAgentSpec
from backend.modules.aion_business.contracts.business_containers import (
    BusinessStructureContainer,
)
from backend.modules.aion_business.contracts.topology import (
    BusinessTopology,
    TopologyEdge,
    TopologyNode,
)
from backend.modules.aion_business.runtime.business_template_registry import (
    BusinessTemplateRegistry,
)


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "item"


class ServiceBusinessTopologyGenerator:
    """
    First-pass topology generator for one real service business.

    v1 goal:
    - convert structured business schema into a graph
    - seed boardroom / ops-flow ready relationships
    - stay deterministic and easy to inspect
    """

    def __init__(
        self,
        *,
        template_registry: Optional[BusinessTemplateRegistry] = None,
    ):
        self.template_registry = template_registry or BusinessTemplateRegistry()

    def generate(
        self,
        *,
        identity: BusinessIdentity,
        channels: Optional[Iterable[BusinessChannel]] = None,
        services: Optional[Iterable[ServiceOffer]] = None,
        revenue_streams: Optional[Iterable[RevenueStream]] = None,
        cost_items: Optional[Iterable[CostLineItem]] = None,
        payment_terms: Optional[Iterable[PaymentTerms]] = None,
        fulfillment_processes: Optional[Iterable[FulfillmentProcess]] = None,
        functions: Optional[Iterable[BusinessFunctionSpec]] = None,
        teams: Optional[Iterable[TeamSpec]] = None,
        human_agents: Optional[Iterable[HumanAgentSpec]] = None,
        ai_agents: Optional[Iterable[AIAgentSpec]] = None,
    ) -> BusinessTopology:
        workspace_id = identity.workspace_id

        channel_list = list(channels or [])
        service_list = list(services or [])
        revenue_stream_list = list(revenue_streams or [])
        cost_item_list = list(cost_items or [])
        payment_terms_list = list(payment_terms or [])
        fulfillment_list = list(fulfillment_processes or [])
        function_list = list(functions or [])
        team_list = list(teams or [])
        human_agent_list = list(human_agents or [])
        ai_agent_list = list(ai_agents or [])

        nodes: List[TopologyNode] = []
        edges: List[TopologyEdge] = []

        workspace_node_id = self._workspace_node_id(workspace_id)
        nodes.append(
            TopologyNode(
                id=workspace_node_id,
                workspace_id=workspace_id,
                node_type="workspace",
                ref_id=workspace_id,
                label=identity.display_name(),
                description=identity.description,
                metadata={
                    "business_type": identity.business_type,
                    "currency": identity.currency,
                    "timezone": identity.timezone,
                },
            )
        )

        department_keys = self._department_keys(identity=identity, functions=function_list)

        for department_key in department_keys:
            dept_node_id = self._department_node_id(workspace_id, department_key)
            nodes.append(
                TopologyNode(
                    id=dept_node_id,
                    workspace_id=workspace_id,
                    node_type="department",
                    ref_id=department_key,
                    label=department_key.replace("_", " ").title(),
                    metadata={"department_key": department_key},
                )
            )
            edges.append(
                TopologyEdge(
                    id=f"edge::{workspace_node_id}::contains::{dept_node_id}",
                    workspace_id=workspace_id,
                    edge_type="contains",
                    from_node_id=workspace_node_id,
                    to_node_id=dept_node_id,
                    label="contains",
                )
            )

        for item in function_list:
            node_id = self._node_id("function", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="function",
                    ref_id=item.id,
                    label=item.name,
                    description=item.description,
                    metadata={
                        "department_key": item.department_key,
                        "function_key": item.key,
                    },
                )
            )
            dept_node_id = self._department_node_id(workspace_id, item.department_key)
            edges.append(
                TopologyEdge(
                    id=f"edge::{dept_node_id}::operates::{node_id}",
                    workspace_id=workspace_id,
                    edge_type="operates",
                    from_node_id=dept_node_id,
                    to_node_id=node_id,
                    label="operates",
                )
            )

        for item in channel_list:
            node_id = self._node_id("channel", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="channel",
                    ref_id=item.id,
                    label=item.name,
                    description=item.description,
                    metadata={
                        "channel_type": item.channel_type,
                        "platform_name": item.platform_name or "",
                    },
                )
            )
            edges.append(
                TopologyEdge(
                    id=f"edge::{workspace_node_id}::uses::{node_id}",
                    workspace_id=workspace_id,
                    edge_type="uses",
                    from_node_id=workspace_node_id,
                    to_node_id=node_id,
                    label="uses",
                )
            )

        for item in service_list:
            node_id = self._node_id("service", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="service",
                    ref_id=item.id,
                    label=item.name,
                    description=item.summary or item.description,
                    metadata={
                        "pricing_type": item.pricing_type,
                        "delivery_mode": item.delivery_mode,
                    },
                )
            )
            edges.append(
                TopologyEdge(
                    id=f"edge::{workspace_node_id}::delivers::{node_id}",
                    workspace_id=workspace_id,
                    edge_type="delivers",
                    from_node_id=workspace_node_id,
                    to_node_id=node_id,
                    label="delivers",
                )
            )

        for item in revenue_stream_list:
            node_id = self._node_id("revenue_stream", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="revenue_stream",
                    ref_id=item.id,
                    label=item.name,
                    description=item.description,
                    metadata={
                        "stream_type": item.stream_type,
                        "cadence": item.cadence,
                    },
                )
            )
            edges.append(
                TopologyEdge(
                    id=f"edge::{workspace_node_id}::earns_from::{node_id}",
                    workspace_id=workspace_id,
                    edge_type="earns_from",
                    from_node_id=workspace_node_id,
                    to_node_id=node_id,
                    label="earns_from",
                )
            )

        for item in cost_item_list:
            node_id = self._node_id("cost_item", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="cost_item",
                    ref_id=item.id,
                    label=item.name,
                    description=item.description,
                    metadata={
                        "cost_type": item.cost_type,
                        "frequency": item.frequency,
                    },
                )
            )
            edges.append(
                TopologyEdge(
                    id=f"edge::{workspace_node_id}::costs_for::{node_id}",
                    workspace_id=workspace_id,
                    edge_type="costs_for",
                    from_node_id=workspace_node_id,
                    to_node_id=node_id,
                    label="costs_for",
                )
            )

        for item in payment_terms_list:
            node_id = self._node_id("payment_terms", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="payment_terms",
                    ref_id=item.id,
                    label=item.name,
                    description=item.description,
                    metadata={"timing": item.timing},
                )
            )
            edges.append(
                TopologyEdge(
                    id=f"edge::{workspace_node_id}::paid_by::{node_id}",
                    workspace_id=workspace_id,
                    edge_type="paid_by",
                    from_node_id=workspace_node_id,
                    to_node_id=node_id,
                    label="paid_by",
                )
            )

        for item in fulfillment_list:
            node_id = self._node_id("fulfillment_process", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="fulfillment_process",
                    ref_id=item.id,
                    label=item.name,
                    description=item.description,
                    metadata={"fulfillment_mode": item.fulfillment_mode},
                )
            )
            edges.append(
                TopologyEdge(
                    id=f"edge::{workspace_node_id}::fulfilled_by::{node_id}",
                    workspace_id=workspace_id,
                    edge_type="fulfilled_by",
                    from_node_id=workspace_node_id,
                    to_node_id=node_id,
                    label="fulfilled_by",
                )
            )

        for item in team_list:
            node_id = self._node_id("team", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="team",
                    ref_id=item.id,
                    label=item.name,
                    description=item.description,
                    metadata={"department_key": item.department_key},
                )
            )
            dept_node_id = self._department_node_id(workspace_id, item.department_key)
            edges.append(
                TopologyEdge(
                    id=f"edge::{dept_node_id}::staffed_by::{node_id}",
                    workspace_id=workspace_id,
                    edge_type="staffed_by",
                    from_node_id=dept_node_id,
                    to_node_id=node_id,
                    label="staffed_by",
                )
            )

        for item in human_agent_list:
            node_id = self._node_id("human_agent", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="human_agent",
                    ref_id=item.id,
                    label=item.name,
                    description=item.role_title,
                    metadata={"department_key": item.department_key},
                )
            )

        for item in ai_agent_list:
            node_id = self._node_id("ai_agent", item.id)
            nodes.append(
                TopologyNode(
                    id=node_id,
                    workspace_id=workspace_id,
                    node_type="ai_agent",
                    ref_id=item.id,
                    label=item.name,
                    description=item.agent_type,
                    metadata={
                        "department_key": item.department_key,
                        "model_policy_ref": item.model_policy_ref or "",
                    },
                )
            )

        edges.extend(self._link_functions_to_channels(workspace_id, function_list))
        edges.extend(self._link_functions_to_services(workspace_id, function_list))
        edges.extend(self._link_functions_to_revenue_streams(workspace_id, function_list))
        edges.extend(self._link_functions_to_costs(workspace_id, function_list))
        edges.extend(self._link_functions_to_payment_terms(workspace_id, function_list))
        edges.extend(self._link_functions_to_fulfillment(workspace_id, function_list))
        edges.extend(self._link_functions_to_humans(workspace_id, function_list))
        edges.extend(self._link_functions_to_ai(workspace_id, function_list))
        edges.extend(self._link_teams_to_members(workspace_id, team_list))
        edges.extend(self._link_service_relationships(workspace_id, service_list, channel_list))
        edges.extend(self._link_revenue_relationships(workspace_id, revenue_stream_list))
        edges.extend(self._link_payment_relationships(workspace_id, payment_terms_list))
        edges.extend(self._link_fulfillment_relationships(workspace_id, fulfillment_list))

        return BusinessTopology(
            workspace_id=workspace_id,
            nodes=nodes,
            edges=self._dedupe_edges(edges),
        )

    def generate_from_business_structure_container(
        self,
        container: BusinessStructureContainer,
    ) -> BusinessTopology:
        identity = BusinessIdentity(**container.identity)

        return self.generate(
            identity=identity,
            channels=[BusinessChannel(**item) for item in container.channels],
            services=[ServiceOffer(**item) for item in container.services],
            revenue_streams=[RevenueStream(**item) for item in container.revenue_streams],
            cost_items=[CostLineItem(**item) for item in container.cost_items],
            payment_terms=[PaymentTerms(**item) for item in container.payment_terms],
            fulfillment_processes=[
                FulfillmentProcess(**item) for item in container.fulfillment_processes
            ],
            functions=[BusinessFunctionSpec(**item) for item in container.functions],
            teams=[TeamSpec(**item) for item in container.teams],
            human_agents=[HumanAgentSpec(**item) for item in container.human_agents],
            ai_agents=[AIAgentSpec(**item) for item in container.ai_agents],
        )

    def _department_keys(
        self,
        *,
        identity: BusinessIdentity,
        functions: List[BusinessFunctionSpec],
    ) -> List[str]:
        keys = {fn.department_key for fn in functions}
        if keys:
            return sorted(keys)

        template = self.template_registry.get_default_for_business_type(identity.business_type)
        if template:
            return list(template.default_departments)

        return ["ceo", "marketing", "sales", "operations", "finance", "support"]

    @staticmethod
    def _workspace_node_id(workspace_id: str) -> str:
        return f"node::workspace::{workspace_id}"

    @staticmethod
    def _department_node_id(workspace_id: str, department_key: str) -> str:
        return f"node::department::{workspace_id}::{department_key}"

    @staticmethod
    def _node_id(node_type: str, ref_id: str) -> str:
        return f"node::{node_type}::{ref_id}"

    def _link_functions_to_channels(
        self,
        workspace_id: str,
        functions: List[BusinessFunctionSpec],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for fn in functions:
            from_id = self._node_id("function", fn.id)
            for channel_id in fn.channel_ids:
                to_id = self._node_id("channel", channel_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::uses::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="uses",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="uses",
                    )
                )
        return edges

    def _link_functions_to_services(
        self,
        workspace_id: str,
        functions: List[BusinessFunctionSpec],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for fn in functions:
            from_id = self._node_id("function", fn.id)
            for service_id in fn.service_ids:
                to_id = self._node_id("service", service_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::supports::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="supported_by",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="supports",
                    )
                )
        return edges

    def _link_functions_to_revenue_streams(
        self,
        workspace_id: str,
        functions: List[BusinessFunctionSpec],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for fn in functions:
            from_id = self._node_id("function", fn.id)
            for stream_id in fn.revenue_stream_ids:
                to_id = self._node_id("revenue_stream", stream_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::earns_from::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="earns_from",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="earns_from",
                    )
                )
        return edges

    def _link_functions_to_costs(
        self,
        workspace_id: str,
        functions: List[BusinessFunctionSpec],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for fn in functions:
            from_id = self._node_id("function", fn.id)
            for cost_id in fn.cost_item_ids:
                to_id = self._node_id("cost_item", cost_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::costs_for::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="costs_for",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="costs_for",
                    )
                )
        return edges

    def _link_functions_to_payment_terms(
        self,
        workspace_id: str,
        functions: List[BusinessFunctionSpec],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for fn in functions:
            from_id = self._node_id("function", fn.id)
            for item_id in fn.payment_terms_ids:
                to_id = self._node_id("payment_terms", item_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::paid_by::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="paid_by",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="paid_by",
                    )
                )
        return edges

    def _link_functions_to_fulfillment(
        self,
        workspace_id: str,
        functions: List[BusinessFunctionSpec],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for fn in functions:
            from_id = self._node_id("function", fn.id)
            for item_id in fn.fulfillment_process_ids:
                to_id = self._node_id("fulfillment_process", item_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::fulfilled_by::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="fulfilled_by",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="fulfilled_by",
                    )
                )
        return edges

    def _link_functions_to_humans(
        self,
        workspace_id: str,
        functions: List[BusinessFunctionSpec],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for fn in functions:
            from_id = self._node_id("function", fn.id)
            for item_id in fn.human_agent_ids:
                to_id = self._node_id("human_agent", item_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::staffed_by::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="staffed_by",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="staffed_by",
                    )
                )
        return edges

    def _link_functions_to_ai(
        self,
        workspace_id: str,
        functions: List[BusinessFunctionSpec],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for fn in functions:
            from_id = self._node_id("function", fn.id)
            for item_id in fn.ai_agent_ids:
                to_id = self._node_id("ai_agent", item_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::supported_by::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="supported_by",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="supported_by",
                    )
                )
        return edges

    def _link_teams_to_members(
        self,
        workspace_id: str,
        teams: List[TeamSpec],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for team in teams:
            from_id = self._node_id("team", team.id)
            for member_id in team.human_agent_ids:
                to_id = self._node_id("human_agent", member_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::contains::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="contains",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="contains",
                    )
                )
            for member_id in team.ai_agent_ids:
                to_id = self._node_id("ai_agent", member_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::contains::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="contains",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="contains",
                    )
                )
        return edges

    def _link_service_relationships(
        self,
        workspace_id: str,
        services: List[ServiceOffer],
        channels: List[BusinessChannel],
    ) -> List[TopologyEdge]:
        channel_ids = {channel.id for channel in channels}
        edges: List[TopologyEdge] = []
        for service in services:
            service_node_id = self._node_id("service", service.id)
            for channel_id in service.service_area:
                if channel_id in channel_ids:
                    channel_node_id = self._node_id("channel", channel_id)
                    edges.append(
                        TopologyEdge(
                            id=f"edge::{service_node_id}::sells_through::{channel_node_id}",
                            workspace_id=workspace_id,
                            edge_type="sells_through",
                            from_node_id=service_node_id,
                            to_node_id=channel_node_id,
                            label="sells_through",
                        )
                    )
        return edges

    def _link_revenue_relationships(
        self,
        workspace_id: str,
        revenue_streams: List[RevenueStream],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for stream in revenue_streams:
            from_id = self._node_id("revenue_stream", stream.id)
            for channel_id in stream.channel_ids:
                to_id = self._node_id("channel", channel_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::sells_through::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="sells_through",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="sells_through",
                    )
                )
            for service_id in stream.service_ids:
                to_id = self._node_id("service", service_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::earns_from::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="earns_from",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="earns_from",
                    )
                )
        return edges

    def _link_payment_relationships(
        self,
        workspace_id: str,
        payment_terms_list: List[PaymentTerms],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for item in payment_terms_list:
            from_id = self._node_id("payment_terms", item.id)
            for channel_id in item.channel_ids:
                to_id = self._node_id("channel", channel_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::uses::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="uses",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="uses",
                    )
                )
            for service_id in item.service_ids:
                to_id = self._node_id("service", service_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::paid_by::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="paid_by",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="paid_by",
                    )
                )
        return edges

    def _link_fulfillment_relationships(
        self,
        workspace_id: str,
        fulfillment_list: List[FulfillmentProcess],
    ) -> List[TopologyEdge]:
        edges: List[TopologyEdge] = []
        for item in fulfillment_list:
            from_id = self._node_id("fulfillment_process", item.id)
            for channel_id in item.channel_ids:
                to_id = self._node_id("channel", channel_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::uses::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="uses",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="uses",
                    )
                )
            for service_id in item.service_ids:
                to_id = self._node_id("service", service_id)
                edges.append(
                    TopologyEdge(
                        id=f"edge::{from_id}::fulfilled_by::{to_id}",
                        workspace_id=workspace_id,
                        edge_type="fulfilled_by",
                        from_node_id=from_id,
                        to_node_id=to_id,
                        label="fulfilled_by",
                    )
                )
        return edges

    @staticmethod
    def _dedupe_edges(edges: List[TopologyEdge]) -> List[TopologyEdge]:
        out: List[TopologyEdge] = []
        seen = set()
        for edge in edges:
            key = (edge.edge_type, edge.from_node_id, edge.to_node_id, edge.label)
            if key in seen:
                continue
            seen.add(key)
            out.append(edge)
        return out