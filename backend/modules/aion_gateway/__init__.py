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
