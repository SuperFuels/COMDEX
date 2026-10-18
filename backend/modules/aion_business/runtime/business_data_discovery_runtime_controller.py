from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any

from backend.modules.aion_business.runtime.business_data_discovery_campaign import (
    build_discovery_campaign_status,
)
from backend.modules.aion_business.runtime.business_data_discovery import load_manifest
from backend.modules.aion_business.runtime.business_data_write_tracer import (
    BusinessDataWriteTracer,
)


class BusinessDataDiscoveryRuntimeControllerError(ValueError):
    pass


class BusinessDataDiscoveryRuntimeController:
    """One active, process-local discovery trace for an instrumented backend.

    The controller returns only counts and identifiers. Full content-free trace
    evidence is written to the controlled engineering evidence directory.
    """

    def __init__(
        self,
        *,
        manifest_path: str | Path,
        trace_root: str | Path,
        source_root: str | Path,
        application_root: str | Path,
        update_root: str | Path,
        vault_roots: list[str | Path],
        path_fingerprint_key: bytes,
        secret_store_roots: list[str | Path] | None = None,
        max_events: int = 100_000,
    ) -> None:
        self.manifest_path = Path(manifest_path).resolve()
        self.trace_root = Path(trace_root).resolve()
        self.source_root = Path(source_root).resolve()
        self.application_root = Path(application_root).resolve()
        self.update_root = Path(update_root).resolve()
        self.vault_roots = [Path(item).resolve() for item in vault_roots]
        self.secret_store_roots = [
            Path(item).resolve() for item in (secret_store_roots or [])
        ]
        self.path_fingerprint_key = bytes(path_fingerprint_key)
        self.max_events = int(max_events)
        self.required_sessions = {
            str(item["id"])
            for item in load_manifest(self.manifest_path)["required_discovery_sessions"]
        }
        self._lock = RLock()
        self._tracer: BusinessDataWriteTracer | None = None
        self._session_id: str | None = None
        self._scenario: str | None = None

    def status(self) -> dict[str, Any]:
        with self._lock:
            active = self._tracer is not None
            session_id = self._session_id
            scenario = self._scenario
        campaign = build_discovery_campaign_status(
            manifest_path=self.manifest_path, trace_root=self.trace_root
        )
        return {
            "active": active,
            "active_session_id": session_id,
            "active_scenario": scenario,
            "required_session_count": campaign["required_session_count"],
            "passed_session_count": campaign["passed_session_count"],
            "failed_session_count": campaign["failed_session_count"],
            "missing_session_count": campaign["missing_session_count"],
            "campaign_ready": campaign["campaign_ready"],
            "customer_content_included": False,
            "raw_paths_included": False,
        }

    def start(self, *, session_id: str, scenario: str) -> dict[str, Any]:
        with self._lock:
            if self._tracer is not None:
                raise BusinessDataDiscoveryRuntimeControllerError(
                    "discovery_runtime_session_already_active"
                )
            if session_id not in self.required_sessions:
                raise BusinessDataDiscoveryRuntimeControllerError(
                    f"discovery_runtime_session_not_required:{session_id}"
                )
            tracer = BusinessDataWriteTracer(
                source_root=self.source_root,
                application_root=self.application_root,
                update_root=self.update_root,
                vault_roots=self.vault_roots,
                secret_store_roots=self.secret_store_roots,
                excluded_roots=[self.trace_root],
                path_fingerprint_key=self.path_fingerprint_key,
                max_events=self.max_events,
            )
            tracer.start()
            self._tracer = tracer
            self._session_id = session_id
            self._scenario = scenario
        return self.status()

    def stop(self, *, scenario_completed: bool) -> dict[str, Any]:
        with self._lock:
            tracer = self._tracer
            session_id = self._session_id
            scenario = self._scenario
            if tracer is None or session_id is None or scenario is None:
                raise BusinessDataDiscoveryRuntimeControllerError(
                    "discovery_runtime_session_not_active"
                )
            tracer.stop()
            report_path = self.trace_root / f"{session_id}.desktop_backend.json"
            tracer.write_report(
                report_path,
                session_id=session_id,
                scenario=scenario,
                scenario_completed=scenario_completed,
                surface="desktop_backend",
            )
            self._tracer = None
            self._session_id = None
            self._scenario = None
        report = tracer.report(
            session_id=session_id,
            scenario=scenario,
            scenario_completed=scenario_completed,
            surface="desktop_backend",
        )
        return {
            "session_id": session_id,
            "scenario": scenario,
            "scenario_completed": report["scenario_completed"],
            "event_count": report["event_count"],
            "dropped_event_count": report["dropped_event_count"],
            "unsafe_write_count": report["unsafe_write_count"],
            "release_gate_passed": report["release_gate_passed"],
            "fragment_name": report_path.name,
            "campaign": self.status(),
            "customer_content_included": False,
            "raw_paths_included": False,
        }
