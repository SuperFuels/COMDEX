from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from typing import Any, Mapping

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from backend.modules.aion_business.runtime.node_capabilities import NodeCapability
from backend.modules.aion_business.runtime.business_data_domain_registry import (
    BusinessDataDomainRegistry,
    BusinessDataDomainRegistryError,
    REQUIRED_DEPARTMENT_VAULT_DOMAINS,
    department_vault_namespaces,
)
from backend.modules.aion_business.runtime.node_platform_qualification import (
    NodePlatformQualificationError,
    verify_node_platform_qualification,
)


NODE_RELEASE_SCHEMA = "tessaris.node-release-manifest.v1"
CHANGE_INVENTORY_SCHEMA = "tessaris.release-change-inventory.v1"
DIGEST = re.compile(r"^[0-9a-f]{64}$")
VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")
MANDATORY_BUSINESS_CONTINUITY_SESSIONS = frozenset(
    {
        "business-onboarding",
        "boardroom-business-maps",
        "aion-pilot-conversations",
        "automations-schedules",
        "files-documents",
        "import-export-migration",
        "backup-recovery",
    }
)


class ReleaseContractError(ValueError):
    pass


def _version_tuple(value: str) -> tuple[int, int, int]:
    match = VERSION.fullmatch(str(value or ""))
    if not match:
        raise ReleaseContractError("release_version_invalid")
    return tuple(int(part) for part in match.groups())


def release_change_inventory_digest(
    *, feature_ids: list[str], department_ids: list[str],
) -> str:
    payload = {
        "schema_version": CHANGE_INVENTORY_SCHEMA,
        "feature_ids": sorted(feature_ids),
        "department_ids": sorted(department_ids),
    }
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return sha256(canonical).hexdigest()


@dataclass(frozen=True)
class ReleasePreflight:
    schema_version: str
    eligible: bool
    release_version: str
    current_version: str
    target_id: str | None
    required_storage_bytes: int
    reasons: tuple[str, ...]

    def payload(self) -> dict[str, Any]:
        return {**asdict(self), "reasons": list(self.reasons)}


