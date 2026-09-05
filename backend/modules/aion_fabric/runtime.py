from __future__ import annotations

import os
import json
import platform
import re
import socket
import threading
import time
import urllib.parse
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Dict, Iterable
from uuid import uuid4

from .canonical import canonical_bytes, canonical_hash, utc_now_iso
from .contracts import (
    Capability,
    CapabilityKind,
    CapabilityCapsule,
    DeviceProfile,
    EnrollmentState,
    NodeRecord,
    NodeRole,
    RiskLevel,
    select_role,
    validate_capabilities,
)
from .delta import DeltaPacket, GlyphDeltaStream, new_delta_packet
from .identity import DeviceIdentity, IdentityStore
from .store import FabricStore
from .discovery import DiscoveryRun, SafeDiscoveryEngine, profile_from_observation
from .field_operator import FieldActionProposal, GovernedFieldOperator
from .schema import DeviceSchemaResolver
from .probe import ReadOnlyProbeReceipt, UpnpProbeRejected, UpnpReadOnlyProbeAdapter, default_probe_arguments
from .webos import WebOsGateway, WebOsIntegrationReceipt, WebOsPairingReceipt
from .voice import parse_voice_intent
from .autopilot import TVAutopilot
from .comdex_bridge import ReadOnlyComdexBridge
from .research import AionTVResearch
from .agent import AionTVAgent
from .planning import AionObjectivePlanner
from .perception import PhoneVisualPerception
from .navigation import PhoneVerifiedNavigation
from .conversation import ConversationMemory
from .entertainment import EntertainmentIntelligence
from .household import HouseholdIdentityRegistry, UniversalNodeAuthority
from .services import ServiceExecutionHub
from .education import EducationLearningCentre
from .live_context import LiveContextStore
from .moments import PilotMomentStore
from .screen_fusion import ScreenUnderstandingFusion
from .provider_metadata import ProviderMetadataResolver
from .observer import ExplicitObserverSessions
from .live_news import LiveNewsIntelligence
from .scene_explanation import SpoilerAwareSceneExplanation
from .live_translation import LocalLiveTranslation
from .sports import LiveSportsInterpreter
from .private_saves import PrivateProgrammeSaves
from .live_events import LiveEventIntelligence
from .live_engagement import HouseholdLiveEngagement
from .fact_check_benchmark import LiveFactCheckBenchmark
from .live_media_authority import LiveMediaAuthority
from .contextual_companion import ContextualCompanion
from .saved_followthrough import SavedItemFollowThrough
from .entertainment_execution import VerifiedEntertainmentExecution
from .entertainment_personalization import PrivateEntertainmentPersonalization
from .verified_navigation import UniversalVerifiedNavigation
from .perception_timeline import MultiFrameScreenPerception
from .provider_telemetry import TrustedProviderTelemetry
from .infrared_gateway import LocalInfraredClimateGateway
from .room_routing import TelevisionRoomRouter
from .tv_reliability import TelevisionReliabilityQualification
from .programme_companion import EvidenceBackedProgrammeCompanion
from .programme_origins import ProgrammeOriginEvidence
from .gaming import GovernedGamingExperience
from .private_identity import ProductionPrivateIdentity
from .pilot_inbox import PilotInbox
from .communication import GovernedCommunication
from .calendar_planning import GovernedCalendarPlanning
from .guardian import PilotGuardian
from .google_oauth import PersonaGoogleOAuth


def _physical_memory_bytes() -> int:
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        return int(pages * page_size)
    except (AttributeError, OSError, ValueError):
        return 0


def inspect_host(node_id: str | None = None) -> DeviceProfile:
    cpu_count = os.cpu_count() or 1
    memory_bytes = _physical_memory_bytes()
    return DeviceProfile(
        node_id=node_id or f"node_{socket.gethostname().lower().replace(' ', '-')}",
        name=socket.gethostname(),
        device_class="computer",
        platform=f"{platform.system()} {platform.release()}",
        cpu_count=cpu_count,
        memory_bytes=memory_bytes,
        can_install_runtime=True,
        can_host_model=cpu_count >= 4 and memory_bytes >= 4 * 1024**3,
        is_mains_powered=True,
        transports=("local", "wifi"),
        controls=(),
        metadata={"machine": platform.machine(), "python": platform.python_version()},
    )


