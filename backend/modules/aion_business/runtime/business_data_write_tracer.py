from __future__ import annotations

import hashlib
import hmac
import inspect
import json
import os
import re
import sqlite3
import sys
import threading
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


TRACE_SCHEMA = "tessaris.business-data-runtime-trace.v1"
WRITE_OPEN_MODES = frozenset("wax+")
WRITE_OPEN_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
SAFE_TRACE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
SOURCE_WRAPPER_PATHS = frozenset({
    "backend/modules/local_node/private_sqlite.py",
    "backend/modules/aion_business/runtime/paths.py",
    "backend/modules/aion_business/runtime/vault_domain_store.py",
    "backend/modules/aion_business/runtime/guardian_business_container_repository.py",
})


def _within(candidate: Path, parent: Path) -> bool:
    try:
        candidate.relative_to(parent)
        return True
    except ValueError:
        return False


class BusinessDataWriteTracerError(ValueError):
    pass


class BusinessDataWriteTracer:
    """Process runtime write evidence with HMAC paths and no business payloads."""

    def __init__(
        self,
        *,
        source_root: str | Path,
        application_root: str | Path,
        update_root: str | Path,
        vault_roots: list[str | Path],
        path_fingerprint_key: bytes,
        secret_store_roots: list[str | Path] | None = None,
        excluded_roots: list[str | Path] | None = None,
        max_events: int = 100_000,
    ) -> None:
        if len(path_fingerprint_key) < 32:
            raise BusinessDataWriteTracerError("trace_fingerprint_key_too_short")
        self.source_root = Path(source_root).resolve(strict=False)
        self.application_root = Path(application_root).resolve(strict=False)
        self.update_root = Path(update_root).resolve(strict=False)
        self.vault_roots = tuple(Path(path).resolve(strict=False) for path in vault_roots)
        self.secret_store_roots = tuple(
            Path(path).resolve(strict=False) for path in (secret_store_roots or [])
        )
        # Engineering evidence is written while a journey is running (for
        # example provider-sandbox receipts).  It is neither customer data nor
        # an approved customer-data destination, so omit it from the business
        # write trace instead of falsely classifying the tracer's own evidence
        # as an external business-data write.
        self.excluded_roots = tuple(
            Path(path).resolve(strict=False) for path in (excluded_roots or [])
        )
        self._fingerprint_key = bytes(path_fingerprint_key)
        self.max_events = max(1, int(max_events))
        self._events: list[dict[str, Any]] = []
        self._counts: Counter[tuple[str, str, str, int]] = Counter()
        self._domain_counts: Counter[tuple[str, str]] = Counter()
        self._domain_source_counts: Counter[tuple[str, str, str, int]] = Counter()
        self._dropped = 0
        self._enabled = False
        self._suspended = threading.local()
        self._lock = threading.RLock()
        sys.addaudithook(self._audit)

    def start(self) -> None:
        with self._lock:
            self._enabled = True

    def stop(self) -> None:
        with self._lock:
            self._enabled = False

    def __enter__(self) -> "BusinessDataWriteTracer":
        self.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stop()

    def _audit(self, event: str, args: tuple[Any, ...]) -> None:
        if not self._enabled or getattr(self._suspended, "value", False):
            return
        if event == "tessaris.vault_domain_access":
            if (
                len(args) >= 2
                and isinstance(args[0], str)
                and isinstance(args[1], str)
                and SAFE_TRACE_ID.fullmatch(args[0])
                and SAFE_TRACE_ID.fullmatch(args[1])
            ):
                source_path, line = self._caller()
                with self._lock:
                    self._domain_counts[(args[0], args[1])] += 1
                    if source_path is not None:
                        self._domain_source_counts[(args[0], args[1], source_path, line)] += 1
            return
        operation, raw_path = self._write_event(event, args)
        if operation is None or raw_path is None:
            return
        try:
            destination = Path(os.fsdecode(raw_path)).expanduser().resolve(strict=False)
        except (TypeError, ValueError, OSError):
            return
        if any(_within(destination, root) for root in self.excluded_roots):
            return
        source_path, line = self._caller()
        if source_path is None:
            return
        destination_class = self._destination_class(destination)
        path_hmac = hmac.new(
            self._fingerprint_key,
            str(destination).encode("utf-8", errors="surrogatepass"),
            hashlib.sha256,
        ).hexdigest()
        key = (operation, destination_class, source_path, line)
        with self._lock:
            self._counts[key] += 1
            if len(self._events) >= self.max_events:
                self._dropped += 1
                return
            self._events.append(
                {
                    "operation": operation,
                    "destination_class": destination_class,
                    "destination_hmac_sha256": path_hmac,
                    "source_path": source_path,
                    "line": line,
                }
            )

    @staticmethod
    def _write_event(event: str, args: tuple[Any, ...]) -> tuple[str | None, Any | None]:
        if event == "open" and args:
            mode = args[1] if len(args) > 1 else ""
            flags = args[2] if len(args) > 2 else 0
            string_write = isinstance(mode, str) and any(character in mode for character in WRITE_OPEN_MODES)
            flag_write = isinstance(flags, int) and bool(flags & WRITE_OPEN_FLAGS)
            return ("file.open_write", args[0]) if string_write or flag_write else (None, None)
        if event in {"os.mkdir", "os.remove", "os.rmdir"} and args:
            return (event, args[0])
        if event in {"os.rename", "os.replace"} and len(args) >= 2:
            return (event, args[1])
        if event == "sqlite3.connect" and args:
            return ("sqlite.connect", args[0])
        return None, None

    def _caller(self) -> tuple[str | None, int]:
        frame = inspect.currentframe()
        try:
            while frame:
                filename = Path(frame.f_code.co_filename).resolve(strict=False)
                if _within(filename, self.source_root) and filename != Path(__file__).resolve(strict=False):
                    relative = filename.relative_to(self.source_root).as_posix()
                    if relative not in SOURCE_WRAPPER_PATHS:
                        return relative, int(frame.f_lineno)
                frame = frame.f_back
        finally:
            del frame
        return None, 0

    def _destination_class(self, destination: Path) -> str:
        if any(_within(destination, root) for root in self.vault_roots):
            return "business_vault"
        if any(_within(destination, root) for root in self.secret_store_roots):
            return "secret_store"
        if _within(destination, self.update_root):
            return "update_boundary"
        if _within(destination, self.application_root):
            return "application_boundary"
        return "external_or_unknown"

    def report(
        self,
        *,
        session_id: str,
        scenario: str,
        scenario_completed: bool = True,
        surface: str = "desktop_backend",
    ) -> dict[str, Any]:
        session_id = str(session_id or "").strip()
        scenario = str(scenario or "").strip()
        surface = str(surface or "").strip()
        if (
            not SAFE_TRACE_ID.fullmatch(session_id)
            or not SAFE_TRACE_ID.fullmatch(scenario)
            or not SAFE_TRACE_ID.fullmatch(surface)
        ):
            raise BusinessDataWriteTracerError("trace_session_identity_required")
        with self._lock:
            events = [dict(event) for event in self._events]
            grouped = [
                {
                    "operation": key[0],
                    "destination_class": key[1],
                    "source_path": key[2],
                    "line": key[3],
                    "count": count,
                }
                for key, count in sorted(self._counts.items())
            ]
            dropped = self._dropped
            domain_counts = dict(self._domain_counts)
            domain_source_counts = dict(self._domain_source_counts)
        destination_counts = Counter(event["destination_class"] for event in events)
        return {
            "schema_version": TRACE_SCHEMA,
            "session_id": session_id,
            "scenario": scenario,
            "surface": surface,
            "evidence_kind": "process_write_observations",
            "privacy": "source_locations_registered_domain_ids_and_keyed_path_fingerprints_only_no_raw_paths_or_values",
            "observed_vault_domains": sorted({domain for domain, _ in domain_counts}),
            "vault_domain_operations": [
                {"domain_id": key[0], "operation": key[1], "count": count}
                for key, count in sorted(domain_counts.items())
            ],
            "vault_domain_source_operations": [
                {
                    "domain_id": key[0],
                    "operation": key[1],
                    "source_path": key[2],
                    "line": key[3],
                    "count": count,
                }
                for key, count in sorted(domain_source_counts.items())
            ],
            "event_count": len(events),
            "scenario_completed": bool(scenario_completed),
            "dropped_event_count": dropped,
            "complete": bool(scenario_completed) and dropped == 0,
            "destination_counts": dict(sorted(destination_counts.items())),
            "unsafe_write_count": sum(
                count for destination, count in destination_counts.items()
                if destination in {"application_boundary", "update_boundary", "external_or_unknown"}
            ),
            "release_gate_passed": bool(events) and bool(scenario_completed) and dropped == 0 and all(
                destination in {"business_vault", "secret_store"}
                for destination in destination_counts
            ),
            "grouped_source_operations": grouped,
            "events": events,
        }

    def write_report(
        self,
        path: str | Path,
        *,
        session_id: str,
        scenario: str,
        scenario_completed: bool = True,
        surface: str = "desktop_backend",
    ) -> None:
        payload = self.report(
            session_id=session_id,
            scenario=scenario,
            scenario_completed=scenario_completed,
            surface=surface,
        )
        target = Path(path)
        self._suspended.value = True
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        finally:
            self._suspended.value = False