def validate_release_manifest(manifest: Mapping[str, Any]) -> None:
    if manifest.get("schema_version") != NODE_RELEASE_SCHEMA:
        raise ReleaseContractError("release_schema_invalid")
    _version_tuple(str(manifest.get("version") or ""))
    if manifest.get("customer_data_included") is not False:
        raise ReleaseContractError("release_customer_data_boundary_invalid")
    if manifest.get("customer_credentials_included") is not False:
        raise ReleaseContractError("release_credentials_boundary_invalid")
    if manifest.get("channel") not in {"stable", "preview", "offline"}:
        raise ReleaseContractError("release_channel_invalid")
    release_stage = manifest.get("release_stage")
    if release_stage not in {"internal-preview", "production-candidate", "production"}:
        raise ReleaseContractError("release_stage_invalid")
    targets = manifest.get("targets")
    if not isinstance(targets, list) or not targets:
        raise ReleaseContractError("release_targets_missing")
    seen: set[str] = set()
    for target in targets:
        if not isinstance(target, Mapping):
            raise ReleaseContractError("release_target_invalid")
        target_id = str(target.get("target_id") or "")
        if not target_id or target_id in seen:
            raise ReleaseContractError("release_target_identity_invalid")
        seen.add(target_id)
        if target.get("system") not in {"darwin", "windows", "linux"}:
            raise ReleaseContractError("release_target_system_invalid")
        architectures = target.get("architectures")
        if (
            not isinstance(architectures, list)
            or not architectures
            or not set(architectures) <= {"x86_64", "arm64"}
        ):
            raise ReleaseContractError("release_target_architecture_invalid")
        size = int(target.get("artifact_bytes") or -1)
        if size < 1 or not DIGEST.fullmatch(str(target.get("sha256") or "")):
            raise ReleaseContractError("release_target_artifact_invalid")
        qualification_digest = str(target.get("qualification_report_sha256") or "")
        if release_stage in {"production-candidate", "production"}:
            if not DIGEST.fullmatch(qualification_digest):
                raise ReleaseContractError(
                    f"release_target_qualification_missing:{target_id}"
                )
        elif qualification_digest and not DIGEST.fullmatch(qualification_digest):
            raise ReleaseContractError(
                f"release_target_qualification_invalid:{target_id}"
            )
    if not isinstance(manifest.get("guardian_api_versions"), list) or not manifest["guardian_api_versions"]:
        raise ReleaseContractError("release_guardian_contract_missing")
    if not isinstance(manifest.get("readable_vault_schemas"), list) or not manifest["readable_vault_schemas"]:
        raise ReleaseContractError("release_vault_contract_missing")
    if not isinstance(manifest.get("health_gates"), list) or not manifest["health_gates"]:
        raise ReleaseContractError("release_health_gates_missing")
    if not manifest.get("rollback_target"):
        raise ReleaseContractError("release_rollback_target_missing")
    discovery = manifest.get("business_data_discovery")
    if not isinstance(discovery, Mapping):
        raise ReleaseContractError("release_business_data_discovery_missing")
    if discovery.get("schema_version") != "tessaris.business-data-release-evidence.v3":
        raise ReleaseContractError("release_business_data_discovery_schema_invalid")
    if not DIGEST.fullmatch(str(discovery.get("manifest_sha256") or "")):
        raise ReleaseContractError("release_business_data_manifest_digest_invalid")
    if not DIGEST.fullmatch(str(discovery.get("report_sha256") or "")):
        raise ReleaseContractError("release_business_data_report_digest_invalid")
    if not DIGEST.fullmatch(str(discovery.get("scenario_catalogue_sha256") or "")):
        raise ReleaseContractError("release_business_data_scenario_catalogue_digest_invalid")
    if int(discovery.get("unknown_write_count", -1)) != 0:
        raise ReleaseContractError("release_unknown_business_data_writes")
    if int(discovery.get("blocking_touchpoint_count", -1)) != 0:
        raise ReleaseContractError("release_blocking_business_data_touchpoints")
    if int(discovery.get("incomplete_discovery_session_count", -1)) != 0:
        raise ReleaseContractError("release_incomplete_business_data_discovery")
    traces = discovery.get("runtime_trace_scenarios")
    if not isinstance(traces, list) or not traces or not all(
        isinstance(item, str) and item.strip() for item in traces
    ):
        raise ReleaseContractError("release_business_data_runtime_traces_missing")
    required_session_count = int(discovery.get("required_discovery_session_count", -1))
    trace_session_count = int(discovery.get("runtime_trace_session_count", -1))
    if required_session_count < 1 or trace_session_count != required_session_count:
        raise ReleaseContractError("release_business_data_runtime_trace_coverage_incomplete")
    trace_digests = discovery.get("runtime_trace_sha256")
    surface_counts = discovery.get("runtime_trace_surface_counts")
    domain_counts = discovery.get("runtime_trace_domain_counts")
    external_class_counts = discovery.get("runtime_trace_external_class_counts")
    if (
        not isinstance(trace_digests, Mapping)
        or len(trace_digests) != trace_session_count
        or not all(
            isinstance(session_id, str)
            and session_id.strip()
            and DIGEST.fullmatch(str(digest or ""))
            for session_id, digest in trace_digests.items()
        )
    ):
        raise ReleaseContractError("release_business_data_runtime_trace_digests_invalid")
    if (
        not isinstance(surface_counts, Mapping)
        or set(surface_counts) != set(trace_digests)
        or not all(int(count) > 0 for count in surface_counts.values())
    ):
        raise ReleaseContractError("release_business_data_runtime_trace_surfaces_invalid")
    if (
        not isinstance(domain_counts, Mapping)
        or set(domain_counts) != set(trace_digests)
        or not all(int(count) > 0 for count in domain_counts.values())
    ):
        raise ReleaseContractError("release_business_data_runtime_trace_domains_invalid")
    if (
        not isinstance(external_class_counts, Mapping)
        or set(external_class_counts) != set(trace_digests)
        or not all(int(count) >= 0 for count in external_class_counts.values())
    ):
        raise ReleaseContractError(
            "release_business_data_runtime_trace_external_classes_invalid"
        )
    missing_continuity_sessions = sorted(
        MANDATORY_BUSINESS_CONTINUITY_SESSIONS - set(trace_digests)
    )
    if missing_continuity_sessions:
        raise ReleaseContractError(
            "release_business_data_continuity_sessions_missing:"
            + ",".join(missing_continuity_sessions)
        )
    domains = manifest.get("business_data_domains")
    if not isinstance(domains, list) or not domains:
        raise ReleaseContractError("release_business_data_domains_missing")
    departments = manifest.get("introduced_department_ids") or []
    if not isinstance(departments, list):
        raise ReleaseContractError("release_department_ids_invalid")
    if len(departments) != len({str(value) for value in departments}):
        raise ReleaseContractError("release_department_ids_duplicate")
    for department_id in departments:
        try:
            department_vault_namespaces(str(department_id))
        except BusinessDataDomainRegistryError as exc:
            raise ReleaseContractError(str(exc)) from exc
    feature_changes = manifest.get("feature_data_changes")
    if not isinstance(feature_changes, list):
        raise ReleaseContractError("release_feature_data_changes_missing")
    change_inventory = manifest.get("release_change_inventory")
    if not isinstance(change_inventory, Mapping):
        raise ReleaseContractError("release_change_inventory_missing")
    if change_inventory.get("schema_version") != CHANGE_INVENTORY_SCHEMA:
        raise ReleaseContractError("release_change_inventory_schema_invalid")
    if not DIGEST.fullmatch(str(change_inventory.get("sha256") or "")):
        raise ReleaseContractError("release_change_inventory_digest_invalid")
    inventoried_features = change_inventory.get("feature_ids")
    inventoried_departments = change_inventory.get("department_ids")
    if (
        not isinstance(inventoried_features, list)
        or not all(isinstance(value, str) and value.strip() for value in inventoried_features)
        or len(inventoried_features) != len(set(inventoried_features))
    ):
        raise ReleaseContractError("release_change_inventory_features_invalid")
    if (
        not isinstance(inventoried_departments, list)
        or not all(isinstance(value, str) and value.strip() for value in inventoried_departments)
        or len(inventoried_departments) != len(set(inventoried_departments))
    ):
        raise ReleaseContractError("release_change_inventory_departments_invalid")
    expected_inventory_digest = release_change_inventory_digest(
        feature_ids=list(inventoried_features),
        department_ids=list(inventoried_departments),
    )
    if str(change_inventory.get("sha256")) != expected_inventory_digest:
        raise ReleaseContractError("release_change_inventory_digest_mismatch")
    if sorted(inventoried_departments) != sorted(str(value) for value in departments):
        raise ReleaseContractError("release_change_inventory_department_mismatch")
    registry = BusinessDataDomainRegistry()
    registered_domains = registry.manifest()
    declared_domains = {str(value) for value in domains}
    seen_features: set[str] = set()
    covered_departments: set[str] = set()
    for change in feature_changes:
        if not isinstance(change, Mapping):
            raise ReleaseContractError("release_feature_data_change_invalid")
        feature_id = str(change.get("feature_id") or "").strip()
        if not feature_id or feature_id in seen_features:
            raise ReleaseContractError("release_feature_data_change_identity_invalid")
        seen_features.add(feature_id)
        captures_business_data = change.get("captures_business_data")
        if not isinstance(captures_business_data, bool):
            raise ReleaseContractError(
                f"release_feature_data_classification_required:{feature_id}"
            )
        feature_domains = change.get("business_data_domains")
        if not isinstance(feature_domains, list):
            raise ReleaseContractError(
                f"release_feature_business_data_domains_invalid:{feature_id}"
            )
        feature_domain_set = {str(value).strip() for value in feature_domains if str(value).strip()}
        migration_strategy = str(change.get("migration_strategy") or "").strip()
        data_artifacts = change.get("data_artifacts")
        legacy_sources = change.get("legacy_sources")
        if not isinstance(data_artifacts, list):
            raise ReleaseContractError(
                f"release_feature_data_artifacts_invalid:{feature_id}"
            )
        if not isinstance(legacy_sources, list) or not all(
            isinstance(value, str) and value.strip() for value in legacy_sources
        ):
            raise ReleaseContractError(
                f"release_feature_legacy_sources_invalid:{feature_id}"
            )
        if captures_business_data:
            if not feature_domain_set:
                raise ReleaseContractError(
                    f"release_feature_business_data_domains_missing:{feature_id}"
                )
            undeclared = sorted(feature_domain_set - declared_domains)
            if undeclared:
                raise ReleaseContractError(
                    f"release_feature_domain_not_in_manifest:{feature_id}:{','.join(undeclared)}"
                )
            if migration_strategy not in {"copy_verify_switch", "new_empty_domain"}:
                raise ReleaseContractError(
                    f"release_feature_migration_strategy_invalid:{feature_id}"
                )
            if migration_strategy == "copy_verify_switch" and not legacy_sources:
                raise ReleaseContractError(
                    f"release_feature_legacy_sources_missing:{feature_id}"
                )
            if migration_strategy == "new_empty_domain" and legacy_sources:
                raise ReleaseContractError(
                    f"release_feature_new_domain_has_legacy_sources:{feature_id}"
                )
            if not data_artifacts:
                raise ReleaseContractError(
                    f"release_feature_data_artifacts_missing:{feature_id}"
                )
            artifact_ids: set[str] = set()
            artifact_domains: set[str] = set()
            artifact_namespaces: set[str] = set()
            for artifact in data_artifacts:
                if not isinstance(artifact, Mapping):
                    raise ReleaseContractError(
                        f"release_feature_data_artifact_invalid:{feature_id}"
                    )
                artifact_id = str(artifact.get("artifact_id") or "").strip()
                domain_id = str(artifact.get("domain_id") or "").strip()
                storage_class = str(artifact.get("storage_class") or "").strip()
                vault_namespace = str(artifact.get("vault_namespace") or "").strip()
                if not artifact_id or artifact_id in artifact_ids or not vault_namespace:
                    raise ReleaseContractError(
                        f"release_feature_data_artifact_identity_invalid:{feature_id}"
                    )
                namespace_parts = vault_namespace.split("/")
                if (
                    vault_namespace.startswith("/")
                    or "\\" in vault_namespace
                    or "://" in vault_namespace
                    or any(part in {"", ".", ".."} for part in namespace_parts)
                    or vault_namespace in artifact_namespaces
                ):
                    raise ReleaseContractError(
                        f"release_feature_vault_namespace_invalid:{feature_id}:{artifact_id}"
                    )
                if domain_id not in feature_domain_set:
                    raise ReleaseContractError(
                        f"release_feature_artifact_domain_invalid:{feature_id}:{artifact_id}"
                    )
                registered = registered_domains.get(domain_id)
                if registered is None or registered.storage_class != storage_class:
                    raise ReleaseContractError(
                        f"release_feature_artifact_storage_class_invalid:{feature_id}:{artifact_id}"
                    )
                artifact_ids.add(artifact_id)
                artifact_domains.add(domain_id)
                artifact_namespaces.add(vault_namespace)
            if artifact_domains != feature_domain_set:
                missing_artifacts = sorted(feature_domain_set - artifact_domains)
                raise ReleaseContractError(
                    f"release_feature_domain_without_artifact:{feature_id}:{','.join(missing_artifacts)}"
                )
            department_id = str(change.get("department_id") or "").strip()
            if department_id:
                if department_id not in departments or department_id in covered_departments:
                    raise ReleaseContractError(
                        f"release_feature_department_binding_invalid:{feature_id}:{department_id}"
                    )
                required_department_domains = REQUIRED_DEPARTMENT_VAULT_DOMAINS
                missing_department_domains = sorted(
                    required_department_domains - feature_domain_set
                )
                if missing_department_domains:
                    raise ReleaseContractError(
                        "release_department_vault_contract_incomplete:"
                        f"{department_id}:{','.join(missing_department_domains)}"
                    )
                department_prefix = f"departments/{department_id}/"
                misplaced = sorted(
                    str(artifact.get("artifact_id") or "")
                    for artifact in data_artifacts
                    if not str(artifact.get("vault_namespace") or "").startswith(
                        department_prefix
                    )
                )
                if misplaced:
                    raise ReleaseContractError(
                        "release_department_vault_namespace_invalid:"
                        f"{department_id}:{','.join(misplaced)}"
                    )
                expected_namespaces = department_vault_namespaces(department_id)
                domain_namespaces: dict[str, list[str]] = {}
                for artifact in data_artifacts:
                    domain_id = str(artifact.get("domain_id") or "").strip()
                    if domain_id in required_department_domains:
                        domain_namespaces.setdefault(domain_id, []).append(
                            str(artifact.get("vault_namespace") or "").strip()
                        )
                noncanonical = sorted(
                    domain_id
                    for domain_id, expected_namespace in expected_namespaces.items()
                    if domain_namespaces.get(domain_id) != [expected_namespace]
                )
                if noncanonical:
                    raise ReleaseContractError(
                        "release_department_vault_namespace_noncanonical:"
                        f"{department_id}:{','.join(noncanonical)}"
                    )
                covered_departments.add(department_id)
        elif (
            feature_domain_set
            or migration_strategy != "not_required"
            or data_artifacts
            or legacy_sources
            or str(change.get("department_id") or "").strip()
        ):
            raise ReleaseContractError(
                f"release_feature_no_data_contract_invalid:{feature_id}"
            )
    missing_department_contracts = sorted(set(departments) - covered_departments)
    if missing_department_contracts:
        raise ReleaseContractError(
            "release_department_vault_contract_missing:"
            + ",".join(missing_department_contracts)
        )
    if sorted(inventoried_features) != sorted(seen_features):
        raise ReleaseContractError("release_change_inventory_feature_mismatch")
    try:
        registry.release_preflight(
            feature_data_domains=domains,
            department_ids=departments,
            require_complete_registry=True,
        )
    except BusinessDataDomainRegistryError as exc:
        raise ReleaseContractError(str(exc)) from exc


