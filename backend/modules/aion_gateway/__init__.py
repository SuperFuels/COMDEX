from backend.modules.aion_gateway.contracts import (
    GatewayPreviewResult,
    NormalizedInboundIntent,
    FulfilmentJobPreview,
)
from backend.modules.aion_gateway.inbound_gateway import (
    preview_inbound_gateway_intent,
    stable_intent_hash,
)
from backend.modules.aion_gateway.fulfilment_job import (
    FULFILMENT_JOB_SCHEMA_VERSION,
    FULFILMENT_JOB_STATES,
    build_fulfilment_job_core_preview,
    stable_job_preview_hash,
)

__all__ = [
    "build_agentmap_dashboard_summary",
    "build_agentmap_dashboard_preview",
    "DASHBOARD_VERSION",
    "build_public_intent_gateway_summary",
    "build_public_intent_gateway_preview",
    "PublicIntentGatewayRequest",
    "PublicIntentGatewayPreview",
    "PUBLIC_INTENT_GATEWAY_VERSION",
    "build_a2a_proof_bundle_summary",
    "build_a2a_proof_bundle_preview",
    "build_a2a_proof_receipt_preview",
    "build_a2a_proof_commitment_preview",
    "A2A_PROOF_RECEIPT_VERSION",
    "build_a2a_job_evidence_settlement_bundle",
    "build_a2a_settlement_readiness_preview",
    "build_a2a_job_evidence_preview",
    "A2A_JOB_EVIDENCE_SETTLEMENT_VERSION",
    "validate_a2a_job_request_preview",
    "build_a2a_job_request_trace_bundle",
    "build_a2a_job_trace_preview",
    "build_a2a_job_request_preview",
    "A2A_JOB_TRACE_VERSION",
    "GatewayPreviewResult",
    "NormalizedInboundIntent",
    "FulfilmentJobPreview",
    "stable_intent_hash",
    "preview_inbound_gateway_intent",
    "FULFILMENT_JOB_SCHEMA_VERSION",
    "FULFILMENT_JOB_STATES",
    "build_fulfilment_job_core_preview",
    "stable_job_preview_hash",
]

from backend.modules.aion_gateway.a2a_contracts import (
    A2A_CONTRACT_SCHEMA_VERSION,
    CapabilityContract,
    AvailabilityContract,
    QuoteContract,
    ExecutionContract,
    TraceContract,
    EvidenceContract,
    ExceptionContract,
    SettlementReadinessContract,
    ProofCommitmentContract,
    build_empty_a2a_contract_bundle,
    stable_contract_hash,
)

from backend.modules.aion_gateway.evidence import (
    EvidenceItem,
    build_evidence_item,
    build_job_proof_hash,
    hash_evidence_item,
)

from backend.modules.aion_gateway.machine_trace import (
    A2A_TRACE_SCHEMA_VERSION,
    MachineA2ATrace,
    build_machine_a2a_trace,
)

from backend.modules.aion_gateway.settlement_readiness import (
    SETTLEMENT_SCHEMA_VERSION,
    SETTLEMENT_STATES,
    PAYMENT_MODES,
    SettlementReadiness,
    build_settlement_readiness,
    stable_fiat_payment_reference_hash,
)

from backend.modules.aion_gateway.glyphchain_proof_commit import (
    PROOF_PROTOCOL_VERSION,
    AION_JOB_PROOF_V1,
    AION_EVIDENCE_PROOF_V1,
    AION_SETTLEMENT_READINESS_PROOF_V1,
    build_aion_proof_envelope,
    preview_glyphchain_proof_commit,
    preview_job_proof_commit,
    verify_aion_proof_commitment,
)

try:
    from .agent_channels import (
        AGENT_CHANNEL_PROTOCOL_VERSION,
        SUPPORTED_AGENT_CHANNELS,
        AgentChannel,
        AgentInboxMessage,
        AgentChannelRoutingResult,
        list_agent_channels,
        build_agent_inbox_message,
        preview_agent_channel_message,
    )
except Exception:
    pass


from backend.modules.aion_gateway.exceptions import (
    EXCEPTION_CONTRACT_VERSION,
    SUPPORTED_EXCEPTION_TYPES,
    SUPPORTED_RECOVERY_ACTIONS,
    DEFAULT_ACTIONS_BY_EXCEPTION_TYPE,
    FulfilmentException,
    ExceptionRecoveryAction,
    ExceptionRecoveryPreview,
    build_exception_recovery_preview,
    build_exception_state_for_machine_trace,
    example_home_fixed_exception_preview,
)


from backend.modules.aion_gateway.home_fixed_vertical import (
    HOME_FIXED_VERTICAL_VERSION,
    build_home_fixed_parallel_profile,
    build_home_fixed_machine_catalog,
    build_home_fixed_machine_cart_request,
    build_home_fixed_quote_preview,
    build_home_fixed_fulfilment_job_preview,
    build_home_fixed_provider_assignment_preview,
    build_home_fixed_job_timeline_preview,
    build_home_fixed_evidence_completion_preview,
    build_home_fixed_settlement_readiness_preview,
    build_home_fixed_job_proof_hash,
    build_home_fixed_machine_trace_preview,
    run_home_fixed_vertical_dry_run,
)

