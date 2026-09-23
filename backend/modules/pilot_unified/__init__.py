"""Versioned contracts for the unified Pilot mobile product.

This package is an adapter boundary. It does not replace the authoritative
stores owned by Pilot Fabric, GlyphNet, or Boardroom.
"""

from .contracts import (
    CONTRACT_VERSION,
    ActionProposal,
    ActionReceipt,
    ActionState,
    ActiveContext,
    ApprovalRecord,
    AttachmentRef,
    CapabilityLease,
    Conversation,
    DeviceRef,
    ExecutionRecord,
    Invitation,
    InvitationState,
    MemoryItemRef,
    Membership,
    MessageEnvelope,
    MessageKind,
    Participant,
    PersonRef,
    PossessionProof,
    PrivacyLevel,
    ServiceConnectionRef,
    SpaceKind,
    SpaceRef,
    SurfaceManifest,
)
from .pairing import MobilePairingAuthority
from .pairing_service import MobilePairingService
from .inbox import UnifiedInbox
from .inbox_live_service import UnifiedInboxLiveService
from .personal import PersonalPilotProjection
from .workspace_gateway import AionBoardroomWorkspaceProvider, ProviderIndependentWorkspaceGateway, WorkspaceBinding, WorkspaceProvider
from .shared_surface import SharedSurfaceManifestAuthority
from .proof_rail import ExistingGlyphChainProofPublisher, SelectiveProofRail
from .ownership import DEPLOYMENT_PROFILES, MotherOwnershipAuthority
from .native_mobile import NativeMobileSecurityAuthority
from .communication_sessions import CommunicationSessionAuthority
from .wave_transport import OptionalWaveTransport
from .adoption import TrustedNetworkAuthority
from .handoff import HANDOFF_TYPES, TrustedHandoffAuthority
from .opaque_relay import OpaqueRelayRouteAuthority, OpaqueRelayStore
from .self_hosted_relay import SelfHostedOpaqueRelayService

__all__ = [
    "CONTRACT_VERSION",
    "ActionProposal",
    "ActionReceipt",
    "ActionState",
    "ActiveContext",
    "ApprovalRecord",
    "AttachmentRef",
    "CapabilityLease",
    "Conversation",
    "DeviceRef",
    "ExecutionRecord",
    "Invitation",
    "InvitationState",
    "MemoryItemRef",
    "Membership",
    "MessageEnvelope",
    "MessageKind",
    "Participant",
    "PersonRef",
    "PossessionProof",
    "PrivacyLevel",
    "ServiceConnectionRef",
    "SpaceKind",
    "SpaceRef",
    "SurfaceManifest",
    "MobilePairingAuthority",
    "MobilePairingService",
    "UnifiedInbox",
    "UnifiedInboxLiveService",
    "PersonalPilotProjection",
    "ProviderIndependentWorkspaceGateway",
    "AionBoardroomWorkspaceProvider",
    "WorkspaceBinding",
    "WorkspaceProvider",
    "SharedSurfaceManifestAuthority",
    "ExistingGlyphChainProofPublisher",
    "SelectiveProofRail",
    "DEPLOYMENT_PROFILES",
    "MotherOwnershipAuthority",
    "NativeMobileSecurityAuthority",
    "CommunicationSessionAuthority",
    "OptionalWaveTransport",
    "TrustedNetworkAuthority",
    "HANDOFF_TYPES",
    "TrustedHandoffAuthority",
    "OpaqueRelayRouteAuthority",
    "OpaqueRelayStore",
    "SelfHostedOpaqueRelayService",
]
