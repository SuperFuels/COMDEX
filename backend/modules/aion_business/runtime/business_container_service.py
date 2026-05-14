from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Tuple

from backend.modules.aion_business.contracts.ai_agents import AIAgentSpec
from backend.modules.aion_business.contracts.business_containers import (
    BoardroomSnapshotContainer,
    BrandFoundationContainer,
    BusinessContainerMeta,
    BusinessIdentityContainer,
    BusinessStructureContainer,
    OperationalRuntimeSummaryContainer,
)
from backend.modules.aion_business.contracts.business_identity import BusinessIdentity
from backend.modules.aion_business.contracts.channels import BusinessChannel
from backend.modules.aion_business.contracts.containers import ContainerBindingSpec
from backend.modules.aion_business.contracts.cost_structure import CostLineItem
from backend.modules.aion_business.contracts.fulfillment import FulfillmentProcess
from backend.modules.aion_business.contracts.functions import BusinessFunctionSpec
from backend.modules.aion_business.contracts.human_agents import HumanAgentSpec
from backend.modules.aion_business.contracts.payment_terms import PaymentTerms
from backend.modules.aion_business.contracts.revenue_streams import RevenueStream
from backend.modules.aion_business.contracts.services import ServiceOffer
from backend.modules.aion_business.contracts.teams import TeamSpec
from backend.modules.aion_business.contracts.topology import BusinessTopology
from backend.modules.aion_business.contracts.workspace import (
    BusinessProfile,
    WorkspaceSpec,
)
from backend.modules.aion_business.runtime.business_container_repository import (
    BusinessContainerRepository,
)
from backend.modules.aion_business.runtime.container_binding_repository import (
    ContainerBindingRepository,
)
from backend.modules.aion_business.runtime.costa_conexion_seed import (
    build_costa_conexion_topology_payload,
)
from backend.modules.aion_business.runtime.service_business_topology_generator import (
    ServiceBusinessTopologyGenerator,
)
from backend.modules.aion_business.runtime.topology_repository import TopologyRepository
from backend.modules.aion_business.runtime.topology_to_boardroom_mapper import (
    TopologyToBoardroomMapper,
)
from backend.modules.aion_business.runtime.workspace_repository import WorkspaceRepository


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _deepcopy_dict(value: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return deepcopy(value)


def _deepcopy_list(value: Optional[List[Any]]) -> List[Any]:
    if not isinstance(value, list):
        return []
    return deepcopy(value)

def _as_dict(value: Any) -> Dict[str, Any]:
    return deepcopy(value) if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return deepcopy(value) if isinstance(value, list) else []


def _string_list(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]

    if isinstance(value, str):
        parts = (
            value.replace("•", "\n")
            .replace("·", "\n")
            .replace("|", "\n")
            .replace(",", "\n")
            .splitlines()
        )
        return [part.strip() for part in parts if part.strip()]

    return []


def _first_defined(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _set_model_attr_if_possible(model: Any, name: str, value: Any) -> None:
    if hasattr(model, name):
        try:
            setattr(model, name, value)
        except Exception:
            pass


def _get_model_attr(model: Any, name: str, default: Any = None) -> Any:
    return getattr(model, name, default)

class BusinessContainerService:
    def __init__(
        self,
        *,
        repository: Optional[BusinessContainerRepository] = None,
        binding_repository: Optional[ContainerBindingRepository] = None,
        workspace_repository: Optional[WorkspaceRepository] = None,
        topology_repository: Optional[TopologyRepository] = None,
        topology_generator: Optional[ServiceBusinessTopologyGenerator] = None,
        boardroom_mapper: Optional[TopologyToBoardroomMapper] = None,
    ) -> None:
        self.repository = repository or BusinessContainerRepository()
        self.binding_repository = binding_repository or ContainerBindingRepository()
        self.workspace_repository = workspace_repository or WorkspaceRepository()
        self.topology_repository = topology_repository or TopologyRepository()
        self.topology_generator = topology_generator or ServiceBusinessTopologyGenerator()
        self.boardroom_mapper = boardroom_mapper or TopologyToBoardroomMapper()

    # -------------------------------------------------------------------------
    # Public canonical bootstrap
    # -------------------------------------------------------------------------

    def ensure_canonical_containers(self, workspace_id: str) -> Dict[str, Any]:
        """
        Ensure canonical containers, bindings, and workspace records exist.

        This method must NOT rebuild topology/boardroom projections as a side effect.
        Reads may safely call this without mutating projection state.
        """
        seed = self._get_seed_payload(workspace_id)

        if seed is not None:
            return self._ensure_from_seed(workspace_id, seed)

        return self._ensure_from_existing_state(workspace_id)

    def rebuild_canonical_projections(self, workspace_id: str) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)
        return self.rebuild_topology_and_boardroom_projection(workspace_id)

    def rebuild_topology_and_boardroom_projection(self, workspace_id: str) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)
        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)
        topology = self._build_topology_from_canonical_containers(workspace_id)

        boardroom_model = self._save_boardroom_snapshot_from_topology(
            workspace_id=workspace_id,
            topology=topology,
            runtime_summary=runtime_summary,
            active_zone="coo",
            selected_seat_id=None,
        )

        self._update_runtime_projection_metadata(
            runtime_summary=runtime_summary,
            workspace_id=workspace_id,
            boardroom_model=boardroom_model,
        )
        self.repository.save_model(runtime_summary)

        return {
            "ok": True,
            "workspace_id": workspace_id,
            "topology_updated_at": boardroom_model.meta.updated_at,
            "boardroom_updated_at": boardroom_model.meta.updated_at,
            "runtime_updated_at": runtime_summary.meta.updated_at,
            "source": "canonical_containers",
        }

    def _get_seed_payload(self, workspace_id: str) -> Optional[Dict[str, Any]]:
        if workspace_id == "costa-conexion":
            return build_costa_conexion_topology_payload()
        return None

    def _ensure_from_seed(self, workspace_id: str, seed: Dict[str, Any]) -> Dict[str, Any]:
        identity_payload = _deepcopy_dict(seed.get("identity"))

        self._ensure_workspace(
            workspace_id=workspace_id,
            identity_payload=identity_payload,
        )
        self._ensure_bindings(workspace_id)
        self._save_business_identity_container_if_missing(workspace_id, identity_payload)
        self._save_business_structure_container_if_missing(workspace_id, seed)
        self._ensure_brand_foundation_container(workspace_id, seed=seed)
        self._ensure_projection_containers_exist(workspace_id)

        return {
            "ok": True,
            "workspace_id": workspace_id,
            "detail": "Canonical business containers ensured from seed.",
            "source": "seed",
        }

    def _ensure_from_existing_state(self, workspace_id: str) -> Dict[str, Any]:
        workspace = self._load_workspace_optional(workspace_id)
        if workspace is None:
            return {
                "ok": True,
                "workspace_id": workspace_id,
                "detail": "No seed or existing workspace found; leaving state unchanged.",
                "source": "none",
            }

        self._ensure_workspace_from_workspace_spec(workspace)
        self._ensure_bindings(workspace_id)
        self._ensure_business_identity_from_workspace(workspace)
        self._ensure_business_structure_from_existing_state(workspace)
        self._ensure_brand_foundation_container(workspace_id)
        self._ensure_projection_containers_exist(workspace_id)

        return {
            "ok": True,
            "workspace_id": workspace_id,
            "detail": "Canonical business containers ensured from existing workspace/container state.",
            "source": "existing_state",
        }

    def _ensure_projection_containers_exist(self, workspace_id: str) -> None:
        self._ensure_operational_runtime_summary_container(workspace_id)

        try:
            self.repository.load_boardroom_snapshot(workspace_id)
        except FileNotFoundError:
            pass

        try:
            self.topology_repository.load(workspace_id)
        except FileNotFoundError:
            pass

    # -------------------------------------------------------------------------
    # Workspace helpers
    # -------------------------------------------------------------------------

    def _load_workspace_optional(self, workspace_id: str) -> Optional[WorkspaceSpec]:
        try:
            return self.workspace_repository.load(workspace_id)
        except FileNotFoundError:
            return None

    def _ensure_workspace(self, *, workspace_id: str, identity_payload: Dict[str, Any]) -> None:
        existing = self._load_workspace_optional(workspace_id)
        if existing is not None:
            return

        workspace = WorkspaceSpec(
            id=workspace_id,
            name=identity_payload.get("public_brand_name")
            or identity_payload.get("business_name")
            or workspace_id,
            business_type=identity_payload.get("business_type") or "service_business",
            owner="kevin",
            deployment_mode="local",
            business_profile=BusinessProfile(
                trading_name=identity_payload.get("public_brand_name")
                or identity_payload.get("business_name"),
                sector=identity_payload.get("business_type") or "service_business",
            ),
            status="active",
        )
        self.workspace_repository.save(workspace)

    def _ensure_workspace_from_workspace_spec(self, workspace: WorkspaceSpec) -> None:
        existing = self._load_workspace_optional(workspace.id)
        if existing is not None:
            return
        self.workspace_repository.save(workspace)

    # -------------------------------------------------------------------------
    # Binding helpers
    # -------------------------------------------------------------------------

    def _required_bindings(self, workspace_id: str) -> List[ContainerBindingSpec]:
        return [
            ContainerBindingSpec(
                id="binding-business-identity",
                workspace_id=workspace_id,
                name="Business Identity",
                category="custom",
                runtime_backend="generated",
                runtime_container_id=f"{workspace_id}.business_identity",
                kg_container_id=f"{workspace_id}.business_identity",
                kg_topic_wa="business.identity",
                kg_graph="work",
                writable=True,
                semantic_writes_enabled=True,
                tags=["business", "identity"],
                description="Canonical business identity container",
            ),
            ContainerBindingSpec(
                id="binding-business-structure",
                workspace_id=workspace_id,
                name="Business Structure",
                category="custom",
                runtime_backend="generated",
                runtime_container_id=f"{workspace_id}.business_structure",
                kg_container_id=f"{workspace_id}.business_structure",
                kg_topic_wa="business.structure",
                kg_graph="work",
                writable=True,
                semantic_writes_enabled=True,
                tags=["business", "structure"],
                description="Canonical business structure container",
            ),
            ContainerBindingSpec(
                id="binding-brand-foundation",
                workspace_id=workspace_id,
                name="Brand Foundation",
                category="marketing",
                runtime_backend="generated",
                runtime_container_id=f"{workspace_id}.brand_foundation",
                kg_container_id=f"{workspace_id}.brand_foundation",
                kg_topic_wa="business.brand_foundation",
                kg_graph="work",
                writable=True,
                semantic_writes_enabled=True,
                tags=["business", "brand", "marketing"],
                description="Canonical brand foundation container",
            ),
            ContainerBindingSpec(
                id="binding-boardroom-snapshot",
                workspace_id=workspace_id,
                name="Boardroom Snapshot",
                category="custom",
                runtime_backend="generated",
                runtime_container_id=f"{workspace_id}.boardroom_snapshot",
                kg_container_id=f"{workspace_id}.boardroom_snapshot",
                kg_topic_wa="business.boardroom_snapshot",
                kg_graph="work",
                writable=False,
                semantic_writes_enabled=True,
                tags=["business", "boardroom", "topology"],
                description="Generated boardroom-ready projection container",
            ),
            ContainerBindingSpec(
                id="binding-operational-runtime-summary",
                workspace_id=workspace_id,
                name="Operational Runtime Summary",
                category="custom",
                runtime_backend="generated",
                runtime_container_id=f"{workspace_id}.operational_runtime_summary",
                kg_container_id=f"{workspace_id}.operational_runtime_summary",
                kg_topic_wa="business.operational_runtime_summary",
                kg_graph="work",
                writable=True,
                semantic_writes_enabled=True,
                tags=["business", "runtime", "summary"],
                description="Runtime summary projection container",
            ),
        ]

    def _ensure_bindings(self, workspace_id: str) -> None:
        existing_by_id = {
            binding.id: binding
            for binding in self.binding_repository.list_bindings(workspace_id)
        }

        for binding in self._required_bindings(workspace_id):
            existing = existing_by_id.get(binding.id)
            if existing is None or existing.model_dump(mode="json") != binding.model_dump(mode="json"):
                self.binding_repository.save(binding)
                try:
                    self.workspace_repository.register_container_binding(workspace_id, binding.id)
                except Exception:
                    pass

    def get_binding_contract_payload(self, workspace_id: str) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)

        items = []
        for binding in self.binding_repository.list_bindings(workspace_id):
            items.append(
                {
                    "binding_id": binding.id,
                    "workspace_id": binding.workspace_id,
                    "container_name": binding.name,
                    "category": binding.category,
                    "runtime_container_id": binding.runtime_container_id,
                    "kg_container_id": binding.kg_container_id,
                    "kg_topic_wa": binding.kg_topic_wa,
                    "kg_graph": binding.kg_graph,
                    "writable": binding.writable,
                    "semantic_writes_enabled": binding.semantic_writes_enabled,
                    "description": binding.description,
                    "tags": list(binding.tags or []),
                }
            )

        return {
            "workspace_id": workspace_id,
            "items": items,
            "updated_at": _utc_now_iso(),
        }

    # -------------------------------------------------------------------------
    # Canonical containers
    # -------------------------------------------------------------------------

    def _save_business_identity_container(self, workspace_id: str, identity_payload: Dict[str, Any]) -> None:
        model = BusinessIdentityContainer(
            id=f"{workspace_id}.business_identity",
            workspace_id=workspace_id,
            meta=BusinessContainerMeta(
                workspace_id=workspace_id,
                container_key="business_identity",
                updated_at=_utc_now_iso(),
            ),
            legal_name=identity_payload.get("business_name"),
            trading_name=identity_payload.get("public_brand_name"),
            business_type=identity_payload.get("business_type"),
            sector=identity_payload.get("sector") or identity_payload.get("business_type") or "service_business",
            owner=identity_payload.get("owner") or "kevin",
            country=identity_payload.get("country"),
            region=identity_payload.get("region"),
            city=identity_payload.get("city"),
            timezone=identity_payload.get("timezone"),
            currency=identity_payload.get("currency"),
            primary_domain=identity_payload.get("primary_domain"),
            website_url=identity_payload.get("website_url"),
            primary_email=identity_payload.get("primary_email"),
            description=identity_payload.get("description"),
            source_refs=["runtime.seed_or_identity_payload"],
        )
        self.repository.save_model(model)

    def _save_business_identity_container_if_missing(
        self,
        workspace_id: str,
        identity_payload: Dict[str, Any],
    ) -> None:
        try:
            self.repository.load_business_identity(workspace_id)
        except FileNotFoundError:
            self._save_business_identity_container(workspace_id, identity_payload)

    def _ensure_business_identity_from_workspace(self, workspace: WorkspaceSpec) -> None:
        try:
            existing = self.repository.load_business_identity(workspace.id)
            if existing.meta.updated_at is None:
                existing.meta.updated_at = _utc_now_iso()
                self.repository.save_model(existing)
            return
        except FileNotFoundError:
            pass

        profile = workspace.business_profile
        model = BusinessIdentityContainer(
            id=f"{workspace.id}.business_identity",
            workspace_id=workspace.id,
            meta=BusinessContainerMeta(
                workspace_id=workspace.id,
                container_key="business_identity",
                updated_at=_utc_now_iso(),
            ),
            legal_name=profile.legal_name,
            trading_name=profile.trading_name or workspace.name,
            business_type=workspace.business_type,
            sector=profile.sector or workspace.business_type,
            stage=profile.stage,
            owner=workspace.owner,
            description=None,
            source_refs=["workspace_repository"],
        )
        self.repository.save_model(model)

    def _save_business_structure_container(self, workspace_id: str, seed: Dict[str, Any]) -> None:
        model = BusinessStructureContainer(
            id=f"{workspace_id}.business_structure",
            workspace_id=workspace_id,
            meta=BusinessContainerMeta(
                workspace_id=workspace_id,
                container_key="business_structure",
                updated_at=_utc_now_iso(),
            ),
            identity=_deepcopy_dict(seed.get("identity")),
            channels=_deepcopy_list(seed.get("channels")),
            services=_deepcopy_list(seed.get("services")),
            revenue_streams=_deepcopy_list(seed.get("revenue_streams")),
            cost_items=_deepcopy_list(seed.get("cost_items")),
            payment_terms=_deepcopy_list(seed.get("payment_terms")),
            fulfillment_processes=_deepcopy_list(seed.get("fulfillment_processes")),
            functions=_deepcopy_list(seed.get("functions")),
            teams=_deepcopy_list(seed.get("teams")),
            human_agents=_deepcopy_list(seed.get("human_agents")),
            ai_agents=_deepcopy_list(seed.get("ai_agents")),
        )
        self.repository.save_model(model)

    def _save_business_structure_container_if_missing(
        self,
        workspace_id: str,
        seed: Dict[str, Any],
    ) -> None:
        try:
            self.repository.load_business_structure(workspace_id)
        except FileNotFoundError:
            self._save_business_structure_container(workspace_id, seed)

    def _ensure_business_structure_from_existing_state(self, workspace: WorkspaceSpec) -> None:
        try:
            existing = self.repository.load_business_structure(workspace.id)
            if existing.meta.updated_at is None:
                existing.meta.updated_at = _utc_now_iso()
                self.repository.save_model(existing)
            return
        except FileNotFoundError:
            pass

        identity_payload = self._identity_payload_from_workspace(workspace)

        model = BusinessStructureContainer(
            id=f"{workspace.id}.business_structure",
            workspace_id=workspace.id,
            meta=BusinessContainerMeta(
                workspace_id=workspace.id,
                container_key="business_structure",
                updated_at=_utc_now_iso(),
            ),
            identity=identity_payload,
            channels=[],
            services=[],
            revenue_streams=[],
            cost_items=[],
            payment_terms=[],
            fulfillment_processes=[],
            functions=[],
            teams=[],
            human_agents=[],
            ai_agents=[],
        )
        self.repository.save_model(model)

    def _identity_payload_from_workspace(self, workspace: WorkspaceSpec) -> Dict[str, Any]:
        profile = workspace.business_profile
        return {
            "workspace_id": workspace.id,
            "business_name": profile.legal_name or workspace.name,
            "public_brand_name": profile.trading_name or workspace.name,
            "business_type": workspace.business_type or "service_business",
            "country": None,
            "region": None,
            "city": None,
            "timezone": None,
            "currency": None,
            "primary_domain": None,
            "website_url": None,
            "primary_email": None,
            "description": None,
        }

    def _default_brand_foundation_model(
        self,
        workspace_id: str,
        *,
        seed: Optional[Dict[str, Any]] = None,
    ) -> BrandFoundationContainer:
        channels: List[str] = []
        identity = _as_dict(seed.get("identity")) if seed else {}

        if seed:
            for item in seed.get("channels", []) or []:
                name = item.get("name")
                if isinstance(name, str) and name.strip():
                    channels.append(name.strip())

        brand_name = (
            identity.get("public_brand_name")
            or identity.get("business_name")
            or "Costa Conexion"
        )

        brand_intelligence_map = self._build_default_brand_intelligence_map(
            workspace_id=workspace_id,
            brand_name=brand_name,
            channels=channels or ["Website"],
        )

        model = BrandFoundationContainer(
            id=f"{workspace_id}.brand_foundation",
            workspace_id=workspace_id,
            meta=BusinessContainerMeta(
                workspace_id=workspace_id,
                container_key="brand_foundation",
                updated_at=_utc_now_iso(),
            ),
            objective="Drive local enquiries",
            funnel_goal="Lead capture",
            target_audience="Local homeowners and small business owners",
            persona="Local service buyer",
            offer="Local business visibility and conversion support",
            channels=channels or ["Website"],
            hashtags=["#LocalBusiness"],
            keywords=["local business", "trusted local services"],
            hard_rules=["Do not auto-publish without approval"],
            guidance_notes=["Keep tone clear, useful, and trusted"],
            campaign_notes=["Maintain local trust and conversion focus"],
        )

        self._apply_brand_intelligence_to_model(
            model,
            brand_intelligence_map,
        )

        return model

    def _build_default_brand_intelligence_map(
        self,
        *,
        workspace_id: str,
        brand_name: str,
        channels: List[str],
    ) -> Dict[str, Any]:
        return {
            "version": "brand_intelligence_map.v2",
            "workspaceId": workspace_id,
            "workspace_id": workspace_id,

            "brandOverview": {
                "brandName": brand_name,
                "whatYouDo": "Provide trusted local services to homeowners and local businesses.",
                "uniqueValueProposition": "Clear, reliable, local service with practical support and simple communication.",
                "businessType": "service_business",
            },

            "brandGoals": {
                "primaryGoal": "Establish ourselves as the trusted local provider in our service area.",
                "commercialGoal": "Generate qualified enquiries that become booked calls, quotes, installs, or retained customers.",
                "awarenessGoal": "Make the brand feel visible, reliable, professional, and easy to contact.",
            },

            "brandPurpose": {
                "purpose": "Provide professional local services in a clear, trustworthy, and customer-focused way.",
            },

            "brandVision": {
                "vision": "Become a leading service provider in the local operating radius.",
                "localRadius": "10 mile radius",
            },

            "brandMission": {
                "mission": "Provide every customer with clear advice, reliable service, professional communication, and a simple next step.",
            },

            "brandValues": {
                "values": [
                    "Professional",
                    "Reliable",
                    "Helpful",
                    "Clear",
                    "Trustworthy",
                    "Cost effective",
                ],
            },

            "brandPositioning": {
                "positioning": "A trusted, local, professional service provider for customers who want clear help without confusion.",
                "differentiation": [
                    "Local presence",
                    "Clear communication",
                    "Reliable service",
                    "Professional standards",
                    "Simple customer journey",
                ],
            },

            "brandPersonality": {
                "traits": [
                    "Sophisticated",
                    "Knowledgeable",
                    "Approachable",
                    "Practical",
                    "Cost effective",
                ],
            },

            "brandVoice": {
                "voice": "Sophisticated, knowledgeable, clear, trusted, and cost effective.",
                "toneOfVoice": [
                    "Professional",
                    "Useful",
                    "Confident",
                    "Local",
                    "Not pushy",
                ],
                "communicationStyle": "Explain the problem clearly, show the value, remove confusion, then give the customer a simple action.",
                "dos": [
                    "Use clear simple language",
                    "Lead with customer pain points",
                    "Show practical benefits",
                    "Make the next step obvious",
                    "Sound professional and calm",
                ],
                "donts": [
                    "Do not use shouting sales language",
                    "Do not overpromise",
                    "Do not use confusing jargon",
                    "Do not publish without approval",
                ],
            },

            "brandStory": {
                "origin": "",
                "journey": "",
                "keyMoments": [],
                "customerReasonToBelieve": "",
            },

            "tagline": {
                "primary": "",
                "alternatives": [],
            },

            "audience": {
                "primaryAudience": "Local homeowners and small business owners",
                "customerType": "B2C and B2B",
                "segments": [
                    {
                        "id": "segment_homeowners",
                        "label": "Local homeowners",
                        "fit": "Home service, repair, installation, upgrade, or maintenance work.",
                        "painPoints": [
                            "Not sure who to trust",
                            "Concerned about cost",
                            "Needs a reliable local provider",
                            "Wants a simple explanation",
                        ],
                        "desiredOutcome": "Fast, professional help with a clear quote or next step.",
                    },
                    {
                        "id": "segment_small_business",
                        "label": "Small business owners",
                        "fit": "Business service, support, maintenance, upgrade, or ongoing provider work.",
                        "painPoints": [
                            "Downtime risk",
                            "Needs reliable support",
                            "Too busy to compare suppliers",
                            "Needs clear professional communication",
                        ],
                        "desiredOutcome": "Dependable service with minimal disruption.",
                    },
                ],
            },

            "customerPersonas": {
                "personas": [
                    {
                        "id": "persona_local_homeowner",
                        "name": "Local Homeowner",
                        "age": "35-65",
                        "gender": "Any",
                        "location": "Local service area",
                        "occupation": "Homeowner",
                        "interests": [
                            "Home improvement",
                            "Local recommendations",
                            "Reliable trades",
                        ],
                        "values": [
                            "Trust",
                            "Fair price",
                            "Professionalism",
                            "Speed",
                        ],
                        "culture": "Local community / recommendation-led buyer",
                        "hobbies": [],
                        "customerType": "B2C",
                        "mainPainPoint": "Needs someone reliable and local without being confused or overcharged.",
                        "messageAngle": "Trusted local help, clear advice, simple next step.",
                    },
                    {
                        "id": "persona_small_business_owner",
                        "name": "Small Business Owner",
                        "age": "30-60",
                        "gender": "Any",
                        "location": "Local service area",
                        "occupation": "Business owner",
                        "interests": [
                            "Keeping the business running",
                            "Local suppliers",
                            "Practical service providers",
                        ],
                        "values": [
                            "Reliability",
                            "Speed",
                            "Professional support",
                            "Low disruption",
                        ],
                        "culture": "Time-poor, practical, ROI-focused",
                        "hobbies": [],
                        "customerType": "B2B",
                        "mainPainPoint": "Needs dependable support without disruption.",
                        "messageAngle": "Professional support that keeps things moving.",
                    },
                ],
            },

            "customerJourney": {
                "basicJourney": [
                    {
                        "step": 1,
                        "stage": "Discovery",
                        "example": "Customer scrolls Facebook or searches locally.",
                    },
                    {
                        "step": 2,
                        "stage": "Targeting",
                        "example": "Customer sees relevant ad or post based on local need.",
                    },
                    {
                        "step": 3,
                        "stage": "Consideration",
                        "example": "Customer checks website, social proof, reviews, or profile.",
                    },
                    {
                        "step": 4,
                        "stage": "Conversion",
                        "example": "Customer messages, calls, requests quote, or submits form.",
                    },
                    {
                        "step": 5,
                        "stage": "Follow-up",
                        "example": "Brand responds quickly and moves the customer to booking.",
                    },
                ],
            },

            "painPoints": {
                "customerProblems": [
                    "Customer does not know who to trust",
                    "Customer wants clear pricing or a clear next step",
                    "Customer wants professional local help",
                    "Customer wants the problem solved without hassle",
                ],
                "serviceProblemsSolved": [
                    "Confusion",
                    "Low trust",
                    "Poor communication",
                    "Slow response",
                    "Unclear options",
                ],
            },

            "competitorAnalysis": {
                "competitorUrls": [],
                "competitorFindings": [],
                "differentiationOpportunities": [
                    "Sound clearer than competitors",
                    "Show local trust faster",
                    "Make the CTA easier",
                    "Use customer pain points more directly",
                ],
            },

            "messaging": {
                "coreMessage": "Trusted local service made simple.",
                "messagePillars": [
                    {
                        "id": "pillar_trust",
                        "label": "Trust",
                        "message": "A local service customers can contact and understand.",
                    },
                    {
                        "id": "pillar_clarity",
                        "label": "Clarity",
                        "message": "Simple explanations, clear options, and obvious next steps.",
                    },
                    {
                        "id": "pillar_reliability",
                        "label": "Reliability",
                        "message": "Professional help focused on solving the customer’s problem properly.",
                    },
                ],
                "ctaLibrary": [
                    "Message us for a free quote.",
                    "Send us your postcode and we’ll advise.",
                    "Ask for availability.",
                    "Book a local check.",
                ],
            },

            "platformStrategy": {
                "defaultPlatform": "facebook",
                "activeChannels": channels or ["Facebook", "Instagram"],
                "facebook": "Use local trust, pain-point-led posts, simple offers, proof, and clear message/call CTAs.",
                "instagram": "Use clean visuals, short hooks, service benefits, and easy DM CTAs.",
                "website": "Use clear service pages, trust signals, locations, benefits, and quote/contact CTAs.",
                "postingRules": [
                    "Do not exceed one main post per day",
                    "Keep message clear and useful",
                    "Always include a simple next step",
                ],
            },

            "creativeDirection": {
                "audienceObjective": "Make the viewer feel the service is reliable, local, professional, and easy to enquire about.",
                "direction": "Clean, professional, local-service creative with strong offer clarity and minimal clutter.",
                "doRules": [
                    "Use simple hierarchy",
                    "Make the customer problem obvious",
                    "Show the benefit clearly",
                    "Keep CTA visible",
                ],
                "doNotRules": [
                    "Do not clutter the design",
                    "Do not use excessive jargon",
                    "Do not make unrealistic claims",
                ],
            },

            "visualIdentity": {
                "colourRules": [
                    "Use clean blue, white space, dark readable text, and restrained accent colour.",
                ],
                "fontRules": [
                    "Use clean bold sans-serif headlines",
                    "Use readable body text",
                ],
                "imageStyleRules": [
                    "Use professional, realistic local-service visuals",
                    "Avoid cartoonish or gimmicky visuals unless explicitly requested",
                ],
                "layoutRules": [
                    "Clear headline",
                    "Simple benefit",
                    "Obvious CTA",
                    "Minimal clutter",
                ],
            },

            "contentRules": {
                "hardRules": [
                    "Do not publish automatically",
                    "Public-facing content must stop for approval",
                    "Avoid overpromising or guaranteed outcomes",
                ],
                "guidanceNotes": [
                    "Lead with the customer problem",
                    "Use local trust language",
                    "Keep the tone professional and helpful",
                ],
                "campaignNotes": [
                    "Use the brand foundation as the source of truth for every post.",
                ],
            },

            "governance": {
                "owner": "Marketing",
                "approvalMode": "draft_and_approval",
                "publishAutonomously": False,
                "reviewCadence": "before_publication",
                "updatedBy": "desktop",
            },
        }

    def _extract_brand_intelligence_map_from_payload(
        self,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        for key in (
            "brandIntelligenceMap",
            "brand_intelligence_map",
            "brandMap",
            "brand_map",
            "map",
        ):
            value = payload.get(key)
            if isinstance(value, dict):
                return deepcopy(value)
        return {}

    def _get_brand_intelligence_from_model(
        self,
        model: BrandFoundationContainer,
    ) -> Dict[str, Any]:
        for attr in (
            "brand_intelligence_map",
            "brandIntelligenceMap",
            "brand_map",
            "brandMap",
        ):
            value = _get_model_attr(model, attr)
            if isinstance(value, dict):
                return deepcopy(value)

        return self._build_default_brand_intelligence_map(
            workspace_id=model.workspace_id,
            brand_name=model.workspace_id,
            channels=list(model.channels or []),
        )

    def _apply_brand_intelligence_to_model(
        self,
        model: BrandFoundationContainer,
        brand_intelligence_map: Dict[str, Any],
    ) -> None:
        if not isinstance(brand_intelligence_map, dict):
            return

        _set_model_attr_if_possible(
            model,
            "brand_intelligence_map",
            deepcopy(brand_intelligence_map),
        )
        _set_model_attr_if_possible(
            model,
            "brandIntelligenceMap",
            deepcopy(brand_intelligence_map),
        )
        _set_model_attr_if_possible(
            model,
            "brand_map",
            deepcopy(brand_intelligence_map),
        )
        _set_model_attr_if_possible(
            model,
            "brandMap",
            deepcopy(brand_intelligence_map),
        )

    def _merge_brand_intelligence_map(
        self,
        *,
        existing: Dict[str, Any],
        incoming: Dict[str, Any],
        flat_payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        merged = deepcopy(existing or {})

        if incoming:
            merged.update(deepcopy(incoming))

        merged.setdefault("version", "brand_intelligence_map.v2")

        if flat_payload.get("objective") is not None:
            merged.setdefault("brandGoals", {})
            merged["brandGoals"]["primaryGoal"] = flat_payload.get("objective")

        if flat_payload.get("targetAudience") is not None or flat_payload.get("target_audience") is not None:
            merged.setdefault("audience", {})
            merged["audience"]["primaryAudience"] = (
                flat_payload.get("targetAudience")
                or flat_payload.get("target_audience")
                or ""
            )

        if flat_payload.get("persona") is not None:
            merged.setdefault("customerPersonas", {})
            merged["customerPersonas"]["primaryPersona"] = flat_payload.get("persona")

        if flat_payload.get("offer") is not None:
            merged.setdefault("messaging", {})
            merged["messaging"]["primaryOffer"] = flat_payload.get("offer")

        if flat_payload.get("channels") is not None:
            merged.setdefault("platformStrategy", {})
            merged["platformStrategy"]["activeChannels"] = _string_list(flat_payload.get("channels"))

        hard_rules = _first_defined(flat_payload.get("hardRules"), flat_payload.get("hard_rules"))
        guidance_notes = _first_defined(flat_payload.get("guidanceNotes"), flat_payload.get("guidance_notes"))
        campaign_notes = _first_defined(flat_payload.get("campaignNotes"), flat_payload.get("campaign_notes"))

        merged.setdefault("contentRules", {})

        if hard_rules is not None:
            merged["contentRules"]["hardRules"] = _string_list(hard_rules)

        if guidance_notes is not None:
            merged["contentRules"]["guidanceNotes"] = _string_list(guidance_notes)

        if campaign_notes is not None:
            merged["contentRules"]["campaignNotes"] = _string_list(campaign_notes)

        merged["updatedAt"] = _utc_now_iso()
        merged["updated_at"] = merged["updatedAt"]

        return merged

    def _ensure_brand_foundation_container(
        self,
        workspace_id: str,
        *,
        seed: Optional[Dict[str, Any]] = None,
    ) -> None:
        try:
            existing = self.repository.load_brand_foundation(workspace_id)
            existing.meta.updated_at = existing.meta.updated_at or _utc_now_iso()
            self.repository.save_model(existing)
        except FileNotFoundError:
            self.repository.save_model(
                self._default_brand_foundation_model(workspace_id, seed=seed)
            )

    # -------------------------------------------------------------------------
    # Topology + boardroom projection
    # -------------------------------------------------------------------------

    def _load_structure(self, workspace_id: str) -> BusinessStructureContainer:
        return self.repository.load_business_structure(workspace_id)

    def _load_identity(self, workspace_id: str) -> BusinessIdentityContainer:
        return self.repository.load_business_identity(workspace_id)

    def _load_brand_foundation(self, workspace_id: str) -> BrandFoundationContainer:
        return self.repository.load_brand_foundation(workspace_id)

    def _identity_contract_from_containers(
        self,
        workspace_id: str,
        structure: BusinessStructureContainer,
        identity_container: BusinessIdentityContainer,
    ) -> BusinessIdentity:
        identity_payload = _deepcopy_dict(structure.identity)
        identity_payload.setdefault("workspace_id", workspace_id)
        identity_payload.setdefault(
            "business_name",
            identity_container.legal_name or identity_container.trading_name or workspace_id,
        )
        identity_payload.setdefault(
            "public_brand_name",
            identity_container.trading_name or identity_container.legal_name or workspace_id,
        )
        identity_payload.setdefault(
            "business_type",
            identity_container.business_type or "service_business",
        )
        identity_payload.setdefault("country", identity_container.country)
        identity_payload.setdefault("region", identity_container.region)
        identity_payload.setdefault("city", identity_container.city)
        identity_payload.setdefault("timezone", identity_container.timezone)
        identity_payload.setdefault("currency", identity_container.currency)
        identity_payload.setdefault("primary_domain", identity_container.primary_domain)
        identity_payload.setdefault("website_url", identity_container.website_url)
        identity_payload.setdefault("primary_email", identity_container.primary_email)
        identity_payload.setdefault("description", identity_container.description)
        identity_payload.setdefault("owner_role_id", "ceo-core")
        identity_payload.setdefault("onboarding_status", "active")
        identity_payload.setdefault("active", True)
        return BusinessIdentity(**identity_payload)

    def _topology_inputs_from_structure(
        self,
        structure: BusinessStructureContainer,
    ) -> Tuple[
        List[BusinessChannel],
        List[ServiceOffer],
        List[RevenueStream],
        List[CostLineItem],
        List[PaymentTerms],
        List[FulfillmentProcess],
        List[BusinessFunctionSpec],
        List[TeamSpec],
        List[HumanAgentSpec],
        List[AIAgentSpec],
    ]:
        return (
            [BusinessChannel(**item) for item in structure.channels],
            [ServiceOffer(**item) for item in structure.services],
            [RevenueStream(**item) for item in structure.revenue_streams],
            [CostLineItem(**item) for item in structure.cost_items],
            [PaymentTerms(**item) for item in structure.payment_terms],
            [FulfillmentProcess(**item) for item in structure.fulfillment_processes],
            [BusinessFunctionSpec(**item) for item in structure.functions],
            [TeamSpec(**item) for item in structure.teams],
            [HumanAgentSpec(**item) for item in structure.human_agents],
            [AIAgentSpec(**item) for item in structure.ai_agents],
        )

    def _build_topology_from_canonical_containers(self, workspace_id: str) -> BusinessTopology:
        structure = self._load_structure(workspace_id)
        identity_container = self._load_identity(workspace_id)

        identity = self._identity_contract_from_containers(
            workspace_id,
            structure,
            identity_container,
        )
        (
            channels,
            services,
            revenue_streams,
            cost_items,
            payment_terms,
            fulfillment_processes,
            functions,
            teams,
            human_agents,
            ai_agents,
        ) = self._topology_inputs_from_structure(structure)

        return self.topology_generator.generate(
            identity=identity,
            channels=channels,
            services=services,
            revenue_streams=revenue_streams,
            cost_items=cost_items,
            payment_terms=payment_terms,
            fulfillment_processes=fulfillment_processes,
            functions=functions,
            teams=teams,
            human_agents=human_agents,
            ai_agents=ai_agents,
        )

    def _runtime_payload_from_runtime_summary(
        self,
        runtime_summary: Optional[OperationalRuntimeSummaryContainer],
    ) -> Dict[str, Any]:
        if runtime_summary is None:
            return {"runs": [], "approvals": [], "operators": [], "triggers": []}

        runtime_payload = dict(runtime_summary.runtime_summary or {})
        boardroom_summary = dict(runtime_payload.get("boardroom_summary") or {})
        runtime_block = dict(boardroom_summary.get("runtime") or {})

        runs = runtime_block.get("runs")
        approvals = runtime_block.get("approvals")
        operators = runtime_block.get("operators")
        triggers = runtime_block.get("triggers")

        if not isinstance(runs, list):
            runs = []
        if not isinstance(approvals, list):
            approvals = []
        if not isinstance(operators, list):
            operators = []
        if not isinstance(triggers, list):
            triggers = []

        return {
            "runs": deepcopy(runs),
            "approvals": deepcopy(approvals),
            "operators": deepcopy(operators),
            "triggers": deepcopy(triggers),
        }

    def _build_boardroom_summary_projection(
        self,
        *,
        workspace_id: str,
        boardroom_payload: Dict[str, Any],
        topology_payload: Dict[str, Any],
        identity: BusinessIdentityContainer,
        brand: Optional[BrandFoundationContainer],
    ) -> Dict[str, Any]:
        departments = list(boardroom_payload.get("departments") or [])
        seats = list(boardroom_payload.get("seats") or [])
        topology_nodes = list(topology_payload.get("nodes") or [])
        topology_edges = list(topology_payload.get("edges") or [])
        runtime_payload = _deepcopy_dict(boardroom_payload.get("runtime"))

        return {
            "workspace": {
                "workspace_id": workspace_id,
                "name": identity.trading_name or identity.legal_name or workspace_id,
                "business_type": identity.business_type,
                "industry": identity.sector,
                "currency": identity.currency,
                "timezone": identity.timezone,
            },
            "boardroom": {
                "active_zone": boardroom_payload.get("active_zone") or "coo",
                "selected_seat_id": boardroom_payload.get("selected_seat_id"),
                "department_count": len(departments),
                "seat_count": len(seats),
                "departments": departments,
                "pulse": _deepcopy_dict(boardroom_payload.get("pulse")),
                "center": _deepcopy_dict(boardroom_payload.get("center")),
                "floors": _deepcopy_dict(boardroom_payload.get("floors")),
                "runtime": runtime_payload,
            },
            "topology": {
                "node_count": len(topology_nodes),
                "edge_count": len(topology_edges),
            },
            "brand_context": {
                "objective": brand.objective if brand else None,
                "funnel_goal": brand.funnel_goal if brand else None,
                "target_audience": brand.target_audience if brand else None,
                "persona": brand.persona if brand else None,
                "offer": brand.offer if brand else None,
                "channels": list(brand.channels or []) if brand else [],
                "hashtags": list(brand.hashtags or []) if brand else [],
                "keywords": list(brand.keywords or []) if brand else [],
                "brandIntelligenceMap": (
                    self._get_brand_intelligence_from_model(brand)
                    if brand
                    else {}
                ),
                "brand_intelligence_map": (
                    self._get_brand_intelligence_from_model(brand)
                    if brand
                    else {}
                ),
            },
            "runtime": runtime_payload,
            "generated_at": _utc_now_iso(),
        }

    def _save_boardroom_snapshot_from_topology(
        self,
        *,
        workspace_id: str,
        topology: BusinessTopology,
        runtime_summary: Optional[OperationalRuntimeSummaryContainer] = None,
        active_zone: str = "coo",
        selected_seat_id: Optional[str] = None,
    ) -> BoardroomSnapshotContainer:
        self.topology_repository.save(topology)

        if runtime_summary is None:
            runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)

        runtime_payload = self._runtime_payload_from_runtime_summary(runtime_summary)

        boardroom_result = self.boardroom_mapper.map_topology(
            topology,
            active_zone=active_zone,
            selected_seat_id=selected_seat_id,
            runtime_summary=runtime_payload,
        )

        topology_json = topology.model_dump(mode="json")
        boardroom_payload = {
            "workspace": boardroom_result.workspace,
            "departments": boardroom_result.departments,
            "seats": boardroom_result.seats,
            "pulse": boardroom_result.pulse,
            "center": boardroom_result.center,
            "active_zone": boardroom_result.active_zone,
            "selected_seat_id": boardroom_result.selected_seat_id,
            "floors": boardroom_result.floors,
            "runtime": _deepcopy_dict(getattr(boardroom_result, "runtime", runtime_payload)),
            "metadata": boardroom_result.metadata,
            "topology": topology_json,
        }

        model = BoardroomSnapshotContainer(
            id=f"{workspace_id}.boardroom_snapshot",
            workspace_id=workspace_id,
            meta=BusinessContainerMeta(
                workspace_id=workspace_id,
                container_key="boardroom_snapshot",
                updated_at=_utc_now_iso(),
            ),
            topology=topology_json,
            boardroom=boardroom_payload,
        )
        self.repository.save_model(model)
        return model

    def _update_runtime_projection_metadata(
        self,
        *,
        runtime_summary: OperationalRuntimeSummaryContainer,
        workspace_id: str,
        boardroom_model: BoardroomSnapshotContainer,
    ) -> None:
        runtime_summary.runtime_summary = dict(runtime_summary.runtime_summary or {})
        runtime_summary.runtime_summary["workspace_id"] = workspace_id
        runtime_summary.runtime_summary["sync_mode"] = "local_primary"
        runtime_summary.runtime_summary["topology_projection_updated_at"] = (
            boardroom_model.meta.updated_at
        )
        runtime_summary.runtime_summary["boardroom_projection_updated_at"] = (
            boardroom_model.meta.updated_at
        )

        identity = self.repository.load_business_identity(workspace_id)
        brand = None
        try:
            brand = self.repository.load_brand_foundation(workspace_id)
        except FileNotFoundError:
            brand = None

        runtime_summary.runtime_summary["boardroom_summary"] = (
            self._build_boardroom_summary_projection(
                workspace_id=workspace_id,
                boardroom_payload=dict(boardroom_model.boardroom or {}),
                topology_payload=dict(boardroom_model.topology or {}),
                identity=identity,
                brand=brand,
            )
        )
        runtime_summary.runtime_summary["generated_at"] = _utc_now_iso()
        runtime_summary.meta.updated_at = _utc_now_iso()

    def get_brand_foundation_payload(self, workspace_id: str) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)
        model = self.repository.load_brand_foundation(workspace_id)

        brand_intelligence_map = self._get_brand_intelligence_from_model(model)

        return {
            "id": model.id,
            "workspace_id": model.workspace_id,

            "objective": model.objective,
            "funnelGoal": model.funnel_goal,
            "funnel_goal": model.funnel_goal,

            "targetAudience": model.target_audience,
            "target_audience": model.target_audience,

            "persona": model.persona,
            "offer": model.offer,

            "channels": list(model.channels or []),
            "hashtags": list(model.hashtags or []),
            "keywords": list(model.keywords or []),

            "hardRules": list(model.hard_rules or []),
            "hard_rules": list(model.hard_rules or []),

            "guidanceNotes": list(model.guidance_notes or []),
            "guidance_notes": list(model.guidance_notes or []),

            "campaignNotes": list(model.campaign_notes or []),
            "campaign_notes": list(model.campaign_notes or []),

            "brandIntelligenceMap": brand_intelligence_map,
            "brand_intelligence_map": brand_intelligence_map,
            "brandMap": brand_intelligence_map,
            "brand_map": brand_intelligence_map,

            "updatedAt": model.meta.updated_at,
            "updated_at": model.meta.updated_at,
        }

    def save_brand_foundation_payload(
        self,
        workspace_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)

        try:
            model = self.repository.load_brand_foundation(workspace_id)
        except FileNotFoundError:
            model = self._default_brand_foundation_model(workspace_id)

        if "objective" in payload:
            model.objective = payload.get("objective")

        if "funnelGoal" in payload:
            model.funnel_goal = payload.get("funnelGoal")
        if "funnel_goal" in payload:
            model.funnel_goal = payload.get("funnel_goal")

        if "targetAudience" in payload:
            model.target_audience = payload.get("targetAudience")
        if "target_audience" in payload:
            model.target_audience = payload.get("target_audience")

        if "persona" in payload:
            model.persona = payload.get("persona")

        if "offer" in payload:
            model.offer = payload.get("offer")

        if "channels" in payload:
            model.channels = _string_list(payload.get("channels"))

        if "hashtags" in payload:
            model.hashtags = _string_list(payload.get("hashtags"))

        if "keywords" in payload:
            model.keywords = _string_list(payload.get("keywords"))

        if "hardRules" in payload:
            model.hard_rules = _string_list(payload.get("hardRules"))
        if "hard_rules" in payload:
            model.hard_rules = _string_list(payload.get("hard_rules"))

        if "guidanceNotes" in payload:
            model.guidance_notes = _string_list(payload.get("guidanceNotes"))
        if "guidance_notes" in payload:
            model.guidance_notes = _string_list(payload.get("guidance_notes"))

        if "campaignNotes" in payload:
            model.campaign_notes = _string_list(payload.get("campaignNotes"))
        if "campaign_notes" in payload:
            model.campaign_notes = _string_list(payload.get("campaign_notes"))

        existing_map = self._get_brand_intelligence_from_model(model)
        incoming_map = self._extract_brand_intelligence_map_from_payload(payload)

        merged_map = self._merge_brand_intelligence_map(
            existing=existing_map,
            incoming=incoming_map,
            flat_payload=payload,
        )

        self._apply_brand_intelligence_to_model(model, merged_map)

        model.meta.updated_at = _utc_now_iso()
        self.repository.save_model(model)

        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)
        runtime_summary.runtime_summary = dict(runtime_summary.runtime_summary or {})
        runtime_summary.runtime_summary["brand_foundation_updated_at"] = model.meta.updated_at
        runtime_summary.runtime_summary["brand_intelligence_map_updated_at"] = model.meta.updated_at
        runtime_summary.runtime_summary["generated_at"] = _utc_now_iso()
        runtime_summary.meta.updated_at = _utc_now_iso()
        self.repository.save_model(runtime_summary)

        return self.get_brand_foundation_payload(workspace_id)

    def _ensure_topology_and_boardroom_snapshot(self, workspace_id: str) -> None:
        self.rebuild_topology_and_boardroom_projection(workspace_id)

    def sync_topology_projection(
        self,
        *,
        workspace_id: str,
        topology: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)

        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)
        business_topology = BusinessTopology(**topology)
        boardroom_model = self._save_boardroom_snapshot_from_topology(
            workspace_id=workspace_id,
            topology=business_topology,
            runtime_summary=runtime_summary,
            active_zone="coo",
            selected_seat_id=None,
        )

        self._update_runtime_projection_metadata(
            runtime_summary=runtime_summary,
            workspace_id=workspace_id,
            boardroom_model=boardroom_model,
        )
        self.repository.save_model(runtime_summary)

        return {
            "ok": True,
            "workspace_id": workspace_id,
            "updated_at": boardroom_model.meta.updated_at,
            "source": "topology_projection_sync",
        }

    # -------------------------------------------------------------------------
    # Runtime summary container
    # -------------------------------------------------------------------------

    def _ensure_operational_runtime_summary_container(
        self,
        workspace_id: str,
    ) -> OperationalRuntimeSummaryContainer:
        try:
            existing = self.repository.load_operational_runtime_summary(workspace_id)
            if not isinstance(existing.dashboard_summary, dict):
                existing.dashboard_summary = {}
            if not isinstance(existing.marketing_summary, dict):
                existing.marketing_summary = {}
            if not isinstance(existing.runtime_summary, dict):
                existing.runtime_summary = {}

            existing.runtime_summary.setdefault("workspace_id", workspace_id)
            existing.runtime_summary.setdefault("sync_mode", "local_primary")
            existing.runtime_summary.setdefault("boardroom_summary", {})
            existing.runtime_summary["generated_at"] = _utc_now_iso()
            existing.meta.updated_at = _utc_now_iso()
            self.repository.save_model(existing)
            return existing
        except FileNotFoundError:
            model = OperationalRuntimeSummaryContainer(
                id=f"{workspace_id}.operational_runtime_summary",
                workspace_id=workspace_id,
                meta=BusinessContainerMeta(
                    workspace_id=workspace_id,
                    container_key="operational_runtime_summary",
                    updated_at=_utc_now_iso(),
                ),
                dashboard_summary={},
                marketing_summary={},
                runtime_summary={
                    "workspace_id": workspace_id,
                    "sync_mode": "local_primary",
                    "boardroom_summary": {},
                    "generated_at": _utc_now_iso(),
                },
            )
            self.repository.save_model(model)
            return model

    # -------------------------------------------------------------------------
    # Public reads
    # -------------------------------------------------------------------------

    def get_boardroom_payload(
        self,
        workspace_id: str,
        *,
        active_zone: str = "coo",
        selected_seat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)

        try:
            boardroom_container = self.repository.load_boardroom_snapshot(workspace_id)
        except FileNotFoundError:
            self.rebuild_topology_and_boardroom_projection(workspace_id)
            boardroom_container = self.repository.load_boardroom_snapshot(workspace_id)

        payload = dict(boardroom_container.boardroom or {})
        payload.setdefault("workspace_id", workspace_id)
        payload["active_zone"] = active_zone or payload.get("active_zone") or "coo"
        payload["selected_seat_id"] = (
            selected_seat_id if selected_seat_id is not None else payload.get("selected_seat_id")
        )
        payload["topology"] = dict(boardroom_container.topology or {})
        payload["runtime"] = _deepcopy_dict(payload.get("runtime"))
        return payload

    def get_topology_payload(self, workspace_id: str) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)

        try:
            boardroom_container = self.repository.load_boardroom_snapshot(workspace_id)
        except FileNotFoundError:
            self.rebuild_topology_and_boardroom_projection(workspace_id)
            boardroom_container = self.repository.load_boardroom_snapshot(workspace_id)

        return dict(boardroom_container.topology or {})

    def get_boardroom_summary_projection(self, workspace_id: str) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)
        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)
        runtime_payload = dict(runtime_summary.runtime_summary or {})

        if not isinstance(runtime_payload.get("boardroom_summary"), dict) or not runtime_payload.get(
            "boardroom_summary"
        ):
            self.rebuild_topology_and_boardroom_projection(workspace_id)
            runtime_summary = self.repository.load_operational_runtime_summary(workspace_id)
            runtime_payload = dict(runtime_summary.runtime_summary or {})

        return {"summary": dict(runtime_payload.get("boardroom_summary") or {})}

    def get_surface_read_contracts(self, workspace_id: str) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)
        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)

        return {
            "workspace_id": workspace_id,
            "surfaces": {
                "dashboard": {
                    "reads_from": "operational_runtime_summary.dashboard_summary",
                    "truth_inputs": [
                        "business_identity",
                        "boardroom_snapshot",
                        "operational_runtime_summary",
                    ],
                    "projection_only": True,
                },
                "marketing_stream": {
                    "reads_from": "operational_runtime_summary.marketing_summary",
                    "truth_inputs": [
                        "brand_foundation",
                        "operational_runtime_summary",
                    ],
                    "projection_only": True,
                },
                "brand_foundation": {
                    "reads_from": "brand_foundation",
                    "truth_inputs": ["brand_foundation"],
                    "projection_only": False,
                },
                "boardroom": {
                    "reads_from": "boardroom_snapshot.boardroom + boardroom_snapshot.boardroom.runtime",
                    "truth_inputs": [
                        "business_identity",
                        "business_structure",
                        "boardroom_snapshot",
                        "operational_runtime_summary",
                    ],
                    "projection_only": True,
                },
                "operations_flow": {
                    "reads_from": "boardroom_snapshot.boardroom + operational_runtime_summary.runtime_summary.boardroom_summary",
                    "truth_inputs": [
                        "boardroom_snapshot",
                        "operational_runtime_summary",
                    ],
                    "projection_only": True,
                },
                "local_node": {
                    "reads_from": "operational_runtime_summary.dashboard_summary + operational_runtime_summary.runtime_summary",
                    "truth_inputs": [
                        "operational_runtime_summary",
                        "boardroom_snapshot",
                        "business_identity",
                    ],
                    "projection_only": True,
                },
            },
            "runtime_summary_updated_at": runtime_summary.meta.updated_at,
            "updated_at": _utc_now_iso(),
        }

    # -------------------------------------------------------------------------
    # Marketing / brand updates
    # -------------------------------------------------------------------------

    def record_marketing_intent(
        self,
        *,
        workspace_id: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)

        brand = self.repository.load_brand_foundation(workspace_id)
        strategy = payload.get("marketing_strategy") or {}
        notes = payload.get("department_notes") or {}

        if strategy.get("objective") is not None:
            brand.objective = strategy.get("objective")
        if strategy.get("funnel_goal") is not None:
            brand.funnel_goal = strategy.get("funnel_goal")
        if strategy.get("target_audience") is not None:
            brand.target_audience = strategy.get("target_audience")
        if strategy.get("persona") is not None:
            brand.persona = strategy.get("persona")
        if strategy.get("offer") is not None:
            brand.offer = strategy.get("offer")

        if strategy.get("channels") is not None:
            brand.channels = _string_list(strategy.get("channels"))
        if strategy.get("hashtags") is not None:
            brand.hashtags = _string_list(strategy.get("hashtags"))
        if strategy.get("keywords") is not None:
            brand.keywords = _string_list(strategy.get("keywords"))

        if notes.get("hard_rules") is not None:
            brand.hard_rules = _string_list(notes.get("hard_rules"))
        if notes.get("guidance_notes") is not None:
            brand.guidance_notes = _string_list(notes.get("guidance_notes"))
        if notes.get("campaign_notes") is not None:
            brand.campaign_notes = _string_list(notes.get("campaign_notes"))

        existing_map = self._get_brand_intelligence_from_model(brand)

        incoming_map = (
            payload.get("brandIntelligenceMap")
            or payload.get("brand_intelligence_map")
            or payload.get("brandMap")
            or payload.get("brand_map")
            or strategy.get("brandIntelligenceMap")
            or strategy.get("brand_intelligence_map")
            or strategy.get("brandMap")
            or strategy.get("brand_map")
            or {}
        )

        merged_map = self._merge_brand_intelligence_map(
            existing=existing_map,
            incoming=incoming_map if isinstance(incoming_map, dict) else {},
            flat_payload={
                "objective": strategy.get("objective"),
                "funnel_goal": strategy.get("funnel_goal"),
                "target_audience": strategy.get("target_audience"),
                "persona": strategy.get("persona"),
                "offer": strategy.get("offer"),
                "channels": strategy.get("channels"),
                "hashtags": strategy.get("hashtags"),
                "keywords": strategy.get("keywords"),
                "hard_rules": notes.get("hard_rules"),
                "guidance_notes": notes.get("guidance_notes"),
                "campaign_notes": notes.get("campaign_notes"),
            },
        )

        self._apply_brand_intelligence_to_model(brand, merged_map)

        brand.meta.updated_at = _utc_now_iso()
        self.repository.save_model(brand)

        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)
        marketing_summary = dict(runtime_summary.marketing_summary or {})
        marketing_summary["latest_intent"] = {
            "brief": payload.get("brief"),
            "marketing_strategy": deepcopy(strategy),
            "department_notes": deepcopy(notes),
            "brandIntelligenceMap": deepcopy(merged_map),
            "brand_intelligence_map": deepcopy(merged_map),
            "require_approval": bool(payload.get("require_approval")),
            "updated_at": _utc_now_iso(),
        }

        runtime_summary.marketing_summary = marketing_summary
        runtime_summary.runtime_summary = dict(runtime_summary.runtime_summary or {})
        runtime_summary.runtime_summary["brand_foundation_updated_at"] = brand.meta.updated_at
        runtime_summary.runtime_summary["brand_intelligence_map_updated_at"] = brand.meta.updated_at
        runtime_summary.runtime_summary["generated_at"] = _utc_now_iso()
        runtime_summary.meta.updated_at = _utc_now_iso()
        self.repository.save_model(runtime_summary)

        return {
            "ok": True,
            "workspace_id": workspace_id,
            "updated_at": brand.meta.updated_at,
        }

    # -------------------------------------------------------------------------
    # Summary projections
    # -------------------------------------------------------------------------

    def build_marketing_stream_summary(
        self,
        *,
        workspace_id: str,
        queue_items: List[Dict[str, Any]],
        approvals: List[Dict[str, Any]],
        fallback_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)

        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)
        brand = self._load_brand_foundation(workspace_id)

        summary = dict(fallback_summary or {})
        prior = dict(runtime_summary.marketing_summary or {})
        latest_intent = prior.get("latest_intent") or {}

        brand_intelligence_map = self._get_brand_intelligence_from_model(brand)

        summary["brand_foundation"] = {
            "objective": brand.objective,
            "funnelGoal": brand.funnel_goal,
            "funnel_goal": brand.funnel_goal,

            "targetAudience": brand.target_audience,
            "target_audience": brand.target_audience,

            "persona": brand.persona,
            "offer": brand.offer,

            "channels": list(brand.channels or []),
            "hashtags": list(brand.hashtags or []),
            "keywords": list(brand.keywords or []),

            "hardRules": list(brand.hard_rules or []),
            "hard_rules": list(brand.hard_rules or []),

            "guidanceNotes": list(brand.guidance_notes or []),
            "guidance_notes": list(brand.guidance_notes or []),

            "campaignNotes": list(brand.campaign_notes or []),
            "campaign_notes": list(brand.campaign_notes or []),

            "brandIntelligenceMap": brand_intelligence_map,
            "brand_intelligence_map": brand_intelligence_map,
            "brandMap": brand_intelligence_map,
            "brand_map": brand_intelligence_map,

            "updatedAt": brand.meta.updated_at,
            "updated_at": brand.meta.updated_at,
        }
        summary["counts"] = {
            "total": len(queue_items),
            "queued": sum(1 for item in queue_items if item.get("status") == "queued"),
            "running": sum(1 for item in queue_items if item.get("status") == "running"),
            "waiting_approval": sum(
                1 for item in queue_items if item.get("status") == "waiting_approval"
            ),
            "completed": sum(1 for item in queue_items if item.get("status") == "completed"),
            "failed": sum(1 for item in queue_items if item.get("status") == "failed"),
            "cancelled": sum(1 for item in queue_items if item.get("status") == "cancelled"),
        }
        summary["runs"] = list(queue_items[:30])
        summary["pending_approvals"] = [
            item for item in approvals if item.get("status") == "pending"
        ][:20]
        summary["resolved_approvals"] = [
            item for item in approvals if item.get("status") != "pending"
        ][:20]

        if latest_intent:
            summary["latest_intent"] = latest_intent
            if latest_intent.get("brief") and not summary.get("brief"):
                summary["brief"] = latest_intent.get("brief")

        summary["generated_at"] = _utc_now_iso()

        runtime_summary.marketing_summary = summary
        runtime_summary.runtime_summary = dict(runtime_summary.runtime_summary or {})
        runtime_summary.runtime_summary["generated_at"] = summary["generated_at"]
        runtime_summary.meta.updated_at = summary["generated_at"]
        self.repository.save_model(runtime_summary)

        return {"summary": summary}

    def build_dashboard_summary(
        self,
        *,
        workspace_id: str,
        control: Dict[str, Any],
        health: Dict[str, Any],
        scheduler: Dict[str, Any],
        queue_items: List[Dict[str, Any]],
        approvals: List[Dict[str, Any]],
        audit_items: List[Dict[str, Any]],
        fallback_summary: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)

        try:
            boardroom = self.repository.load_boardroom_snapshot(workspace_id)
        except FileNotFoundError:
            self.rebuild_topology_and_boardroom_projection(workspace_id)
            boardroom = self.repository.load_boardroom_snapshot(workspace_id)

        identity = self.repository.load_business_identity(workspace_id)
        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)

        summary = dict(fallback_summary or {})
        boardroom_payload = dict(boardroom.boardroom or {})
        departments = boardroom_payload.get("departments") or []
        pulse = boardroom_payload.get("pulse") or {}
        center = boardroom_payload.get("center") or {}
        runtime_block = _deepcopy_dict(boardroom_payload.get("runtime"))

        queue_counts = {
            "queued": sum(1 for item in queue_items if item.get("status") == "queued"),
            "running": sum(1 for item in queue_items if item.get("status") == "running"),
            "waiting_approval": sum(
                1 for item in queue_items if item.get("status") == "waiting_approval"
            ),
            "completed": sum(1 for item in queue_items if item.get("status") == "completed"),
            "failed": sum(1 for item in queue_items if item.get("status") == "failed"),
            "cancelled": sum(1 for item in queue_items if item.get("status") == "cancelled"),
        }
        approval_counts = {
            "pending": sum(1 for item in approvals if item.get("status") == "pending"),
            "approved": sum(1 for item in approvals if item.get("status") == "approved"),
            "rejected": sum(1 for item in approvals if item.get("status") == "rejected"),
        }

        summary["workspace"] = {
            "workspace_id": workspace_id,
            "name": identity.trading_name or identity.legal_name or workspace_id,
            "business_type": identity.business_type,
            "industry": identity.sector,
            "currency": identity.currency,
            "timezone": identity.timezone,
            "node_id": control.get("node_id"),
            "deployment_mode": control.get("deployment_mode") or "local_first",
            "sync_mode": "local_primary",
        }
        summary["node"] = {
            "status": control.get("status", "unknown"),
            "started_at": health.get("started_at"),
        }
        summary["health"] = {
            "lifecycle_state": (
                "healthy"
                if control.get("status") == "running"
                else control.get("status", "unknown")
            ),
            "last_heartbeat_at": health.get("last_heartbeat_at"),
            "last_error": health.get("last_error"),
        }
        summary["scheduler"] = scheduler or {}
        summary["queue"] = queue_counts
        summary["approvals"] = approval_counts
        summary["audit_event_count"] = len(audit_items)
        summary["recent_audit"] = list(audit_items[:8])
        summary["departments"] = departments
        summary["pulse"] = pulse
        summary["center"] = center
        summary["runtime"] = runtime_block
        summary["alerts"] = list(summary.get("alerts") or [])
        summary["generated_at"] = _utc_now_iso()

        runtime_summary.dashboard_summary = summary
        runtime_summary.runtime_summary = dict(runtime_summary.runtime_summary or {})
        runtime_summary.runtime_summary["generated_at"] = summary["generated_at"]
        runtime_summary.meta.updated_at = summary["generated_at"]
        self.repository.save_model(runtime_summary)

        return {"summary": summary}

    def get_dashboard_summary_projection(self, workspace_id: str) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)
        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)

        if not isinstance(runtime_summary.dashboard_summary, dict) or not runtime_summary.dashboard_summary:
            try:
                self.repository.load_boardroom_snapshot(workspace_id)
            except FileNotFoundError:
                self.rebuild_topology_and_boardroom_projection(workspace_id)
            runtime_summary = self.repository.load_operational_runtime_summary(workspace_id)

        return {"summary": dict(runtime_summary.dashboard_summary or {})}

    def get_marketing_stream_summary(self, workspace_id: str) -> Dict[str, Any]:
        self.ensure_canonical_containers(workspace_id)
        runtime_summary = self._ensure_operational_runtime_summary_container(workspace_id)
        return {"summary": dict(runtime_summary.marketing_summary or {})}