def evaluate_release_preflight(
    manifest: Mapping[str, Any],
    capability: NodeCapability,
    *,
    current_version: str,
    guardian_api_version: str,
    vault_schema_version: str,
    signature_verified: bool,
    repository_metadata_fresh: bool,
    platform_qualification_verified: bool = False,
    available_storage_bytes: int | None = None,
) -> ReleasePreflight:
    validate_release_manifest(manifest)
    release_version = str(manifest["version"])
    reasons: list[str] = []
    if not signature_verified:
        reasons.append("release_signature_unverified")
    if not repository_metadata_fresh:
        reasons.append("release_repository_metadata_stale")
    if not capability.qualified:
        reasons.append("node_platform_unqualified")
    try:
        if _version_tuple(release_version) <= _version_tuple(current_version):
            reasons.append("release_not_newer_than_installed")
    except ReleaseContractError:
        reasons.append("installed_version_invalid")

    target = next(
        (
            item
            for item in manifest["targets"]
            if item["system"] == capability.system
            and capability.architecture in set(item["architectures"])
        ),
        None,
    )
    if target is None:
        reasons.append("release_target_not_available")
        required_storage = 0
    else:
        artifact_bytes = int(target["artifact_bytes"])
        required_storage = artifact_bytes * 2 + 512 * 1024**2
        available = (
            capability.available_storage_bytes
            if available_storage_bytes is None
            else int(available_storage_bytes)
        )
        if available < required_storage:
            reasons.append("release_storage_insufficient")
        if (
            manifest["release_stage"] in {"production-candidate", "production"}
            and not platform_qualification_verified
        ):
            reasons.append("release_platform_qualification_unverified")
    if guardian_api_version not in set(manifest["guardian_api_versions"]):
        reasons.append("guardian_api_incompatible")
    if vault_schema_version not in set(manifest["readable_vault_schemas"]):
        reasons.append("vault_schema_incompatible")

    return ReleasePreflight(
        schema_version="tessaris.node-release-preflight.v1",
        eligible=not reasons,
        release_version=release_version,
        current_version=current_version,
        target_id=str(target["target_id"]) if target else None,
        required_storage_bytes=required_storage,
        reasons=tuple(sorted(set(reasons))),
    )


