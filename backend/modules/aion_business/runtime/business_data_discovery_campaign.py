from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Callable, Iterable

from backend.modules.aion_business.runtime.business_data_discovery import load_manifest
from backend.modules.aion_business.runtime.business_data_discovery_scenarios import (
    load_discovery_scenario_catalogue,
)
from backend.modules.aion_business.runtime.business_data_write_tracer import (
    BusinessDataWriteTracer,
    TRACE_SCHEMA,
)


CAMPAIGN_SCHEMA = "tessaris.business-data-discovery-campaign.v1"
PYTHON_DISCOVERY_SURFACES = frozenset({
    "desktop_backend", "filesystem_import", "update_runner",
})


class BusinessDataDiscoveryCampaignError(ValueError):
    pass


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _required_sessions(manifest_path: str | Path) -> list[dict[str, str]]:
    manifest = load_manifest(Path(manifest_path))
    return [
        {"id": str(item["id"]), "name": str(item["name"])}
        for item in manifest["required_discovery_sessions"]
    ]


def _read_report(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BusinessDataDiscoveryCampaignError(
            f"discovery_trace_invalid:{path.name}"
        ) from exc
    if payload.get("schema_version") != TRACE_SCHEMA:
        raise BusinessDataDiscoveryCampaignError(
            f"discovery_trace_schema_invalid:{path.name}"
        )
    return payload


def build_discovery_campaign_status(
    *, manifest_path: str | Path, trace_root: str | Path
) -> dict[str, Any]:
    """Return deterministic, content-free coverage across every required session."""

    manifest_path = Path(manifest_path)
    trace_root = Path(trace_root)
    sessions: list[dict[str, Any]] = []
    passed = failed = missing = 0
    for required in _required_sessions(manifest_path):
        report_path = trace_root / f"{required['id']}.json"
        if not report_path.is_file():
            missing += 1
            sessions.append({
                **required,
                "evidence_status": "missing",
                "scenario": None,
                "event_count": 0,
                "unsafe_write_count": None,
                "dropped_event_count": None,
                "report_sha256": None,
            })
            continue
        report = _read_report(report_path)
        if report.get("session_id") != required["id"]:
            raise BusinessDataDiscoveryCampaignError(
                f"discovery_trace_session_mismatch:{required['id']}"
            )
        report_passed = (
            report.get("scenario_completed") is True
            and report.get("complete") is True
            and report.get("release_gate_passed") is True
            and int(report.get("dropped_event_count", -1)) == 0
            and int(report.get("unsafe_write_count", -1)) == 0
            and int(report.get("event_count", 0)) > 0
        )
        if report_passed:
            passed += 1
        else:
            failed += 1
        sessions.append({
            **required,
            "evidence_status": "passed" if report_passed else "failed",
            "scenario": str(report.get("scenario") or ""),
            "event_count": int(report.get("event_count", 0)),
            "unsafe_write_count": int(report.get("unsafe_write_count", -1)),
            "dropped_event_count": int(report.get("dropped_event_count", -1)),
            "report_sha256": _digest(report_path),
        })
    return {
        "schema_version": CAMPAIGN_SCHEMA,
        "privacy": "coverage_counts_hashes_and_scenario_ids_only_no_raw_paths_or_values",
        "manifest_sha256": _digest(manifest_path),
        "required_session_count": len(sessions),
        "passed_session_count": passed,
        "failed_session_count": failed,
        "missing_session_count": missing,
        "campaign_ready": passed == len(sessions) and failed == 0 and missing == 0,
        "sessions": sessions,
    }


def run_discovery_session(
    *,
    manifest_path: str | Path,
    scenario_catalogue_path: str | Path,
    trace_root: str | Path,
    session_id: str,
    scenario: str,
    scenario_callable: Callable[[], Any],
    source_root: str | Path,
    application_root: str | Path,
    update_root: str | Path,
    vault_roots: Iterable[str | Path],
    path_fingerprint_key: bytes,
    secret_store_roots: Iterable[str | Path] | None = None,
    surface: str = "desktop_backend",
    max_events: int = 100_000,
) -> dict[str, Any]:
    """Execute one in-process scenario and retain a trace even when it fails.

    Subprocesses are deliberately unsupported because Python audit hooks do not
    cross process boundaries. Electron and external-provider sessions require a
    separately instrumented runner rather than a false passing trace.
    """

    required = {item["id"] for item in _required_sessions(manifest_path)}
    if session_id not in required:
        raise BusinessDataDiscoveryCampaignError(
            f"discovery_session_not_required:{session_id}"
        )
    surface = str(surface or "").strip()
    if surface not in PYTHON_DISCOVERY_SURFACES:
        raise BusinessDataDiscoveryCampaignError(
            f"discovery_surface_not_python_instrumented:{surface}"
        )
    catalogue = load_discovery_scenario_catalogue(
        catalogue_path=scenario_catalogue_path,
        manifest_path=manifest_path,
    )
    scenario_row = next(
        item for item in catalogue["scenarios"] if item["session_id"] == session_id
    )
    if surface not in set(scenario_row["execution_surfaces"]):
        raise BusinessDataDiscoveryCampaignError(
            f"discovery_surface_not_required:{session_id}:{surface}"
        )
    if not callable(scenario_callable):
        raise BusinessDataDiscoveryCampaignError("discovery_scenario_not_callable")
    tracer = BusinessDataWriteTracer(
        source_root=source_root,
        application_root=application_root,
        update_root=update_root,
        vault_roots=list(vault_roots),
        secret_store_roots=list(secret_store_roots or []),
        path_fingerprint_key=path_fingerprint_key,
        max_events=max_events,
    )
    scenario_completed = False
    failure: BaseException | None = None
    try:
        with tracer:
            scenario_callable()
        scenario_completed = True
    except BaseException as exc:  # evidence must survive scenario failure
        failure = exc
    report_path = Path(trace_root) / f"{session_id}.{surface}.json"
    tracer.write_report(
        report_path,
        session_id=session_id,
        scenario=scenario,
        scenario_completed=scenario_completed,
        surface=surface,
    )
    report = _read_report(report_path)
    if failure is not None:
        raise BusinessDataDiscoveryCampaignError(
            f"discovery_scenario_failed:{session_id}"
        ) from failure
    return report
