from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Iterable, List

from .canonical import canonical_hash, utc_now_iso


class NodeRole(str, Enum):
    MOTHER = "mother"
    COMPUTE_WORKER = "compute_worker"
    EDGE = "edge"
    GATEWAY = "gateway"
    RELAY = "relay"
    OBSERVER = "observer"


class EnrollmentState(str, Enum):
    DISCOVERED = "discovered"
    ENROLLED = "enrolled"
    REVOKED = "revoked"


class CapabilityKind(str, Enum):
    OBSERVE = "observe"
    CONTROL = "control"
    COMPUTE = "compute"
    RELAY = "relay"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True, slots=True)
class Capability:
    capability_id: str
    kind: CapabilityKind
    description: str
    risk: RiskLevel = RiskLevel.LOW
    requires_approval: bool = False
    schema: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["kind"] = self.kind.value
        value["risk"] = self.risk.value
        return value


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    node_id: str
    name: str
    device_class: str
    platform: str
    cpu_count: int
    memory_bytes: int
    can_install_runtime: bool
    can_host_model: bool
    is_mains_powered: bool
    transports: tuple[str, ...] = ()
    controls: tuple[str, ...] = ()
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        value = asdict(self)
        value["transports"] = list(self.transports)
        value["controls"] = list(self.controls)
        return value

    @classmethod
    def from_dict(cls, value: Dict[str, Any]) -> "DeviceProfile":
        data = dict(value)
        data["transports"] = tuple(data.get("transports", ()))
        data["controls"] = tuple(data.get("controls", ()))
        return cls(**data)


def select_role(
    profile: DeviceProfile,
    *,
    mother_present: bool,
    prefer_mother: bool = False,
) -> NodeRole:
    """Select a conservative initial role from measurable device properties."""
    capable_host = (
        profile.can_install_runtime
        and profile.can_host_model
        and profile.cpu_count >= 4
        and profile.memory_bytes >= 4 * 1024**3
    )
    if capable_host and (prefer_mother or not mother_present):
        return NodeRole.MOTHER
    if capable_host:
        return NodeRole.COMPUTE_WORKER
    if not profile.can_install_runtime:
        return NodeRole.GATEWAY
    if profile.controls:
        return NodeRole.EDGE
    if profile.transports:
        return NodeRole.RELAY
    return NodeRole.OBSERVER


@dataclass(slots=True)
class NodeRecord:
    profile: DeviceProfile
    role: NodeRole
    public_key: str
    enrollment: EnrollmentState = EnrollmentState.DISCOVERED
    mother_id: str | None = None
    last_seen_at: str = field(default_factory=utc_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile": self.profile.to_dict(),
            "role": self.role.value,
            "public_key": self.public_key,
            "enrollment": self.enrollment.value,
            "mother_id": self.mother_id,
            "last_seen_at": self.last_seen_at,
        }


@dataclass(slots=True)
class CapabilityCapsule:
    capsule_id: str
    issuer_node_id: str
    subject_node_id: str
    capabilities: List[Dict[str, Any]]
    issued_at: str
    expires_at: str | None
    policy_version: str
    payload_hash: str = ""
    signature: str = ""

    def unsigned_dict(self) -> Dict[str, Any]:
        return {
            "capsule_id": self.capsule_id,
            "issuer_node_id": self.issuer_node_id,
            "subject_node_id": self.subject_node_id,
            "capabilities": self.capabilities,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "policy_version": self.policy_version,
        }

    def seal_hash(self) -> str:
        self.payload_hash = canonical_hash(self.unsigned_dict())
        return self.payload_hash

    def to_dict(self) -> Dict[str, Any]:
        return {**self.unsigned_dict(), "payload_hash": self.payload_hash, "signature": self.signature}


def validate_capabilities(capabilities: Iterable[Capability]) -> List[Capability]:
    result = list(capabilities)
    seen: set[str] = set()
    for capability in result:
        if not capability.capability_id or capability.capability_id in seen:
            raise ValueError("Capability IDs must be non-empty and unique")
        seen.add(capability.capability_id)
        if capability.risk is RiskLevel.HIGH and not capability.requires_approval:
            raise ValueError("High-risk capabilities must require explicit approval")
    return result