def evaluate_release_preflight_with_qualification(
    manifest: Mapping[str, Any],
    capability: NodeCapability,
    *,
    current_version: str,
    guardian_api_version: str,
    vault_schema_version: str,
    signature_verified: bool,
    repository_metadata_fresh: bool,
    qualification_envelope: Mapping[str, Any] | None,
    qualification_public_key: Ed25519PublicKey | None,
    available_storage_bytes: int | None = None,
) -> ReleasePreflight:
    """Verify exact signed platform evidence before production preflight eligibility."""

    qualification_verified = False
    if manifest.get("release_stage") in {"production-candidate", "production"}:
        if qualification_envelope is not None and qualification_public_key is not None:
            try:
                report = verify_node_platform_qualification(
                    qualification_envelope,
                    public_key=qualification_public_key,
                    release_manifest=manifest,
                )
                qualification_verified = (
                    report["declared_system"] == capability.system
                    and report["declared_architecture"] == capability.architecture
                )
            except NodePlatformQualificationError:
                qualification_verified = False
    return evaluate_release_preflight(
        manifest,
        capability,
        current_version=current_version,
        guardian_api_version=guardian_api_version,
        vault_schema_version=vault_schema_version,
        signature_verified=signature_verified,
        repository_metadata_fresh=repository_metadata_fresh,
        platform_qualification_verified=qualification_verified,
        available_storage_bytes=available_storage_bytes,
    )
