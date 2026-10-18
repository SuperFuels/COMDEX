from __future__ import annotations

from pathlib import Path
from threading import RLock
from typing import Any

from backend.modules.aion_business.runtime.business_data_external_surface_evidence import (
    BusinessDataExternalSurfaceEvidenceError,
    BusinessDataExternalSurfaceEvidenceRecorder,
    EXTERNAL_SURFACES,
)


class BusinessDataExternalSurfaceControllerError(ValueError):
    pass


class BusinessDataExternalSurfaceController:
    """Authenticated lifecycle for content-free provider/mobile evidence.

    One run per external surface may be active. Callers submit only a keyed
    identifier fingerprint; raw external identifiers and customer content are
    not accepted by this boundary.
    """

    def __init__(
        self,
        *,
        manifest_path: str | Path,
        scenario_catalogue_path: str | Path,
        trace_root: str | Path,
        fingerprint_key: bytes,
        max_events: int = 100_000,
    ) -> None:
        self.manifest_path = Path(manifest_path).resolve()
        self.scenario_catalogue_path = Path(scenario_catalogue_path).resolve()
        self.trace_root = Path(trace_root).resolve()
        self.fingerprint_key = bytes(fingerprint_key)
        self.max_events = max(1, int(max_events))
        self._lock = RLock()
        self._active: dict[str, tuple[str, str, BusinessDataExternalSurfaceEvidenceRecorder]] = {}

    def status(self) -> dict[str, Any]:
        with self._lock:
            active = {
                surface: {"session_id": row[0], "scenario": row[1]}
                for surface, row in sorted(self._active.items())
            }
        return {
            "active_surfaces": active,
            "allowed_surfaces": sorted(EXTERNAL_SURFACES),
            "customer_content_accepted": False,
            "raw_identifiers_accepted": False,
        }

    def start(
        self, *, session_id: str, scenario: str, surface: str
    ) -> dict[str, Any]:
        with self._lock:
            if surface in self._active:
                raise BusinessDataExternalSurfaceControllerError(
                    f"external_surface_session_already_active:{surface}"
                )
            try:
                recorder = BusinessDataExternalSurfaceEvidenceRecorder(
                    manifest_path=self.manifest_path,
                    scenario_catalogue_path=self.scenario_catalogue_path,
                    session_id=session_id,
                    scenario=scenario,
                    surface=surface,
                    fingerprint_key=self.fingerprint_key,
                    max_events=self.max_events,
                )
            except BusinessDataExternalSurfaceEvidenceError as exc:
                raise BusinessDataExternalSurfaceControllerError(str(exc)) from exc
            self._active[surface] = (session_id, scenario, recorder)
        return self.status()

    def record(
        self,
        *,
        surface: str,
        operation: str,
        external_class: str,
        identifier_hmac_sha256: str,
        approved: bool,
    ) -> dict[str, Any]:
        with self._lock:
            row = self._active.get(surface)
            if row is None:
                raise BusinessDataExternalSurfaceControllerError(
                    f"external_surface_session_not_active:{surface}"
                )
            try:
                row[2].record_fingerprint(
                    operation=operation,
                    external_class=external_class,
                    identifier_hmac_sha256=identifier_hmac_sha256,
                    approved=approved,
                )
            except BusinessDataExternalSurfaceEvidenceError as exc:
                raise BusinessDataExternalSurfaceControllerError(str(exc)) from exc
            report = row[2].report(scenario_completed=False)
        return {
            "surface": surface,
            "session_id": row[0],
            "event_count": report["event_count"],
            "dropped_event_count": report["dropped_event_count"],
            "customer_content_accepted": False,
            "raw_identifiers_accepted": False,
        }

    def stop(self, *, surface: str, scenario_completed: bool) -> dict[str, Any]:
        with self._lock:
            row = self._active.get(surface)
            if row is None:
                raise BusinessDataExternalSurfaceControllerError(
                    f"external_surface_session_not_active:{surface}"
                )
            session_id, scenario, recorder = row
            report_path = self.trace_root / f"{session_id}.{surface}.json"
            report = recorder.write_report(
                report_path, scenario_completed=scenario_completed
            )
            del self._active[surface]
        return {
            "surface": surface,
            "session_id": session_id,
            "scenario": scenario,
            "scenario_completed": report["scenario_completed"],
            "event_count": report["event_count"],
            "dropped_event_count": report["dropped_event_count"],
            "unsafe_write_count": report["unsafe_write_count"],
            "release_gate_passed": report["release_gate_passed"],
            "fragment_name": report_path.name,
            "customer_content_accepted": False,
            "raw_identifiers_accepted": False,
        }