from backend.modules.aion_gateway.boardroom_parallel_twin_payload import (
    BOARDROOM_PARALLEL_TWIN_PAYLOAD_VERSION,
    build_boardroom_parallel_twin_payload,
    build_boardroom_parallel_twin_summary,
)

from backend.modules.aion_gateway.trust_reputation import (
    TRUST_REPUTATION_VERSION,
    BusinessTrustSummary,
    build_business_trust_summary,
    build_home_fixed_trust_summary_fixture,
)

from backend.modules.aion_gateway.a2a_api import (
    A2A_API_VERSION,
    A2A_ALLOWED_PREVIEW_ENDPOINTS,
    A2AEndpointPreview,
    build_a2a_endpoint_preview,
    build_guarded_a2a_namespace_preview,
    build_a2a_namespace_summary,
)

from backend.modules.aion_gateway.a2a_capabilities import (
    A2A_CAPABILITIES_VERSION,
    build_a2a_capabilities_catalog_bundle,
    build_business_capabilities_preview,
    build_business_machine_catalog_preview,
)

from backend.modules.aion_gateway.a2a_availability_quote import (
    A2A_AVAILABILITY_QUOTE_VERSION,
    build_a2a_availability_quote_bundle,
    build_business_availability_preview,
    build_machine_cart_quote_request_preview,
    validate_machine_cart_quote_request_preview,
)

from .a2a_job_trace import (
    A2A_JOB_TRACE_VERSION,
    build_a2a_job_request_preview,
    build_a2a_job_trace_preview,
    build_a2a_job_request_trace_bundle,
    validate_a2a_job_request_preview,
)

from .a2a_job_evidence_settlement import (
    A2A_JOB_EVIDENCE_SETTLEMENT_VERSION,
    build_a2a_job_evidence_preview,
    build_a2a_settlement_readiness_preview,
    build_a2a_job_evidence_settlement_bundle,
)

from backend.modules.aion_gateway.a2a_proof_receipt import (
    A2A_PROOF_RECEIPT_VERSION,
    build_a2a_proof_commitment_preview,
    build_a2a_proof_receipt_preview,
    build_a2a_proof_bundle_preview,
    build_a2a_proof_bundle_summary,
)

from .a2a_trust_summary import (
    A2A_TRUST_SUMMARY_CONTRACT_VERSION,
    build_a2a_trust_summary_endpoint_preview,
    build_a2a_trust_summary_endpoint_summary,
)

from .a2a_well_known_discovery import (
    A2A_WELL_KNOWN_DISCOVERY_VERSION,
    A2A_WELL_KNOWN_PATHS,
    ACCEPTED_PROTOCOLS,
    A2AWellKnownDiscoveryPreview,
    build_well_known_discovery_preview,
    build_well_known_discovery_summary,
)

from .a2a_handshake_preview import (
    A2A_HANDSHAKE_PREVIEW_VERSION,
    build_a2a_handshake_preview,
    build_a2a_quote_negotiation_preview,
    build_a2a_live_status_polling_preview,
    build_a2a_handshake_preview_bundle,
    build_a2a_handshake_preview_summary,
)


from .public_intent_gateway import (
    PUBLIC_INTENT_GATEWAY_VERSION,
    PublicIntentGatewayPreview,
    PublicIntentGatewayRequest,
    build_public_intent_gateway_preview,
    build_public_intent_gateway_summary,
)


from .public_widget_request_mapping import (
    PUBLIC_WIDGET_REQUEST_MAPPING_VERSION,
    build_public_widget_request_mapping_preview,
    build_public_widget_request_mapping_summary,
)

from .public_embed_guard_envelope import (

    PUBLIC_EMBED_GUARD_ENVELOPE_VERSION,

    SUPPORTED_WIDGET_SOURCES,

    build_public_embed_guard_envelope_preview,

    build_public_embed_guard_envelope_summary,

)


from .public_embed_human_review_handoff import (
    PUBLIC_EMBED_HUMAN_REVIEW_HANDOFF_VERSION,
    SUPPORTED_REVIEW_DECISIONS,
    build_public_embed_human_review_handoff_preview,
    build_public_embed_human_review_handoff_summary,
)

from .universal_vertical_adapter import UNIVERSAL_VERTICAL_ADAPTER_VERSION, build_home_fixed_universal_vertical_adapter, build_universal_vertical_adapter_contract, build_universal_vertical_adapter_summary


from .agentmap_discovery_endpoint import (
    AGENTMAP_DISCOVERY_ENDPOINT_VERSION,
    CANONICAL_AGENTMAP_PATH,
    WELL_KNOWN_AGENTMAP_PATH,
    build_agentmap_discovery_endpoint_preview,
    build_agentmap_discovery_endpoint_summary,
)


from .agentmap_live_verification import (
    VERIFICATION_VERSION,
    build_agentmap_live_verification_preview,
    build_agentmap_live_verification_summary,
)

from .agentmap_synthetic_agent_simulation import (
    SIMULATION_VERSION,
    build_synthetic_inbound_agent_simulation_preview,
    build_synthetic_inbound_agent_simulation_summary,
)

from .agentmap_human_review_simulation_bridge import (
    BRIDGE_VERSION,
    build_agentmap_human_review_simulation_bridge_preview,
    build_agentmap_human_review_simulation_bridge_summary,
)

from .agentmap_dashboard import (
    DASHBOARD_VERSION,
    build_agentmap_dashboard_preview,
    build_agentmap_dashboard_summary,
)