@dataclass(slots=True)
class AionFabricRuntime:
    base_dir: Path
    profile: DeviceProfile
    identity: DeviceIdentity
    store: FabricStore
    role: NodeRole
    _scan_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _audit_cache_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _audit_cache_value: bool | None = field(default=None, repr=False)
    _audit_cache_checked_at: float = field(default=0.0, repr=False)

    def _cached_audit_chain_valid(self, *, ttl_seconds: float = 30.0) -> bool:
        now = time.monotonic()
        if self._audit_cache_value is not None and now - self._audit_cache_checked_at < ttl_seconds:
            return self._audit_cache_value
        with self._audit_cache_lock:
            now = time.monotonic()
            if self._audit_cache_value is not None and now - self._audit_cache_checked_at < ttl_seconds:
                return self._audit_cache_value
            self._audit_cache_value = self.store.verify_audit_chain()
            self._audit_cache_checked_at = time.monotonic()
            return self._audit_cache_value

    @property
    def tv_autopilot(self) -> TVAutopilot:
        return TVAutopilot(self.base_dir)

    @property
    def comdex_bridge(self) -> ReadOnlyComdexBridge:
        return ReadOnlyComdexBridge(Path(__file__).resolve().parents[3])

    @property
    def tv_research(self) -> AionTVResearch:
        return AionTVResearch(self.base_dir)

    @property
    def tv_agent(self) -> AionTVAgent:
        return AionTVAgent(self.base_dir)

    @property
    def tv_rooms(self) -> TelevisionRoomRouter:
        return TelevisionRoomRouter(self.base_dir)

    @property
    def tv_reliability(self) -> TelevisionReliabilityQualification:
        return TelevisionReliabilityQualification(self.base_dir)

    def run_safe_tv_reliability_baseline(self) -> Dict[str, Any]:
        """Run only read-only and reversible LG checks, restoring the original volume."""
        integrated = next(
            (node for node in self.store.list_nodes() if node.enrollment is EnrollmentState.ENROLLED and node.profile.metadata.get("webos_integration") == "connected"),
            None,
        )
        if integrated is None:
            raise RuntimeError("No integrated television is available")
        host = self._refresh_webos_host(integrated)
        gateway = WebOsGateway(self.base_dir / "pairing" / "webos")
        qualification = self.tv_reliability
        cases = []
        started = time.monotonic()

        probe = gateway.probe_endpoint(host, timeout=2.0)
        cases.append(qualification.record(
            device_id=integrated.profile.node_id, adapter="lg_webos_gateway",
            area="connection_recovery", operation="paired_ssap_probe",
            outcome="verified" if probe.get("connected") else "not_verified",
            evidence_source="device_read_after_write", evidence_id=f"baseline-probe-{utc_now_iso()}",
            duration_ms=int((time.monotonic() - started) * 1000),
        ))

        observations = []
        for _ in range(3):
            receipt = gateway.execute_governed_action(
                node_id=integrated.profile.node_id, host=host, action="observe_state", arguments={}, maximum_voice_volume=50,
            )
            self.store.save_webos_action_receipt(receipt, source="section_3_safe_baseline")
            observations.append(receipt)
            cases.append(qualification.record(
                device_id=integrated.profile.node_id, adapter="lg_webos_gateway",
                area="state_observation", operation="foreground_and_audio_observation",
                outcome="verified" if receipt.verified else "not_verified",
                evidence_source="device_read_after_write", evidence_id=receipt.receipt_id,
            ))

        original = int(observations[-1].after.get("volume"))
        delta = -1 if original >= 50 else 1
        changed = gateway.execute_governed_action(
            node_id=integrated.profile.node_id, host=host, action="change_volume",
            arguments={"delta": delta}, maximum_voice_volume=50,
        )
        self.store.save_webos_action_receipt(changed, source="section_3_safe_baseline")
        restored = gateway.execute_governed_action(
            node_id=integrated.profile.node_id, host=host, action="set_volume",
            arguments={"volume": original}, maximum_voice_volume=50,
        )
        self.store.save_webos_action_receipt(restored, source="section_3_safe_baseline")
        restored_ok = bool(restored.verified and restored.after.get("volume") == original)
        for operation, receipt, outcome in (
            ("volume_step", changed, changed.verified),
            ("volume_restore", restored, restored_ok),
        ):
            cases.append(qualification.record(
                device_id=integrated.profile.node_id, adapter="lg_webos_gateway",
                area="reversible_audio", operation=operation,
                outcome="verified" if outcome else "not_verified",
                evidence_source="device_read_after_write", evidence_id=receipt.receipt_id,
            ))

        idempotency_key = f"baseline-{uuid4().hex}"
        transaction = self.verified_navigation.start(
            device_id=integrated.profile.node_id, surface="baseline", goal="observe",
            expected={"kind": "receipt_verified"}, routes=[{"route_id": "baseline.observe", "command": "observe"}],
            idempotency_key=idempotency_key,
        )
        observed_receipt = observations[-1].to_dict()
        self.verified_navigation.record_action_receipt(observed_receipt)
        duplicate = self.verified_navigation.start(
            device_id=integrated.profile.node_id, surface="baseline", goal="observe",
            expected={"kind": "receipt_verified"}, routes=[{"route_id": "baseline.observe", "command": "observe"}],
            idempotency_key=idempotency_key,
        )
        cases.append(qualification.record(
            device_id=integrated.profile.node_id, adapter="lg_webos_gateway",
            area="duplicate_suppression", operation="same_request_replay",
            outcome="verified" if duplicate.get("duplicate_suppressed") and duplicate.get("transaction_id") == transaction.get("transaction_id") else "not_verified",
            evidence_source="local_idempotency_proof", evidence_id=f"idempotency-{idempotency_key}",
        ))
        report = qualification.report(device_id=integrated.profile.node_id, adapter="lg_webos_gateway")
        self.store.append_audit("section_3_safe_baseline_completed", {
            "node_id": integrated.profile.node_id,
            "cases": len(cases),
            "verified": sum(item.get("outcome") == "verified" for item in cases),
            "original_volume": original,
            "restored_volume": restored.after.get("volume"),
            "volume_restored": restored_ok,
            "section_3_closed": report["section_3_closed"],
        })
        return {"accepted": True, "cases": cases, "report": report, "volume_restored": restored_ok}

    @property
    def objective_planner(self) -> AionObjectivePlanner:
        return AionObjectivePlanner(self.base_dir)

    @property
    def phone_perception(self) -> PhoneVisualPerception:
        return PhoneVisualPerception(self.base_dir)

    @property
    def phone_navigation(self) -> PhoneVerifiedNavigation:
        return PhoneVerifiedNavigation(self.base_dir)

    @property
    def conversation_memory(self) -> ConversationMemory:
        return ConversationMemory(self.base_dir)

    @property
    def entertainment(self) -> EntertainmentIntelligence:
        return EntertainmentIntelligence(self.base_dir, researcher=self.tv_research)

    @property
    def entertainment_personalization(self) -> PrivateEntertainmentPersonalization:
        return PrivateEntertainmentPersonalization(self.base_dir)

    @property
    def household(self) -> HouseholdIdentityRegistry:
        return HouseholdIdentityRegistry(self.base_dir)

    @property
    def local_persona(self) -> Dict[str, Any]:
        return self.household.ensure_local_persona(mother_id=self.profile.node_id)

    @property
    def universal_node(self) -> UniversalNodeAuthority:
        return UniversalNodeAuthority(self.base_dir, node_id=self.profile.node_id, identity=self.identity)

    @property
    def service_hub(self) -> ServiceExecutionHub:
        return ServiceExecutionHub(self.base_dir, household=self.household)

    @property
    def education(self) -> EducationLearningCentre:
        return EducationLearningCentre(self.base_dir)

    @property
    def gaming(self) -> GovernedGamingExperience:
        return GovernedGamingExperience(self.base_dir)

    @property
    def private_identity(self) -> ProductionPrivateIdentity:
        return ProductionPrivateIdentity(self.base_dir)

    @property
    def pilot_inbox(self) -> PilotInbox:
        return PilotInbox(self.base_dir, identities=self.private_identity)

    @property
    def communication(self) -> GovernedCommunication:
        return GovernedCommunication(self.base_dir, identities=self.private_identity, inbox=self.pilot_inbox)

    @property
    def calendar_planning(self) -> GovernedCalendarPlanning:
        return GovernedCalendarPlanning(self.base_dir, identities=self.private_identity)

    @property
    def guardian(self) -> PilotGuardian:
        return PilotGuardian(self.base_dir, identities=self.private_identity, inbox=self.pilot_inbox)

    @property
    def google_oauth(self) -> PersonaGoogleOAuth:
        return PersonaGoogleOAuth(self.base_dir, identities=self.private_identity)

    @property
    def live_context(self) -> LiveContextStore:
        return LiveContextStore(self.base_dir)

    @property
    def pilot_moments(self) -> PilotMomentStore:
        return PilotMomentStore(self.base_dir)

    @property
    def screen_understanding(self) -> ScreenUnderstandingFusion:
        return ScreenUnderstandingFusion(self.base_dir)

    @property
    def provider_metadata(self) -> ProviderMetadataResolver:
        return ProviderMetadataResolver(self.base_dir)

    @property
    def observer_sessions(self) -> ExplicitObserverSessions:
        return ExplicitObserverSessions(self.base_dir)

    @property
    def live_news(self) -> LiveNewsIntelligence:
        return LiveNewsIntelligence(self.base_dir)

    @property
    def scene_explanation(self) -> SpoilerAwareSceneExplanation:
        return SpoilerAwareSceneExplanation(self.base_dir)

    @property
    def programme_companion(self) -> EvidenceBackedProgrammeCompanion:
        return EvidenceBackedProgrammeCompanion(self.base_dir)

    @property
    def programme_origins(self) -> ProgrammeOriginEvidence:
        return ProgrammeOriginEvidence(self.base_dir)

    @property
    def live_translation(self) -> LocalLiveTranslation:
        return LocalLiveTranslation(self.base_dir)

    @property
    def live_sports(self) -> LiveSportsInterpreter:
        return LiveSportsInterpreter(self.base_dir)

    @property
    def private_saves(self) -> PrivateProgrammeSaves:
        return PrivateProgrammeSaves(self.base_dir)

    @property
    def live_events(self) -> LiveEventIntelligence:
        return LiveEventIntelligence(self.base_dir)

    @property
    def live_engagement(self) -> HouseholdLiveEngagement:
        return HouseholdLiveEngagement(self.base_dir)

    @property
    def fact_check_benchmark(self) -> LiveFactCheckBenchmark:
        return LiveFactCheckBenchmark(self.base_dir)

    @property
    def live_media_authority(self) -> LiveMediaAuthority:
        return LiveMediaAuthority(self.base_dir)

    @property
    def contextual_companion(self) -> ContextualCompanion:
        return ContextualCompanion(self.base_dir)

    @property
    def saved_followthrough(self) -> SavedItemFollowThrough:
        return SavedItemFollowThrough(self.base_dir)

    @property
    def entertainment_execution(self) -> VerifiedEntertainmentExecution:
        return VerifiedEntertainmentExecution(self.base_dir)

    @property
    def verified_navigation(self) -> UniversalVerifiedNavigation:
        return UniversalVerifiedNavigation(self.base_dir)

    @property
    def perception_timeline(self) -> MultiFrameScreenPerception:
        return MultiFrameScreenPerception(self.base_dir)

    @property
    def provider_telemetry(self) -> TrustedProviderTelemetry:
        return TrustedProviderTelemetry(self.base_dir)

    @property
    def infrared_climate(self) -> LocalInfraredClimateGateway:
        return LocalInfraredClimateGateway(self.base_dir)

    @classmethod
    def bootstrap(
        cls,
        base_dir: str | Path = ".runtime/aion_fabric",
        *,
        profile: DeviceProfile | None = None,
        prefer_mother: bool = True,
    ) -> "AionFabricRuntime":
        root = Path(base_dir)
        root.mkdir(parents=True, exist_ok=True)
        profile = profile or inspect_host()
        identity = IdentityStore(root / "identity").load_or_create()
        store = FabricStore(root / "fabric.sqlite3")
        role = select_role(profile, mother_present=False, prefer_mother=prefer_mother)
        runtime = cls(root, profile, identity, store, role)
        store.save_node(
            NodeRecord(
                profile=profile,
                role=role,
                public_key=identity.public_key_b64,
                enrollment=EnrollmentState.ENROLLED,
                mother_id=profile.node_id if role is NodeRole.MOTHER else None,
            )
        )
        runtime.reconcile_topology()
        runtime.local_persona
        store.append_audit("fabric_started", {"node_id": profile.node_id, "role": role.value})
        return runtime

    @staticmethod
    def _profile_aliases(profile: DeviceProfile) -> set[str]:
        metadata = profile.metadata
        aliases = {str(value).lower() for value in metadata.get("identity_aliases", []) if value}
        identifiers = metadata.get("identifiers", {})
        if isinstance(identifiers, dict):
            for key in ("mac", "bluetooth_address"):
                value = identifiers.get(key)
                if value:
                    aliases.add(f"{key}:{str(value).strip().lower()}")
            usn = identifiers.get("usn")
            if usn:
                aliases.add(f"usn_uuid:{str(usn).split('::', 1)[0].strip().lower()}")
        attributes = metadata.get("attributes", {})
        txt = attributes.get("txt", {}) if isinstance(attributes, dict) else {}
        if isinstance(txt, dict):
            for key in ("id", "deviceid"):
                value = txt.get(key)
                if value:
                    aliases.add(f"advertised_{key}:{str(value).strip().lower()}")
        for address in metadata.get("addresses", []):
            if address:
                aliases.add(f"address:{str(address).split('%', 1)[0].strip().lower()}")
        return aliases

    @staticmethod
    def _name_key(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", value.lower().replace("’", ""))

    def _local_addresses(self) -> set[str]:
        addresses = {"127.0.0.1", "::1"}
        try:
            addresses.update(
                item[4][0].split("%", 1)[0]
                for item in socket.getaddrinfo(socket.gethostname(), None)
            )
        except OSError:
            pass
        return addresses

    def _is_local_advertisement(self, profile: DeviceProfile) -> bool:
        if profile.node_id == self.profile.node_id:
            return True
        addresses = {
            str(value).split("%", 1)[0]
            for value in profile.metadata.get("addresses", [])
            if value
        }
        local_name = self._name_key(self.profile.name.removesuffix(".local"))
        advertised_name = self._name_key(profile.name)
        name_matches = bool(local_name and (local_name in advertised_name or advertised_name in local_name))
        platform_is_mac = "mac" in profile.platform.lower()
        local_address_matches = bool(addresses.intersection(self._local_addresses()))
        return (platform_is_mac and (name_matches or local_address_matches)) or (
            profile.device_class == "computer" and local_address_matches
        )

    def _existing_identity_match(self, profile: DeviceProfile) -> NodeRecord | None:
        aliases = self._profile_aliases(profile)
        if not aliases:
            return None
        candidates = []
        for record in self.store.list_nodes():
            if record.profile.node_id == self.profile.node_id:
                continue
            overlap = aliases.intersection(self._profile_aliases(record.profile))
            if not overlap:
                continue
            canonical_id = record.profile.metadata.get("superseded_by")
            if canonical_id:
                record = self.store.get_node(str(canonical_id)) or record
            strong = sum(not value.startswith("address:") for value in overlap)
            candidates.append((record.enrollment is EnrollmentState.ENROLLED, strong, len(overlap), record))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (-int(item[0]), -item[1], -item[2], item[3].profile.node_id))
        return candidates[0][3]

    def reconcile_topology(self) -> Dict[str, Any]:
        """Hide self-advertisements and superseded identities without deleting evidence."""
        nodes = self.store.list_nodes()
        changed: list[str] = []

        for record in nodes:
            if record.profile.node_id == self.profile.node_id or record.enrollment is EnrollmentState.ENROLLED:
                continue
            if self._is_local_advertisement(record.profile):
                metadata = {
                    **record.profile.metadata,
                    "hidden_from_topology": True,
                    "superseded_by": self.profile.node_id,
                    "reconciliation_reason": "local_mother_advertisement",
                }
                if metadata != record.profile.metadata:
                    record.profile = replace(record.profile, metadata=metadata)
                    self.store.save_node(record)
                    changed.append(record.profile.node_id)

        nodes = [
            node
            for node in self.store.list_nodes()
            if node.profile.node_id != self.profile.node_id
            and node.profile.metadata.get("reconciliation_reason") != "local_mother_advertisement"
        ]
        parent = {node.profile.node_id: node.profile.node_id for node in nodes}

        def find(node_id: str) -> str:
            while parent[node_id] != node_id:
                parent[node_id] = parent[parent[node_id]]
                node_id = parent[node_id]
            return node_id

        def union(left: str, right: str) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for index, left in enumerate(nodes):
            left_aliases = self._profile_aliases(left.profile)
            if not left_aliases:
                continue
            for right in nodes[index + 1 :]:
                overlap = left_aliases.intersection(self._profile_aliases(right.profile))
                if overlap:
                    union(left.profile.node_id, right.profile.node_id)

        groups: Dict[str, list[NodeRecord]] = {}
        for record in nodes:
            groups.setdefault(find(record.profile.node_id), []).append(record)
        for records in groups.values():
            if len(records) < 2:
                continue
            records.sort(
                key=lambda item: (
                    -int(item.enrollment is EnrollmentState.ENROLLED),
                    -int(item.profile.metadata.get("documentation_artifacts", 0)),
                    -len(item.profile.controls),
                    item.profile.node_id,
                )
            )
            canonical = records[0]
            canonical_metadata = dict(canonical.profile.metadata)
            canonical_metadata.pop("hidden_from_topology", None)
            canonical_metadata.pop("superseded_by", None)
            canonical_metadata.pop("reconciliation_reason", None)
            if canonical_metadata != canonical.profile.metadata:
                canonical.profile = replace(canonical.profile, metadata=canonical_metadata)
                self.store.save_node(canonical)
                changed.append(canonical.profile.node_id)
            for duplicate in records[1:]:
                metadata = {
                    **duplicate.profile.metadata,
                    "hidden_from_topology": True,
                    "superseded_by": canonical.profile.node_id,
                    "reconciliation_reason": "same_advertised_device",
                }
                if metadata != duplicate.profile.metadata:
                    duplicate.profile = replace(duplicate.profile, metadata=metadata)
                    self.store.save_node(duplicate)
                    changed.append(duplicate.profile.node_id)

        for record in self.store.list_nodes():
            if record.profile.metadata.get("hidden_from_topology"):
                continue
            schema = self.store.get_schema_for_node(record.profile.node_id)
            if schema is None or len(schema.controls) <= len(record.profile.controls):
                continue
            metadata = {
                **record.profile.metadata,
                "schema_id": schema.schema_id,
                "schema_confidence": schema.confidence,
                "documentation_artifacts": len(schema.documentation),
                "inferred_controls": len(schema.controls),
                "read_only_action_ids": [
                    control.action_id
                    for control in schema.controls
                    if control.risk.value == "low"
                    and control.name.lower().startswith(("get", "query", "list", "read", "browse", "search"))
                ],
            }
            advertised_platform = " ".join(
                value for value in (schema.manufacturer, schema.model_name) if value
            )
            record.profile = replace(
                record.profile,
                name=schema.friendly_name or record.profile.name,
                platform=advertised_platform or record.profile.platform,
                controls=tuple(control.name for control in schema.controls),
                metadata=metadata,
            )
            self.store.save_node(record)
            changed.append(record.profile.node_id)
        for record in self.store.list_nodes():
            integration = self.store.latest_webos_integration_receipt(record.profile.node_id)
            if integration is None or record.profile.metadata.get("webos_integration") == "connected":
                continue
            record.profile = replace(
                record.profile,
                metadata={
                    **record.profile.metadata,
                    "webos_integration": "connected",
                    "webos_connected_surfaces": integration.connected_surfaces,
                    "webos_read_errors": integration.read_errors,
                    "webos_volume_round_trip": integration.volume_round_trip,
                },
            )
            self.store.save_node(record)
            changed.append(record.profile.node_id)
        return {"changed_node_ids": changed, "preserved": True}

    def _refresh_webos_host(self, record: NodeRecord) -> str:
        """Follow a paired TV across DHCP changes using strong discovery identity evidence."""
        old_host = str(record.profile.metadata.get("webos_host") or "")
        if not old_host:
            raise ValueError("The paired LG host is unavailable")
        record_aliases = self._profile_aliases(record.profile)
        candidates: list[tuple[str, set[str]]] = []
        for observation in self.store.list_observations():
            observed_profile = profile_from_observation(observation)
            overlap = record_aliases.intersection(self._profile_aliases(observed_profile))
            if not any(not alias.startswith("address:") for alias in overlap):
                continue
            observed_hosts: list[str] = []
            for descriptor_url in observation.descriptor_urls:
                hostname = urllib.parse.urlparse(descriptor_url).hostname
                if hostname and hostname not in observed_hosts:
                    observed_hosts.append(hostname)
            for address in observation.addresses:
                try:
                    parsed = urllib.parse.urlparse(f"//{address}").hostname
                    if parsed and ":" not in parsed and parsed not in observed_hosts:
                        observed_hosts.append(parsed)
                except ValueError:
                    continue
            for host in observed_hosts:
                if not any(existing == host for existing, _ in candidates):
                    candidates.append((host, overlap))
        if not any(existing == old_host for existing, _ in candidates):
            candidates.append((old_host, set()))
        if not candidates:
            return old_host

        # Discovery records can briefly contain both the pre- and post-DHCP
        # addresses. Require a valid SSAP hello. A sleeping LG can accept TCP
        # while never completing WebSocket/WebOS negotiation, which is not a
        # usable control endpoint and must not be reported as recovered.
        selected: tuple[str, set[str]] | None = None
        candidates.sort(key=lambda item: (item[0] != old_host, -len(item[1]), item[0]))
        for host, overlap in candidates[:8]:
            try:
                WebOsGateway.probe_endpoint(host, timeout=0.6)
                selected = (host, overlap)
                break
            except Exception:
                continue
        if selected is None:
            return old_host
        new_host, overlap = selected
        if new_host == old_host:
            return old_host
        try:
            WebOsGateway(self.base_dir / "pairing" / "webos").migrate_paired_host(
                node_id=record.profile.node_id,
                old_host=old_host,
                new_host=new_host,
            )
        except FileNotFoundError:
            # The pairing file may already have moved during an overlapping
            # recovery attempt. The store update below is still authoritative.
            pass
        metadata = {
            **record.profile.metadata,
            "webos_host": new_host,
            "webos_previous_host": old_host,
            "webos_host_refreshed_at": utc_now_iso(),
            "webos_host_evidence": sorted(overlap),
        }
        record.profile = replace(record.profile, metadata=metadata)
        self.store.save_node(record)
        self.store.append_audit(
            "webos_host_refreshed",
            {
                "node_id": record.profile.node_id,
                "old_host": old_host,
                "new_host": new_host,
                "identity_evidence": sorted(overlap),
                "selection": "reachable_paired_webos_socket",
            },
        )
        return new_host

    def discover(self, profile: DeviceProfile, public_key: str) -> NodeRecord:
        """Record visibility only. Discovery never grants authority."""
        existing = self.store.get_node(profile.node_id)
        if existing is not None and existing.enrollment is EnrollmentState.ENROLLED:
            existing.profile = replace(
                profile,
                metadata={**existing.profile.metadata, **profile.metadata},
            )
            existing.last_seen_at = utc_now_iso()
            self.store.save_node(existing)
            return existing
        role = select_role(profile, mother_present=self.role is NodeRole.MOTHER)
        record = NodeRecord(profile=profile, role=role, public_key=public_key)
        self.store.save_node(record)
        return record

    def enroll(self, node_id: str, *, approved_by: str) -> NodeRecord:
        if self.role is not NodeRole.MOTHER:
            raise PermissionError("Only the active mother node can enroll devices")
        record = self.store.get_node(node_id)
        if record is None:
            raise KeyError(f"Unknown discovered node: {node_id}")
        if not approved_by.strip():
            raise ValueError("Enrollment requires a human approval identity")
        record.enrollment = EnrollmentState.ENROLLED
        record.mother_id = self.profile.node_id
        record.last_seen_at = utc_now_iso()
        self.store.save_node(record)
        self.store.append_audit("node_enrolled", {"node_id": node_id, "approved_by": approved_by})
        return record

    def issue_capabilities(
        self,
        node_id: str,
        capabilities: Iterable[Capability],
        *,
        approved_by: str,
        expires_at: str | None = None,
    ) -> CapabilityCapsule:
        if self.role is not NodeRole.MOTHER:
            raise PermissionError("Only the active mother node can issue capabilities")
        record = self.store.get_node(node_id)
        if record is None or record.enrollment is not EnrollmentState.ENROLLED:
            raise PermissionError("Capabilities require an enrolled device")
        if not approved_by.strip():
            raise ValueError("Capability issuance requires a human approval identity")
        checked = validate_capabilities(capabilities)
        capsule = CapabilityCapsule(
            capsule_id=f"cap_{uuid4().hex}",
            issuer_node_id=self.profile.node_id,
            subject_node_id=node_id,
            capabilities=[capability.to_dict() for capability in checked],
            issued_at=utc_now_iso(),
            expires_at=expires_at,
            policy_version="aion-fabric-v1",
        )
        capsule.seal_hash()
        capsule.signature = self.identity.sign(canonical_bytes(capsule.unsigned_dict()))
        self.store.save_capsule(capsule)
        self.store.append_audit("capability_approval", {"capsule_id": capsule.capsule_id, "approved_by": approved_by})
        return capsule

    def accept_delta(self, packet: DeltaPacket) -> Dict[str, Any]:
        if self.role is not NodeRole.MOTHER:
            raise PermissionError("Only the active mother node accepts authoritative deltas")
        record = self.store.get_node(packet.node_id)
        if record is None or record.enrollment is not EnrollmentState.ENROLLED:
            raise PermissionError("Delta sender is not enrolled")
        return self.store.accept_delta(packet, public_key=record.public_key)

    def accept_stream(self, stream: GlyphDeltaStream) -> Dict[str, Any]:
        if self.role is not NodeRole.MOTHER:
            raise PermissionError("Only the active mother node accepts authoritative streams")
        record = self.store.get_node(stream.node_id)
        if record is None or record.enrollment is not EnrollmentState.ENROLLED:
            raise PermissionError("Stream sender is not enrolled")
        return self.store.accept_stream(stream, public_key=record.public_key)

    def scan_devices(self, *, timeout_seconds: float = 2.5) -> Dict[str, Any]:
        """Discover advertised devices, acquire safe descriptors, and infer schemas.

        This method never enrolls a device and never sends a control request.
        """
        if self.role is not NodeRole.MOTHER:
            raise PermissionError("Only the active mother node coordinates discovery")
        with self._scan_lock:
            run = SafeDiscoveryEngine().scan(timeout_seconds=timeout_seconds)
            self.store.save_discovery_run(run)
            resolved = []
            resolver = DeviceSchemaResolver(self.base_dir / "documentation")
            for observation in run.observations:
                profile = profile_from_observation(observation)
                if self._is_local_advertisement(profile):
                    resolved.append({"ignored": "local_mother_advertisement", "observation": observation.to_dict()})
                    continue
                existing = self._existing_identity_match(profile)
                if existing is not None:
                    profile = replace(profile, node_id=existing.profile.node_id)
                record = self.discover(profile, public_key="")
                schema = resolver.resolve(record.profile.node_id, observation)
                self.store.save_schema(schema)
                schema = self.store.get_schema_for_node(record.profile.node_id) or schema
                enriched_metadata = {
                    **record.profile.metadata,
                    "schema_id": schema.schema_id,
                    "schema_confidence": schema.confidence,
                    "documentation_artifacts": len(schema.documentation),
                    "inferred_controls": len(schema.controls),
                    "control_state": "disabled_until_enrolled",
                    "read_only_action_ids": [
                        control.action_id
                        for control in schema.controls
                        if control.risk.value == "low"
                        and control.name.lower().startswith(("get", "query", "list", "read", "browse", "search"))
                    ],
                }
                advertised_platform = " ".join(
                    value for value in (schema.manufacturer, schema.model_name) if value
                )
                record.profile = replace(
                    record.profile,
                    name=schema.friendly_name or record.profile.name,
                    platform=advertised_platform or record.profile.platform,
                    controls=tuple(control.name for control in schema.controls),
                    metadata=enriched_metadata,
                )
                self.store.save_node(record)
                resolved.append(
                    {
                        "node": record.to_dict(),
                        "schema": schema.to_dict(),
                    }
                )
            reconciliation = self.reconcile_topology()
            return {
                "run": run.to_dict(),
                "resolved": resolved,
                "reconciliation": reconciliation,
                "safety": {
                    "devices_enrolled": 0,
                    "control_requests_sent": 0,
                    "credential_attempts": 0,
                    "port_scans": 0,
                },
            }

    def discovery_status(self) -> Dict[str, Any]:
        return {
            "observations": [item.to_dict() for item in self.store.list_observations()],
            "schemas": [item.to_dict() for item in self.store.list_schemas()],
        }

    def propose_field_action(
        self,
        *,
        node_id: str,
        action_id: str,
        arguments: Dict[str, Any],
    ) -> FieldActionProposal:
        schema = self.store.get_schema_for_node(node_id)
        record = self.store.get_node(node_id)
        if schema is None or record is None:
            raise KeyError("A schema-backed discovered node is required")
        proposal = GovernedFieldOperator().propose(
            schema,
            action_id=action_id,
            arguments=arguments,
            enrollment=record.enrollment,
        )
        self.store.save_action_proposal(proposal)
        return proposal

    def enroll_gateway_for_read_only_testing(
        self,
        *,
        node_id: str,
        approved_by: str,
    ) -> Dict[str, Any]:
        """Create a local gateway identity and grant only evidenced read actions."""
        if self.role is not NodeRole.MOTHER:
            raise PermissionError("Only the active mother node can enroll a gateway")
        record = self.store.get_node(node_id)
        schema = self.store.get_schema_for_node(node_id)
        if record is None or schema is None:
            raise KeyError("A discovered node with an evidenced schema is required")
        read_controls = [
            control
            for control in schema.controls
            if control.risk.value == "low"
            and control.name.lower().startswith(("get", "query", "list", "read", "browse", "search"))
        ]
        if not read_controls:
            raise ValueError("This device has no evidenced read-only actions")
        gateway_identity = IdentityStore(self.base_dir / "gateway_identities" / node_id).load_or_create()
        record.public_key = gateway_identity.public_key_b64
        self.store.save_node(record)
        enrolled = self.enroll(node_id, approved_by=approved_by)
        capabilities = [
            Capability(
                capability_id=control.action_id,
                kind=CapabilityKind.OBSERVE,
                description=f"Read-only {control.protocol} action: {control.name}",
                risk=control.risk,
                requires_approval=False,
                schema={
                    "action_name": control.name,
                    "protocol": control.protocol,
                    "endpoint": control.endpoint,
                    "arguments": control.arguments,
                    "mode": "read_only_probe",
                },
            )
            for control in read_controls
        ]
        capsule = self.issue_capabilities(
            node_id,
            capabilities,
            approved_by=approved_by,
        )
        self.store.append_audit(
            "gateway_read_only_enrollment",
            {
                "node_id": node_id,
                "approved_by": approved_by,
                "read_only_capabilities": len(capabilities),
            },
        )
        return {
            "node": enrolled.to_dict(),
            "capsule": capsule.to_dict(),
            "read_only_capabilities": len(capabilities),
            "live_mutating_capabilities": 0,
        }

    def run_read_only_probe(
        self,
        *,
        node_id: str,
        action_id: str | None = None,
    ) -> ReadOnlyProbeReceipt:
        record = self.store.get_node(node_id)
        schema = self.store.get_schema_for_node(node_id)
        capsule = self.store.latest_capsule_for_node(node_id)
        if record is None or schema is None or capsule is None:
            raise PermissionError("An enrolled device and signed capability capsule are required")
        if record.enrollment is not EnrollmentState.ENROLLED:
            raise PermissionError("The device is not enrolled")
        if capsule.payload_hash != canonical_hash(capsule.unsigned_dict()) or not DeviceIdentity.verify(
            self.identity.public_key_b64,
            canonical_bytes(capsule.unsigned_dict()),
            capsule.signature,
        ):
            raise PermissionError("The capability capsule is invalid")
        permitted_ids = {item["capability_id"] for item in capsule.capabilities}
        candidates = [
            control
            for control in schema.controls
            if control.action_id in permitted_ids
            and control.protocol == "upnp"
            and control.risk.value == "low"
        ]
        if action_id:
            candidates = [control for control in candidates if control.action_id == action_id]
        if not candidates:
            raise PermissionError("No permitted read-only UPnP action matches this request")
        preferred_names = (
            "GetCurrentConnectionIDs",
            "GetProtocolInfo",
            "GetVolume",
            "GetTransportInfo",
            "GetMediaInfo",
            "GetDeviceCapabilities",
        )
        ordered = [item for name in preferred_names for item in candidates if item.name == name]
        ordered.extend(item for item in candidates if item not in ordered)
        failures: list[str] = []
        adapter = UpnpReadOnlyProbeAdapter()
        for control in ordered:
            try:
                arguments = default_probe_arguments(control)
                receipt = adapter.execute(
                    node_id=node_id,
                    control=control,
                    arguments=arguments,
                )
                self.store.save_probe_receipt(receipt)
                if failures:
                    self.store.append_audit(
                        "read_only_probe_fallback",
                        {"node_id": node_id, "accepted_action": control.name, "rejected_actions": failures},
                    )
                return receipt
            except (UpnpProbeRejected, ValueError, OSError) as exc:
                failures.append(str(exc))
        raise PermissionError(
            "The device accepted none of its permitted read-only queries: " + "; ".join(failures)
        )

    def pair_webos_and_prove_read_only(
        self,
        *,
        node_id: str,
        approved_by: str,
    ) -> WebOsPairingReceipt:
        if self.role is not NodeRole.MOTHER:
            raise PermissionError("Only the active mother node can coordinate pairing")
        record = self.store.get_node(node_id)
        schema = self.store.get_schema_for_node(node_id)
        if record is None or schema is None or record.enrollment is not EnrollmentState.ENROLLED:
            raise PermissionError("An enrolled, schema-backed television is required")
        if "lg" not in f"{schema.manufacturer} {record.profile.platform}".lower() or "webos" not in record.profile.name.lower():
            raise ValueError("This pairing adapter is limited to discovered LG webOS televisions")
        if not approved_by.strip():
            raise ValueError("Pairing requires a human approval identity")

        descriptor_hosts = [
            urllib.parse.urlsplit(item.url).hostname
            for item in schema.documentation
            if urllib.parse.urlsplit(item.url).hostname
        ]
        address_hosts = [
            str(value).split("%", 1)[0]
            for value in record.profile.metadata.get("addresses", [])
            if value and ":" not in str(value)
        ]
        host = next(iter(descriptor_hosts or address_hosts), None)
        if not host:
            raise ValueError("No local webOS address is evidenced for this television")

        current_capsule = self.store.latest_capsule_for_node(node_id)
        existing_capabilities: list[Capability] = []
        if current_capsule is not None:
            for item in current_capsule.capabilities:
                existing_capabilities.append(
                    Capability(
                        capability_id=item["capability_id"],
                        kind=CapabilityKind(item["kind"]),
                        description=item["description"],
                        risk=RiskLevel(item["risk"]),
                        requires_approval=bool(item.get("requires_approval", False)),
                        schema=dict(item.get("schema", {})),
                    )
                )
        if not any(item.capability_id == "webos.audio.getVolume" for item in existing_capabilities):
            existing_capabilities.append(
                Capability(
                    capability_id="webos.audio.getVolume",
                    kind=CapabilityKind.OBSERVE,
                    description="Read the paired LG webOS television volume and mute state",
                    risk=RiskLevel.LOW,
                    requires_approval=False,
                    schema={
                        "protocol": "webos-ssap",
                        "uri": "ssap://audio/getVolume",
                        "mode": "read_only_pairing_proof",
                    },
                )
            )
            self.issue_capabilities(
                node_id,
                existing_capabilities,
                approved_by=approved_by,
            )

        receipt = WebOsGateway(self.base_dir / "pairing" / "webos").pair_and_prove_read_only(
            node_id=node_id,
            host=host,
        )
        self.store.save_webos_pairing_receipt(receipt)
        metadata = {
            **record.profile.metadata,
            "webos_pairing": "paired",
            "webos_read_only_proof": receipt.proof_values,
            "webos_host": host,
        }
        record.profile = replace(record.profile, metadata=metadata)
        self.store.save_node(record)
        self.store.append_audit(
            "webos_pairing_owner_approved",
            {"node_id": node_id, "approved_by": approved_by, "mutating_actions_executed": 0},
        )
        return receipt

    def expand_webos_integration(
        self,
        *,
        node_id: str,
        approved_by: str,
    ) -> WebOsIntegrationReceipt:
        """Connect broad read surfaces and run one verified reversible volume test."""
        record = self.store.get_node(node_id)
        if record is None or record.enrollment is not EnrollmentState.ENROLLED:
            raise PermissionError("An enrolled LG gateway is required")
        if record.profile.metadata.get("webos_pairing") != "paired":
            raise PermissionError("LG webOS pairing must be completed first")
        if not approved_by.strip():
            raise ValueError("Expanded integration requires a human approval identity")
        host = str(record.profile.metadata.get("webos_host") or "")
        if not host:
            raise ValueError("The paired LG host is unavailable")

        latest = self.store.latest_capsule_for_node(node_id)
        capabilities: list[Capability] = []
        if latest is not None:
            for item in latest.capabilities:
                capabilities.append(
                    Capability(
                        capability_id=item["capability_id"],
                        kind=CapabilityKind(item["kind"]),
                        description=item["description"],
                        risk=RiskLevel(item["risk"]),
                        requires_approval=bool(item.get("requires_approval", False)),
                        schema=dict(item.get("schema", {})),
                    )
                )
        observe_endpoints = {
            "webos.system.info": "system/getSystemInfo",
            "webos.power.observe": "com.webos.service.tvpower/power/getPowerState",
            "webos.audio.status": "audio/getStatus",
            "webos.audio.getVolume": "audio/getVolume",
            "webos.app.foreground": "com.webos.applicationManager/getForegroundAppInfo",
            "webos.inputs.list": "tv/getExternalInputList",
            "webos.apps.list": "com.webos.applicationManager/listLaunchPoints",
            "webos.network.observe": "com.webos.service.connectionmanager/getinfo",
            "webos.services.list": "api/getServiceList",
        }
        existing_ids = {item.capability_id for item in capabilities}
        for capability_id, endpoint in observe_endpoints.items():
            if capability_id in existing_ids:
                continue
            capabilities.append(
                Capability(
                    capability_id=capability_id,
                    kind=CapabilityKind.OBSERVE,
                    description=f"Observe paired LG webOS surface: {endpoint}",
                    risk=RiskLevel.LOW,
                    requires_approval=False,
                    schema={"protocol": "webos-ssap", "uri": f"ssap://{endpoint}"},
                )
            )
        if "webos.audio.setVolume.roundtrip" not in existing_ids:
            capabilities.append(
                Capability(
                    capability_id="webos.audio.setVolume.roundtrip",
                    kind=CapabilityKind.CONTROL,
                    description="Change LG volume by one step and restore the original value with verification",
                    risk=RiskLevel.MEDIUM,
                    requires_approval=True,
                    schema={
                        "protocol": "webos-ssap",
                        "uri": "ssap://audio/setVolume",
                        "constraint": "one_step_then_restore",
                    },
                )
            )
        self.issue_capabilities(node_id, capabilities, approved_by=approved_by)
        self.store.append_audit(
            "webos_integration_owner_approved",
            {
                "node_id": node_id,
                "approved_by": approved_by,
                "read_surfaces": sorted(observe_endpoints),
                "control_test": "volume_one_step_then_restore",
                "power_changes": 0,
                "input_changes": 0,
                "app_launches": 0,
            },
        )
        receipt = WebOsGateway(self.base_dir / "pairing" / "webos").inventory_and_volume_round_trip(
            node_id=node_id,
            host=host,
        )
        self.store.save_webos_integration_receipt(receipt)
        latest_state = {
            "volume": receipt.read_results.get("volume", {}),
            "audio": receipt.read_results.get("audio", {}),
            "power": receipt.read_results.get("power", {}),
            "foreground_app": receipt.read_results.get("foreground_app", {}),
        }
        record = self.store.get_node(node_id) or record
        record.profile = replace(
            record.profile,
            metadata={
                **record.profile.metadata,
                "webos_integration": "connected",
                "webos_connected_surfaces": receipt.connected_surfaces,
                "webos_read_errors": receipt.read_errors,
                "webos_latest_state": latest_state,
                "webos_volume_round_trip": receipt.volume_round_trip,
            },
        )
        self.store.save_node(record)
        return receipt

    def enable_voice_tv_policy(self, *, node_id: str, approved_by: str) -> Dict[str, Any]:
        record = self.store.get_node(node_id)
        if record is None or record.profile.metadata.get("webos_integration") != "connected":
            raise PermissionError("A proven LG webOS integration is required before voice control")
        latest = self.store.latest_capsule_for_node(node_id)
        capabilities: list[Capability] = []
        if latest is not None:
            for item in latest.capabilities:
                capabilities.append(
                    Capability(
                        capability_id=item["capability_id"],
                        kind=CapabilityKind(item["kind"]),
                        description=item["description"],
                        risk=RiskLevel(item["risk"]),
                        requires_approval=bool(item.get("requires_approval", False)),
                        schema=dict(item.get("schema", {})),
                    )
                )
        policy_capabilities = [
            Capability(
                capability_id="voice.webos.volume.read",
                kind=CapabilityKind.OBSERVE,
                description="Read LG TV volume after the local Pilot wake phrase",
                risk=RiskLevel.LOW,
                schema={"maximum_volume": 50, "raw_audio_retained": False},
            ),
            Capability(
                capability_id="voice.webos.volume.control",
                kind=CapabilityKind.CONTROL,
                description="Set LG TV volume from an explicit local voice command",
                risk=RiskLevel.MEDIUM,
                schema={"minimum": 0, "maximum": 50, "default_step": 2},
            ),
            Capability(
                capability_id="voice.webos.mute.control",
                kind=CapabilityKind.CONTROL,
                description="Mute or unmute LG TV from an explicit local voice command",
                risk=RiskLevel.MEDIUM,
            ),
            Capability(
                capability_id="voice.webos.media.control",
                kind=CapabilityKind.CONTROL,
                description="Play, pause or stop LG TV media from an explicit local voice command",
                risk=RiskLevel.MEDIUM,
            ),
            Capability(
                capability_id="voice.webos.input.control",
                kind=CapabilityKind.CONTROL,
                description="Switch LG TV to an explicitly named HDMI input",
                risk=RiskLevel.MEDIUM,
            ),
            Capability(
                capability_id="voice.webos.app.launch",
                kind=CapabilityKind.CONTROL,
                description="Launch an explicitly named mapped LG TV app",
                risk=RiskLevel.MEDIUM,
            ),
            Capability(
                capability_id="voice.webos.canvas.open",
                kind=CapabilityKind.CONTROL,
                description="Open a token-protected read-only AION Canvas on the paired TV",
                risk=RiskLevel.MEDIUM,
                schema={"lan_only": True, "control_endpoints_exposed": False},
            ),
            Capability(
                capability_id="voice.webos.scene.movie",
                kind=CapabilityKind.CONTROL,
                description="Launch the mapped movie app and apply the governed movie volume",
                risk=RiskLevel.MEDIUM,
                schema={"app_id": "netflix", "volume": 20, "maximum_volume": 50},
            ),
            Capability(
                capability_id="voice.webos.navigation.control",
                kind=CapabilityKind.CONTROL,
                description="Deliver bounded navigation or an installed app's advertised in-app voice intent to the paired TV",
                risk=RiskLevel.MEDIUM,
                schema={
                    "buttons": ["UP", "DOWN", "LEFT", "RIGHT", "ENTER", "BACK", "HOME"],
                    "maximum_sequence": 12,
                    "app_intents": {"netflix": "inAppVoiceIntent"},
                },
            ),
            Capability(
                capability_id="voice.web.research",
                kind=CapabilityKind.OBSERVE,
                description="Use the mother node to research a spoken request and show sanitized sourced results",
                risk=RiskLevel.LOW,
                schema={"provider_key_on_tv": False, "raw_response_retained": False, "maximum_results": 5},
            ),
            Capability(
                capability_id="voice.entertainment.research",
                kind=CapabilityKind.OBSERVE,
                description="Research current cross-service entertainment availability and preference-fit on the mother node",
                risk=RiskLevel.LOW,
                schema={"region": "ES", "services": ["Netflix", "Prime Video", "Disney+", "YouTube"], "availability_must_be_evidenced": True},
            ),
            Capability(
                capability_id="voice.entertainment.memory",
                kind=CapabilityKind.CONTROL,
                description="Remember an explicitly stated watched or avoided title in local household entertainment memory",
                risk=RiskLevel.LOW,
                schema={"outcomes": ["watched", "liked", "disliked", "avoid"], "external_account_write": False},
            ),
            Capability(
                capability_id="voice.web.result.open",
                kind=CapabilityKind.CONTROL,
                description="Open an explicitly selected HTTPS research result in the TV browser",
                risk=RiskLevel.MEDIUM,
                schema={"explicit_result_selection": True, "https_only": True},
            ),
            Capability(
                capability_id="voice.games.launch",
                kind=CapabilityKind.CONTROL,
                description="Open the allowlisted GeForce NOW cloud-gaming surface on the paired TV",
                risk=RiskLevel.MEDIUM,
                schema={"provider": "GeForce NOW", "origin": "https://play.geforcenow.com", "credentials_retained": False},
            ),
            Capability(
                capability_id="voice.education.start",
                kind=CapabilityKind.CONTROL,
                description="Start the local child-safe Spanish Learning Centre on AION Canvas",
                risk=RiskLevel.LOW,
                schema={"open_web": False, "advertising": False, "default_profile": "explorer_a"},
            ),
            Capability(
                capability_id="voice.webos.perception.read",
                kind=CapabilityKind.OBSERVE,
                description="Read the paired TV's foreground application and audio state before agent planning",
                risk=RiskLevel.LOW,
                schema={"pixel_capture": False, "foreground_app": True, "read_after_action": True},
            ),
            Capability(
                capability_id="voice.live.context.read",
                kind=CapabilityKind.OBSERVE,
                description="Build bounded context from TV state and the local ephemeral speech window after an explicit request",
                risk=RiskLevel.LOW,
                schema={"rolling_audio_seconds": 30, "raw_audio_retained": False, "general_pixel_capture": False},
            ),
            Capability(
                capability_id="voice.live.fact_check",
                kind=CapabilityKind.OBSERVE,
                description="Check an explicitly referenced television claim against current sourced evidence",
                risk=RiskLevel.LOW,
                schema={"primary_sources_preferred": True, "uncertainty_required": True, "maximum_results": 5},
            ),
            Capability(
                capability_id="voice.live.translate",
                kind=CapabilityKind.OBSERVE,
                description="Translate only bounded locally observed dialogue or owner-captured subtitles without web or paid AI",
                risk=RiskLevel.LOW,
                schema={"raw_audio_retained": False, "playback_preserved": True, "default_target_language": "en"},
            ),
            Capability(
                capability_id="voice.live.sports",
                kind=CapabilityKind.OBSERVE,
                description="Interpret an owner-captured scoreboard or explain a named sports rule without claiming to verify an unseen incident",
                risk=RiskLevel.LOW,
                schema={"player_identity_inferred": False, "referee_decision_verified": False, "playback_preserved": True},
            ),
            Capability(
                capability_id="voice.live.event.feed",
                kind=CapabilityKind.OBSERVE,
                description="Retrieve an authenticated bounded sports or event feed and reconcile it with separately labelled screen evidence",
                risk=RiskLevel.LOW,
                schema={
                    "provider_secret_on_tv_or_phone": False,
                    "raw_response_retained": False,
                    "screen_and_provider_facts_separated": True,
                    "paid_ai_required": False,
                },
            ),
            Capability(
                capability_id="voice.private-save.prepare",
                kind=CapabilityKind.OBSERVE,
                description="Prepare a programme-derived evidence card for explicit private-phone persona claim",
                risk=RiskLevel.LOW,
                schema={"shared_tv_selects_persona": False, "purchase_executed": False, "private_claim_required": True},
            ),
            Capability(
                capability_id="voice.moment.prepare",
                kind=CapabilityKind.OBSERVE,
                description="Prepare a signed service-aware moment card without copying protected television media",
                risk=RiskLevel.LOW,
                schema={"maximum_seconds": 30, "protected_audio_copied": False, "protected_video_copied": False},
            ),
            Capability(
                capability_id="voice.agent.plan",
                kind=CapabilityKind.OBSERVE,
                description="Compile open-ended requests into persistent allowlisted plans with private approval gates",
                risk=RiskLevel.LOW,
                schema={
                    "direct_model_execution": False,
                    "private_approval": ["booking", "shopping", "communication", "calendar"],
                    "service_execution_without_adapter": False,
                },
            ),
            Capability(
                capability_id="voice.inbox.manage",
                kind=CapabilityKind.CONTROL,
                description="Read a signed-in person's task counts and prepare local Pilot inbox actions",
                risk=RiskLevel.MEDIUM,
                schema={"signed_active_identity_required": True, "shared_screen_private_titles": False, "recipient_acceptance": True},
            ),
            Capability(
                capability_id="companion.webos.navigation.control",
                kind=CapabilityKind.CONTROL,
                description="Send one bounded remote-control action from the paired private phone companion",
                risk=RiskLevel.MEDIUM,
                schema={"buttons": ["UP", "DOWN", "LEFT", "RIGHT", "ENTER", "BACK", "HOME"], "rate_limited": True},
            ),
            Capability(
                capability_id="companion.webos.media.control",
                kind=CapabilityKind.CONTROL,
                description="Control TV volume, mute and playback from the paired private phone companion",
                risk=RiskLevel.MEDIUM,
                schema={"maximum_volume": 50, "rate_limited": True, "read_after_write": True},
            ),
            Capability(
                capability_id="companion.webos.app.launch",
                kind=CapabilityKind.CONTROL,
                description="Launch an allowlisted TV app or AION Canvas from the paired private phone companion",
                risk=RiskLevel.MEDIUM,
                schema={"apps": ["netflix", "youtube.leanback.v4", "aion_canvas", "geforce_now"]},
            ),
            Capability(
                capability_id="companion.webos.private_keyboard",
                kind=CapabilityKind.CONTROL,
                description="Deliver ephemeral private phone text to the currently focused LG TV field",
                risk=RiskLevel.MEDIUM,
                schema={"purposes": ["username", "password", "game_search"], "maximum_characters": 320, "retained": False, "audited_value": False},
            ),
            Capability(
                capability_id="companion.webos.perception.submit",
                kind=CapabilityKind.OBSERVE,
                description="Accept an owner-captured TV image for local ephemeral Apple Vision analysis",
                risk=RiskLevel.LOW,
                schema={"explicit_capture": True, "image_retained": False, "maximum_bytes": 5242880},
            ),
            Capability(
                capability_id="companion.screen.context.correct",
                kind=CapabilityKind.CONTROL,
                description="Attach an owner correction to the latest structured screen observation",
                risk=RiskLevel.LOW,
                schema={"fields": ["subtitle", "scoreboard", "product", "location", "scene"], "source_pixels_retained": False},
            ),
            Capability(
                capability_id="companion.screen.observer.control",
                kind=CapabilityKind.CONTROL,
                description="Start or stop a visible, short-lived private phone observer session",
                risk=RiskLevel.MEDIUM,
                schema={"maximum_seconds": 600, "minimum_frame_interval_seconds": 3, "raw_frames_retained": False, "silent_start": False},
            ),
            Capability(
                capability_id="companion.agent.request",
                kind=CapabilityKind.OBSERVE,
                description="Send a typed private request to the mother intelligence through the phone companion",
                risk=RiskLevel.LOW,
                schema={"maximum_characters": 300, "direct_model_execution": False},
            ),
            Capability(
                capability_id="companion.communication.manage",
                kind=CapabilityKind.CONTROL,
                description="Prepare, privately approve and verify persona-bound communications",
                risk=RiskLevel.MEDIUM,
                schema={"exact_recipient_and_content": True, "provider_receipt_required": True, "child_guardian_gate": True},
            ),
            Capability(
                capability_id="companion.calendar.manage",
                kind=CapabilityKind.CONTROL,
                description="Prepare and privately approve exact calendar changes with conflict checks",
                risk=RiskLevel.MEDIUM,
                schema={"scope_hash_required": True, "conflicts_private": True, "provider_receipt_required": True},
            ),
            Capability(
                capability_id="companion.guardian.manage",
                kind=CapabilityKind.CONTROL,
                description="Configure and confirm trusted-contact urgent-help alerts without dispatch claims",
                risk=RiskLevel.HIGH,
                requires_approval=True,
                schema={"explicit_emergency_permission": True, "large_confirmation": True, "ambulance_dispatch_claim": False},
            ),
            Capability(
                capability_id="companion.education.play",
                kind=CapabilityKind.CONTROL,
                description="Run a local child-safe adaptive learning session on AION Canvas",
                risk=RiskLevel.LOW,
                schema={"open_web": False, "advertising": False, "child_accounts": False, "profiles": ["explorer_a", "explorer_b"]},
            ),
            Capability(
                capability_id="companion.gaming.manage",
                kind=CapabilityKind.CONTROL,
                description="Observe controller input and manage persona-private shortcuts without claiming provider gameplay",
                risk=RiskLevel.LOW,
                schema={"gamepad_api": True, "advertisement_is_compatibility": False, "credentials_retained": False},
            ),
            Capability(
                capability_id="companion.identity.manage",
                kind=CapabilityKind.CONTROL,
                description="Onboard and govern private identities, memory, devices and service consent from the private phone",
                risk=RiskLevel.MEDIUM,
                schema={"shared_tv_private_details": False, "signed_phone_possession": True, "biometric_attestation_required_for_biometric_claim": True},
            ),
            Capability(
                capability_id="companion.inbox.manage",
                kind=CapabilityKind.CONTROL,
                description="Manage persona-bound lists, tasks, reminders, delegation and Pilot-to-Pilot inbox items",
                risk=RiskLevel.MEDIUM,
                schema={"recipient_acceptance": True, "external_delivery_requires_approval": True, "location_permission_required": True},
            ),
            Capability(
                capability_id="companion.tv.rooms.manage",
                kind=CapabilityKind.CONTROL,
                description="Privately name a television room and prepare verified cross-room handoff",
                risk=RiskLevel.MEDIUM,
                schema={"private_phone_only": True, "verified_playback_required": True, "credentials_projected": False},
            ),
            Capability(
                capability_id="companion.tv.reliability.test",
                kind=CapabilityKind.CONTROL,
                description="Run a bounded reversible television qualification baseline and restore audio state",
                risk=RiskLevel.MEDIUM,
                schema={"private_phone_only": True, "volume_restored": True, "power_control": False, "account_changes": False},
            ),
        ]
        existing_by_id = {item.capability_id: item for item in capabilities}
        policy_ids = {item.capability_id for item in policy_capabilities}
        added = [item for item in policy_capabilities if item.capability_id not in existing_by_id]
        policy_changed = any(
            item.capability_id not in existing_by_id
            or existing_by_id[item.capability_id].to_dict() != item.to_dict()
            for item in policy_capabilities
        )
        if policy_changed:
            capabilities = [item for item in capabilities if item.capability_id not in policy_ids]
            capabilities.extend(policy_capabilities)
            self.issue_capabilities(node_id, capabilities, approved_by=approved_by)
        record.profile = replace(
            record.profile,
            metadata={
                **record.profile.metadata,
                "voice_control": "enabled",
                "voice_policy": {
                    "wake_phrase_required": True,
                    "maximum_volume": 50,
                    "volume_step": 2,
                    "power_control": "blocked",
                    "purchases": "blocked",
                    "service_actions": "proposal_and_private_approval_only",
                    "account_and_security_changes": "blocked",
                    "raw_audio_retained": False,
                },
            },
        )
        self.store.save_node(record)
        return {"enabled": True, "capabilities_added": len(added), "maximum_volume": 50}

    def execute_companion_command(
        self,
        command: str,
        arguments: Dict[str, Any],
        *,
        canvas_url: str | None = None,
        canvas_view_callback: Callable[[str], None] | None = None,
        companion_url: str | None = None,
        continue_verified_navigation: bool = False,
    ) -> Dict[str, Any]:
        """Route a private phone command through the same signed TV policy."""
        command = re.sub(r"[^a-z0-9_]+", "", str(command).lower())[:40]
        groups = {
            "navigation": {
                "up", "down", "left", "right", "enter", "back", "home", "accept_google",
                "profile_1", "profile_2", "profile_3", "profile_4", "profile_5",
                "profile_menu", "pointer_move", "pointer_click", "netflix_search",
            },
            "media": {"volume_up", "volume_down", "play", "pause", "mute", "unmute", "observe"},
            "app": {"netflix", "youtube", "aion", "games", "god_view"},
            "agent": {"ask", "claim_task", "service_details"},
            "screen": {"screen_correction", "profile_names_save"},
            "observer": {
                "observer_start", "observer_stop", "observer_pause", "observer_resume",
                "observer_configure", "observer_resource_state",
            },
            "education": {
                "education_start", "education_answer", "education_next", "education_repeat",
                "education_pronunciation", "education_parent_report", "education_parent_correction",
            },
            "gaming": {"gaming_controller_observe", "gaming_save_shortcut", "gaming_continue"},
            "identity": {
                "identity_onboard", "identity_memory_add", "identity_memory_update",
                "identity_memory_delete", "identity_export", "identity_consent_grant",
                "identity_consent_revoke", "identity_device_revoke", "identity_recover",
                "identity_phone_begin", "identity_phone_complete", "identity_activate",
                "identity_logout",
            },
            "inbox": {
                "inbox_list_create", "inbox_task_create", "inbox_message_send",
                "inbox_delegation_respond", "inbox_task_complete", "inbox_task_snooze",
                "inbox_reminder_add", "inbox_route_stop_suggest", "inbox_route_stop_accept",
                "inbox_contact_save", "inbox_external_delivery_approve",
            },
            "communication": {
                "communication_draft", "communication_approve", "communication_guardian_decide",
                "communication_execute", "communication_convert", "communication_follow_up",
                "communication_call_prepare",
            },
            "calendar": {"calendar_prepare", "calendar_decide", "calendar_execute", "calendar_availability"},
            "guardian": {"guardian_permission", "guardian_request", "guardian_confirm", "guardian_cancel", "guardian_deliver", "guardian_respond"},
            "climate": {"ir_discover", "ir_select", "ir_learn_begin", "ir_learn_capture", "ir_send"},
            "rooms": {"tv_room_name", "tv_room_default", "tv_handoff_prepare", "tv_handoff_confirm"},
            "reliability": {"reliability_baseline"},
        }
        group = next((name for name, commands in groups.items() if command in commands), None)
        if group is None:
            raise PermissionError("That phone command is outside the governed controller")
        if group == "climate":
            if command == "ir_discover":
                result = self.infrared_climate.discover(timeout=float(arguments.get("timeout") or 3))
                event = "local_ir_gateway_discovered"
                spoken = (
                    f"Found {len(result['found'])} local infrared gateway."
                    if len(result["found"]) == 1 else
                    f"Found {len(result['found'])} local infrared gateways."
                )
            elif command == "ir_select":
                result = self.infrared_climate.select(str(arguments.get("mac") or ""))
                event = "local_ir_gateway_selected"
                spoken = "The local infrared gateway is selected."
            elif command == "ir_learn_begin":
                result = self.infrared_climate.begin_learning(str(arguments.get("preset") or ""))
                event = "local_ir_learning_started"
                spoken = str(result["instruction"])
            elif command == "ir_learn_capture":
                result = self.infrared_climate.capture_learning()
                event = "local_ir_preset_learned"
                spoken = f"The Toshiba {result['preset'].replace('_', ' ')} preset is learned locally."
            else:
                preset = str(arguments.get("preset") or "")
                result = self.infrared_climate.send_last_active() if preset == "last_active" else self.infrared_climate.send(preset)
                event = "local_ir_command_delivered"
                spoken = (
                    f"I sent Toshiba {result['preset'].replace('_', ' ')}. "
                    "Infrared is one-way, so the air conditioner state is not independently verified."
                )
            self.store.append_audit(
                event,
                {
                    "preset": result.get("preset") if isinstance(result, dict) else None,
                    "code_sha256": result.get("code_sha256") if isinstance(result, dict) else None,
                    "transport_delivered": result.get("transport_delivered") if isinstance(result, dict) else None,
                    "air_conditioner_state_verified": False,
                    "raw_ir_code_retained_in_audit": False,
                },
            )
            return {"accepted": True, "spoken_response": spoken, "infrared_climate": result}
        integrated = next(
            (
                node for node in self.store.list_nodes()
                if node.enrollment is EnrollmentState.ENROLLED
                and node.profile.metadata.get("webos_integration") == "connected"
            ),
            None,
        )
        if integrated is None:
            raise RuntimeError("No integrated television is available")
        capability = {
            "navigation": "companion.webos.navigation.control",
            "media": "companion.webos.media.control",
            "app": "companion.webos.app.launch",
            "agent": "companion.agent.request",
            "screen": "companion.screen.context.correct",
            "observer": "companion.screen.observer.control",
            "education": "companion.education.play",
            "gaming": "companion.gaming.manage",
            "identity": "companion.identity.manage",
            "inbox": "companion.inbox.manage",
            "communication": "companion.communication.manage",
            "calendar": "companion.calendar.manage",
            "guardian": "companion.guardian.manage",
            "rooms": "companion.tv.rooms.manage",
            "reliability": "companion.tv.reliability.test",
        }[group]
        capsule = self.store.latest_capsule_for_node(integrated.profile.node_id)
        permitted = {item["capability_id"] for item in capsule.capabilities} if capsule else set()
        if capability not in permitted:
            raise PermissionError(f"The signed phone capability {capability} is unavailable")
        if command not in {"identity_activate", "identity_logout", "identity_phone_begin", "identity_phone_complete"}:
            active_session = dict(self.private_identity.snapshot().get("active_shared_identity") or {})
            if active_session.get("persona_id"):
                self.private_identity.touch_shared_screen(
                    persona_id=str(active_session["persona_id"]), source="private_phone_controller"
                )

        if group == "identity":
            if command in {
                "identity_memory_add", "identity_memory_update", "identity_memory_delete",
                "identity_export", "identity_consent_grant", "identity_consent_revoke",
            }:
                requested_persona = str(arguments.get("persona_id") or "")
                active_session = dict(self.private_identity.snapshot().get("active_shared_identity") or {})
                if not requested_persona or requested_persona != str(active_session.get("persona_id") or ""):
                    raise PermissionError("Activate this identity from its trusted phone before accessing its private workspace")
            if command == "identity_onboard":
                result = self.private_identity.onboard(
                    display_name=str(arguments.get("display_name") or ""),
                    role=str(arguments.get("role") or "adult"),
                    guardian_persona_id=str(arguments.get("guardian_persona_id") or "") or None,
                    age_band=str(arguments.get("age_band") or ""),
                )
                spoken = f"{result['display_name']} now has a private Pilot identity. Save the recovery code somewhere private; it is shown only once."
                event = "private_identity_onboarded"
            elif command == "identity_phone_begin":
                result = self.private_identity.begin_phone_enrollment(
                    persona_id=str(arguments.get("persona_id") or ""), device_label=str(arguments.get("device_label") or "Private phone"),
                    public_key=str(arguments.get("public_key") or ""), biometric_capable=bool(arguments.get("biometric_capable")),
                )
                spoken, event = "Sign the one-time possession challenge on this phone.", "private_phone_enrollment_started"
            elif command == "identity_phone_complete":
                result = self.private_identity.complete_phone_enrollment(str(arguments.get("challenge_id") or ""), signature=str(arguments.get("signature") or ""))
                spoken, event = "This phone proved possession of its private key and is now trusted.", "private_phone_possession_verified"
            elif command == "identity_activate":
                result = self.private_identity.activate_shared_screen(
                    persona_id=str(arguments.get("persona_id") or ""), device_id=str(arguments.get("device_id") or ""),
                    nonce=str(arguments.get("nonce") or ""), signature=str(arguments.get("signature") or ""),
                )
                spoken, event = f"{result['display_name']} is now clearly active on shared screens for a limited session.", "shared_screen_identity_activated"
            elif command == "identity_logout":
                result = self.private_identity.release_shared_screen_signed(
                    persona_id=str(arguments.get("persona_id") or ""), device_id=str(arguments.get("device_id") or ""),
                    nonce=str(arguments.get("nonce") or ""), signature=str(arguments.get("signature") or ""),
                )
                spoken, event = "The television workspace is locked.", "shared_screen_identity_released"
            elif command == "identity_memory_add":
                result = self.private_identity.remember(
                    persona_id=str(arguments.get("persona_id") or ""), kind=str(arguments.get("kind") or "note"),
                    summary=str(arguments.get("summary") or ""), scope=str(arguments.get("scope") or "private"),
                    source_reference=str(arguments.get("source_reference") or ""),
                )
                spoken, event = "The memory is saved with the selected scope.", "private_memory_added"
            elif command == "identity_memory_update":
                result = self.private_identity.update_memory(
                    persona_id=str(arguments.get("persona_id") or ""), memory_id=str(arguments.get("memory_id") or ""),
                    summary=str(arguments["summary"]) if "summary" in arguments else None,
                    scope=str(arguments["scope"]) if "scope" in arguments else None,
                )
                spoken, event = "The memory and its scope are updated.", "private_memory_updated"
            elif command == "identity_memory_delete":
                result = self.private_identity.delete_memory(persona_id=str(arguments.get("persona_id") or ""), memory_id=str(arguments.get("memory_id") or ""))
                spoken, event = "That selected memory is deleted.", "private_memory_deleted"
            elif command == "identity_export":
                persona_id = str(arguments.get("persona_id") or "")
                result = self.private_identity.export(persona_id=persona_id, requester_persona_id=persona_id)
                spoken, event = "Your private identity export is ready on this phone.", "private_identity_exported"
            elif command == "identity_consent_grant":
                result = self.private_identity.grant_consent(
                    persona_id=str(arguments.get("persona_id") or ""), service=str(arguments.get("service") or ""),
                    scopes=[str(value) for value in list(arguments.get("scopes") or [])], device_id=str(arguments.get("device_id") or ""),
                )
                spoken, event = "The exact service scopes are now consented.", "service_consent_granted"
            elif command == "identity_consent_revoke":
                result = self.private_identity.revoke_consent(persona_id=str(arguments.get("persona_id") or ""), consent_id=str(arguments.get("consent_id") or ""))
                spoken, event = "That service consent is revoked.", "service_consent_revoked"
            elif command == "identity_device_revoke":
                result = self.private_identity.revoke_device(persona_id=str(arguments.get("persona_id") or ""), device_id=str(arguments.get("device_id") or ""), reason=str(arguments.get("reason") or "owner_requested"))
                spoken, event = "The lost phone and its active sessions are revoked.", "private_phone_revoked"
            else:
                result = self.private_identity.recover(persona_id=str(arguments.get("persona_id") or ""), recovery_code=str(arguments.get("recovery_code") or ""))
                spoken, event = "Account recovery completed and every previously trusted phone was revoked.", "private_identity_recovered"
            self.store.append_audit(event, {
                "persona_id": result.get("persona_id"), "object_id": result.get("memory_id") or result.get("consent_id") or result.get("device_id") or result.get("recovery_id"),
                "raw_recovery_code_retained": False, "raw_memory_in_audit": False,
            })
            return {"accepted": True, "spoken_response": spoken, "result": result, "private_identity": self.private_identity.snapshot(viewer_persona_id=str(result.get("persona_id") or arguments.get("persona_id") or ""))}

        if group in {"communication", "calendar", "guardian"}:
            actor = str(arguments.get("persona_id") or "")
            active_session = dict(self.private_identity.snapshot().get("active_shared_identity") or {})
            if not actor or actor != str(active_session.get("persona_id") or ""):
                raise PermissionError("Activate this identity from its trusted phone before using this private capability")
            if group == "communication":
                if command == "communication_draft":
                    result = self.communication.draft(
                        persona_id=actor, contact_id=str(arguments.get("contact_id") or ""),
                        channel=str(arguments.get("channel") or "email"), body=str(arguments.get("body") or ""),
                        subject=str(arguments.get("subject") or ""), reply_to_message_id=str(arguments.get("reply_to_message_id") or ""),
                    )
                    spoken, event = "The AION Native draft is ready. Review the exact recipient and content before approving it.", "communication_draft_prepared"
                elif command == "communication_approve":
                    result = self.communication.approve(draft_id=str(arguments.get("draft_id") or ""), persona_id=actor, content_hash=str(arguments.get("content_hash") or ""), approved=bool(arguments.get("approved")))
                    spoken, event = ("The exact draft is approved for its connected sending account." if result["status"] == "approved_pending_adapter" else "The draft is rejected."), "communication_draft_decided"
                elif command == "communication_guardian_decide":
                    result = self.communication.guardian_decide(draft_id=str(arguments.get("draft_id") or ""), guardian_persona_id=actor, approved=bool(arguments.get("approved")))
                    spoken, event = "The guardian communication decision is recorded.", "communication_guardian_decided"
                elif command == "communication_execute":
                    result = self.communication.execute(draft_id=str(arguments.get("draft_id") or ""), persona_id=actor)
                    spoken, event = "The provider verified delivery and returned a receipt.", "communication_delivery_verified"
                elif command == "communication_convert":
                    result = self.communication.convert_received(message_id=str(arguments.get("message_id") or ""), persona_id=actor, target=str(arguments.get("target") or "task"))
                    spoken, event = "The received message is now a private proposal.", "communication_converted"
                elif command == "communication_follow_up":
                    result = self.communication.schedule_no_reply_follow_up(draft_id=str(arguments.get("draft_id") or ""), persona_id=actor, due_at=str(arguments.get("due_at") or ""))
                    spoken, event = "Pilot will remind you if no verified reply has arrived by that time.", "communication_follow_up_scheduled"
                else:
                    result = self.communication.prepare_call(persona_id=actor, contact_id=str(arguments.get("contact_id") or ""))
                    spoken, event = "The call is prepared. Placing it still requires your explicit tap on an authorized phone surface.", "communication_call_prepared"
            elif group == "calendar":
                if command == "calendar_prepare":
                    result = self.calendar_planning.prepare(
                        persona_id=actor, action=str(arguments.get("action") or "create"), title=str(arguments.get("title") or ""),
                        start=str(arguments.get("start") or ""), end=str(arguments.get("end") or ""),
                        provider_event_id=str(arguments.get("provider_event_id") or ""), location=str(arguments.get("location") or ""),
                        travel_minutes=int(arguments.get("travel_minutes") or 0), reminder_minutes=int(arguments.get("reminder_minutes") or 0),
                    )
                    spoken = f"The exact calendar {result['action']} is prepared with {result['conflict_count']} private conflict. Review it before approval." if result["conflict_count"] == 1 else f"The exact calendar {result['action']} is prepared with {result['conflict_count']} private conflicts. Review it before approval."
                    event = "calendar_change_prepared"
                elif command == "calendar_decide":
                    result = self.calendar_planning.decide(proposal_id=str(arguments.get("proposal_id") or ""), persona_id=actor, scope_hash=str(arguments.get("scope_hash") or ""), approved=bool(arguments.get("approved")), accept_conflicts=bool(arguments.get("accept_conflicts")))
                    spoken, event = "The exact calendar change is approved for the connected calendar." if result["status"] == "approved_pending_adapter" else "The calendar change is rejected.", "calendar_change_decided"
                elif command == "calendar_execute":
                    result = self.calendar_planning.execute(proposal_id=str(arguments.get("proposal_id") or ""), persona_id=actor)
                    spoken, event = "The calendar provider verified the change and returned a receipt.", "calendar_change_verified"
                else:
                    result = self.calendar_planning.availability(persona_id=actor, start=str(arguments.get("start") or ""), end=str(arguments.get("end") or ""), slot_minutes=int(arguments.get("slot_minutes") or 30))
                    spoken, event = f"I found {len(result['free_slots'])} available slots without exposing private event details.", "calendar_availability_queried"
            else:
                if command == "guardian_permission":
                    result = self.guardian.grant_emergency_contact(persona_id=actor, contact_id=str(arguments.get("contact_id") or ""), channel=str(arguments.get("channel") or "pilot"), share_location=bool(arguments.get("share_location")), location_permission_receipt=str(arguments.get("location_permission_receipt") or ""), allow_interruption=bool(arguments.get("allow_interruption", True)))
                    spoken, event = "The separate Guardian contact permission is active.", "guardian_permission_granted"
                elif command == "guardian_request":
                    result = self.guardian.request_help(persona_id=actor, trigger=str(arguments.get("trigger") or "Explicit phone help request"), surface="private_phone", location=dict(arguments.get("location") or {}))
                    spoken, event = "Guardian is waiting for your large confirmation. No alert or ambulance request has been sent.", "guardian_help_confirmation_opened"
                else:
                    incidents = list(self.guardian.snapshot(persona_id=actor).get("incidents") or [])
                    incident_id = str(arguments.get("incident_id") or (incidents[-1]["incident_id"] if incidents else ""))
                    if command == "guardian_confirm":
                        result = self.guardian.confirm(incident_id=incident_id, persona_id=actor); spoken, event = "The trusted-contact alert is confirmed for its authorized delivery route.", "guardian_alert_confirmed"
                    elif command == "guardian_cancel":
                        result = self.guardian.cancel(incident_id=incident_id, persona_id=actor); spoken, event = "Guardian is cancelled as a false alarm.", "guardian_alert_cancelled"
                    elif command == "guardian_deliver":
                        result = self.guardian.deliver_alerts(incident_id=incident_id, persona_id=actor); spoken, event = "Guardian checked the trusted-contact delivery routes. It has not claimed ambulance dispatch.", "guardian_delivery_attempted"
                    else:
                        result = self.guardian.record_response(response_token=str(arguments.get("response_token") or ""), responder_name=str(arguments.get("responder_name") or "Trusted contact"), message=str(arguments.get("message") or "")); spoken, event = "The trusted contact response is visible in Guardian.", "guardian_response_received"
            self.store.append_audit(event, {
                "persona_id": actor, "object_id": result.get("draft_id") or result.get("proposal_id") or result.get("incident_id") or result.get("receipt_id"),
                "external_effect": bool(result.get("verified")), "provider_secrets_retained": False,
                "ambulance_dispatched": False if group == "guardian" else None,
            })
            return {"accepted": True, "spoken_response": spoken, group: result}

        if group == "inbox":
            actor = str(arguments.get("persona_id") or arguments.get("owner_persona_id") or "")
            active_session = dict(self.private_identity.snapshot().get("active_shared_identity") or {})
            if not actor or actor != str(active_session.get("persona_id") or ""):
                raise PermissionError("Activate this identity from its trusted phone before opening or changing its Pilot stream")
            if command == "inbox_list_create":
                result = self.pilot_inbox.create_list(owner_persona_id=actor, name=str(arguments.get("name") or ""), scope=str(arguments.get("scope") or "private"))
                spoken, event = "The list is ready in your Pilot stream.", "pilot_list_created"
            elif command == "inbox_task_create":
                result = self.pilot_inbox.create_task(
                    requester_persona_id=actor, owner_persona_id=actor, title=str(arguments.get("title") or ""),
                    assignee_persona_id=str(arguments.get("assignee_persona_id") or "") or None,
                    list_id=str(arguments.get("list_id") or "") or None, notes=str(arguments.get("notes") or ""),
                    source=dict(arguments.get("source") or {}),
                )
                spoken = "The task request is waiting for the recipient to accept it." if result["recipient_acceptance_required"] else "The task is on your Pilot list."
                event = "pilot_task_created"
            elif command == "inbox_message_send":
                result = self.pilot_inbox.send_message(sender_persona_id=actor, recipient_persona_id=str(arguments.get("recipient_persona_id") or ""), body=str(arguments.get("body") or ""))
                spoken, event = "The message is in the recipient's Pilot inbox.", "pilot_message_delivered"
            elif command == "inbox_contact_save":
                result = self.pilot_inbox.save_contact(
                    owner_persona_id=actor, display_name=str(arguments.get("display_name") or ""),
                    email=str(arguments.get("email") or ""), whatsapp=str(arguments.get("whatsapp") or ""),
                    pilot_persona_id=str(arguments.get("pilot_persona_id") or ""),
                    preferred_route=str(arguments.get("preferred_route") or ""),
                )
                spoken, event = f"{result['display_name']} is saved in your private contacts.", "pilot_private_contact_saved"
            elif command == "inbox_external_delivery_approve":
                result = self.pilot_inbox.approve_external_delivery(
                    proposal_id=str(arguments.get("proposal_id") or ""), persona_id=actor,
                )
                spoken = "The handoff is approved and waiting for your connected sending account. Nothing has been sent yet."
                event = "pilot_external_task_delivery_approved_pending_adapter"
            elif command == "inbox_delegation_respond":
                result = self.pilot_inbox.respond_to_delegation(task_id=str(arguments.get("task_id") or ""), recipient_persona_id=actor, accept=bool(arguments.get("accept")))
                spoken, event = ("The task is accepted." if result["status"] == "open" else "The task request is declined."), "pilot_task_delegation_decided"
            elif command == "inbox_task_complete":
                result = self.pilot_inbox.complete(task_id=str(arguments.get("task_id") or ""), actor_persona_id=actor)
                spoken, event = "Task completed.", "pilot_task_completed"
            elif command == "inbox_task_snooze":
                result = self.pilot_inbox.snooze(task_id=str(arguments.get("task_id") or ""), actor_persona_id=actor, until=str(arguments.get("until") or ""))
                spoken, event = "The task is snoozed until the selected time.", "pilot_task_snoozed"
            elif command == "inbox_reminder_add":
                result = self.pilot_inbox.add_reminder(
                    persona_id=actor, task_id=str(arguments.get("task_id") or ""), trigger=str(arguments.get("trigger") or "time"),
                    at=str(arguments.get("at") or "") or None, location_label=str(arguments.get("location_label") or ""),
                    repetition=str(arguments.get("repetition") or "none"), location_permission_id=str(arguments.get("location_permission_id") or "") or None,
                )
                spoken, event = "The reminder is scheduled with the selected permission boundary.", "pilot_reminder_scheduled"
            elif command == "inbox_route_stop_suggest":
                result = self.pilot_inbox.suggest_route_stop(persona_id=actor, task_id=str(arguments.get("task_id") or ""), accepted_route_id=str(arguments.get("accepted_route_id") or ""), reason=str(arguments.get("reason") or ""))
                spoken, event = "The stop is suggested, not added to the route.", "pilot_route_stop_suggested"
            else:
                result = self.pilot_inbox.accept_route_stop(suggestion_id=str(arguments.get("suggestion_id") or ""), persona_id=actor)
                spoken, event = "The stop is accepted and waiting for an authorized car adapter.", "pilot_route_stop_accepted"
            self.store.append_audit(event, {
                "actor_persona_id": actor,
                "object_id": result.get("task_id") or result.get("message_id") or result.get("list_id") or result.get("reminder_id") or result.get("suggestion_id"),
                "recipient_acceptance_required": result.get("recipient_acceptance_required"),
                "external_effect": False,
            })
            return {"accepted": True, "spoken_response": spoken, "result": result, "pilot_inbox": self.pilot_inbox.stream(persona_id=actor)}

        if group == "reliability":
            result = self.run_safe_tv_reliability_baseline()
            return {
                **result,
                "spoken_response": (
                    "The safe LG baseline passed and restored the original volume. More visual field cases are still required."
                    if result.get("volume_restored") else
                    "The baseline could not confirm that the original volume was restored. Stop testing and inspect the television."
                ),
            }
        if group == "gaming":
            if command == "gaming_save_shortcut":
                latest = dict(self.gaming.snapshot(persona_id=str(self.local_persona["persona_id"])).get("latest_session") or {})
                shortcut = self.gaming.save_shortcut(str(arguments.get("session_id") or latest.get("session_id") or ""), persona_id=str(self.local_persona["persona_id"]))
                self.store.append_audit("verified_game_shortcut_saved", {"shortcut_id": shortcut["shortcut_id"], "persona_id": self.local_persona["persona_id"], "title_hash": canonical_hash(shortcut["title"])})
                return {"accepted": True, "game_shortcut": shortcut, "gaming": self.gaming.snapshot(persona_id=str(self.local_persona["persona_id"])), "spoken_response": f"{shortcut['title']} is saved privately."}
            if command == "gaming_continue":
                prepared = self.gaming.continue_last(persona_id=str(self.local_persona["persona_id"]))
                response = self.execute_voice_command(
                    f"Pilot find a game called {prepared['query']} on GeForce Now",
                    canvas_url=canvas_url, canvas_view_callback=canvas_view_callback,
                    companion_url=companion_url, conversation_channel="private_phone",
                    persona_id=str(self.local_persona["persona_id"]),
                )
                return {**response, "gaming_continuation": prepared}
            controller = self.gaming.observe_controller(
                controller_id=str(arguments.get("controller_id") or "browser-gamepad"),
                name=str(arguments.get("name") or ""),
                capabilities=[str(value) for value in list(arguments.get("capabilities") or [])],
                input_events_seen=[str(value) for value in list(arguments.get("input_events_seen") or [])],
            )
            self.store.append_audit("gaming_controller_observed", {
                "controller_id_hash": canonical_hash(controller["controller_id"]),
                "profile": controller["profile"],
                "input_mode": controller["input_mode"],
                "compatibility": controller["compatibility"],
                "gameplay_ready": controller["gameplay_ready"],
            })
            return {"accepted": True, "gaming_controller": controller, "gaming": self.gaming.snapshot(persona_id=str(self.local_persona["persona_id"])), "spoken_response": "Controller input was observed locally." if controller["gameplay_ready"] else "The controller was detected but gameplay input is not verified yet."}

        if command == "profile_names_save":
            profile_record = self.phone_perception.save_profile_names(list(arguments.get("names") or []))
            self.store.append_audit(
                "netflix_profile_labels_saved",
                {
                    "profile_count": len(profile_record["names"]),
                    "profile_labels_hash": canonical_hash(profile_record["names"]),
                    "raw_profile_labels_in_audit": False,
                },
            )
            return {
                "accepted": True,
                "spoken_response": "The five Netflix profile names are saved on this mother brain.",
                "netflix_profiles": profile_record,
            }

        if group == "rooms":
            current = next(
                (item for item in self.tv_rooms.snapshot().get("televisions", []) if item.get("node_id") == integrated.profile.node_id),
                {},
            )
            if command in {"tv_room_name", "tv_room_default"}:
                result = self.tv_rooms.register(
                    node_id=integrated.profile.node_id,
                    device_name=integrated.profile.name,
                    room_name=str(arguments.get("room_name") or current.get("room_name") or "Primary TV"),
                    endpoint=str(integrated.profile.metadata.get("webos_host") or ""),
                    make_default=command == "tv_room_default",
                )
                event = "television_room_named" if command == "tv_room_name" else "default_television_room_changed"
                spoken = f"This television is now registered as {result['room_name']}."
            elif command == "tv_handoff_prepare":
                telemetry = self.provider_telemetry.latest(persona_id=str(self.local_persona["persona_id"])) or {}
                playback = dict(telemetry.get("playback") or {})
                playback.update({
                    "provider": telemetry.get("provider"),
                    "title": (telemetry.get("content") or {}).get("title"),
                    "content_id": (telemetry.get("content") or {}).get("content_id"),
                    "playback_verified": playback.get("state") == "playing",
                })
                result = self.tv_rooms.prepare_handoff(
                    source_node_id=integrated.profile.node_id,
                    destination_room=str(arguments.get("destination_room") or ""),
                    persona_id=str(self.local_persona["persona_id"]),
                    playback=playback,
                )
                event = "television_handoff_prepared"
                spoken = f"Review the private handoff to {result['destination_room']}. Nothing has opened there yet."
            else:
                result = self.tv_rooms.confirm_handoff(
                    str(arguments.get("handoff_id") or ""),
                    persona_id=str(self.local_persona["persona_id"]),
                    confirmation_hash=str(arguments.get("confirmation_hash") or ""),
                )
                event = "television_handoff_confirmed_pending_adapter"
                spoken = "The handoff is approved, but Pilot will not claim destination playback until its adapter verifies it."
            self.store.append_audit(event, {
                "node_id": integrated.profile.node_id,
                "room_name": result.get("room_name") or result.get("destination_room"),
                "handoff_id": result.get("handoff_id"),
                "status": result.get("status"),
                "credentials_projected": False,
                "playback_claimed_on_destination": bool(result.get("playback_claimed_on_destination")),
            })
            return {"accepted": True, "spoken_response": spoken, "tv_rooms": self.tv_rooms.snapshot()}

        navigation_transaction = None
        if continue_verified_navigation:
            navigation_transaction = self.verified_navigation.snapshot().get("active")
            if not navigation_transaction or navigation_transaction.get("status") != "recovery_ready":
                raise ValueError("No verified navigation recovery is ready")
        elif group in {"navigation", "media", "app"}:
            latest_perception = self.phone_perception.latest() or {}
            current_surface = str((self.tv_autopilot.snapshot().get("belief") or {}).get("surface") or "unknown")
            app_ids = {"netflix": "netflix", "youtube": "youtube.leanback.v4"}
            if command in app_ids:
                expected_transaction = {"kind": "device_field", "field": "foreground_app_id", "equals": app_ids[command]}
            elif command == "observe" or command.startswith("volume_") or command in {"mute", "unmute"}:
                expected_transaction = {"kind": "receipt_verified"}
            elif group == "app":
                expected_transaction = {"kind": "device_field", "field": "foreground_app_id", "present": True}
            elif command == "profile_menu":
                expected_transaction = {"kind": "view", "value": "profile_chooser"}
            elif command.startswith("profile_"):
                expected_transaction = {"kind": "surface_screen_changed", "surface": "netflix"}
            elif command == "netflix_search":
                expected_transaction = {"kind": "text_contains", "value": " ".join(str(arguments.get("query") or "").lower().split())}
            elif command == "accept_google":
                expected_transaction = {"kind": "view_not", "value": "google_consent"}
            else:
                expected_transaction = {"kind": "screen_changed"}
            operation_arguments = {key: value for key, value in arguments.items() if not str(key).startswith("_")}
            routes = [{"route_id": f"phone.{command}", "command": command, "arguments": operation_arguments}]
            if command.startswith("profile_") or command == "accept_google":
                routes.append({"route_id": "phone.pointer_click", "command": "pointer_click", "arguments": {}})
            navigation_transaction = self.verified_navigation.start(
                device_id=integrated.profile.node_id,
                surface=current_surface,
                goal=command,
                expected=expected_transaction,
                routes=routes,
                before={
                    "image_sha256": str(latest_perception.get("image_sha256") or ""),
                    "belief": dict(self.tv_autopilot.snapshot().get("belief") or {}),
                },
                idempotency_key=str(arguments.get("_request_id") or ""),
            )
            if navigation_transaction.get("duplicate_suppressed"):
                self.store.append_audit(
                    "duplicate_tv_command_suppressed",
                    {
                        "node_id": integrated.profile.node_id,
                        "goal": command,
                        "transaction_id": navigation_transaction.get("transaction_id"),
                        "idempotency_key_hash": canonical_hash(str(arguments.get("_request_id") or "")),
                    },
                )
                return {
                    "accepted": True,
                    "duplicate_suppressed": True,
                    "spoken_response": "Pilot suppressed a repeated delivery of that television command.",
                    "verified_navigation": navigation_transaction,
                }

        if group == "observer":
            persona_id = str(self.local_persona["persona_id"])
            if command == "observer_start":
                observer = self.observer_sessions.start(
                    persona_id=persona_id,
                    duration_seconds=int(arguments.get("duration_seconds") or 600),
                    interval_seconds=int(arguments.get("interval_seconds") or 5),
                    capture_profile=str(arguments.get("capture_profile") or "balanced"),
                )
                event = "screen_observer_started"
                spoken = "Observer Mode is ready. Camera permission and the visible indicator must remain active on your phone."
            elif command == "observer_stop":
                observer = self.observer_sessions.stop(persona_id=persona_id)
                event = "screen_observer_stopped"
                spoken = "Observer Mode is stopped. No more frames will be accepted."
            elif command == "observer_pause":
                observer = self.observer_sessions.pause(persona_id=persona_id)
                event = "screen_observer_paused"
                spoken = "Observer Mode is paused and the camera should now be closed."
            elif command == "observer_resume":
                observer = self.observer_sessions.resume(persona_id=persona_id)
                event = "screen_observer_resumed"
                spoken = "Observer Mode may resume after the visible camera is reopened."
            elif command == "observer_configure":
                observer = self.observer_sessions.configure(
                    persona_id=persona_id,
                    capture_profile=str(arguments.get("capture_profile") or "balanced"),
                    interval_seconds=int(arguments["interval_seconds"]) if arguments.get("interval_seconds") else None,
                )
                event = "screen_observer_policy_changed"
                spoken = f"Observer Mode is using the {observer.get('capture_profile', 'balanced').replace('_', ' ')} profile."
            else:
                observer = self.observer_sessions.report_client_state(
                    persona_id=persona_id,
                    battery_level=(float(arguments["battery_level"]) if arguments.get("battery_level") is not None else None),
                    charging=(bool(arguments["charging"]) if arguments.get("charging") is not None else None),
                    thermal_state=str(arguments.get("thermal_state") or "nominal"),
                    visibility=str(arguments.get("visibility") or "visible"),
                )
                event = "screen_observer_resource_policy_applied"
                spoken = "Observer resource policy updated."
            self.store.append_audit(event, {
                "session_id": observer.get("session_id"),
                "persona_id": persona_id,
                "capture_profile": observer.get("capture_profile"),
                "effective_interval_seconds": observer.get("effective_interval_seconds"),
                "battery_band": (observer.get("resource_state") or {}).get("battery_band"),
                "thermal_state": (observer.get("resource_state") or {}).get("thermal_state"),
                "paused": observer.get("paused"),
                "raw_frames_retained": False,
            })
            return {"accepted": True, "spoken_response": spoken, "observer": observer}
        if group == "screen":
            fused = self.screen_understanding.correct(
                observation_id=str(arguments.get("observation_id") or ""),
                field=str(arguments.get("field") or "scene"),
                value=str(arguments.get("value") or ""),
                persona_id=str(self.local_persona["persona_id"]),
            )
            self.store.append_audit(
                "screen_understanding_corrected",
                {
                    "observation_id": fused["observation_id"],
                    "field": str(arguments.get("field") or "scene"),
                    "value_hash": canonical_hash(str(arguments.get("value") or "")),
                    "persona_id": self.local_persona["persona_id"],
                },
            )
            return {"accepted": True, "spoken_response": "Your correction is attached to this observation.", "screen_understanding": fused}
        if group == "education":
            if command == "education_start":
                education = self.education.start(
                    str(arguments.get("profile_id") or "explorer_a"),
                    age_band=str(arguments.get("age_band") or "") or None,
                    difficulty=str(arguments.get("difficulty") or "") or None,
                    subject=str(arguments.get("subject") or "") or None,
                )
                if canvas_url is None or canvas_view_callback is None:
                    raise RuntimeError("The secure TV Canvas is not running")
                canvas_view_callback("education")
                receipt = WebOsGateway(self.base_dir / "pairing" / "webos").execute_governed_action(
                    node_id=integrated.profile.node_id,
                    host=self._refresh_webos_host(integrated),
                    action="open_url",
                    arguments={"target": f"{canvas_url}/education"},
                    maximum_voice_volume=50,
                )
                self.store.save_webos_action_receipt(receipt, source="private_phone_education")
                result = {
                    "accepted": True,
                    "receipt": receipt.to_dict(),
                    "receipts": [receipt.to_dict()],
                    "education": education,
                    "spoken_response": "Spanish Learning Centre is on the TV. Choose an answer on the phone.",
                }
            elif command == "education_answer":
                education = self.education.answer(int(arguments.get("choice_index", -1)))
                result = {"accepted": True, "education": education, "spoken_response": str((education.get("session") or {}).get("feedback") or "Answer checked.")}
            elif command == "education_next":
                education = self.education.next_round()
                result = {"accepted": True, "education": education, "spoken_response": "Next Spanish challenge."}
            elif command == "education_pronunciation":
                assessment = self.education.assess_pronunciation(str(arguments.get("recognised_text") or ""))
                education = assessment["education"]
                result = {
                    "accepted": True, "education": education, "pronunciation": assessment["assessment"],
                    "spoken_response": str(assessment["assessment"]["feedback"]),
                }
            elif command == "education_parent_report":
                profile_id = str(arguments.get("profile_id") or "explorer_a")
                report = self.education.parent_report(profile_id, guardian_persona_id=str(self.local_persona["persona_id"]))
                education = self.education.snapshot()
                result = {"accepted": True, "education": education, "parent_report": report, "spoken_response": "The private parent progress report is ready on this phone."}
            elif command == "education_parent_correction":
                profile_id = str(arguments.get("profile_id") or "explorer_a")
                correction = self.education.record_parent_correction(
                    profile_id, guardian_persona_id=str(self.local_persona["persona_id"]),
                    card_id=str(arguments.get("card_id") or "general"), note=str(arguments.get("note") or ""),
                )
                education = self.education.snapshot()
                result = {"accepted": True, "education": education, "parent_correction": correction, "spoken_response": "The private learning correction is saved for future practice."}
            else:
                education = self.education.repeat()
                result = {"accepted": True, "education": education, "spoken_response": "Repeating the Spanish."}
            self.store.append_audit(
                "education_interaction",
                {
                    "node_id": integrated.profile.node_id,
                    "command": command,
                    "profile_id": str(((education.get("session") or {}).get("profile_id") or "")),
                    "round_number": int(((education.get("session") or {}).get("round_number") or 0)),
                    "raw_child_voice_retained": False,
                },
            )
            return result
        if command in {"pointer_move", "pointer_click"}:
            dx = int(arguments.get("dx", 0))
            dy = int(arguments.get("dy", 0))
            if command == "pointer_click":
                dx = dy = 0
            receipt = WebOsGateway(self.base_dir / "pairing" / "webos").execute_governed_action(
                node_id=integrated.profile.node_id,
                host=self._refresh_webos_host(integrated),
                action=command,
                arguments={"dx": dx, "dy": dy} if command == "pointer_move" else {},
                maximum_voice_volume=50,
            )
            self.store.save_webos_action_receipt(receipt, source="private_phone_pointer")
            result = {
                "accepted": True,
                "receipt": receipt.to_dict(),
                "receipts": [receipt.to_dict()],
                "spoken_response": "Pointer moved." if command == "pointer_move" else "TV pointer clicked.",
            }
        elif command == "observe":
            host = self._refresh_webos_host(integrated)
            receipt = WebOsGateway(self.base_dir / "pairing" / "webos").execute_governed_action(
                node_id=integrated.profile.node_id,
                host=host,
                action="observe_state",
                arguments={},
                maximum_voice_volume=50,
            )
            self.store.save_webos_action_receipt(receipt, source="private_phone_controller")
            observed = receipt.after
            app_id = str(observed.get("foreground_app_id") or "").lower()
            surface = "netflix" if app_id == "netflix" else "youtube" if "youtube" in app_id else "aion_canvas" if "browser" in app_id else "media_app"
            self.tv_autopilot.observe(
                surface=surface,
                confidence=0.93,
                evidence=f"webOS reported foreground app {app_id or 'unknown'} from a private phone refresh",
            )
            result = {
                "accepted": True,
                "receipt": receipt.to_dict(),
                "receipts": [receipt.to_dict()],
                "spoken_response": f"TV state refreshed. {observed.get('foreground_app_title') or app_id}; volume {observed.get('volume')}.",
            }
        else:
            phrases = {
                "up": "Pilot go up", "down": "Pilot go down", "left": "Pilot go left", "right": "Pilot go right",
                "enter": "Pilot press OK", "back": "Pilot go back", "home": "Pilot go home", "volume_up": "Pilot turn up the TV",
                "volume_down": "Pilot turn down the TV", "play": "Pilot play", "pause": "Pilot pause",
                "mute": "Pilot mute the TV", "unmute": "Pilot unmute the TV", "netflix": "Pilot open Netflix",
                "youtube": "Pilot open YouTube", "aion": "Pilot take over the TV",
                "games": "Pilot open games",
                "god_view": "Pilot open God View",
                "accept_google": "Pilot accept Google",
                "profile_1": "Pilot select the first Netflix profile",
                "profile_2": "Pilot select the second Netflix profile",
                "profile_3": "Pilot select the third Netflix profile",
                "profile_4": "Pilot select the fourth Netflix profile",
                "profile_5": "Pilot select the fifth Netflix profile",
                "profile_menu": "Pilot open Netflix profile chooser",
            }
            if command == "service_details":
                proposal = self.service_hub.update_details(
                    str(arguments.get("proposal_id") or ""),
                    persona_id=str(self.local_persona["persona_id"]),
                    details=dict(arguments.get("details") or {}),
                )
                return {"accepted": True, "spoken_response": "The private service details are complete and ready for exact approval." if proposal["status"] == "awaiting_private_approval" else "More private details are still required.", "service_proposal": proposal}
            if command == "claim_task":
                task = self.tv_agent.latest()
                if not task or task.get("route") not in {"calendar", "communication", "shopping", "booking"}:
                    raise ValueError("There is no consequential task waiting to be claimed")
                approval = dict(task.get("approval") or {})
                approval_id = str(approval.get("approval_id") or "")
                existing = self.service_hub.for_agent_approval(approval_id)
                if existing:
                    return {"accepted": True, "spoken_response": "This action is already prepared for private review.", "service_proposal": existing}
                service_name = "email" if task["route"] == "communication" else str(task["route"])
                prepared = dict(task.get("prepared_result") or {})
                proposal = self.service_hub.prepare(
                    persona_id=str(self.local_persona["persona_id"]),
                    service=service_name,
                    action=f"prepare_{service_name}",
                    parameters={
                        "request": str(task.get("request") or "")[:500],
                        "summary": str(prepared.get("summary") or "")[:700],
                        "items": list(prepared.get("items") or [])[:5],
                    },
                    agent_approval_id=approval_id,
                )
                self.store.append_audit("service_task_claimed_by_private_persona", {"task_id": task["task_id"], "proposal_id": proposal["proposal_id"], "persona_id": self.local_persona["persona_id"]})
                return {"accepted": True, "spoken_response": "The action is now bound to this private identity. Review its exact scope before approving.", "service_proposal": proposal}
            if command.startswith("profile_"):
                active_navigation = dict(self.verified_navigation.snapshot().get("active") or {})
                latest_perception = dict(self.phone_perception.latest() or {})
                latest_inference = dict(latest_perception.get("inference") or {})
                observed_text = " ".join(str(value) for value in latest_perception.get("texts") or []).lower()
                chooser_visible = (
                    active_navigation.get("goal") == "profile_menu"
                    and active_navigation.get("status") in {"awaiting_after_observation", "recovery_ready"}
                ) or latest_inference.get("view") == "profile_chooser" or any(
                    phrase in observed_text for phrase in ("choose a profile", "choose profile", "who's watching", "whos watching")
                )
                if chooser_visible:
                    position_words = {"profile_1": "first", "profile_2": "second", "profile_3": "third", "profile_4": "fourth", "profile_5": "fifth"}
                    transcript = f"Pilot select visible {position_words[command]} Netflix profile"
                else:
                    transcript = phrases[command]
            elif command == "netflix_search":
                query = " ".join(str(arguments.get("query") or "").split()).strip()[:120]
                if not query:
                    raise ValueError("Enter a Netflix title to verify")
                transcript = f"Pilot search Netflix for {query}"
            elif command == "ask":
                text = " ".join(str(arguments.get("text") or "").split()).strip()[:300]
                if len(text) < 2:
                    raise ValueError("Type a request for AION")
                transcript = text if re.search(r"\bpilot\b", text, re.IGNORECASE) else f"Pilot {text}"
            else:
                transcript = phrases[command]
            if group != "agent":
                latest_perception = self.phone_perception.latest() or {}
                expected = (
                    "profile_selected" if command.startswith("profile_")
                    else "google_consent_dismissed" if command == "accept_google"
                    else "surface:netflix" if command == "netflix"
                    else "surface:youtube" if command == "youtube"
                    else "surface:aion_canvas" if command == "aion"
                    else "surface:games" if command == "games"
                    else "surface:aion_canvas" if command == "god_view"
                    else "screen_changed" if group == "navigation"
                    else "device_state_changed"
                )
                self.phone_navigation.begin(
                    command,
                    expected=expected,
                    before_image_sha256=str(latest_perception.get("image_sha256") or "") or None,
                )
            result = self.execute_voice_command(
                transcript,
                canvas_url=canvas_url,
                canvas_view_callback=canvas_view_callback,
                companion_url=companion_url,
                conversation_channel="private_phone",
                persona_id=str(self.local_persona["persona_id"]),
            )
        if navigation_transaction and isinstance(result.get("receipt"), dict):
            transaction = self.verified_navigation.record_action_receipt(dict(result["receipt"]))
            result["verified_navigation"] = transaction
            qualification = self.tv_reliability.record_navigation(transaction)
            if qualification:
                result["reliability_case"] = qualification
            self.store.append_audit(
                "verified_navigation_action_observed",
                {
                    "transaction_id": transaction.get("transaction_id"),
                    "node_id": integrated.profile.node_id,
                    "goal": transaction.get("goal"),
                    "status": transaction.get("status"),
                    "transaction_hash": transaction.get("transaction_hash"),
                    "button_delivery_alone_is_success": False,
                },
            )
        self.store.append_audit(
            "companion_command_executed",
            {
                "node_id": integrated.profile.node_id,
                "command": command,
                "arguments_hash": canonical_hash(arguments),
                "accepted": bool(result.get("accepted")),
            },
        )
        return result

    def send_private_tv_text(self, text: str, *, purpose: str) -> Dict[str, Any]:
        """Deliver private phone text to the focused LG field without persistence."""
        if purpose not in {"username", "password", "game_search"}:
            raise PermissionError("That private keyboard purpose is not allowed")
        integrated = next(
            (
                node for node in self.store.list_nodes()
                if node.enrollment is EnrollmentState.ENROLLED
                and node.profile.metadata.get("webos_integration") == "connected"
            ),
            None,
        )
        if integrated is None:
            raise RuntimeError("No integrated television is available")
        capsule = self.store.latest_capsule_for_node(integrated.profile.node_id)
        permitted = {item["capability_id"] for item in capsule.capabilities} if capsule else set()
        if "companion.webos.private_keyboard" not in permitted:
            raise PermissionError("The signed private keyboard capability is unavailable")
        result = WebOsGateway(self.base_dir / "pairing" / "webos").send_ephemeral_text(
            node_id=integrated.profile.node_id,
            host=self._refresh_webos_host(integrated),
            text=text,
            replace=True,
        )
        return {
            **result,
            "purpose": purpose,
            "spoken_response": "Private text was delivered to the focused TV field and was not retained by AION.",
        }

    def execute_private_entertainment(self, execution_id: str, *, persona_id: str) -> Dict[str, Any]:
        """Open a privately confirmed official route and record only device-observed facts."""
        execution = self.entertainment_execution.get(execution_id, persona_id=persona_id)
        if execution.get("status") != "approved_for_device_attempt":
            raise PermissionError("Confirm that exact entertainment route on the private phone first")
        integrated = next(
            (
                node for node in self.store.list_nodes()
                if node.enrollment is EnrollmentState.ENROLLED
                and node.profile.metadata.get("webos_integration") == "connected"
            ),
            None,
        )
        if integrated is None:
            raise RuntimeError("No integrated television is available")
        capsule = self.store.latest_capsule_for_node(integrated.profile.node_id)
        permitted = {item["capability_id"] for item in capsule.capabilities} if capsule else set()
        if "companion.webos.app.launch" not in permitted:
            raise PermissionError("The signed private app-launch capability is unavailable")
        if execution["provider"] == "Netflix":
            action = "netflix_search"
            arguments = {
                "query": execution["title"],
                "title": execution["title"],
                "title_id": execution["provider_content_id"],
                "official_url": execution["canonical_url"],
            }
        else:
            action = "open_public_url"
            arguments = {"target": execution["canonical_url"]}
        receipt = WebOsGateway(self.base_dir / "pairing" / "webos").execute_governed_action(
            node_id=integrated.profile.node_id,
            host=self._refresh_webos_host(integrated),
            action=action,
            arguments=arguments,
            maximum_voice_volume=50,
        )
        self.store.save_webos_action_receipt(receipt, source="private_verified_entertainment")
        result = self.entertainment_execution.record_attempt(
            execution_id,
            persona_id=persona_id,
            receipt=receipt.to_dict(),
        )
        self.store.append_audit(
            "private_entertainment_provider_route_attempted",
            {
                "execution_id": execution_id,
                "persona_id": persona_id,
                "provider": result["provider"],
                "route_hash": result["route_hash"],
                "device_receipt_id": receipt.receipt_id,
                "provider_open_verified": result["provider_open_verified"],
                "playback_verified": result["playback_verified"],
                "raw_url_recorded_in_audit": False,
            },
        )
        return {"accepted": True, "entertainment_execution": result, "receipt": receipt.to_dict()}

    def accept_provider_telemetry(self, envelope: Dict[str, Any], signature: str) -> Dict[str, Any]:
        """Accept signed provider facts and reconcile a matching private execution."""
        telemetry = self.provider_telemetry.accept(envelope, signature)
        execution = self.entertainment_execution.reconcile_telemetry(telemetry)
        self.store.append_audit(
            "signed_provider_telemetry_accepted",
            {
                "telemetry_id": telemetry["telemetry_id"],
                "source_id": telemetry["source_id"],
                "provider": telemetry["provider"],
                "persona_id": telemetry["persona_id"],
                "record_hash": telemetry["record_hash"],
                "playback_state": telemetry["playback"].get("state"),
                "entitlement_verified": telemetry["entitlement"].get("verified"),
                "execution_id": (execution or {}).get("execution_id"),
                "raw_provider_response_retained": False,
                "provider_secret_exposed": False,
            },
        )
        return {"accepted": True, "provider_telemetry": telemetry, "entertainment_execution": execution}

    def accept_phone_perception(self, payload: bytes, media_type: str, observer_token: str | None = None) -> Dict[str, Any]:
        integrated = next(
            (node for node in self.store.list_nodes() if node.profile.metadata.get("webos_integration") == "connected"),
            None,
        )
        if integrated is None:
            raise RuntimeError("No integrated television is available")
        capsule = self.store.latest_capsule_for_node(integrated.profile.node_id)
        permitted = {item["capability_id"] for item in capsule.capabilities} if capsule else set()
        if "companion.webos.perception.submit" not in permitted:
            raise PermissionError("The signed phone perception capability is unavailable")
        observer = self.observer_sessions.accept_frame(observer_token) if observer_token else None
        record = self.phone_perception.analyze(payload, media_type)
        live = self.live_context.latest() or {}
        state = dict(integrated.profile.metadata.get("webos_latest_state") or {})
        app = dict(live.get("app") or {})
        foreground = dict(state.get("foreground_app") or {})
        references = [
            value
            for value in [
                *(record.get("texts") or []),
                *(dict(live.get("playback") or {}).values()),
            ]
            if str(value or "").startswith("https://")
        ]
        prior_timeline = dict(self.perception_timeline.snapshot().get("current") or {})
        prior_programme = dict(prior_timeline.get("programme") or {})
        current_surface = str((record.get("inference") or {}).get("surface") or "unknown")
        programme_candidates = [
            str(value).strip()
            for value in (
                (live.get("playback") or {}).get("media_title"),
                (live.get("playback") or {}).get("title"),
            )
            if str(value or "").strip()
        ]
        if (
            prior_programme.get("stable")
            and prior_programme.get("identity_source") == "repeated_ocr"
            and str(prior_timeline.get("surface") or "") == current_surface
            and prior_programme.get("title")
        ):
            programme_candidates.append(str(prior_programme["title"]))
        provider = self.provider_metadata.resolve(
            references,
            app_id=str(foreground.get("appId") or foreground.get("app_id") or app.get("id") or ""),
            app_title=str(foreground.get("title") or foreground.get("appName") or app.get("title") or ""),
            programme_candidates=programme_candidates,
        )
        telemetry_provider = str(
            provider.get("application_provider_hint")
            or provider.get("provider")
            or ""
        )
        telemetry = self.provider_telemetry.latest(
            persona_id=str(self.local_persona["persona_id"]),
            provider=telemetry_provider if telemetry_provider not in {"", "unknown", "programme_catalogue"} else None,
        )
        fused = self.screen_understanding.fuse(
            perception=record,
            device_state=state,
            live_context=live,
            belief=dict(self.tv_autopilot.snapshot().get("belief") or {}),
            provider_metadata=provider,
            provider_telemetry=telemetry,
        )
        record["screen_understanding"] = fused
        record["provider_metadata"] = provider
        record["provider_telemetry"] = telemetry
        if observer:
            record["observer"] = observer
        timeline = self.perception_timeline.accept(
            perception=record,
            fused=fused,
            observer_session_id=str((observer or {}).get("session_id") or "") or None,
            provider_telemetry=telemetry,
        )
        record["multi_frame_perception"] = timeline
        navigation_result = self.phone_navigation.verify(record)
        universal_navigation_result = self.verified_navigation.record_observation(record)
        inference = dict(record.get("inference") or {})
        surface = str(inference.get("surface") or "unknown")
        if surface in {"unknown", "aion_canvas", "netflix", "youtube", "games", "hdmi", "media_app", "web_browser"}:
            self.tv_autopilot.observe(
                surface=surface,
                view=str(inference.get("view") or "camera_observation"),
                confidence=float(inference.get("confidence") or 0),
                evidence=f"Owner-captured phone vision: {inference.get('summary') or 'no supported surface identified'}",
            )
        self.store.append_audit(
            "phone_visual_perception_accepted",
            {
                "node_id": integrated.profile.node_id,
                "image_sha256": record["image_sha256"],
                "image_bytes": record["image_bytes"],
                "image_retained": False,
                "surface": surface,
                "view": inference.get("view"),
                "confidence": inference.get("confidence"),
                "screen_observation_id": fused["observation_id"],
                "screen_evidence_hash": fused["evidence_hash"],
                "observer_session_id": (observer or {}).get("session_id"),
                "timeline_evidence_hash": timeline.get("evidence_hash"),
                "timeline_frame_count": timeline.get("frame_count"),
                "timeline_surface_stable": timeline.get("surface_stable"),
                "signed_provider_telemetry": bool(telemetry),
            },
        )
        if navigation_result is not None:
            self.tv_autopilot.record_navigation_attempt(
                action=f"phone.{navigation_result['action']}",
                expected=str(navigation_result["expected"]),
                observed=str(navigation_result["evidence"]),
                success=bool(navigation_result["success"]),
            )
            record["navigation_verification"] = navigation_result
        if universal_navigation_result is not None:
            record["verified_navigation"] = universal_navigation_result
            qualification = self.tv_reliability.record_navigation(universal_navigation_result)
            if qualification:
                record["reliability_case"] = qualification
            self.store.append_audit(
                "verified_navigation_after_observation",
                {
                    "transaction_id": universal_navigation_result.get("transaction_id"),
                    "status": universal_navigation_result.get("status"),
                    "transaction_hash": universal_navigation_result.get("transaction_hash"),
                    "source_frame_retained": False,
                },
            )
        return record

    def execute_voice_command(
        self,
        transcript: str,
        *,
        canvas_url: str | None = None,
        canvas_view_callback: Callable[[str], None] | None = None,
        companion_url: str | None = None,
        conversation_channel: str = "shared_tv",
        persona_id: str | None = None,
        recent_context: list[str] | None = None,
    ) -> Dict[str, Any]:
        intent = parse_voice_intent(transcript)
        if intent is None:
            return {"accepted": False, "spoken_response": "Wake phrase not detected."}
        if intent.action == "wake_acknowledged":
            return {"accepted": True, "intent": intent.to_dict(), "spoken_response": "Yes?"}
        if intent.action == "voice_sleep":
            self.store.append_audit("voice_microphone_sleep_requested", {"transcript_hash": canonical_hash(transcript)})
            return {
                "accepted": True,
                "intent": intent.to_dict(),
                "spoken_response": "Going to sleep. The microphone is now off. Resume me from the local dashboard.",
            }
        if intent.action == "emergency_stop":
            agent_task = self.tv_agent.cancel_active(reason="voice_owner_cancelled")
            conversation = self.conversation_memory.cancel_active()
            tv_plan = self.tv_autopilot.cancel_active(summary="Cancelled by owner voice command")
            navigation = self.verified_navigation.cancel_active(reason="voice_owner_cancelled")
            services = self.service_hub.cancel_pending(persona_id=str(self.local_persona["persona_id"]))
            cancelled_layers = [
                name for name, value in {
                    "agent_task": agent_task,
                    "conversation": conversation,
                    "tv_plan": tv_plan,
                    "navigation": navigation,
                }.items() if value is not None
            ]
            self.store.append_audit(
                "voice_emergency_stop",
                {
                    "transcript_hash": canonical_hash(transcript),
                    "cancelled_layers": cancelled_layers,
                    "service_proposals_cancelled": services["cancelled_count"],
                    "in_flight_not_claimed_cancelled": len(services["in_flight_not_claimed_cancelled"]),
                },
            )
            caution = (
                " An external adapter may already be in flight and requires reconciliation."
                if services["in_flight_not_claimed_cancelled"] else ""
            )
            return {
                "accepted": True,
                "intent": intent.to_dict(),
                "spoken_response": f"Stopped. Cancelled {len(cancelled_layers)} active layers and {services['cancelled_count']} pending service actions.{caution}",
                "cancellation": {
                    "cancelled_layers": cancelled_layers,
                    "service_proposals_cancelled": services["cancelled_count"],
                    "in_flight_not_claimed_cancelled": services["in_flight_not_claimed_cancelled"],
                },
            }
        if intent.action == "blocked_power":
            return {
                "accepted": False,
                "intent": intent.to_dict(),
                "spoken_response": "TV power control is not enabled yet.",
            }
        if intent.action == "climate_ir":
            preset = str(intent.arguments.get("preset") or "")
            try:
                receipt = self.infrared_climate.send_last_active() if preset == "last_active" else self.infrared_climate.send(preset)
            except Exception as exc:
                return {"accepted": False, "intent": intent.to_dict(), "spoken_response": str(exc)}
            self.store.append_audit(
                "voice_local_ir_command_delivered",
                {
                    "transcript_hash": canonical_hash(transcript),
                    "preset": receipt["preset"],
                    "code_sha256": receipt["code_sha256"],
                    "transport_delivered": True,
                    "air_conditioner_state_verified": False,
                },
            )
            return {
                "accepted": True,
                "intent": intent.to_dict(),
                "spoken_response": (
                    f"I sent Toshiba {receipt['preset'].replace('_', ' ')}. "
                    "The infrared command was delivered, but the unit cannot report its state back."
                ),
                "infrared_climate": receipt,
            }
        if intent.action in {"guardian_help", "guardian_confirm", "guardian_cancel"}:
            identities = self.private_identity.snapshot()
            active = dict(identities.get("active_shared_identity") or {})
            protected_persona = str(persona_id or active.get("persona_id") or "")
            if not protected_persona:
                return {
                    "accepted": False, "intent": intent.to_dict(),
                    "spoken_response": (
                        "I heard the urgent request, but I cannot safely identify the person. "
                        "Use the phone emergency button or call local emergency services directly."
                    ),
                }
            incidents = list(self.guardian.snapshot(persona_id=protected_persona).get("incidents") or [])
            latest = next((item for item in reversed(incidents) if item.get("status") not in {"cancelled", "alerts_verified"}), None)
            if intent.action == "guardian_help":
                result = self.guardian.request_help(
                    persona_id=protected_persona, trigger=str(intent.arguments.get("trigger") or transcript),
                    surface=conversation_channel,
                )
                spoken = (
                    "I have opened the large Guardian confirmation. Say Pilot, confirm emergency alert, "
                    "to alert your authorized trusted contacts, or say Pilot, false alarm, to cancel. "
                    "I have not contacted an ambulance."
                )
                event = "guardian_help_confirmation_opened"
            elif latest is None:
                return {"accepted": False, "intent": intent.to_dict(), "spoken_response": "There is no active Guardian alert."}
            elif intent.action == "guardian_cancel":
                result = self.guardian.cancel(incident_id=str(latest["incident_id"]), persona_id=protected_persona)
                spoken, event = "The Guardian alert is cancelled as a false alarm.", "guardian_alert_cancelled"
            else:
                try:
                    result = self.guardian.confirm(incident_id=str(latest["incident_id"]), persona_id=protected_persona)
                except RuntimeError as exc:
                    return {"accepted": False, "intent": intent.to_dict(), "spoken_response": f"{exc}. Call local emergency services directly if you need urgent help."}
                spoken = (
                    "The urgent trusted-contact alert is confirmed and ready for its authorized delivery route. "
                    "Pilot has not contacted an ambulance and will not claim that it has."
                )
                event = "guardian_trusted_contact_alert_confirmed"
            self.store.append_audit(event, {
                "incident_id": result.get("incident_id"), "persona_id": protected_persona,
                "ambulance_dispatched": False, "medical_diagnosis_made": False,
            })
            return {"accepted": True, "intent": intent.to_dict(), "spoken_response": spoken, "guardian": result}
        if intent.action == "web_research" and intent.arguments.get("mode") == "contextual":
            active_surface = str(self.tv_autopilot.snapshot().get("belief", {}).get("surface") or "")
            if active_surface == "netflix":
                intent = replace(intent, action="netflix_search", arguments={"query": intent.arguments["query"]})
            else:
                intent = replace(intent, arguments={**intent.arguments, "mode": "general"})
        if intent.action == "unknown":
            return {
                "accepted": False,
                "intent": intent.to_dict(),
                "spoken_response": "I heard you, but that TV command is not enabled.",
            }
        self.conversation_memory.record_turn(
            "user",
            transcript,
            channel=conversation_channel,
            intent=intent.action,
        )
        if intent.action == "conversation_pause":
            paused = self.conversation_memory.pause_active()
            spoken = "I saved that task for later." if paused else "There is no active conversational task to pause."
            self.conversation_memory.record_turn("assistant", spoken, channel=conversation_channel, intent=intent.action)
            self.store.append_audit("conversation_task_paused", {"had_active_task": bool(paused)})
            return {"accepted": bool(paused), "intent": intent.to_dict(), "spoken_response": spoken, "conversation": self.conversation_memory.snapshot(channel=conversation_channel)}
        if intent.action == "conversation_resume":
            resumed = self.conversation_memory.resume_previous()
            if not resumed:
                spoken = "There is no paused task to resume."
                self.conversation_memory.record_turn("assistant", spoken, channel=conversation_channel, intent=intent.action)
                return {"accepted": False, "intent": intent.to_dict(), "spoken_response": spoken, "conversation": self.conversation_memory.snapshot(channel=conversation_channel)}
            intent = replace(intent, action="agent_request", arguments={"request": resumed["composed_request"], "resumed": True})
        record = next(
            (
                item
                for item in self.store.list_nodes()
                if item.enrollment is EnrollmentState.ENROLLED
                and item.profile.metadata.get("voice_control") == "enabled"
                and item.profile.metadata.get("webos_pairing") == "paired"
            ),
            None,
        )
        if record is None:
            return {"accepted": False, "spoken_response": "No voice-enabled television is connected."}
        capability_for_action = {
            "get_volume": "voice.webos.volume.read",
            "set_volume": "voice.webos.volume.control",
            "change_volume": "voice.webos.volume.control",
            "set_mute": "voice.webos.mute.control",
            "media_play": "voice.webos.media.control",
            "media_pause": "voice.webos.media.control",
            "media_stop": "voice.webos.media.control",
            "switch_input": "voice.webos.input.control",
            "launch_app": "voice.webos.app.launch",
            "open_games": "voice.games.launch",
            "game_continue": "voice.games.launch",
            "education_start": "voice.education.start",
            "show_canvas": "voice.webos.canvas.open",
            "scene_movie": "voice.webos.scene.movie",
            "remote_button": "voice.webos.navigation.control",
            "netflix_profile": "voice.webos.navigation.control",
            "netflix_profile_menu": "voice.webos.navigation.control",
            "netflix_saved_profile": "voice.webos.navigation.control",
            "netflix_search": "voice.webos.navigation.control",
            "web_research": "voice.web.research",
            "open_research_result": "voice.web.result.open",
            "show_research_results": "voice.webos.canvas.open",
            "google_consent_accept": "voice.webos.navigation.control",
            "exit_content": "voice.webos.navigation.control",
            "continue_last": "voice.webos.app.launch",
            "scene_evening": "voice.webos.volume.control",
            "agent_request": "voice.agent.plan",
            "entertainment_search": "voice.entertainment.research",
            "entertainment_recommend": "voice.entertainment.research",
            "entertainment_feedback": "voice.entertainment.memory",
            "live_explain": "voice.live.context.read",
            "live_translate": "voice.live.translate",
            "live_sports": "voice.live.sports",
            "live_event": "voice.live.event.feed",
            "private_save_prepare": "voice.private-save.prepare",
            "live_fact_check": "voice.live.fact_check",
            "live_fact_followup": "voice.live.fact_check",
            "share_moment": "voice.moment.prepare",
            "screen_query": "voice.live.context.read",
            "inbox_summary": "voice.inbox.manage",
            "inbox_add_self": "voice.inbox.manage",
            "inbox_delegate_spoken": "voice.inbox.manage",
            "inbox_message_spoken": "voice.inbox.manage",
            "identity_logout": "voice.inbox.manage",
        }
        capability_id = capability_for_action[intent.action]
        capsule = self.store.latest_capsule_for_node(record.profile.node_id)
        permitted = {item["capability_id"] for item in capsule.capabilities} if capsule else set()
        if capability_id not in permitted:
            raise PermissionError(f"The signed voice capability {capability_id} is unavailable")
        private_workspace_views = {"tasks", "calendar", "boardroom", "files", "iot", "work"}
        requested_view = str(intent.arguments.get("view") or "")
        if intent.action == "show_canvas" and requested_view in private_workspace_views:
            active_session = dict(self.private_identity.snapshot().get("active_shared_identity") or {})
            if not active_session.get("persona_id"):
                label = "Business" if requested_view == "boardroom" else requested_view.replace("_", " ").title()
                return {
                    "accepted": False, "intent": intent.to_dict(),
                    "spoken_response": f"Your {label} workspace is locked. Acquire the television from your trusted phone first.",
                }
        if intent.action != "identity_logout":
            active_session = dict(self.private_identity.snapshot().get("active_shared_identity") or {})
            if active_session.get("persona_id"):
                self.private_identity.touch_shared_screen(
                    persona_id=str(active_session["persona_id"]), source="shared_tv_voice"
                )
        if intent.action == "identity_logout":
            active = dict(self.private_identity.snapshot().get("active_shared_identity") or {})
            result = self.private_identity.release_shared_screen(
                persona_id=str(active.get("persona_id") or "") or None,
                reason="explicit_voice_logout",
            )
            self.store.append_audit("shared_screen_identity_released", {
                "persona_id": active.get("persona_id"), "reason": "explicit_voice_logout",
                "private_details_on_shared_screen": False,
            })
            return {"accepted": True, "intent": intent.to_dict(), "spoken_response": "You are logged out. The television workspace is locked.", "result": result}
        if intent.action in {"inbox_summary", "inbox_add_self", "inbox_delegate_spoken", "inbox_message_spoken"}:
            active = dict(self.private_identity.snapshot().get("active_shared_identity") or {})
            active_persona = str(active.get("persona_id") or "")
            if not active_persona:
                return {
                    "accepted": False, "intent": intent.to_dict(),
                    "spoken_response": "No private person is signed in on this shared screen. Confirm your identity from your trusted phone first.",
                }
            self.private_identity.touch_shared_screen(persona_id=active_persona, source="shared_tv_voice")
            if intent.action == "inbox_summary":
                summary = self.pilot_inbox.shared_summary(persona_id=active_persona)
                spoken = f"You have {summary['open_tasks']} open tasks and {summary['waiting_for_acceptance']} task requests waiting for acceptance. I kept the private titles on your phone."
                result = summary
                event = "shared_tv_task_summary_read"
            elif intent.action == "inbox_add_self":
                result = self.pilot_inbox.create_task(requester_persona_id=active_persona, owner_persona_id=active_persona, title=str(intent.arguments.get("title") or ""), source={"surface": "shared_tv", "explicit_voice": True})
                spoken, event = "That is now on your private Pilot task list.", "shared_tv_private_task_added"
            else:
                profiles = list(self.private_identity.snapshot().get("profiles") or [])
                requested_name = str(intent.arguments.get("recipient_name") or "").casefold().strip()
                matches = [item for item in profiles if str(item.get("display_name") or "").casefold() == requested_name]
                contact_matches = self.pilot_inbox.resolve_spoken_contacts(owner_persona_id=active_persona, display_name=requested_name)
                if len(matches) == 1:
                    recipient = str(matches[0]["persona_id"])
                    if intent.action == "inbox_delegate_spoken":
                        result = self.pilot_inbox.create_task(requester_persona_id=active_persona, owner_persona_id=active_persona, assignee_persona_id=recipient, title=str(intent.arguments.get("title") or ""), source={"surface": "shared_tv", "explicit_voice": True})
                        spoken, event = f"I sent {matches[0]['display_name']} a task request. It is not assigned until they accept it.", "shared_tv_task_request_sent"
                    else:
                        result = self.pilot_inbox.send_message(sender_persona_id=active_persona, recipient_persona_id=recipient, body=str(intent.arguments.get("body") or ""))
                        spoken, event = f"The message is in {matches[0]['display_name']}'s Pilot inbox.", "shared_tv_pilot_message_sent"
                elif len(matches) == 0 and len(contact_matches) == 1 and intent.action == "inbox_delegate_spoken":
                    contact = contact_matches[0]
                    pilot_recipient = str(contact.get("pilot_persona_id") or "")
                    if pilot_recipient:
                        result = self.pilot_inbox.create_task(requester_persona_id=active_persona, owner_persona_id=active_persona, assignee_persona_id=pilot_recipient, title=str(intent.arguments.get("title") or ""), source={"surface": "shared_tv", "explicit_voice": True})
                        spoken, event = f"I sent {contact['display_name']} a Pilot task request. It is not assigned until they accept it.", "shared_tv_task_request_sent"
                    else:
                        result = self.pilot_inbox.prepare_external_task(sender_persona_id=active_persona, contact_id=str(contact["contact_id"]), title=str(intent.arguments.get("title") or ""))
                        spoken = f"I prepared the task for {contact['display_name']} by {result['channel']}. Review it on your phone. It has not been sent."
                        event = "shared_tv_external_task_prepared"
                else:
                    return {"accepted": False, "intent": intent.to_dict(), "spoken_response": "I could not resolve exactly one recipient. Add or choose the contact privately on your phone."}
            self.store.append_audit(event, {"persona_id": active_persona, "object_id": result.get("task_id") or result.get("message_id"), "private_titles_on_shared_screen": False, "external_effect": False})
            return {"accepted": True, "intent": intent.to_dict(), "spoken_response": spoken, "pilot_inbox": result}
        if intent.action == "live_fact_followup":
            try:
                follow_up = self.live_news.follow_up(str(intent.arguments.get("kind") or "evidence"))
            except LookupError as exc:
                return {"accepted": False, "intent": intent.to_dict(), "spoken_response": str(exc)}
            spoken = str(follow_up["answer"])[:320]
            self.conversation_memory.record_turn("assistant", spoken, channel=conversation_channel, intent=intent.action)
            self.store.append_audit(
                "live_fact_check_followed_up",
                {
                    "fact_check_id": follow_up["fact_check_id"],
                    "follow_up_id": follow_up["follow_up_id"],
                    "kind": follow_up["kind"],
                    "evidence_hash": follow_up["evidence_hash"],
                    "derived_without_model": True,
                    "playback_preserved": True,
                },
            )
            return {
                "accepted": True,
                "intent": intent.to_dict(),
                "spoken_response": spoken,
                "fact_check_follow_up": follow_up,
                "live_news": self.live_news.latest(),
                "conversation": self.conversation_memory.snapshot(channel=conversation_channel),
            }
        if intent.action == "entertainment_feedback":
            remembered = self.entertainment_personalization.prepare_history(title=str(intent.arguments["title"]), outcome=str(intent.arguments["outcome"]))
            spoken = f"I prepared that {remembered['title']} preference. Claim it on the private phone so it is not assigned to the wrong household member."
            self.conversation_memory.record_turn("assistant", spoken, channel=conversation_channel, intent=intent.action)
            self.store.append_audit("entertainment_preference_prepared", {"title_hash": canonical_hash(remembered["title"]), "outcome": remembered["outcome"], "persona_bound": False})
            return {"accepted": True, "intent": intent.to_dict(), "spoken_response": spoken, "entertainment_personalization": remembered, "conversation": self.conversation_memory.snapshot(channel=conversation_channel)}
        if intent.action == "screen_query":
            screen = self.screen_understanding.latest()
            if not screen:
                return {
                    "accepted": False,
                    "intent": intent.to_dict(),
                    "spoken_response": "I do not have a current screen observation. Take a picture from the private phone controller first.",
                }
            kind = str(intent.arguments.get("kind") or "scene")
            if kind == "scoreboard":
                finding = dict(screen.get("scoreboard") or {})
                detail = str(finding.get("score_text") or finding.get("clock") or "")
            elif kind == "subtitle":
                finding = dict(screen.get("subtitles") or {})
                detail = " ".join(str(item) for item in list(finding.get("lines") or []))
            elif kind == "product":
                finding = dict(screen.get("products") or {})
                detail = str(finding.get("candidate_text") or " ".join(finding.get("prices") or []))
            elif kind == "ingredients":
                finding = dict(screen.get("cooking") or {})
                detail = ", ".join(str(value) for value in list(finding.get("ingredients") or []))
            elif kind == "technique":
                finding = dict(screen.get("cooking") or {})
                detail = ", ".join(str(value) for value in list(finding.get("techniques") or []))
            elif kind == "objects":
                finding = dict(screen.get("objects") or {})
                detail = ", ".join(str(value) for value in list(finding.get("labels") or []))
            else:
                finding = screen
                detail = str(screen.get("summary") or "")
            if not detail or (kind != "scene" and not finding.get("detected")):
                spoken = f"The latest capture does not establish a reliable {kind}. Capture the screen again if it has changed."
                accepted = False
            else:
                confidence = int(round(float(finding.get("confidence") or screen.get("confidence") or 0) * 100))
                spoken = f"From the private screen observation, at {confidence} percent confidence: {detail}"[:300]
                accepted = True
            self.store.append_audit(
                "screen_understanding_queried",
                {"observation_id": screen["observation_id"], "kind": kind, "accepted": accepted, "evidence_hash": screen["evidence_hash"]},
            )
            return {"accepted": accepted, "intent": intent.to_dict(), "spoken_response": spoken, "screen_understanding": screen}
        if intent.action == "contextual_companion":
            support = self.contextual_companion.prepare_wellbeing(
                statement=transcript,
                channel=conversation_channel if conversation_channel in {"shared_tv", "private_phone", "car"} else "shared_tv",
            )
            self.store.append_audit(
                "contextual_companion_support_prepared",
                {
                    "support_id": support["support_id"],
                    "category": support["category"],
                    "channel": support["channel"],
                    "persona_bound": bool(support.get("persona_id")),
                    "emergency_service_contacted": False,
                    "medical_diagnosis_made": False,
                    "human_or_conscious_claimed": False,
                },
            )
            return {"accepted": True, "intent": intent.to_dict(), "spoken_response": support["response"], "contextual_companion": support}
        webos_host = self._refresh_webos_host(record)
        gateway = WebOsGateway(self.base_dir / "pairing" / "webos")
        action = intent.action
        arguments = dict(intent.arguments)
        preliminary_receipts = []
        research_record = None
        agent_task = None
        if action in {"live_explain", "programme_cast", "programme_origin", "live_translate", "live_sports", "live_event", "live_engagement", "private_save_prepare", "live_fact_check", "share_moment"}:
            if "voice.webos.perception.read" not in permitted:
                raise PermissionError("The signed TV perception capability is unavailable")
            perception_receipt = gateway.execute_governed_action(
                node_id=record.profile.node_id,
                host=webos_host,
                action="observe_state",
                arguments={},
                maximum_voice_volume=50,
            )
            self.store.save_webos_action_receipt(perception_receipt, source="local_voice_live_context")
            live_context = self.live_context.build(
                device_state=dict(perception_receipt.after),
                recent_transcripts=recent_context or [],
                belief=dict(self.tv_autopilot.snapshot().get("belief") or {}),
            )
            if action == "programme_cast":
                timeline = dict(self.perception_timeline.snapshot().get("current") or {})
                cast = self.programme_companion.lookup(
                    programme=dict(timeline.get("programme") or {}),
                    provider_metadata=self.provider_metadata.latest(),
                    question_kind=str(arguments.get("kind") or "cast"),
                    character=str(arguments.get("character") or ""),
                    person=str(arguments.get("person") or ""),
                )
                self.store.append_audit(
                    "programme_cast_looked_up",
                    {
                        "node_id": record.profile.node_id,
                        "lookup_id": cast["lookup_id"],
                        "programme_title": cast["programme"].get("title"),
                        "catalogue_id": cast["programme"].get("catalogue_id"),
                        "question_kind": cast["question_kind"],
                        "identity_route": cast["identity_route"],
                        "evidence_hash": cast["evidence_hash"],
                        "face_recognition_used": False,
                        "visible_person_identified": False,
                        "playback_preserved": True,
                    },
                )
                return {
                    "accepted": cast["confidence"] > 0,
                    "intent": intent.to_dict(),
                    "spoken_response": str(cast["answer"])[:320],
                    "live_context": live_context,
                    "programme_companion": cast,
                    "receipt": perception_receipt.to_dict(),
                    "receipts": [perception_receipt.to_dict()],
                }
            if action == "programme_origin":
                timeline = dict(self.perception_timeline.snapshot().get("current") or {})
                origins = self.programme_origins.lookup(
                    programme=dict(timeline.get("programme") or {}),
                    question_kind=str(arguments.get("kind") or "original_source"),
                )
                self.store.append_audit(
                    "programme_origin_looked_up",
                    {
                        "node_id": record.profile.node_id,
                        "lookup_id": origins["lookup_id"],
                        "programme_title": origins["programme"].get("title"),
                        "question_kind": origins["question_kind"],
                        "evidence_hash": origins["evidence_hash"],
                        "source_provider": origins["source"].get("provider"),
                        "face_recognition_used": False,
                        "plot_inference_used": False,
                        "playback_preserved": True,
                    },
                )
                return {
                    "accepted": origins["confidence"] > 0,
                    "intent": intent.to_dict(),
                    "spoken_response": str(origins["answer"])[:320],
                    "live_context": live_context,
                    "programme_origins": origins,
                    "receipt": perception_receipt.to_dict(),
                    "receipts": [perception_receipt.to_dict()],
                }
            if action == "share_moment":
                latest_fact_check = self.live_news.latest()
                wants_fact_check = "fact" in transcript.lower() or "evidence" in transcript.lower()
                if wants_fact_check and latest_fact_check:
                    moment = self.pilot_moments.create_fact_check(
                        fact_check=latest_fact_check,
                        request=transcript,
                        issuer_node_id=self.profile.node_id,
                        public_key=self.identity.public_key_b64,
                        signer=self.identity.sign,
                    )
                else:
                    moment = self.pilot_moments.create(
                        context=live_context,
                        request=transcript,
                        issuer_node_id=self.profile.node_id,
                        public_key=self.identity.public_key_b64,
                        signer=self.identity.sign,
                        recipient=None,
                        requested_seconds=int(arguments.get("seconds") or 30),
                    )
                self.store.append_audit(
                    "pilot_moment_prepared",
                    {
                        "moment_id": moment["moment_id"],
                        "context_hash": moment["context_hash"],
                        "share_mode": moment["share_mode"],
                        "delivery_state": moment["delivery_state"],
                        "protected_media_copied": False,
                        "fact_check_bound": moment.get("kind") == "fact_check",
                    },
                )
                spoken = (
                    "I prepared a signed Moment on your private phone. I did not copy protected video or audio, "
                    "and I have not sent it yet."
                )
                return {
                    "accepted": True,
                    "intent": intent.to_dict(),
                    "spoken_response": spoken,
                    "live_context": live_context,
                    "moment": moment,
                    "receipt": perception_receipt.to_dict(),
                    "receipts": [perception_receipt.to_dict()],
                }

            if action == "live_sports":
                sports = self.live_sports.interpret(
                    live_context=live_context,
                    screen_understanding=self.screen_understanding.latest(),
                    question_kind=str(arguments.get("kind") or "decision"),
                    question=str(arguments.get("question") or transcript),
                )
                spoken = str(sports["answer"])[:280]
                self.store.append_audit(
                    "live_sports_interpreted",
                    {
                        "node_id": record.profile.node_id,
                        "interpretation_id": sports["interpretation_id"],
                        "evidence_hash": sports["evidence_hash"],
                        "question_kind": sports["question_kind"],
                        "scoreboard_detected": sports["scoreboard"]["detected"],
                        "observed_incident_cue": sports["observed_incident_cue"],
                        "referee_decision_verified": False,
                        "player_identity_inferred": False,
                        "playback_preserved": True,
                    },
                )
                return {
                    "accepted": sports["confidence"] > 0,
                    "intent": intent.to_dict(),
                    "spoken_response": spoken,
                    "live_context": live_context,
                    "sports": sports,
                    "receipt": perception_receipt.to_dict(),
                    "receipts": [perception_receipt.to_dict()],
                }

            if action == "live_event":
                local_sports = self.live_sports.interpret(
                    live_context=live_context,
                    screen_understanding=self.screen_understanding.latest(),
                    question_kind=str(arguments.get("kind") or "score"),
                    question=str(arguments.get("question") or transcript),
                )
                live_event = self.live_events.query(
                    question_kind=str(arguments.get("kind") or "score"),
                    question=str(arguments.get("question") or transcript),
                    local_interpretation=local_sports,
                    history_days=int(arguments["history_days"]) if str(arguments.get("history_days") or "").isdigit() else None,
                )
                self.store.append_audit(
                    "live_event_feed_queried",
                    {
                        "node_id": record.profile.node_id,
                        "event_query_id": live_event["event_query_id"],
                        "question_kind": live_event["question_kind"],
                        "provider": live_event["provider"].get("provider"),
                        "provider_connected": live_event["provider"].get("connected"),
                        "authenticated": live_event["provider"].get("authenticated", False),
                        "reconciliation": live_event["reconciliation"],
                        "evidence_hash": live_event["evidence_hash"],
                        "provider_secret_recorded": False,
                        "raw_provider_response_retained": False,
                        "playback_preserved": True,
                    },
                )
                return {
                    "accepted": live_event["confidence"] > 0,
                    "intent": intent.to_dict(),
                    "spoken_response": str(live_event["answer"])[:320],
                    "live_context": live_context,
                    "sports": local_sports,
                    "live_event": live_event,
                    "receipt": perception_receipt.to_dict(),
                    "receipts": [perception_receipt.to_dict()],
                }

            if action == "live_engagement":
                kind = str(arguments.get("kind") or "")
                if kind != "close_watch":
                    raise ValueError("That shared-room live engagement requires private phone setup")
                live_event = self.live_events.latest()
                watch = self.live_engagement.prepare_close_watch(
                    live_event=live_event,
                    margin=int(arguments.get("margin") or 1),
                )
                self.store.append_audit(
                    "live_event_watch_prepared",
                    {
                        "watch_id": watch["watch_id"],
                        "provider_match_id": watch["event"]["provider_match_id"],
                        "threshold": watch["threshold"],
                        "persona_bound": False,
                        "external_notification_sent": False,
                    },
                )
                return {
                    "accepted": True,
                    "intent": intent.to_dict(),
                    "spoken_response": "That close-match alert is ready on the private phone. Claim it there so Pilot knows who should receive it.",
                    "live_engagement": watch,
                    "receipt": perception_receipt.to_dict(),
                    "receipts": [perception_receipt.to_dict()],
                }

            if action == "private_save_prepare":
                private_save = self.private_saves.prepare(
                    category=str(arguments.get("category") or "idea"),
                    request=transcript,
                    live_context=live_context,
                    screen_understanding=self.screen_understanding.latest(),
                    provider_metadata=self.provider_metadata.latest(),
                )
                self.store.append_audit(
                    "programme_private_save_prepared",
                    {
                        "node_id": record.profile.node_id,
                        "save_id": private_save["save_id"],
                        "category": private_save["category"],
                        "evidence_hash": private_save["evidence_hash"],
                        "confidence": private_save["confidence"],
                        "shared_tv_selected_persona": False,
                        "external_action_executed": False,
                        "raw_content_recorded_in_audit": False,
                    },
                )
                spoken = (
                    f"I prepared that {private_save['category']} on the private phone. "
                    "It is not saved to anyone yet; choose Save to my Pilot on the phone."
                )
                return {
                    "accepted": True,
                    "intent": intent.to_dict(),
                    "spoken_response": spoken,
                    "live_context": live_context,
                    "private_save": private_save,
                    "receipt": perception_receipt.to_dict(),
                    "receipts": [perception_receipt.to_dict()],
                }

            statement = str(live_context.get("recent_statement") or "").strip()
            if not statement:
                screen = self.screen_understanding.latest() or {}
                corrections = list(screen.get("corrections") or [])
                corrected = next((str(item.get("value") or "") for item in reversed(corrections) if item.get("field") in {"subtitle", "scene"}), "")
                subtitle_lines = list((screen.get("subtitles") or {}).get("lines") or [])
                product_claim = str((screen.get("products") or {}).get("candidate_text") or "")
                statement = corrected or (
                    product_claim
                    if action == "live_fact_check" and str(arguments.get("kind") or "") == "product_claim"
                    else str(subtitle_lines[-1]) if subtitle_lines else ""
                )
            if not statement:
                return {
                    "accepted": False,
                    "intent": intent.to_dict(),
                    "spoken_response": (
                        "I can identify the current TV app, but I did not capture enough recent speech to explain or verify. "
                        "Ask again immediately after the claim."
                    ),
                    "live_context": live_context,
                    "receipt": perception_receipt.to_dict(),
                }
            if action == "live_translate":
                translation = self.live_translation.translate(
                    live_context=live_context,
                    screen_understanding=self.screen_understanding.latest(),
                    target_language=str(arguments.get("target_language") or "english"),
                    source_kind=str(arguments.get("source_kind") or "dialogue"),
                )
                translated = str(translation.get("translation") or "")
                target_names = {"en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian", "pt": "Portuguese"}
                target_name = target_names.get(str(translation.get("target_language") or "en"), "the requested language")
                spoken = (
                    f"In {target_name}: {translated}"[:280]
                    if translated
                    else f"I could not translate that safely. {translation['uncertainty']}"[:280]
                )
                self.store.append_audit(
                    "live_dialogue_translated",
                    {
                        "node_id": record.profile.node_id,
                        "translation_id": translation["translation_id"],
                        "evidence_hash": translation["evidence_hash"],
                        "source_evidence": translation["source_evidence"],
                        "target_language": translation["target_language"],
                        "provider": translation["provider"],
                        "internet_used": False,
                        "paid_ai_used": False,
                        "playback_preserved": True,
                    },
                )
                return {
                    "accepted": bool(translated),
                    "intent": intent.to_dict(),
                    "spoken_response": spoken,
                    "speech_language": translation["target_language"],
                    "live_context": live_context,
                    "translation": translation,
                    "receipt": perception_receipt.to_dict(),
                    "receipts": [perception_receipt.to_dict()],
                }
            if action == "live_explain":
                explanation = self.scene_explanation.explain(
                    live_context=live_context,
                    screen_understanding=self.screen_understanding.latest(),
                    request_kind=str(arguments.get("kind") or "scene"),
                    audience=str(arguments.get("audience") or "general"),
                    detail_level=str(arguments.get("detail_level") or "normal"),
                    learning_subject=str(arguments.get("learning_subject") or ""),
                )
                spoken = str(explanation["answer"])[:280]
                self.store.append_audit(
                    "spoiler_aware_scene_explained",
                    {
                        "node_id": record.profile.node_id,
                        "explanation_id": explanation["explanation_id"],
                        "context_hash": live_context["context_hash"],
                        "evidence_hash": explanation["evidence_hash"],
                        "spoiler_policy": explanation["spoiler_policy"],
                        "future_plot_sources_used": False,
                        "playback_preserved": True,
                        "provider": explanation["provider"],
                        "audience": explanation["audience"],
                        "detail_level": explanation["detail_level"],
                        "learning_subject": explanation.get("learning_subject"),
                    },
                )
                return {
                    "accepted": explanation["confidence"] > 0,
                    "intent": intent.to_dict(),
                    "spoken_response": spoken,
                    "live_context": live_context,
                    "scene_explanation": explanation,
                    "receipt": perception_receipt.to_dict(),
                    "receipts": [perception_receipt.to_dict()],
                }
            if action == "live_explain" and (canvas_url is None or canvas_view_callback is None):
                raise RuntimeError("The secure TV Canvas is not running")
            query = (
                statement
                if action == "live_fact_check"
                else f"Explain this television statement clearly and concisely: {statement}"
            )
            research_started = time.monotonic()
            research_record = self.tv_research.search(
                query,
                mode="fact_check" if action == "live_fact_check" else "live_explain",
            )
            research_latency_ms = int(round((time.monotonic() - research_started) * 1000))
            answer = str(research_record.get("answer") or "I could not establish a reliable answer.").strip()
            live_news = None
            if action == "live_fact_check":
                live_news = self.live_news.compile(
                    live_context=live_context,
                    research=research_record,
                    screen_understanding=self.screen_understanding.latest(),
                    latency_ms=research_latency_ms,
                )
                verdict = str(live_news.get("verdict") or "Unverifiable")
                spoken = answer[:280] if answer.lower().startswith(verdict.lower()) else f"{verdict}. {answer}"[:280]
                result_receipt = perception_receipt
                receipts = [perception_receipt.to_dict()]
                display_mode = "spoken_summary_and_private_phone"
            else:
                assert canvas_view_callback is not None and canvas_url is not None
                canvas_view_callback("research")
                canvas_receipt = gateway.execute_governed_action(
                    node_id=record.profile.node_id,
                    host=webos_host,
                    action="open_url",
                    arguments={"target": canvas_url},
                    maximum_voice_volume=50,
                )
                self.store.save_webos_action_receipt(canvas_receipt, source="local_voice_live_evidence")
                self.tv_autopilot.observe(
                    surface="aion_canvas",
                    view="research",
                    confidence=0.99,
                    evidence="Pilot controls the evidence-labelled live-context projection",
                )
                spoken = answer[:280]
                result_receipt = canvas_receipt
                receipts = [perception_receipt.to_dict(), canvas_receipt.to_dict()]
                display_mode = "tv_canvas_and_private_phone"
            self.store.append_audit(
                "live_context_answered",
                {
                    "node_id": record.profile.node_id,
                    "intent": action,
                    "context_hash": live_context["context_hash"],
                    "provider": research_record.get("provider"),
                    "source_count": len(research_record.get("items") or []),
                    "receipt_id": result_receipt.receipt_id,
                    "fact_check_id": (live_news or {}).get("fact_check_id"),
                    "verdict": (live_news or {}).get("verdict"),
                    "display_mode": display_mode,
                    "latency_ms": research_latency_ms,
                },
            )
            return {
                "accepted": True,
                "intent": intent.to_dict(),
                "spoken_response": spoken,
                "live_context": live_context,
                "research": research_record,
                "live_news": live_news,
                "receipt": result_receipt.to_dict(),
                "receipts": receipts,
            }
        if action == "agent_request":
            if "voice.webos.perception.read" not in permitted:
                raise PermissionError("The signed TV perception capability is unavailable")
            perception_receipt = gateway.execute_governed_action(
                node_id=record.profile.node_id,
                host=webos_host,
                action="observe_state",
                arguments={},
                maximum_voice_volume=50,
            )
            self.store.save_webos_action_receipt(perception_receipt, source="local_voice_agent_perception")
            preliminary_receipts.append(perception_receipt)
            observed = perception_receipt.after
            app_id = str(observed.get("foreground_app_id") or "unknown")
            surface = (
                "netflix" if app_id == "netflix"
                else "youtube" if "youtube" in app_id
                else "web_browser" if "browser" in app_id
                else "aion_canvas" if app_id in {"com.webos.app.browser", "webappmanager"} and canvas_url
                else "media_app"
            )
            perception = {
                **observed,
                "summary": (
                    f"Foreground app {observed.get('foreground_app_title') or app_id}; "
                    f"TV volume {observed.get('volume')}"
                ),
                "observed_at": utc_now_iso(),
                "verified": perception_receipt.verified,
            }
            self.tv_autopilot.observe(
                surface=surface,
                confidence=0.93,
                evidence=f"webOS reported foreground app {app_id} and audio state",
            )
            agent_request = str(arguments.get("request") or "").strip()
            refinement = str(arguments.get("refinement") or "").strip()
            if arguments.get("resumed"):
                conversation = {**self.conversation_memory.snapshot(channel=conversation_channel), "composed_request": agent_request, "is_refinement": False}
            else:
                conversation = self.conversation_memory.prepare_request(
                    refinement or agent_request,
                    explicit_refinement=bool(refinement),
                )
            if refinement and not conversation.get("is_refinement"):
                return {
                    "accepted": False,
                    "intent": intent.to_dict(),
                    "spoken_response": "There is no active plan to refine yet.",
                }
            agent_request = str(conversation["composed_request"])
            agent_task = self.tv_agent.create_plan(
                agent_request,
                perception=perception,
                companion_url=companion_url,
            )
            self.conversation_memory.bind_task(str(agent_task["task_id"]))
            route = str(agent_task["route"])
            if "voice.web.research" not in permitted:
                raise PermissionError("The signed research capability is unavailable")
            objective_plan = self.objective_planner.prepare(
                str(agent_task["request"]),
                perception=perception,
            )
            agent_task = self.tv_agent.mark_prepared(
                str(agent_task["task_id"]),
                evidence=(
                    f"COMDEX local intelligence built {len(objective_plan.get('itinerary') or [])} plan stages "
                    f"from {len(objective_plan.get('evidence') or [])} bounded sources"
                ),
                result=objective_plan,
            )
            if canvas_url is None or canvas_view_callback is None:
                raise RuntimeError("The secure TV Canvas is not running")
            canvas_view_callback("agent")
            canvas_receipt = gateway.execute_governed_action(
                node_id=record.profile.node_id,
                host=webos_host,
                action="open_url",
                arguments={"target": canvas_url},
                maximum_voice_volume=50,
            )
            self.store.save_webos_action_receipt(canvas_receipt, source="local_voice_agent_handoff")
            receipts = preliminary_receipts + [canvas_receipt]
            self.tv_autopilot.observe(
                surface="aion_canvas",
                view="agent",
                confidence=0.99,
                evidence="AION controls the objective plan, evidence projection and approval boundary",
            )
            approval = agent_task.get("approval") or {}
            self.store.append_audit(
                "agent_objective_plan_prepared",
                {
                    "node_id": record.profile.node_id,
                    "task_id": agent_task["task_id"],
                    "route": route,
                    "approval_id": approval.get("approval_id"),
                    "request_hash": canonical_hash(agent_task["request"]),
                    "model": objective_plan.get("model"),
                    "evidence_count": len(objective_plan.get("evidence") or []),
                    "receipt_id": canvas_receipt.receipt_id,
                },
            )
            approval_phrase = (
                " Review and approve this specific action privately on your phone."
                if approval.get("state") == "pending" else ""
            )
            missing = list(objective_plan.get("missing_constraints") or [])
            refinement_prompt = ""
            if missing:
                refinement_prompt = f" Tell me {str(missing[0]).rstrip('.').lower()}."
            response = {
                "accepted": True,
                "intent": intent.to_dict(),
                "receipt": canvas_receipt.to_dict(),
                "receipts": [item.to_dict() for item in receipts],
                "spoken_response": (
                    f"I built a structured {objective_plan.get('title') or route} with "
                    f"{len(objective_plan.get('itinerary') or [])} stages and put it on the TV."
                    f"{approval_phrase}{refinement_prompt}"
                ),
                "agent_task": agent_task,
                "objective_plan": objective_plan,
                "companion_url": companion_url,
                "autopilot": self.tv_autopilot.snapshot(),
                "follow_up": (
                    {"kind": "agent_refinement", "expires_seconds": 90, "task_id": agent_task["task_id"]}
                    if missing else None
                ),
            }
            self.conversation_memory.record_turn(
                "assistant",
                str(response["spoken_response"]),
                channel=conversation_channel,
                intent="agent_plan_ready",
                task_id=str(agent_task["task_id"]),
            )
            response["conversation"] = self.conversation_memory.snapshot(channel=conversation_channel)
            return response
        if action == "netflix_saved_profile":
            preference_path = self.base_dir / "preferences" / "tv.json"
            if not preference_path.exists():
                return {"accepted": False, "intent": intent.to_dict(), "spoken_response": "No Netflix profile is remembered yet."}
            try:
                saved_profile = int(json.loads(preference_path.read_text(encoding="utf-8")).get("netflix_profile_index"))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                saved_profile = 0
            if saved_profile not in {1, 2, 3, 4, 5}:
                return {"accepted": False, "intent": intent.to_dict(), "spoken_response": "The remembered Netflix profile is invalid."}
            action = "netflix_profile"
            arguments = {"profile_index": saved_profile}
        if action == "open_research_result":
            action = "open_public_url"
            arguments = {"target": self.tv_research.result_url(int(intent.arguments["result_index"]))}
        if action == "open_games":
            gaming_session = self.gaming.prepare_provider_handoff(
                query=str(arguments.get("query") or ""),
                persona_id=str(persona_id or self.local_persona["persona_id"]),
            )
            action = "launch_games"
            arguments = {"provider": "geforce_now"}
        if action == "game_continue":
            gaming_session = self.gaming.continue_last(persona_id=str(persona_id or self.local_persona["persona_id"]))
            action = "launch_games"
            arguments = {"provider": "geforce_now"}
        if action == "education_start":
            if canvas_url is None or canvas_view_callback is None:
                raise RuntimeError("The secure TV Canvas is not running")
            self.education.start(str(intent.arguments.get("profile_id") or "explorer_a"))
            canvas_view_callback("education")
            action = "open_url"
            arguments = {"target": f"{canvas_url}/education"}
        if action == "show_research_results":
            if canvas_url is None or canvas_view_callback is None:
                raise RuntimeError("The secure TV Canvas is not running")
            latest_research = self.tv_research.latest()
            if not latest_research or not latest_research.get("items"):
                return {
                    "accepted": False,
                    "intent": intent.to_dict(),
                    "spoken_response": "I do not have previous research results to show yet.",
                }
            canvas_view_callback("research")
            action = "open_url"
            arguments = {"target": canvas_url}
        if action == "google_consent_accept":
            action = "remote_button"
            arguments = {"button": "ENTER"}
        if action == "exit_content":
            action = "remote_button"
            arguments = {"button": "BACK"}
        if action == "netflix_search":
            resolution = self.tv_research.resolve_netflix_title(str(arguments.get("query") or ""))
            arguments = {
                "query": str(arguments.get("query") or ""),
                "title": resolution["title"],
                "title_id": resolution["title_id"],
                "official_url": resolution["url"],
                "match_score": resolution["match_score"],
            }
        if action == "continue_last":
            remembered_surface = str(self.tv_autopilot.snapshot().get("belief", {}).get("surface") or "")
            app_id = {"netflix": "netflix", "youtube": "youtube.leanback.v4"}.get(remembered_surface)
            if app_id is None:
                return {
                    "accepted": False,
                    "intent": intent.to_dict(),
                    "spoken_response": "I do not yet have a verified last streaming app to continue.",
                }
            action = "launch_app"
            arguments = {"app_id": app_id}
        if action == "scene_evening":
            action = "set_volume"
            arguments = {"volume": 18}
        if action == "show_canvas":
            if canvas_url is None or canvas_view_callback is None:
                raise RuntimeError("The secure TV Canvas is not running")
            canvas_view_callback(str(arguments["view"]))
            volume_receipt = gateway.execute_governed_action(
                node_id=record.profile.node_id,
                host=webos_host,
                action="get_volume",
                arguments={},
                maximum_voice_volume=50,
            )
            self.store.save_webos_action_receipt(volume_receipt, source="local_voice_canvas_state")
            preliminary_receipts.append(volume_receipt)
            action = "open_url"
            target = f"{canvas_url}/god-view" if str(intent.arguments.get("view")) == "god_view" else canvas_url
            if str(intent.arguments.get("view")) == "god_view" and intent.arguments.get("god_action"):
                query = urllib.parse.urlencode(
                    {
                        "mode": str(intent.arguments.get("god_action") or "")[:40],
                        "place": str(intent.arguments.get("place") or "")[:120],
                    }
                )
                target = f"{target}?{query}"
            arguments = {"target": target}
        preferred_profile = None
        if intent.action in {"entertainment_search", "entertainment_recommend"}:
            if canvas_url is None or canvas_view_callback is None:
                raise RuntimeError("The secure TV Canvas is not running")
            plan_id = self.tv_autopilot.start_plan(
                name="Cross-service Entertainment",
                goal=str(intent.arguments["query"]),
                steps=[
                    {"name": "Research current provider evidence", "verification": "evidence-labelled provider results"},
                    {"name": "Present the shortlist", "verification": "LG Canvas launch receipt"},
                ],
            )
            try:
                self.tv_autopilot.mark_step(plan_id, 0, status="running", evidence="Checking current Spain streaming evidence")
                research_record = self.entertainment.discover(
                    str(intent.arguments["query"]),
                    minutes=int(intent.arguments["minutes"]) if intent.arguments.get("minutes") else None,
                )
                self.tv_autopilot.mark_step(plan_id, 0, status="verified", evidence=f"Prepared {len(research_record['items'])} evidence-labelled options")
                canvas_view_callback("entertainment")
                receipt = gateway.execute_governed_action(
                    node_id=record.profile.node_id,
                    host=webos_host,
                    action="open_url",
                    arguments={"target": canvas_url},
                    maximum_voice_volume=50,
                )
                self.store.save_webos_action_receipt(receipt, source="local_voice_entertainment")
                receipts = [receipt]
                self.tv_autopilot.mark_step(plan_id, 1, status="verified", evidence=f"Receipt {receipt.receipt_id}")
                self.tv_autopilot.finish_plan(plan_id, status="completed", summary="Cross-service options displayed with availability caveats")
                self.tv_autopilot.observe(surface="aion_canvas", view="entertainment", confidence=0.99, evidence="AION controls the evidence-labelled entertainment projection")
                spoken = f"I checked the entertainment services and put {len(research_record['items'])} current options on the TV. Say open the first or second result."
            except Exception as exc:
                self.tv_autopilot.finish_plan(plan_id, status="failed", summary=f"{type(exc).__name__}: {exc}")
                raise
        elif intent.action == "web_research":
            if canvas_url is None or canvas_view_callback is None:
                raise RuntimeError("The secure TV Canvas is not running")
            plan_id = self.tv_autopilot.start_plan(
                name="Live Research",
                goal=str(intent.arguments["query"]),
                steps=[
                    {"name": "Research current web evidence", "verification": "structured sourced response"},
                    {"name": "Present sanitized results", "verification": "LG Canvas launch receipt"},
                ],
            )
            try:
                self.tv_autopilot.mark_step(plan_id, 0, status="running", evidence="OpenAI web search requested by owner")
                research_record = self.tv_research.search(
                    str(intent.arguments["query"]),
                    mode=str(intent.arguments.get("mode") or "general"),
                )
                self.tv_autopilot.mark_step(
                    plan_id, 0, status="verified", evidence=f"Structured response with {len(research_record['items'])} HTTPS results"
                )
                canvas_view_callback("research")
                self.tv_autopilot.mark_step(plan_id, 1, status="running", evidence="Opening private Canvas research view")
                receipt = gateway.execute_governed_action(
                    node_id=record.profile.node_id,
                    host=webos_host,
                    action="open_url",
                    arguments={"target": canvas_url},
                    maximum_voice_volume=50,
                )
                self.store.save_webos_action_receipt(receipt, source="local_voice_research")
                receipts = [receipt]
                self.tv_autopilot.mark_step(plan_id, 1, status="verified", evidence=f"Receipt {receipt.receipt_id}")
                self.tv_autopilot.finish_plan(plan_id, status="completed", summary="Current sourced results displayed on TV")
                self.tv_autopilot.observe(
                    surface="aion_canvas",
                    view="research",
                    confidence=0.99,
                    evidence="AION controls the sanitized research state and Canvas presentation",
                )
                spoken = f"I found {len(research_record['items'])} results and put them on the TV. Say open the first or second result."
                if agent_task is not None:
                    agent_task = self.tv_agent.mark_prepared(
                        str(agent_task["task_id"]),
                        evidence=f"Completed bounded research with {len(research_record['items'])} results",
                        result={"answer": research_record.get("answer"), "items": research_record.get("items")},
                    )
                preference_path = self.base_dir / "preferences" / "tv.json"
                try:
                    preferences = json.loads(preference_path.read_text(encoding="utf-8")) if preference_path.exists() else {}
                except (OSError, json.JSONDecodeError):
                    preferences = {}
                if (
                    research_record.get("provider") == "safe_search_handoff"
                    and not preferences.get("google_consent_authorized_at")
                ):
                    spoken += " If Google asks for consent, highlight Accept and say Pilot accept Google once."
            except Exception as exc:
                self.tv_autopilot.finish_plan(plan_id, status="failed", summary=f"{type(exc).__name__}: {exc}")
                raise
        elif intent.action == "scene_movie":
            receipts = []
            scene_actions = [
                ("launch_app", {"app_id": "netflix"}),
                ("set_volume", {"volume": 20}),
            ]
            plan_id = self.tv_autopilot.start_plan(
                name="Movie Mode",
                goal="Open Netflix and establish a comfortable bounded volume",
                steps=[
                    {"name": "Open Netflix", "verification": "LG launch receipt"},
                    {"name": "Set volume to 20", "verification": "read-after-write TV volume"},
                ],
            )
            preference_path = self.base_dir / "preferences" / "tv.json"
            if preference_path.exists():
                try:
                    preferred_profile = int(json.loads(preference_path.read_text(encoding="utf-8")).get("netflix_profile_index"))
                except (OSError, ValueError, TypeError, json.JSONDecodeError):
                    preferred_profile = None
            try:
                for step_index, (scene_action, scene_arguments) in enumerate(scene_actions):
                    self.tv_autopilot.mark_step(plan_id, step_index, status="running", evidence="Command dispatched")
                    scene_receipt = gateway.execute_governed_action(
                        node_id=record.profile.node_id,
                        host=webos_host,
                        action=scene_action,
                        arguments=scene_arguments,
                        maximum_voice_volume=50,
                    )
                    self.store.save_webos_action_receipt(scene_receipt, source="local_voice_scene")
                    receipts.append(scene_receipt)
                    self.tv_autopilot.mark_step(
                        plan_id,
                        step_index,
                        status="verified",
                        evidence=f"Receipt {scene_receipt.receipt_id}",
                    )
            except Exception as exc:
                self.tv_autopilot.finish_plan(plan_id, status="failed", summary=f"{type(exc).__name__}: {exc}")
                raise
            self.tv_autopilot.finish_plan(plan_id, status="completed", summary="Netflix launched and volume verified at 20")
            self.tv_autopilot.observe(
                surface="netflix",
                confidence=0.76,
                evidence="LG acknowledged Netflix launch; third-party pixels are not observed",
            )
            spoken = (
                "Netflix is open and volume is 20. If the profile chooser is visible, say Pilot select my Netflix profile."
                if preferred_profile in {1, 2, 3, 4, 5}
                else "Netflix is open and volume is 20. Tell me to select the first, second, or third profile."
            )
            receipt = receipts[-1]
        else:
            receipt = gateway.execute_governed_action(
                node_id=record.profile.node_id,
                host=webos_host,
                action=action,
                arguments=arguments,
                maximum_voice_volume=50,
            )
            self.store.save_webos_action_receipt(receipt, source="local_voice")
            receipts = preliminary_receipts + [receipt]
            if intent.action in {
                "launch_app", "show_canvas", "remote_button", "netflix_profile", "netflix_profile_menu",
                "netflix_saved_profile", "netflix_search", "exit_content",
                "open_research_result", "show_research_results", "continue_last", "open_games", "education_start",
            }:
                screen_observed = bool(receipt.after.get("screen_effect_observed", receipt.after.get("opened", False)))
                self.tv_autopilot.record_navigation_attempt(
                    action=intent.action,
                    expected=str(intent.arguments)[:160],
                    observed=(
                        f"foreground={receipt.after.get('foreground_app_id')}; "
                        f"transport_verified={receipt.after.get('transport_verified')}; "
                        f"screen_effect_observed={screen_observed}"
                    ),
                    success=bool(receipt.verified and screen_observed),
                )
            if intent.action == "show_canvas":
                self.tv_autopilot.observe(
                    surface="aion_canvas",
                    view=str(intent.arguments["view"]),
                    confidence=0.99,
                    evidence="AION controls both the launched URL and Canvas session state",
                )
            elif intent.action == "launch_app":
                app_id = str(intent.arguments.get("app_id"))
                self.tv_autopilot.observe(
                    surface="netflix" if app_id == "netflix" else "youtube",
                    confidence=0.76,
                    evidence=f"LG acknowledged app launch for {app_id}; third-party pixels are not observed",
                )
            elif intent.action == "switch_input":
                self.tv_autopilot.observe(
                    surface="hdmi",
                    confidence=0.8,
                    evidence=f"LG acknowledged input {intent.arguments.get('input_id')}",
                )
            elif intent.action in {"netflix_profile", "netflix_saved_profile"}:
                self.tv_autopilot.observe(
                    surface="netflix",
                    confidence=0.58,
                    evidence="Explicit owner-directed profile navigation delivered; screen effect is not observed",
                )
            elif intent.action == "netflix_search":
                self.tv_autopilot.observe(
                    surface="netflix",
                    view="search_results",
                    confidence=0.84,
                    evidence="Installed Netflix schema advertised inAppVoiceIntent and webOS accepted the search relaunch parameters",
                )
            elif intent.action == "exit_content":
                self.tv_autopilot.observe(
                    surface="netflix",
                    view="browse",
                    confidence=0.72,
                    evidence="LG accepted Back from the explicitly requested current-content exit; pixels are not observed",
                )
            elif intent.action == "open_research_result":
                self.tv_autopilot.observe(
                    surface="web_browser",
                    confidence=0.78,
                    evidence="LG acknowledged the explicitly selected public HTTPS result",
                )
            elif intent.action == "open_games":
                self.tv_autopilot.observe(
                    surface="games",
                    view="geforce_now",
                    confidence=0.78,
                    evidence="LG acknowledged the allowlisted GeForce NOW HTTPS launch",
                )
            elif intent.action == "education_start":
                self.tv_autopilot.observe(
                    surface="aion_canvas",
                    view="education",
                    confidence=0.99,
                    evidence="AION opened its local child-safe learning session on Canvas",
                )
            elif intent.action == "show_research_results":
                self.tv_autopilot.observe(
                    surface="aion_canvas",
                    view="research",
                    confidence=0.99,
                    evidence="AION reopened its persisted sanitized research projection after an explicit request",
                )
            elif intent.action == "continue_last":
                continued = "netflix" if arguments.get("app_id") == "netflix" else "youtube"
                self.tv_autopilot.observe(
                    surface=continued,
                    confidence=0.76,
                    evidence=f"LG acknowledged relaunch of remembered surface {continued}",
                )
        if intent.action == "get_volume":
            spoken = f"The TV volume is {receipt.after.get('volume')}."
        elif intent.action in {"set_volume", "change_volume"}:
            spoken = f"TV volume is now {receipt.after.get('volume')}."
        elif intent.action == "set_mute":
            spoken = "The TV is muted." if intent.arguments["muted"] else "The TV is unmuted."
        elif intent.action == "switch_input":
            spoken = f"Switched the TV to {intent.arguments['input_id'].replace('_', ' ')}."
        elif intent.action == "launch_app":
            spoken = f"Opening {intent.arguments['app_id'].split('.')[0]}."
        elif intent.action == "show_canvas":
            if intent.arguments.get("god_action") == "fly":
                spoken = f"Flying to {intent.arguments.get('place', 'that location')} in God View."
            elif intent.arguments.get("god_action") == "iss_live":
                spoken = "Opening NASA's live video from the International Space Station."
            elif intent.arguments.get("god_action") == "iss_track":
                spoken = "Tracking the International Space Station in God View."
            elif intent.arguments.get("god_action") == "nasa_earth":
                spoken = "Showing the newest NASA Earth satellite image."
            else:
                spoken = f"Showing Pilot {intent.arguments['view']} on the TV."
        elif intent.action == "remote_button":
            spoken = f"TV remote {intent.arguments['button'].lower()} sent."
        elif intent.action == "netflix_profile":
            profile_index = int(intent.arguments["profile_index"])
            if intent.arguments.get("remember"):
                preference_path = self.base_dir / "preferences" / "tv.json"
                preference_path.parent.mkdir(parents=True, exist_ok=True)
                try:
                    preferences = json.loads(preference_path.read_text(encoding="utf-8")) if preference_path.exists() else {}
                except (OSError, json.JSONDecodeError):
                    preferences = {}
                preferences["netflix_profile_index"] = profile_index
                temporary = preference_path.with_suffix(".tmp")
                temporary.write_bytes(canonical_bytes(preferences))
                os.replace(temporary, preference_path)
                spoken = f"Netflix profile {profile_index} is selected and remembered for movie mode."
            else:
                spoken = f"Netflix profile {profile_index} is selected."
        elif intent.action == "netflix_profile_menu":
            spoken = "The Netflix profile chooser is open."
        elif intent.action == "netflix_saved_profile":
            spoken = f"Your remembered Netflix profile {arguments['profile_index']} is selected."
        elif intent.action == "netflix_search":
            spoken = f"Opening {receipt.after.get('title') or intent.arguments['query']} inside Netflix."
        elif intent.action == "web_research":
            pass
        elif intent.action in {"entertainment_search", "entertainment_recommend"}:
            pass
        elif intent.action == "open_research_result":
            spoken = f"Opening research result {intent.arguments['result_index']} on the TV."
        elif intent.action == "show_research_results":
            spoken = "Showing your latest research results again."
        elif intent.action == "open_games":
            query = str(intent.arguments.get("query") or "").strip()
            spoken = (
                f"I sent GeForce NOW to the TV and prepared a search for {query}. The provider screen, game and stream still need verification."
                if query else
                "I sent GeForce NOW to the TV. Sign in on the provider surface if asked; Pilot will not claim a game is running until it is verified."
            )
        elif intent.action == "game_continue":
            spoken = f"I reopened GeForce NOW and prepared {gaming_session['query']}. The stream is not reported as playing until verified."
        elif intent.action == "education_start":
            spoken = "Spanish Learning Centre is ready. Choose an answer on the private phone controller."
        elif intent.action == "google_consent_accept":
            preference_path = self.base_dir / "preferences" / "tv.json"
            preference_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                preferences = json.loads(preference_path.read_text(encoding="utf-8")) if preference_path.exists() else {}
            except (OSError, json.JSONDecodeError):
                preferences = {}
            preferences["google_consent_authorized_at"] = utc_now_iso()
            temporary = preference_path.with_suffix(".tmp")
            temporary.write_bytes(canonical_bytes(preferences))
            os.replace(temporary, preference_path)
            spoken = "I selected the currently focused Google consent choice. The TV browser should remember it."
        elif intent.action == "exit_content":
            spoken = "Exiting the current film or series."
        elif intent.action == "continue_last":
            spoken = "Continuing your last remembered streaming app."
        elif intent.action == "scene_evening":
            spoken = "Evening comfort is set. TV volume is 18."
        elif intent.action != "scene_movie":
            spoken = {"media_play": "Playing.", "media_pause": "Paused.", "media_stop": "Playback stopped."}[intent.action]
        self.store.append_audit(
            "voice_intent_executed",
            {
                "node_id": record.profile.node_id,
                "transcript_hash": canonical_hash(transcript),
                "intent": intent.action,
                "arguments": intent.arguments,
                "receipt_id": receipt.receipt_id,
            },
        )
        response = {
            "accepted": True,
            "intent": intent.to_dict(),
            "receipt": receipt.to_dict(),
            "receipts": [item.to_dict() for item in receipts],
            "spoken_response": spoken,
            "autopilot": self.tv_autopilot.snapshot(),
            "agent_task": agent_task,
            "gaming": self.gaming.snapshot(persona_id=persona_id) if intent.action in {"open_games", "game_continue"} else None,
            "follow_up": (
                {"kind": "netflix_profile", "expires_seconds": 30, "prompt": "Which Netflix profile position?"}
                if intent.action == "scene_movie" and preferred_profile not in {1, 2, 3, 4, 5}
                else {"kind": "research_result", "expires_seconds": 45, "prompt": "Which research result?"}
                if intent.action == "web_research" and research_record and research_record.get("items")
                else None
            ),
        }
        self.conversation_memory.record_turn(
            "assistant",
            str(response["spoken_response"]),
            channel=conversation_channel,
            intent=intent.action,
            task_id=str((agent_task or {}).get("task_id") or "") or None,
        )
        response["conversation"] = self.conversation_memory.snapshot(channel=conversation_channel)
        return response

    def status(self) -> Dict[str, Any]:
        nodes = self.store.list_nodes()
        private_identity = self.private_identity.snapshot()
        active_persona_id = str(dict(private_identity.get("active_shared_identity") or {}).get("persona_id") or "")
        shared_inbox_summary = self.pilot_inbox.shared_summary(persona_id=active_persona_id) if active_persona_id else None
        return {
            "ok": True,
            "fabric_version": "0.66.0",
            "node_id": self.profile.node_id,
            "role": self.role.value,
            "identity_fingerprint": self.identity.fingerprint,
            "mother_id": self.profile.node_id if self.role is NodeRole.MOTHER else next(
                (node.mother_id for node in nodes if node.profile.node_id == self.profile.node_id), None
            ),
            "nodes": [node.to_dict() for node in nodes],
            "ledger": self.store.counts(),
            "audit_chain_valid": self._cached_audit_chain_valid(),
            "tv_autopilot": self.tv_autopilot.snapshot(),
            "comdex_bridge": self.comdex_bridge.snapshot(),
            "tv_research": self.tv_research.latest(),
            "intelligence": self.tv_research.policy.status(),
            "tv_agent": self.tv_agent.snapshot(),
            "phone_perception": self.phone_perception.latest(),
            "phone_navigation": self.phone_navigation.snapshot(),
            "conversation": self.conversation_memory.snapshot(channel="shared_tv"),
            "entertainment": self.entertainment.snapshot(),
            "household": self.household.snapshot(),
            "universal_node": self.universal_node.snapshot(),
            "service_execution": self.service_hub.snapshot(),
            "education": self.education.snapshot(),
            "gaming": self.gaming.snapshot(persona_id=str(self.local_persona["persona_id"])),
            "private_identity": private_identity,
            "pilot_inbox": self.pilot_inbox.snapshot(),
            "pilot_inbox_shared_summary": shared_inbox_summary,
            "live_context": self.live_context.latest(),
            "pilot_moments": self.pilot_moments.snapshot(),
            "screen_understanding": self.screen_understanding.latest(),
            "provider_metadata": self.provider_metadata.latest(),
            "observer": self.observer_sessions.snapshot(),
            "live_news": self.live_news.latest(),
            "scene_explanation": self.scene_explanation.latest(),
            "programme_companion": self.programme_companion.latest(),
            "programme_origins": self.programme_origins.latest(),
            "live_translation": self.live_translation.latest(),
            "live_sports": self.live_sports.latest(),
            "live_events": self.live_events.status(),
            "live_engagement": self.live_engagement.snapshot(persona_id=str(self.local_persona["persona_id"])),
            "fact_check_benchmark": self.fact_check_benchmark.latest(),
            "live_media_authority": self.live_media_authority.latest(),
            "contextual_companion": self.contextual_companion.snapshot(persona_id=str(self.local_persona["persona_id"])),
            "private_saves": self.private_saves.snapshot(),
            "saved_followthrough": self.saved_followthrough.snapshot(persona_id=str(self.local_persona["persona_id"])),
            "entertainment_execution": self.entertainment_execution.snapshot(persona_id=str(self.local_persona["persona_id"])),
            "entertainment_personalization": self.entertainment_personalization.snapshot(persona_id=str(self.local_persona["persona_id"])),
            "verified_navigation": self.verified_navigation.snapshot(),
            "tv_reliability": self.tv_reliability.report(adapter="lg_webos_gateway"),
            "perception_timeline": self.perception_timeline.snapshot(),
            "provider_telemetry": self.provider_telemetry.snapshot(
                persona_id=str(self.local_persona["persona_id"])
            ),
            "infrared_climate": self.infrared_climate.snapshot(),
            "runtime_dir": str(self.base_dir),
        }


def build_node_delta(
    *,
    node_id: str,
    identity: DeviceIdentity,
    previous: Dict[str, Any],
    current: Dict[str, Any],
    sequence: int,
) -> DeltaPacket:
    return new_delta_packet(
        node_id=node_id,
        sequence=sequence,
        previous=previous,
        current=current,
        identity=identity,
    )
