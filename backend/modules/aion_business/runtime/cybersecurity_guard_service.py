"""Local-first, evidence-bounded cybersecurity guard for a Tessaris workspace.

The guard deliberately separates observation from response.  A safe scan may
inventory the current machine and read security state.  It never probes remote
hosts, changes a firewall, stops a service, quarantines or deletes content.
Those operations are represented as approval-gated proposals for a later,
separately authorised executor.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import base64
import http.client
import ipaddress
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import socket
import ssl
import subprocess
import tempfile
import threading
import uuid
import zipfile
from io import BytesIO
from typing import Any
from functools import wraps

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from backend.modules.aion_business.runtime.paths import AIONBusinessPaths
from backend.modules.aion_business.runtime.business_vault_runtime import (
    configured_business_vault_runtime,
    guardian_mode_requested,
)
from backend.modules.aion_business.runtime.vault_domain_store import VaultDomainStore


SCHEMA = "aion.cybersecurity.guard.v1"
DISRUPTIVE_ACTIONS = {
    "quarantine_file", "delete_file", "block_address", "change_firewall",
    "stop_process", "stop_service", "revoke_access", "isolate_device",
}
_WORKSPACE_LOCKS: dict[str, threading.RLock] = {}
_WORKSPACE_LOCKS_GUARD = threading.Lock()


def _workspace_locked(function):
    @wraps(function)
    def wrapped(self, workspace_id: str, *args, **kwargs):
        key = _safe_id(workspace_id)
        with _WORKSPACE_LOCKS_GUARD:
            lock = _WORKSPACE_LOCKS.setdefault(key, threading.RLock())
        with lock:
            return function(self, workspace_id, *args, **kwargs)
    return wrapped


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(value or "")).strip("-.")
    if not cleaned or cleaned in {".", ".."}:
        raise ValueError("invalid_workspace_id")
    return cleaned[:160]


def _digest(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass
class CommandEvidence:
    status: str
    summary: str
    source: str


class CybersecurityGuardService:
    def __init__(self, *, root: str | Path | None = None, command_timeout: float = 4.0,
                 trusted_feed_public_key: str | None = None,
                 allowed_scan_roots: list[str | Path] | None = None,
                 response_executor: Any | None = None,
                 domain_store: VaultDomainStore | None = None) -> None:
        if root is None and domain_store is None and guardian_mode_requested():
            runtime = configured_business_vault_runtime()
            domain_store = VaultDomainStore(runtime.guardian, actor_id="cybersecurity-guard-runtime")
        self.domain_store = domain_store
        self.root = Path(root) if root else AIONBusinessPaths.ROOT / "cybersecurity_guard"
        self.command_timeout = max(0.5, min(float(command_timeout), 15.0))
        self.trusted_feed_public_key = str(
            trusted_feed_public_key or os.environ.get("TESSARIS_CYBERSECURITY_FEED_PUBLIC_KEY") or ""
        ).strip()
        configured_roots = allowed_scan_roots or [Path.cwd()]
        self.allowed_scan_roots = [Path(item).expanduser().resolve() for item in configured_roots]
        self.response_executor = response_executor
        self.sentinel_root = Path(os.environ.get("TESSARIS_SENTINEL_STATE_DIR") or "~/.tessaris/security-sentinel").expanduser()

    def sentinel_status(self) -> dict[str, Any]:
        path = self.sentinel_root / "status.json"
        try:
            if path.stat().st_size > 64 * 1024:
                raise ValueError("sentinel_status_too_large")
            value = json.loads(path.read_text(encoding="utf-8"))
            heartbeat = datetime.fromisoformat(str(value.get("heartbeat_at", "")))
            age = (datetime.now(timezone.utc) - heartbeat.astimezone(timezone.utc)).total_seconds()
            if age > 30:
                return {"state": "offline", "detail": "The standalone sentinel heartbeat is stale."}
            return {
                "state": value.get("state", "offline"), "heartbeat_at": value.get("heartbeat_at"),
                "recent_event_count": int(value.get("recent_event_count", 0)),
                "last_event": value.get("last_event"), "coverage": value.get("coverage", {}),
                "mode": value.get("mode", "LOCAL_OBSERVE_ONLY"),
            }
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return {"state": "offline", "detail": "The standalone sentinel is not running."}

    def _sentinel_findings(self) -> list[dict[str, Any]]:
        path = self.sentinel_root / "events.jsonl"
        try:
            lines = path.read_text(encoding="utf-8").splitlines()[-200:]
        except OSError:
            return []
        findings = []
        for line in lines:
            try:
                event = json.loads(line)
                severity = str(event.get("severity", "LOW")).upper()
                if severity not in {"MEDIUM", "HIGH", "CRITICAL"}:
                    continue
                event_id = str(event.get("event_id", ""))[:100]
                findings.append(self._finding(
                    category=str(event.get("category", "sentinel_event")), severity=severity,
                    title=str(event.get("title", "Sentinel event"))[:240],
                    summary=str(event.get("summary", ""))[:500], source="standalone_security_sentinel",
                    asset_id="local_desktop", confidence="MEDIUM" if severity == "MEDIUM" else "HIGH",
                ) | {"sentinel_event_id": event_id, "observed_at": event.get("observed_at", _now())})
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
        unique = {item["finding_id"]: item for item in findings}
        return list(unique.values())[-100:]

    def set_sentinel_state(self, state: str, *, actor_id: str, seconds: int = 30) -> dict[str, Any]:
        if state not in {"investigating", "verified"}:
            raise ValueError("invalid_sentinel_control_state")
        self.sentinel_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        expires = datetime.now(timezone.utc).timestamp() + max(5, min(int(seconds), 300))
        payload = {"state": state, "set_at": _now(), "expires_at": datetime.fromtimestamp(expires, timezone.utc).isoformat(),
                   "actor_digest": sha256(str(actor_id).encode()).hexdigest()}
        path = self.sentinel_root / "control.json"
        fd, temp_name = tempfile.mkstemp(prefix="control-", suffix=".json", dir=str(self.sentinel_root))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True); handle.flush(); os.fsync(handle.fileno())
            os.chmod(temp_name, 0o600); os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name): os.unlink(temp_name)
        return {"state": state, "expires_at": payload["expires_at"]}

    def _workspace_dir(self, workspace_id: str) -> Path:
        if self.domain_store is not None:
            return Path("/__tessaris_guardian_cybersecurity__") / _safe_id(workspace_id)
        path = self.root / _safe_id(workspace_id)
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            path.chmod(0o700)
        except OSError:
            pass
        return path

    def _state_path(self, workspace_id: str) -> Path:
        return self._workspace_dir(workspace_id) / "state.json"

    def _journal_path(self, workspace_id: str) -> Path:
        return self._workspace_dir(workspace_id) / "events.jsonl"

    def _default_state(self, workspace_id: str) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA,
            "workspace_id": workspace_id,
            "guard": {
                "mode": "LOCAL_READ_ONLY",
                "status": "FOUNDATION_ACTIVE",
                "schedule": "desktop_runtime_every_30_minutes",
                "last_scan_at": None,
                "next_scan_at": None,
                "aion_role": "EVIDENCE_GROUNDED_INVESTIGATOR",
            },
            "capabilities": {
                "device_inventory": "AVAILABLE",
                "applications": "AVAILABLE",
                "software_licences": "MANUAL_EVIDENCE_REQUIRED",
                "listening_services": "AVAILABLE_WHEN_OS_TOOL_PRESENT",
                "firewall": "AVAILABLE_WHEN_OS_TOOL_PRESENT",
                "backup": "AVAILABLE_WHEN_OS_TOOL_PRESENT",
                "vulnerability_feed": "NOT_CONFIGURED",
                "credential_exposure_scan": "EXPLICIT_SCOPE_REQUIRED",
                "attachment_analysis": "EXPLICIT_FILE_REQUIRED",
                "domain_security": "EXPLICIT_TARGET_REQUIRED",
                "active_network_scan": "APPROVAL_REQUIRED",
                "response_execution": "NOT_ENABLED",
            },
            "assets": [], "findings": [], "incidents": [], "action_proposals": [], "scan_runs": [],
            "attachment_analyses": [], "domain_checks": [], "secret_scans": [],
            "restore_tests": [], "update_checks": [], "vulnerability_assessments": [], "vulnerability_feed": None,
            "updated_at": _now(),
        }

    def load(self, workspace_id: str) -> dict[str, Any]:
        if self.domain_store is not None:
            record = self.domain_store.get_optional(
                "security.records", workspace_id=workspace_id, entity_id="guard/state"
            )
            if record is None:
                state = self._default_state(workspace_id)
                self._write(workspace_id, state)
            else:
                state = record["payload"]
            if state.get("workspace_id") != workspace_id:
                raise RuntimeError("cybersecurity_workspace_mismatch")
            return self._hydrate_runtime_state(workspace_id, state)
        path = self._state_path(workspace_id)
        if not path.exists():
            state = self._default_state(workspace_id)
            self._write(workspace_id, state)
            state["sentinel"] = self.sentinel_status()
            return state
        state = json.loads(path.read_text(encoding="utf-8"))
        if state.get("workspace_id") != workspace_id:
            raise RuntimeError("cybersecurity_workspace_mismatch")
        return self._hydrate_runtime_state(workspace_id, state)

    def _hydrate_runtime_state(self, workspace_id: str, state: dict[str, Any]) -> dict[str, Any]:
        defaults = self._default_state(workspace_id)
        state.setdefault("capabilities", {})
        for key, value in defaults["capabilities"].items():
            state["capabilities"].setdefault(key, value)
        state.setdefault("guard", defaults["guard"])
        for key in ("assets", "findings", "incidents", "action_proposals", "scan_runs",
                    "attachment_analyses", "domain_checks", "secret_scans", "restore_tests", "update_checks",
                    "vulnerability_assessments"):
            state.setdefault(key, [])
        state.setdefault("vulnerability_feed", None)
        state["sentinel"] = self.sentinel_status()
        known = {item.get("finding_id") for item in state["findings"]}
        state["findings"].extend(item for item in self._sentinel_findings() if item.get("finding_id") not in known)
        return state

    def _write(self, workspace_id: str, state: dict[str, Any]) -> None:
        state["updated_at"] = _now()
        if self.domain_store is not None:
            current = self.domain_store.get_optional(
                "security.records", workspace_id=workspace_id, entity_id="guard/state"
            )
            self.domain_store.put(
                "security.records", workspace_id=workspace_id, entity_id="guard/state",
                payload=state, expected_version=int(current["version"]) if current else None,
            )
            return
        path = self._state_path(workspace_id)
        fd, temp_name = tempfile.mkstemp(prefix="state-", suffix=".json", dir=str(path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(state, handle, sort_keys=True, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temp_name, 0o600)
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)

    def _event(self, workspace_id: str, event_type: str, actor_id: str, payload: dict[str, Any]) -> None:
        event = {
            "event_id": f"cybevt_{uuid.uuid4().hex}", "occurred_at": _now(),
            "workspace_id": workspace_id, "event_type": event_type,
            "actor_id": str(actor_id or "system")[:160], "payload_digest": _digest(payload),
        }
        if self.domain_store is not None:
            self.domain_store.put(
                "security.audit", workspace_id=workspace_id,
                entity_id=f"events/{event['event_id']}", payload=event,
            )
            return
        path = self._journal_path(workspace_id)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def _command(self, argv: list[str]) -> CommandEvidence:
        try:
            completed = subprocess.run(
                argv, capture_output=True, text=True, timeout=self.command_timeout,
                check=False, env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"},
            )
        except FileNotFoundError:
            return CommandEvidence("UNAVAILABLE", "Operating-system tool is not installed.", argv[0])
        except subprocess.TimeoutExpired:
            return CommandEvidence("TIMEOUT", "Read-only check exceeded its time limit.", argv[0])
        output = (completed.stdout or completed.stderr or "").strip().replace("\x00", "")
        # Raw command output can contain usernames, paths or addresses.  The state
        # stores only a short summary and its digest, never the unbounded output.
        summary = " ".join(output.split())[:500] if output else f"Exited with status {completed.returncode}."
        return CommandEvidence("OK" if completed.returncode == 0 else "CHECK_FAILED", summary, argv[0])

    def _inventory(self) -> tuple[list[dict[str, Any]], dict[str, CommandEvidence]]:
        host = socket.gethostname()[:160]
        os_record = {
            "asset_id": f"device_{sha256(host.encode()).hexdigest()[:16]}",
            "asset_type": "desktop_or_vm", "display_name": host,
            "operating_system": platform.system(), "os_release": platform.release(),
            "architecture": platform.machine(), "observed_at": _now(), "source": "python_platform",
        }
        software: list[dict[str, str]] = []
        if platform.system() == "Darwin":
            applications = Path("/Applications")
            if applications.exists():
                for item in sorted(applications.iterdir())[:1000]:
                    if item.suffix.lower() != ".app":
                        continue
                    name, version = item.stem, "unknown"
                    try:
                        with (item / "Contents" / "Info.plist").open("rb") as handle:
                            info = plistlib.load(handle)
                        name = str(info.get("CFBundleDisplayName") or info.get("CFBundleName") or name)[:240]
                        version = str(info.get("CFBundleShortVersionString") or info.get("CFBundleVersion") or version)[:120]
                    except (OSError, plistlib.InvalidFileException):
                        pass
                    software.append({"name": name, "version": version, "ecosystem": "macos_application"})
        os_record["application_count"] = len(software)
        os_record["software"] = software
        evidence: dict[str, CommandEvidence] = {}
        if platform.system() == "Darwin":
            evidence["listening_services"] = self._command(["/usr/sbin/lsof", "-nP", "-iTCP", "-sTCP:LISTEN"])
            evidence["firewall"] = self._command(["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"])
            evidence["backup"] = self._command(["/usr/bin/tmutil", "latestbackup"])
        else:
            evidence["listening_services"] = self._command(["/usr/bin/ss", "-lnt"])
            evidence["firewall"] = CommandEvidence("NOT_ASSESSED", "Platform-specific firewall adapter is not configured.", "platform_adapter")
            evidence["backup"] = CommandEvidence("NOT_ASSESSED", "Platform-specific backup adapter is not configured.", "platform_adapter")
        return [os_record], evidence

    @staticmethod
    def _finding(*, category: str, severity: str, title: str, summary: str, source: str,
                 asset_id: str, confidence: str = "HIGH", status: str = "OPEN") -> dict[str, Any]:
        evidence_digest = sha256(f"{category}|{source}|{summary}".encode()).hexdigest()
        return {
            "finding_id": f"cybf_{evidence_digest[:20]}", "category": category,
            "severity": severity, "confidence": confidence, "title": title,
            "summary": summary, "affected_asset_id": asset_id, "source": source,
            "evidence_digest": evidence_digest, "status": status,
            "requires_approval": False, "observed_at": _now(),
        }

    @staticmethod
    def _backup_age_hours(summary: str) -> float | None:
        match = re.search(r"(20\d{2})-(\d{2})-(\d{2})-(\d{6})", str(summary or ""))
        if not match:
            return None
        try:
            observed = datetime.strptime("".join(match.groups()), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.now(timezone.utc) - observed).total_seconds() / 3600)
        except ValueError:
            return None

    @_workspace_locked
    def run_safe_scan(self, workspace_id: str, *, actor_id: str) -> dict[str, Any]:
        state = self.load(workspace_id)
        started_at = _now()
        assets, evidence = self._inventory()
        findings: list[dict[str, Any]] = []
        device_id = assets[0]["asset_id"]
        firewall = evidence.get("firewall")
        if firewall and firewall.status == "OK" and "disabled" in firewall.summary.lower():
            findings.append(self._finding(
                category="firewall", severity="HIGH", title="Host firewall appears disabled",
                summary="The operating-system firewall check reported a disabled global state.",
                source=firewall.source, asset_id=device_id,
            ))
        backup = evidence.get("backup")
        backup_age = self._backup_age_hours(backup.summary) if backup and backup.status == "OK" else None
        if backup_age is not None and backup_age > 48:
            findings.append(self._finding(
                category="backup_freshness", severity="MEDIUM", title="Latest backup appears stale",
                summary=f"The latest recorded backup is approximately {int(backup_age)} hours old.",
                source=backup.source, asset_id=device_id,
            ))
        for key, item in evidence.items():
            if item.status in {"UNAVAILABLE", "TIMEOUT", "CHECK_FAILED", "NOT_ASSESSED"}:
                findings.append(self._finding(
                    category="coverage", severity="INFO", title=f"{key.replace('_', ' ').title()} not fully assessed",
                    summary=item.summary, source=item.source, asset_id=device_id,
                    confidence="HIGH", status="COVERAGE_GAP",
                ))
        run = {
            "run_id": f"cybscan_{uuid.uuid4().hex}", "kind": "SAFE_LOCAL_READ_ONLY",
            "started_at": started_at, "completed_at": _now(), "actor_id": actor_id,
            "asset_count": len(assets), "finding_count": len(findings),
            "evidence": {key: {"status": value.status, "summary": value.summary,
                                "source": value.source, "digest": sha256(value.summary.encode()).hexdigest()}
                         for key, value in evidence.items()},
            "boundaries": ["no_remote_probe", "no_file_content_scan", "no_configuration_change", "no_response_action"],
        }
        prior = {item["finding_id"]: item for item in state.get("findings", [])}
        for finding in findings:
            prior[finding["finding_id"]] = finding
        state["assets"] = assets
        state["findings"] = sorted(prior.values(), key=lambda item: (item.get("severity") != "HIGH", item.get("title", "")))
        state.setdefault("scan_runs", []).insert(0, run)
        state["scan_runs"] = state["scan_runs"][:100]
        state["guard"]["last_scan_at"] = run["completed_at"]
        self._write(workspace_id, state)
        self._event(workspace_id, "SAFE_SCAN_COMPLETED", actor_id, run)
        return {"state": state, "scan_run": run}

    @_workspace_locked
    def import_vulnerability_feed(self, workspace_id: str, *, actor_id: str,
                                  feed: dict[str, Any], signature_base64: str) -> dict[str, Any]:
        """Verify and retain only a signed feed.

        The public key is configuration, never request data.  This prevents a
        feed from appointing its own trust anchor.
        """
        if not self.trusted_feed_public_key:
            raise RuntimeError("trusted_vulnerability_feed_key_not_configured")
        canonical = json.dumps(feed, sort_keys=True, separators=(",", ":")).encode()
        try:
            public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(self.trusted_feed_public_key, validate=True))
            public_key.verify(base64.b64decode(signature_base64, validate=True), canonical)
        except (ValueError, InvalidSignature) as exc:
            raise PermissionError("vulnerability_feed_signature_invalid") from exc
        if feed.get("schema_version") != "tessaris.cybersecurity.vulnerability-feed.v1":
            raise ValueError("unsupported_vulnerability_feed_schema")
        try:
            issued_at = datetime.fromisoformat(str(feed.get("issued_at") or "").replace("Z", "+00:00"))
            expires_at = datetime.fromisoformat(str(feed.get("expires_at") or "").replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if issued_at.tzinfo is None or expires_at.tzinfo is None or issued_at > now or expires_at <= now:
                raise ValueError("vulnerability_feed_time_window_invalid")
        except (TypeError, ValueError) as exc:
            if str(exc) == "vulnerability_feed_time_window_invalid":
                raise
            raise ValueError("vulnerability_feed_time_window_invalid") from exc
        entries = feed.get("entries")
        if not isinstance(entries, list) or len(entries) > 100_000:
            raise ValueError("invalid_vulnerability_feed_entries")
        descriptor = {
            "feed_id": str(feed.get("feed_id") or "")[:160],
            "issued_at": str(feed.get("issued_at") or "")[:80],
            "expires_at": str(feed.get("expires_at") or "")[:80],
            "entry_count": len(entries), "sha256": sha256(canonical).hexdigest(),
            "signature_verified": True, "imported_at": _now(),
        }
        if self.domain_store is not None:
            self.domain_store.put(
                "security.records", workspace_id=workspace_id,
                entity_id="guard/vulnerability-feed", payload=feed,
            )
        else:
            feed_path = self._workspace_dir(workspace_id) / "vulnerability-feed.json"
            feed_path.write_text(json.dumps(feed, sort_keys=True, separators=(",", ":")), encoding="utf-8")
            feed_path.chmod(0o600)
        state = self.load(workspace_id)
        state["vulnerability_feed"] = descriptor
        state["capabilities"]["vulnerability_feed"] = "SIGNED_FEED_ACTIVE"
        self._write(workspace_id, state)
        self._event(workspace_id, "SIGNED_VULNERABILITY_FEED_IMPORTED", actor_id, descriptor)
        return descriptor

    @_workspace_locked
    def assess_vulnerabilities(self, workspace_id: str, *, actor_id: str) -> dict[str, Any]:
        state = self.load(workspace_id)
        descriptor = state.get("vulnerability_feed")
        feed_record = self.domain_store.get_optional(
            "security.records", workspace_id=workspace_id, entity_id="guard/vulnerability-feed"
        ) if self.domain_store is not None else None
        feed_path = self._workspace_dir(workspace_id) / "vulnerability-feed.json"
        if not descriptor or not descriptor.get("signature_verified") or (feed_record is None and not feed_path.exists()):
            raise RuntimeError("signed_vulnerability_feed_required")
        feed = feed_record["payload"] if feed_record is not None else json.loads(feed_path.read_text(encoding="utf-8"))
        installed: dict[tuple[str, str], dict[str, str]] = {}
        for asset in state.get("assets", []):
            for item in asset.get("software", []):
                installed[(str(item.get("ecosystem", "")).casefold(), str(item.get("name", "")).casefold())] = item
        matches: list[dict[str, Any]] = []
        for entry in feed.get("entries", []):
            if not isinstance(entry, dict):
                continue
            key = (str(entry.get("ecosystem", "")).casefold(), str(entry.get("product", "")).casefold())
            application = installed.get(key)
            affected_versions = {str(value) for value in entry.get("affected_versions", []) if isinstance(value, (str, int, float))}
            if not application or str(application.get("version")) not in affected_versions:
                continue
            match = {
                "advisory_id": str(entry.get("advisory_id") or "")[:160],
                "product": application["name"], "installed_version": application["version"],
                "fixed_version": str(entry.get("fixed_version") or "unknown")[:120],
                "severity": str(entry.get("severity") or "MEDIUM").upper()[:20],
                "feed_sha256": descriptor["sha256"],
            }
            matches.append(match)
            state["findings"].append(self._finding(
                category="known_vulnerable_software", severity=match["severity"],
                title=f"Known vulnerable software: {match['product']}",
                summary=f"Installed version {match['installed_version']} matches {match['advisory_id']}; feed fixed version is {match['fixed_version']}.",
                source=f"signed_feed:{descriptor['feed_id']}", asset_id="local_software_inventory", confidence="HIGH",
            ))
        record = {
            "assessment_id": f"cybvuln_{uuid.uuid4().hex}", "assessed_at": _now(),
            "feed_id": descriptor["feed_id"], "feed_sha256": descriptor["sha256"],
            "installed_product_count": len(installed), "match_count": len(matches), "matches": matches,
            "comparison": "exact_version_membership_v1",
        }
        state.setdefault("vulnerability_assessments", []).insert(0, record)
        state["vulnerability_assessments"] = state["vulnerability_assessments"][:50]
        # Multiple assessments of the same evidence must not create duplicate findings.
        state["findings"] = list({item["finding_id"]: item for item in state["findings"]}.values())
        self._write(workspace_id, state); self._event(workspace_id, "VULNERABILITY_ASSESSMENT_COMPLETED", actor_id, record)
        return record

    @_workspace_locked
    def check_updates(self, workspace_id: str, *, actor_id: str) -> dict[str, Any]:
        """Run explicit read-only update checks; never install an update."""
        checks: dict[str, CommandEvidence] = {}
        if platform.system() == "Darwin":
            checks["operating_system"] = self._command(["/usr/sbin/softwareupdate", "--list"])
            brew = Path("/opt/homebrew/bin/brew")
            checks["homebrew"] = self._command([str(brew), "outdated", "--verbose"]) if brew.exists() else CommandEvidence("UNAVAILABLE", "Homebrew is not installed at the configured path.", str(brew))
        else:
            checks["operating_system"] = CommandEvidence("NOT_ASSESSED", "A platform update adapter is not configured.", "platform_adapter")
        record = {
            "check_id": f"cybupd_{uuid.uuid4().hex}", "checked_at": _now(),
            "actor_id": actor_id, "installation_performed": False,
            "sources": {key: {"status": value.status, "summary": value.summary, "source": value.source,
                              "digest": sha256(value.summary.encode()).hexdigest()} for key, value in checks.items()},
        }
        state = self.load(workspace_id)
        state["update_checks"].insert(0, record); state["update_checks"] = state["update_checks"][:50]
        self._write(workspace_id, state); self._event(workspace_id, "UPDATE_CHECK_COMPLETED", actor_id, record)
        return record

    @_workspace_locked
    def scan_secrets(self, workspace_id: str, *, actor_id: str, scope: str,
                     maximum_files: int = 2_000) -> dict[str, Any]:
        requested = Path(scope).expanduser().resolve()
        if not any(requested == root or root in requested.parents for root in self.allowed_scan_roots):
            raise PermissionError("secret_scan_scope_not_allowed")
        if not requested.exists() or not requested.is_dir():
            raise ValueError("secret_scan_scope_must_be_directory")
        patterns = {
            "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
            "generic_secret_assignment": re.compile(rb"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_./+\-=]{16,}"),
            "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
            "openai_style_key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
        }
        excluded = {".git", "node_modules", ".venv", "venv", "dist", "build", "__pycache__"}
        matches: list[dict[str, Any]] = []
        scanned = 0
        for path in requested.rglob("*"):
            if scanned >= max(1, min(int(maximum_files), 10_000)):
                break
            if path.is_symlink() or not path.is_file() or any(part in excluded for part in path.parts):
                continue
            try:
                if path.stat().st_size > 2_000_000:
                    continue
                data = path.read_bytes()
            except OSError:
                continue
            if b"\x00" in data[:4096]:
                continue
            scanned += 1
            for pattern_name, pattern in patterns.items():
                for match in list(pattern.finditer(data))[:20]:
                    line_number = data[:match.start()].count(b"\n") + 1
                    relative = str(path.relative_to(requested))
                    file_mode = path.stat().st_mode & 0o777
                    matches.append({
                        "kind": pattern_name, "relative_path": relative[:500], "line": line_number,
                        "fingerprint": sha256(match.group(0)).hexdigest(), "value_redacted": True,
                        "file_mode": f"{file_mode:03o}", "excessive_permissions": bool(file_mode & 0o077),
                    })
                    if len(matches) >= 500:
                        break
                if len(matches) >= 500:
                    break
            if len(matches) >= 500:
                break
        record = {
            "scan_id": f"cybsec_{uuid.uuid4().hex}", "scope_digest": sha256(str(requested).encode()).hexdigest(),
            "scope_label": requested.name, "scanned_files": scanned, "match_count": len(matches),
            "matches": matches, "truncated": scanned >= maximum_files or len(matches) >= 500,
            "completed_at": _now(), "raw_values_retained": False,
        }
        state = self.load(workspace_id); state["secret_scans"].insert(0, record); state["secret_scans"] = state["secret_scans"][:30]
        for item in matches:
            state["findings"].append(self._finding(
                category="credential_exposure", severity="HIGH", title=f"Potential {item['kind'].replace('_', ' ')}",
                summary=f"A redacted credential pattern was detected in {item['relative_path']} at line {item['line']}.",
                source="bounded_local_secret_scan", asset_id="workspace_files", confidence="MEDIUM",
            ))
        self._write(workspace_id, state); self._event(workspace_id, "SCOPED_SECRET_SCAN_COMPLETED", actor_id, record)
        return record

    @_workspace_locked
    def analyse_attachment(self, workspace_id: str, *, actor_id: str, filename: str,
                           media_type: str, data: bytes) -> dict[str, Any]:
        if len(data) > 25 * 1024 * 1024:
            raise ValueError("attachment_exceeds_25mb_limit")
        name = Path(filename).name[:240]
        lower = name.lower()
        indicators: list[dict[str, str]] = []
        dangerous_extensions = {".exe", ".dll", ".scr", ".bat", ".cmd", ".ps1", ".js", ".vbs", ".jar", ".dmg", ".pkg"}
        suffixes = [item.lower() for item in Path(lower).suffixes]
        if suffixes and suffixes[-1] in dangerous_extensions:
            indicators.append({"type": "executable_or_script", "severity": "HIGH", "detail": f"File extension {suffixes[-1]} can execute code."})
        if len(suffixes) > 1 and suffixes[-2] in {".pdf", ".doc", ".docx", ".jpg", ".png", ".txt"}:
            indicators.append({"type": "double_extension", "severity": "HIGH", "detail": "Filename uses a misleading double extension."})
        sample = data[:5_000_000].lower()
        if b"/javascript" in sample or b"/openaction" in sample or b"powershell" in sample:
            indicators.append({"type": "active_content", "severity": "HIGH", "detail": "Static content markers indicate script or automatic actions."})
        if data[:4] == b"PK\x03\x04":
            try:
                with zipfile.ZipFile(BytesIO(data)) as archive:
                    names = [item.lower() for item in archive.namelist()[:10_000]]
                    if any("vbaproject.bin" in item or item.endswith(".js") or item.endswith(".exe") for item in names):
                        indicators.append({"type": "embedded_active_content", "severity": "HIGH", "detail": "The archive contains macro or executable content."})
            except zipfile.BadZipFile:
                indicators.append({"type": "malformed_archive", "severity": "MEDIUM", "detail": "The archive structure is malformed."})
        urls = sorted({match.decode("utf-8", "ignore")[:500] for match in re.findall(rb"https?://[^\s<>\"']{4,500}", sample)})[:50]
        if urls:
            indicators.append({"type": "external_links", "severity": "INFO", "detail": f"Found {len(urls)} external link(s); reputation was not checked."})
        record = {
            "analysis_id": f"cybatt_{uuid.uuid4().hex}", "filename": name,
            "media_type": str(media_type)[:160], "size": len(data), "sha256": sha256(data).hexdigest(),
            "indicators": indicators, "external_link_count": len(urls),
            "malware_engine_used": False, "content_retained": False, "analysed_at": _now(),
        }
        state = self.load(workspace_id); state["attachment_analyses"].insert(0, record); state["attachment_analyses"] = state["attachment_analyses"][:100]
        for item in indicators:
            if item["severity"] in {"HIGH", "MEDIUM"}:
                state["findings"].append(self._finding(
                    category="suspicious_attachment", severity=item["severity"], title=f"Attachment: {item['type'].replace('_', ' ')}",
                    summary=f"{name}: {item['detail']}", source="local_static_attachment_analysis",
                    asset_id=f"attachment_{record['sha256'][:16]}", confidence="MEDIUM",
                ))
        self._write(workspace_id, state); self._event(workspace_id, "ATTACHMENT_ANALYSED", actor_id, record)
        return record

    @_workspace_locked
    def check_domain(self, workspace_id: str, *, actor_id: str, hostname: str, port: int = 443) -> dict[str, Any]:
        host = str(hostname or "").strip().lower().rstrip(".")
        if not re.fullmatch(r"(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}", host):
            raise ValueError("invalid_domain_name")
        port = int(port)
        if port < 1 or port > 65535:
            raise ValueError("invalid_tls_port")
        addresses = sorted({item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)})[:20]
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise ValueError("domain_resolves_to_non_public_address")
        context = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=5) as raw:
            with context.wrap_socket(raw, server_hostname=host) as secured:
                certificate = secured.getpeercert()
                protocol = secured.version()
        expires_raw = str(certificate.get("notAfter") or "")
        expires_at = None
        if expires_raw:
            expires_at = datetime.fromtimestamp(ssl.cert_time_to_seconds(expires_raw), tz=timezone.utc).isoformat()
        required_headers = {
            "strict-transport-security": "HSTS", "content-security-policy": "CSP",
            "x-content-type-options": "MIME sniffing protection", "x-frame-options": "frame protection",
            "referrer-policy": "referrer policy", "permissions-policy": "browser permissions policy",
        }
        response_status = None
        observed_headers: dict[str, bool] = {key: False for key in required_headers}
        header_check_status = "UNAVAILABLE"
        try:
            connection = http.client.HTTPSConnection(host, port=port, timeout=5, context=context)
            connection.request("HEAD", "/", headers={"User-Agent": "Tessaris-Security-Guard/1"})
            response = connection.getresponse()
            response_status = response.status
            names = {name.lower() for name, _ in response.getheaders()}
            observed_headers = {key: key in names for key in required_headers}
            response.read(1024)
            connection.close()
            header_check_status = "ASSESSED"
        except (OSError, ssl.SSLError, http.client.HTTPException):
            pass
        record = {
            "check_id": f"cybdom_{uuid.uuid4().hex}", "hostname": host, "port": port,
            "addresses": addresses, "tls_protocol": protocol, "certificate_expires_at": expires_at,
            "certificate_subject_digest": sha256(json.dumps(certificate.get("subject", []), sort_keys=True).encode()).hexdigest(),
            "dnssec_assessed": False, "http_headers_assessed": header_check_status == "ASSESSED",
            "http_status": response_status, "security_headers": observed_headers,
            "checked_at": _now(),
        }
        state = self.load(workspace_id); state["domain_checks"].insert(0, record); state["domain_checks"] = state["domain_checks"][:100]
        if expires_at:
            expires = datetime.fromisoformat(expires_at)
            remaining_days = (expires - datetime.now(timezone.utc)).total_seconds() / 86400
            if remaining_days < 30:
                state["findings"].append(self._finding(
                    category="certificate_expiry", severity="HIGH" if remaining_days < 7 else "MEDIUM",
                    title=f"TLS certificate expires in {max(0, int(remaining_days))} days",
                    summary=f"The verified certificate for {host} expires at {expires_at}.",
                    source="explicit_tls_check", asset_id=f"domain_{host}", confidence="HIGH",
                ))
        if header_check_status == "ASSESSED":
            missing = [label for key, label in required_headers.items() if not observed_headers[key]]
            if missing:
                state["findings"].append(self._finding(
                    category="website_security_headers", severity="LOW",
                    title="Website security headers require review",
                    summary=f"{host} did not return: {', '.join(missing)} on the checked HTTPS response.",
                    source="explicit_https_head_check", asset_id=f"domain_{host}", confidence="MEDIUM",
                ))
        state["findings"] = list({item["finding_id"]: item for item in state["findings"]}.values())
        self._write(workspace_id, state); self._event(workspace_id, "DOMAIN_TLS_CHECK_COMPLETED", actor_id, record)
        return record

    @_workspace_locked
    def record_restore_test(self, workspace_id: str, *, actor_id: str, backup_system: str,
                            tested_at: str, result: str, evidence_reference: str,
                            notes: str = "") -> dict[str, Any]:
        result = str(result).upper()
        if result not in {"PASSED", "FAILED", "PARTIAL"}:
            raise ValueError("invalid_restore_test_result")
        record = {
            "restore_test_id": f"cybrst_{uuid.uuid4().hex}", "backup_system": str(backup_system)[:160],
            "tested_at": str(tested_at)[:80], "result": result,
            "evidence_reference": str(evidence_reference)[:500], "notes": str(notes)[:2000],
            "recorded_at": _now(), "recorded_by": actor_id,
        }
        state = self.load(workspace_id); state["restore_tests"].insert(0, record); state["restore_tests"] = state["restore_tests"][:100]
        self._write(workspace_id, state); self._event(workspace_id, "RESTORE_TEST_RECORDED", actor_id, record)
        return record

    @_workspace_locked
    def propose_action(self, workspace_id: str, *, actor_id: str, action_type: str,
                       target: str, reason: str) -> dict[str, Any]:
        action_type = str(action_type or "").strip().lower()
        if action_type not in DISRUPTIVE_ACTIONS:
            raise ValueError("unsupported_security_action")
        proposal = {
            "proposal_id": f"cybact_{uuid.uuid4().hex}", "action_type": action_type,
            "target": str(target)[:500], "reason": str(reason)[:2000],
            "status": "AWAITING_APPROVAL", "requires_approval": True,
            "execution_enabled": self.response_executor is not None, "created_at": _now(), "created_by": actor_id,
        }
        state = self.load(workspace_id)
        state.setdefault("action_proposals", []).insert(0, proposal)
        self._write(workspace_id, state)
        self._event(workspace_id, "ACTION_PROPOSED", actor_id, proposal)
        return proposal

    @_workspace_locked
    def approve_action(self, workspace_id: str, proposal_id: str, *, actor_id: str,
                       confirmation: str) -> dict[str, Any]:
        state = self.load(workspace_id)
        proposal = next((item for item in state.get("action_proposals", []) if item.get("proposal_id") == proposal_id), None)
        if not proposal:
            raise KeyError("security_action_proposal_not_found")
        expected = f"APPROVE {proposal_id}"
        if confirmation != expected:
            raise PermissionError("exact_security_action_confirmation_required")
        proposal.update({"status": "APPROVED_NOT_EXECUTED", "approved_at": _now(), "approved_by": actor_id})
        self._write(workspace_id, state)
        self._event(workspace_id, "ACTION_APPROVED_NOT_EXECUTED", actor_id, proposal)
        return proposal

    @_workspace_locked
    def execute_approved_action(self, workspace_id: str, proposal_id: str, *, actor_id: str,
                                confirmation: str) -> dict[str, Any]:
        """Invoke a separately supplied endpoint-response adapter, never shell logic.

        The default production construction supplies no adapter, so this fails
        closed even after approval.  An adapter must return a content-free,
        serialisable receipt and remains responsible for platform policy.
        """
        if self.response_executor is None:
            raise RuntimeError("endpoint_response_executor_not_configured")
        state = self.load(workspace_id)
        proposal = next((item for item in state.get("action_proposals", []) if item.get("proposal_id") == proposal_id), None)
        if not proposal:
            raise KeyError("security_action_proposal_not_found")
        if proposal.get("status") != "APPROVED_NOT_EXECUTED":
            raise PermissionError("security_action_must_be_approved_before_execution")
        if confirmation != f"EXECUTE {proposal_id}":
            raise PermissionError("exact_security_execution_confirmation_required")
        receipt = self.response_executor.execute(dict(proposal))
        if not isinstance(receipt, dict) or receipt.get("ok") is not True:
            raise RuntimeError("endpoint_response_executor_failed")
        safe_receipt = {
            "executor": str(receipt.get("executor") or "configured_adapter")[:160],
            "reference": str(receipt.get("reference") or "")[:500],
            "completed_at": str(receipt.get("completed_at") or _now())[:80], "ok": True,
        }
        proposal.update({"status": "EXECUTED", "executed_at": _now(), "executed_by": actor_id,
                         "execution_receipt": safe_receipt})
        self._write(workspace_id, state)
        self._event(workspace_id, "APPROVED_ACTION_EXECUTED", actor_id, {"proposal_id": proposal_id, **safe_receipt})
        return proposal

    @_workspace_locked
    def create_incident(self, workspace_id: str, *, actor_id: str, title: str,
                        severity: str, summary: str) -> dict[str, Any]:
        severity = str(severity or "MEDIUM").upper()
        if severity not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
            raise ValueError("invalid_incident_severity")
        incident = {
            "incident_id": f"cybinc_{uuid.uuid4().hex}", "title": str(title)[:240],
            "severity": severity, "summary": str(summary)[:5000], "status": "OPEN",
            "created_at": _now(), "events": [{"event_type": "OPENED", "at": _now(), "actor_id": actor_id}],
        }
        state = self.load(workspace_id)
        state.setdefault("incidents", []).insert(0, incident)
        self._write(workspace_id, state)
        self._event(workspace_id, "INCIDENT_OPENED", actor_id, incident)
        return incident

    def investigate(self, workspace_id: str, *, question: str) -> dict[str, Any]:
        self.set_sentinel_state("investigating", actor_id="security_pilot", seconds=20)
        state = self.load(workspace_id)
        open_findings = [item for item in state.get("findings", []) if item.get("status") in {"OPEN", "COVERAGE_GAP"}]
        highest = next((level for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
                        if any(item.get("severity") == level for item in open_findings)), "NONE")
        return {
            "answer": (
                f"I reviewed the current local Security Guard evidence. There are {len(open_findings)} open findings "
                f"and the highest recorded severity is {highest}. I have not run an active network probe or changed "
                "the device. Review the cited findings and coverage gaps before approving any response."
            ),
            "question": str(question)[:4000], "finding_ids": [item["finding_id"] for item in open_findings[:20]],
            "evidence_as_of": state.get("guard", {}).get("last_scan_at"),
            "limitations": ["deterministic_summary_not_security_certification", "no_unrecorded_claims", "no_response_executed"],
        }


class CybersecurityGuardScheduler:
    """Recurring safe scans for workspaces that have activated the guard."""

    def __init__(self, service: CybersecurityGuardService | None = None, *, interval_seconds: int = 1800) -> None:
        self.service = service or CybersecurityGuardService()
        self.interval_seconds = max(60, int(interval_seconds))
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def run_once(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        if self.service.domain_store is not None:
            workspace_ids = sorted({
                str(record.get("workspace_id") or "")
                for record in self.service.domain_store.list_all("security.records")
                if record.get("entity_id") == "guard/state"
                and record.get("workspace_id")
            })
            for workspace_id in workspace_ids:
                try:
                    scan = self.service.run_safe_scan(
                        workspace_id, actor_id="cybersecurity_guard_scheduler"
                    )
                    results.append({
                        "workspace_id": workspace_id,
                        "ok": True,
                        "run_id": scan["scan_run"]["run_id"],
                    })
                except Exception as exc:
                    results.append({
                        "workspace_id": workspace_id,
                        "ok": False,
                        "error": type(exc).__name__,
                    })
            return results
        if not self.service.root.exists():
            return results
        for state_path in sorted(self.service.root.glob("*/state.json")):
            workspace_id = state_path.parent.name
            try:
                scan = self.service.run_safe_scan(workspace_id, actor_id="cybersecurity_guard_scheduler")
                results.append({"workspace_id": workspace_id, "ok": True, "run_id": scan["scan_run"]["run_id"]})
            except Exception as exc:  # failure is recorded without stopping other workspaces
                results.append({"workspace_id": workspace_id, "ok": False, "error": type(exc).__name__})
        return results

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            self.run_once()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="tessaris-cybersecurity-guard", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
