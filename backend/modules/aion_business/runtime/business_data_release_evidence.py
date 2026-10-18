from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable

from backend.modules.aion_business.runtime.business_data_discovery import load_manifest
from backend.modules.aion_business.runtime.business_data_discovery_scenarios import (
    load_discovery_scenario_catalogue,
)
from backend.modules.aion_business.runtime.business_data_write_tracer import TRACE_SCHEMA


EVIDENCE_SCHEMA = "tessaris.business-data-release-evidence.v3"
HEX_DIGEST_LENGTH = 64


class BusinessDataReleaseEvidenceError(ValueError):
    pass


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def build_business_data_release_evidence(
    *,
    manifest_path: str | Path,
    scenario_catalogue_path: str | Path,
    audit_report_path: str | Path,
    trace_report_paths: Iterable[str | Path],
) -> dict[str, Any]:
    """Bind static discovery and every required runtime session to one release artifact."""

    manifest_path = Path(manifest_path)
    scenario_catalogue_path = Path(scenario_catalogue_path)
    audit_report_path = Path(audit_report_path)
    trace_paths = [Path(raw_path) for raw_path in trace_report_paths]
    manifest = load_manifest(manifest_path)
    catalogue = load_discovery_scenario_catalogue(
        catalogue_path=scenario_catalogue_path,
        manifest_path=manifest_path,
    )
    catalogued = {
        str(item["session_id"]): {
            "surfaces": sorted({str(value) for value in item["execution_surfaces"]}),
            "domains": sorted({str(value) for value in item["expected_domains"]}),
            "external_classes": sorted({
                str(value)
                for value in item["expected_external_classes"]
                if value != "none"
            }),
        }
        for item in catalogue["scenarios"]
    }
    try:
        audit = json.loads(audit_report_path.read_text(encoding="utf-8"))
        reconciliation = audit["reconciliation"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise BusinessDataReleaseEvidenceError("business_data_audit_report_invalid") from exc

    unknown = int(reconciliation.get("unknown_count", -1))
    blocking_touchpoints = int(reconciliation.get("blocking_touchpoint_count", -1))
    incomplete = int(reconciliation.get("incomplete_discovery_session_count", -1))
    if unknown != 0:
        raise BusinessDataReleaseEvidenceError("unknown_business_data_writes")
    if blocking_touchpoints != 0:
        raise BusinessDataReleaseEvidenceError("blocking_business_data_touchpoints")
    if incomplete != 0:
        raise BusinessDataReleaseEvidenceError("incomplete_business_data_discovery")
    if reconciliation.get("vault_boundary_ready") is not True:
        raise BusinessDataReleaseEvidenceError("business_data_vault_boundary_not_ready")

    required_ids = {
        str(item["id"])
        for item in manifest["required_discovery_sessions"]
    }
    traces: dict[str, dict[str, Any]] = {}
    for path in trace_paths:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BusinessDataReleaseEvidenceError("runtime_trace_report_invalid") from exc
        session_id = str(report.get("session_id") or "")
        if report.get("schema_version") != TRACE_SCHEMA or session_id not in required_ids:
            raise BusinessDataReleaseEvidenceError(f"runtime_trace_identity_invalid:{session_id}")
        if path.name != f"{session_id}.json" or report.get("surface") != "aggregated":
            raise BusinessDataReleaseEvidenceError(
                f"runtime_trace_not_canonical_aggregate:{session_id}"
            )
        if session_id in traces:
            raise BusinessDataReleaseEvidenceError(f"runtime_trace_duplicate:{session_id}")
        expected_surfaces = catalogued[session_id]["surfaces"]
        required_surfaces = sorted({str(value) for value in report.get("required_surfaces") or []})
        included_surfaces = sorted({str(value) for value in report.get("included_surfaces") or []})
        missing_surfaces = list(report.get("missing_surfaces") or [])
        fragment_digests = report.get("fragment_sha256")
        if required_surfaces != expected_surfaces or included_surfaces != expected_surfaces:
            raise BusinessDataReleaseEvidenceError(
                f"runtime_trace_surface_coverage_invalid:{session_id}"
            )
        if missing_surfaces:
            raise BusinessDataReleaseEvidenceError(
                f"runtime_trace_surfaces_missing:{session_id}"
            )
        expected_domains = catalogued[session_id]["domains"]
        declared_domains = sorted({
            str(value) for value in report.get("expected_vault_domains") or []
        })
        observed_domains = sorted({
            str(value) for value in report.get("observed_vault_domains") or []
        })
        missing_domains = list(report.get("missing_vault_domains") or [])
        unexpected_domains = list(report.get("unexpected_vault_domains") or [])
        if (
            declared_domains != expected_domains
            or observed_domains != expected_domains
            or missing_domains
            or unexpected_domains
        ):
            raise BusinessDataReleaseEvidenceError(
                f"runtime_trace_domain_coverage_invalid:{session_id}"
            )
        expected_external = catalogued[session_id]["external_classes"]
        declared_external = sorted({
            str(value) for value in report.get("expected_external_classes") or []
        })
        observed_external = sorted({
            str(value) for value in report.get("observed_external_classes") or []
        })
        missing_external = list(report.get("missing_external_classes") or [])
        unexpected_external = list(report.get("unexpected_external_classes") or [])
        if (
            declared_external != expected_external
            or observed_external != expected_external
            or missing_external
            or unexpected_external
        ):
            raise BusinessDataReleaseEvidenceError(
                f"runtime_trace_external_coverage_invalid:{session_id}"
            )
        if (
            not isinstance(fragment_digests, dict)
            or sorted(fragment_digests) != expected_surfaces
            or not all(
                isinstance(value, str)
                and len(value) == HEX_DIGEST_LENGTH
                and all(character in "0123456789abcdef" for character in value)
                for value in fragment_digests.values()
            )
        ):
            raise BusinessDataReleaseEvidenceError(
                f"runtime_trace_fragment_digests_invalid:{session_id}"
            )
        if (
            report.get("scenario_completed") is not True
            or
            report.get("complete") is not True
            or report.get("release_gate_passed") is not True
            or int(report.get("dropped_event_count", -1)) != 0
            or int(report.get("unsafe_write_count", -1)) != 0
            or int(report.get("event_count", 0)) < 1
        ):
            raise BusinessDataReleaseEvidenceError(f"runtime_trace_failed:{session_id}")
        traces[session_id] = report

    missing = sorted(required_ids - set(traces))
    if missing:
        raise BusinessDataReleaseEvidenceError(
            "runtime_trace_sessions_missing:" + ",".join(missing)
        )
    scenarios = sorted({str(report["scenario"]) for report in traces.values()})
    trace_path_by_session = {
        path.stem: path for path in trace_paths if path.name == f"{path.stem}.json"
    }
    return {
        "schema_version": EVIDENCE_SCHEMA,
        "manifest_sha256": _digest(manifest_path),
        "scenario_catalogue_sha256": _digest(scenario_catalogue_path),
        "report_sha256": _digest(audit_report_path),
        "unknown_write_count": 0,
        "blocking_touchpoint_count": 0,
        "incomplete_discovery_session_count": 0,
        "required_discovery_session_count": len(required_ids),
        "runtime_trace_session_count": len(traces),
        "runtime_trace_scenarios": scenarios,
        "runtime_trace_sha256": {
            session_id: _digest(trace_path_by_session[session_id])
            for session_id in sorted(traces)
        },
        "runtime_trace_surface_counts": {
            session_id: len(catalogued[session_id]["surfaces"])
            for session_id in sorted(traces)
        },
        "runtime_trace_domain_counts": {
            session_id: len(catalogued[session_id]["domains"])
            for session_id in sorted(traces)
        },
        "runtime_trace_external_class_counts": {
            session_id: len(catalogued[session_id]["external_classes"])
            for session_id in sorted(traces)
        },
    }
