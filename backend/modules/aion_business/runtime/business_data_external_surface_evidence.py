from __future__ import annotations

from collections import Counter
import hashlib
import hmac
import json
from pathlib import Path
import re
from typing import Any

from backend.modules.aion_business.runtime.business_data_discovery_scenarios import (
    load_discovery_scenario_catalogue,
)
from backend.modules.aion_business.runtime.business_data_write_tracer import TRACE_SCHEMA


EXTERNAL_SURFACES = frozenset({"provider_sandbox", "mobile_companion"})
SAFE_OPERATION = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
SAFE_FINGERPRINT = re.compile(r"^[0-9a-f]{64}$")


class BusinessDataExternalSurfaceEvidenceError(ValueError):
    pass


class BusinessDataExternalSurfaceEvidenceRecorder:
    """Content-free discovery evidence for provider and mobile boundaries.

    Callers submit only an operation class, declared external class and a local
    identifier. The identifier is immediately HMACed and never retained in the
    report. Request/response bodies, contact data and credentials are prohibited.
    """

    def __init__(
        self,
        *,
        manifest_path: str | Path,
        scenario_catalogue_path: str | Path,
        session_id: str,
        scenario: str,
        surface: str,
        fingerprint_key: bytes,
        max_events: int = 100_000,
    ) -> None:
        if len(fingerprint_key) < 32:
            raise BusinessDataExternalSurfaceEvidenceError(
                "external_surface_fingerprint_key_too_short"
            )
        if surface not in EXTERNAL_SURFACES:
            raise BusinessDataExternalSurfaceEvidenceError(
                f"external_surface_invalid:{surface}"
            )
        catalogue = load_discovery_scenario_catalogue(
            catalogue_path=scenario_catalogue_path,
            manifest_path=manifest_path,
        )
        indexed = {str(item["session_id"]): item for item in catalogue["scenarios"]}
        if session_id not in indexed:
            raise BusinessDataExternalSurfaceEvidenceError(
                f"external_surface_session_invalid:{session_id}"
            )
        row = indexed[session_id]
        if surface not in set(row["execution_surfaces"]):
            raise BusinessDataExternalSurfaceEvidenceError(
                f"external_surface_not_required:{session_id}:{surface}"
            )
        self.session_id = session_id
        self.scenario = scenario
        self.surface = surface
        self.expected_external_classes = frozenset(
            str(value) for value in row["expected_external_classes"] if value != "none"
        )
        self._fingerprint_key = bytes(fingerprint_key)
        self._max_events = max(1, int(max_events))
        self._events: list[dict[str, Any]] = []
        self._dropped = 0

    def record(
        self,
        *,
        operation: str,
        external_class: str,
        identifier: str,
        approved: bool,
    ) -> None:
        operation = str(operation or "").strip()
        external_class = str(external_class or "").strip()
        identifier = str(identifier or "")
        if not SAFE_OPERATION.fullmatch(operation):
            raise BusinessDataExternalSurfaceEvidenceError(
                "external_surface_operation_invalid"
            )
        if external_class not in self.expected_external_classes:
            raise BusinessDataExternalSurfaceEvidenceError(
                f"external_surface_class_undeclared:{external_class}"
            )
        if not identifier:
            raise BusinessDataExternalSurfaceEvidenceError(
                "external_surface_identifier_required"
            )
        self._append(
            operation=operation,
            external_class=external_class,
            destination_hmac_sha256=hmac.new(
                self._fingerprint_key,
                identifier.encode("utf-8", errors="surrogatepass"),
                hashlib.sha256,
            ).hexdigest(),
            approved=approved,
        )

    def record_fingerprint(
        self,
        *,
        operation: str,
        external_class: str,
        identifier_hmac_sha256: str,
        approved: bool,
    ) -> None:
        """Record a fingerprint created on another instrumented surface.

        The authenticated intake API accepts this form only, so raw provider or
        mobile identifiers never cross into the desktop discovery controller.
        """
        operation = str(operation or "").strip()
        external_class = str(external_class or "").strip()
        fingerprint = str(identifier_hmac_sha256 or "").strip().lower()
        if not SAFE_OPERATION.fullmatch(operation):
            raise BusinessDataExternalSurfaceEvidenceError(
                "external_surface_operation_invalid"
            )
        if external_class not in self.expected_external_classes:
            raise BusinessDataExternalSurfaceEvidenceError(
                f"external_surface_class_undeclared:{external_class}"
            )
        if not SAFE_FINGERPRINT.fullmatch(fingerprint):
            raise BusinessDataExternalSurfaceEvidenceError(
                "external_surface_identifier_fingerprint_invalid"
            )
        self._append(
            operation=operation,
            external_class=external_class,
            destination_hmac_sha256=fingerprint,
            approved=approved,
        )

    def _append(
        self,
        *,
        operation: str,
        external_class: str,
        destination_hmac_sha256: str,
        approved: bool,
    ) -> None:
        if len(self._events) >= self._max_events:
            self._dropped += 1
            return
        self._events.append({
            "operation": operation,
            "external_class": external_class,
            "destination_class": "external_approved" if approved else "external_or_unknown",
            "destination_hmac_sha256": destination_hmac_sha256,
            "source_path": f"external_surface/{self.surface}",
            "line": 0,
        })

    def report(self, *, scenario_completed: bool) -> dict[str, Any]:
        destination_counts = Counter(
            event["destination_class"] for event in self._events
        )
        observed_classes = sorted({event["external_class"] for event in self._events})
        unsafe = int(destination_counts.get("external_or_unknown", 0))
        complete = bool(scenario_completed) and self._dropped == 0
        class_coverage_complete = set(observed_classes) == set(self.expected_external_classes)
        return {
            "schema_version": TRACE_SCHEMA,
            "session_id": self.session_id,
            "scenario": self.scenario,
            "surface": self.surface,
            "evidence_kind": "external_surface_observations",
            "privacy": "operation_classes_and_keyed_identifier_fingerprints_only_no_payloads_credentials_or_raw_identifiers",
            "expected_external_classes": sorted(self.expected_external_classes),
            "observed_external_classes": observed_classes,
            "event_count": len(self._events),
            "scenario_completed": bool(scenario_completed),
            "dropped_event_count": self._dropped,
            "complete": complete,
            "destination_counts": dict(sorted(destination_counts.items())),
            "unsafe_write_count": unsafe,
            "release_gate_passed": (
                complete
                and class_coverage_complete
                and bool(self._events)
                and unsafe == 0
            ),
            "grouped_source_operations": [],
            "events": [dict(event) for event in self._events],
        }

    def write_report(
        self,
        path: str | Path,
        *,
        scenario_completed: bool,
    ) -> dict[str, Any]:
        target = Path(path)
        report = self.report(scenario_completed=scenario_completed)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        try:
            target.chmod(0o600)
        except OSError:
            pass
        return report
