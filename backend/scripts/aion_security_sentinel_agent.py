#!/usr/bin/env python3
"""Tessaris user-space security sentinel.

Runs independently of the desktop UI, records bounded metadata only and never
performs containment.  It is deliberately stdlib-only so launchd can start it
before the Tessaris backend is available.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class SecuritySentinel:
    STATES = {"idle", "observing", "investigating", "review", "urgent", "verified", "offline"}

    def __init__(self, root: str | Path | None = None, watch_roots: list[str | Path] | None = None) -> None:
        self.root = Path(root or os.environ.get("TESSARIS_SENTINEL_STATE_DIR") or "~/.tessaris/security-sentinel").expanduser()
        raw_roots = watch_roots or [p for p in os.environ.get("TESSARIS_SENTINEL_WATCH_ROOTS", "").split(os.pathsep) if p]
        self.watch_roots = [Path(p).expanduser().resolve() for p in raw_roots if Path(p).expanduser().exists()]
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        self._previous: dict[str, Any] = {}
        self._recent: list[dict[str, Any]] = []
        self._cycle = 0
        self._hash_cache: dict[tuple[str, int, int], str] = {}
        try:
            for line in (self.root / "events.jsonl").read_text(encoding="utf-8").splitlines()[-50:]:
                value = json.loads(line)
                if isinstance(value, dict): self._recent.append(value)
        except (OSError, json.JSONDecodeError): pass

    def known_malware_hashes(self) -> set[str]:
        values: set[str] = set()
        feed_root = Path(os.environ.get("TESSARIS_CYBERSECURITY_FEED_ROOT", str(self.root))).expanduser()
        for path in feed_root.glob("**/vulnerability-feed.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                for item in payload.get("malware_hashes", []):
                    value = str(item.get("sha256") if isinstance(item, dict) else item).lower()
                    if re.fullmatch(r"[0-9a-f]{64}", value): values.add(value)
            except (OSError, json.JSONDecodeError): pass
        return values

    def known_endpoint_hashes(self) -> set[str]:
        values: set[str] = set()
        feed_root = Path(os.environ.get("TESSARIS_CYBERSECURITY_FEED_ROOT", str(self.root))).expanduser()
        for path in feed_root.glob("**/vulnerability-feed.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                for item in payload.get("malicious_endpoint_hashes", []):
                    value = str(item.get("sha256") if isinstance(item, dict) else item).lower()
                    if re.fullmatch(r"[0-9a-f]{64}", value): values.add(value)
            except (OSError, json.JSONDecodeError): pass
        return values

    def _file_hash(self, path: str) -> str | None:
        try:
            stat = os.stat(path)
            if not os.path.isfile(path) or stat.st_size > 500 * 1024 * 1024: return None
            key = (path, stat.st_mtime_ns, stat.st_size)
            if key in self._hash_cache: return self._hash_cache[key]
            hasher = hashlib.sha256()
            with open(path, "rb") as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b""): hasher.update(chunk)
            value = hasher.hexdigest(); self._hash_cache[key] = value; return value
        except OSError: return None

    def _run(self, argv: list[str], timeout: float = 8.0) -> str:
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, check=False,
                                    env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"})
            return (result.stdout or "")[:2_000_000] if result.returncode == 0 else ""
        except (OSError, subprocess.TimeoutExpired):
            return ""

    def _write_json(self, path: Path, payload: Any) -> None:
        fd, name = tempfile.mkstemp(prefix="sentinel-", suffix=".json", dir=str(self.root))
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, sort_keys=True, indent=2)
                handle.flush(); os.fsync(handle.fileno())
            os.chmod(name, 0o600); os.replace(name, path)
        finally:
            if os.path.exists(name): os.unlink(name)

    def emit(self, category: str, severity: str, title: str, summary: str, source: str) -> None:
        safe_summary = re.sub(r"(?i)(token|password|secret|key)\s*[=:]\s*\S+", r"\1=[REDACTED]", summary)[:500]
        event = {"event_id": f"se_{digest([category, title, safe_summary, time.time_ns()])[:20]}", "observed_at": now(),
                 "category": category[:80], "severity": severity.upper()[:16], "title": title[:200],
                 "summary": safe_summary, "source": source[:120], "requires_human_review": severity.upper() in {"HIGH", "CRITICAL"}}
        with (self.root / "events.jsonl").open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"); handle.flush(); os.fsync(handle.fileno())
        (self.root / "events.jsonl").chmod(0o600)
        self._recent.append(event); self._recent = self._recent[-50:]

    def process_snapshot(self) -> dict[str, Any]:
        records = []
        known_hashes = self.known_malware_hashes()
        own_tools = {"ps", "lsof", "system_profiler", "log", "socketfilterfw", "spctl", "fdesetup", "csrutil"}
        for line in self._run(["/bin/ps", "-axo", "pid=,ppid=,user=,comm="]).splitlines():
            parts = line.strip().split(None, 3)
            if len(parts) == 4:
                if Path(parts[3]).name in own_tools: continue
                record = {"pid": parts[0], "ppid": parts[1], "user_hash": hashlib.sha256(parts[2].encode()).hexdigest()[:12],
                          "executable": Path(parts[3]).name[:160], "path_hash": hashlib.sha256(parts[3].encode()).hexdigest()[:20]}
                if parts[3].startswith(("/tmp/", "/private/tmp/", "/var/tmp/")):
                    record["risk_hint"] = "executable_started_from_temporary_directory"
                if known_hashes:
                    file_hash = self._file_hash(parts[3])
                    if file_hash: record["sha256"] = file_hash
                records.append(record)
        stable = sorted({(item["executable"], item["path_hash"], item.get("sha256")) for item in records})
        return {"count": len(records), "records": records[:4000], "digest": digest(stable)}

    def network_snapshot(self) -> dict[str, Any]:
        rows = []
        malicious = self.known_endpoint_hashes()
        output = self._run(["/usr/sbin/lsof", "-nP", "-iTCP"])
        for line in output.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 9:
                endpoint = parts[8]
                remote = endpoint.split("->", 1)[-1]
                endpoint_hash = hashlib.sha256(remote.encode()).hexdigest()
                rows.append({"process": parts[0][:100], "connection": "LISTEN" if "LISTEN" in line else "ESTABLISHED",
                             "endpoint_hash": endpoint_hash[:20], "threat_match": endpoint_hash in malicious})
        return {"count": len(rows), "records": rows[:1000], "digest": digest(rows)}

    def file_snapshot(self, maximum: int = 30_000) -> dict[str, Any]:
        records: dict[str, dict[str, Any]] = {}
        attachment_risk = {".app", ".command", ".dmg", ".docm", ".iso", ".jar", ".js", ".pkg", ".sh", ".xlsm"}
        for root in self.watch_roots:
            for base, dirs, files in os.walk(root):
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", ".venv", "__pycache__"}][:200]
                for name in files:
                    if len(records) >= maximum: break
                    path = Path(base) / name
                    try:
                        stat = path.stat(); key = hashlib.sha256(str(path).encode()).hexdigest()[:24]
                        suffixes = [value.lower() for value in path.suffixes]
                        records[key] = {"modified": stat.st_mtime_ns, "size": stat.st_size,
                                        "suffix": suffixes[-1] if suffixes else "",
                                        "attachment_risk": bool((suffixes and suffixes[-1] in attachment_risk) or
                                                                (len(suffixes) > 1 and suffixes[-1] in {".app", ".command", ".js", ".sh"}))}
                    except OSError: pass
                if len(records) >= maximum: break
        return {"count": len(records), "records": records, "digest": digest(records)}

    def persistence_snapshot(self) -> dict[str, Any]:
        records = []
        for directory in (Path("~/Library/LaunchAgents").expanduser(), Path("/Library/LaunchAgents"), Path("/Library/LaunchDaemons")):
            if not directory.exists(): continue
            for path in sorted(directory.glob("*.plist"))[:1000]:
                try:
                    raw = path.read_bytes(); plistlib.loads(raw)
                    records.append({"name": path.name, "sha256": hashlib.sha256(raw).hexdigest()})
                except (OSError, plistlib.InvalidFileException): pass
        return {"count": len(records), "records": records, "digest": digest(records)}

    def usb_snapshot(self) -> dict[str, Any]:
        raw = self._run(["/usr/sbin/system_profiler", "SPUSBDataType", "-json"], 15.0)
        try: payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError: payload = {}
        return {"digest": digest(payload), "available": bool(payload)}

    def security_snapshot(self) -> dict[str, Any]:
        firewall = self._run(["/usr/libexec/ApplicationFirewall/socketfilterfw", "--getglobalstate"])
        gatekeeper = self._run(["/usr/sbin/spctl", "--status"])
        filevault = self._run(["/usr/bin/fdesetup", "status"])
        sip = self._run(["/usr/bin/csrutil", "status"])
        values = {"firewall": " ".join(firewall.split())[:200], "gatekeeper": " ".join(gatekeeper.split())[:200],
                  "filevault": " ".join(filevault.split())[:200], "system_integrity": " ".join(sip.split())[:200]}
        return {**values, "digest": digest(values)}

    def authentication_snapshot(self) -> dict[str, Any]:
        # Unified-log access can be restricted by macOS privacy controls.  Only
        # event counts/digests are retained, never account names or messages.
        argv = ["/usr/bin/log", "show", "--last", "2m", "--style", "json", "--predicate",
                "process != 'log' AND (eventMessage CONTAINS[c] 'authentication failed' OR eventMessage CONTAINS[c] 'login failed' OR eventMessage CONTAINS[c] 'privilege escalation')"]
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=12.0, check=False,
                                    env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"})
            raw, available = (result.stdout or "")[:2_000_000], result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            raw, available = "", False
        lines = [line for line in raw.splitlines() if line.lstrip().startswith("{")]
        return {"count": len(lines), "digest": digest(lines), "available": available}

    def malware_hash_snapshot(self) -> dict[str, Any]:
        bad_hashes = self.known_malware_hashes()
        matches = []
        for record in self._previous.get("processes", {}).get("records", []):
            if record.get("sha256") in bad_hashes: matches.append(record["sha256"])
        return {"feed_hash_count": len(bad_hashes), "matches": matches, "digest": digest([len(bad_hashes), matches])}

    def _compare(self, name: str, current: dict[str, Any]) -> None:
        previous = self._previous.get(name)
        if previous and previous.get("digest") != current.get("digest"):
            if name == "files":
                before, after = previous.get("records", {}), current.get("records", {})
                changed = sum(1 for key, value in after.items() if before.get(key) != value)
                deleted = len(set(before) - set(after))
                risky_new = [value for key, value in after.items() if key not in before and value.get("attachment_risk")]
                if risky_new:
                    self.emit("attachment", "MEDIUM", "Potentially risky downloaded file observed",
                              f"{len(risky_new)} new executable, macro-enabled or script attachment(s) require local review.", "file_metadata")
                if changed + deleted >= 50:
                    self.emit("ransomware_behaviour", "CRITICAL", "Rapid file-change pattern detected",
                              f"{changed} files changed and {deleted} disappeared in one observation interval.", "local_file_metadata")
            elif name == "persistence":
                self.emit("persistence", "HIGH", "Startup service configuration changed",
                          "A launch-agent or launch-daemon record was added, removed or modified.", "launchd_metadata")
            elif name == "usb":
                self.emit("external_storage", "MEDIUM", "USB device set changed", "A USB device was connected or removed.", "system_profiler")
            elif name == "security":
                self.emit("security_settings", "HIGH", "Firewall configuration changed", "The macOS firewall state changed.", "application_firewall")
            elif name == "network":
                threat_matches = sum(1 for item in current.get("records", []) if item.get("threat_match"))
                if threat_matches:
                    self.emit("network", "HIGH", "Connection matched approved threat intelligence",
                              f"{threat_matches} connection endpoint(s) matched the locally approved indicator feed.", "lsof_and_signed_feed")
                else:
                    self.emit("network", "LOW", "Network connection set changed", "A local TCP listener or connection appeared or disappeared.", "lsof")
            elif name == "processes":
                previous_keys = {(x.get("executable"), x.get("path_hash")) for x in previous.get("records", [])}
                risky = [x for x in current.get("records", []) if (x.get("executable"), x.get("path_hash")) not in previous_keys and x.get("risk_hint")]
                if risky:
                    self.emit("process", "MEDIUM", "Unusual process origin observed",
                              f"{len(risky)} new executable(s) started from a temporary writable location.", "process_metadata")
                else:
                    self.emit("process", "LOW", "Process activity observed", "The running executable set changed.", "process_metadata")
        self._previous[name] = current

    def cycle(self) -> dict[str, Any]:
        self._cycle += 1
        self._compare("processes", self.process_snapshot())
        if self._cycle % 2 == 0: self._compare("network", self.network_snapshot())
        if self._cycle % 2 == 0: self._compare("files", self.file_snapshot())
        if self._cycle % 6 == 0:
            self._compare("persistence", self.persistence_snapshot()); self._compare("security", self.security_snapshot())
            auth = self.authentication_snapshot(); self._previous["authentication"] = auth
            if auth["count"]: self.emit("authentication", "HIGH", "Authentication or privilege failures observed", f"{auth['count']} authentication or privilege events were observed.", "macos_unified_log")
            malware = self.malware_hash_snapshot()
            if malware["matches"]: self.emit("malware", "CRITICAL", "Known malware digest observed", f"{len(malware['matches'])} process digests matched the approved threat feed.", "signed_local_threat_feed")
        if self._cycle % 12 == 0: self._compare("usb", self.usb_snapshot())
        current_time = time.time()
        freshness = {"LOW": 15, "MEDIUM": 300, "HIGH": 600, "CRITICAL": 900}
        fresh = [e for e in self._recent if datetime.fromisoformat(e["observed_at"]).timestamp() >= current_time - freshness.get(e["severity"], 60)]
        control = {}
        try: control = json.loads((self.root / "control.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError): pass
        if control.get("state") == "verified":
            try:
                reviewed_at = datetime.fromisoformat(str(control.get("set_at"))).timestamp()
                fresh = [e for e in fresh if datetime.fromisoformat(e["observed_at"]).timestamp() > reviewed_at]
            except (ValueError, TypeError): pass
        severities = {e["severity"] for e in fresh}
        state = "urgent" if severities & {"CRITICAL"} else "review" if severities & {"HIGH"} else "observing" if fresh else "idle"
        try:
            if datetime.fromisoformat(str(control.get("expires_at"))).timestamp() > current_time:
                requested = str(control.get("state"))
                if requested in {"investigating", "verified"} and state not in {"urgent", "review"}: state = requested
        except (OSError, ValueError, TypeError, json.JSONDecodeError): pass
        status = {"schema_version": "aion.security.sentinel.v1", "state": state, "heartbeat_at": now(),
                  "agent": "AION_SECURITY_SENTINEL", "mode": "LOCAL_OBSERVE_ONLY", "containment": "HUMAN_APPROVAL_REQUIRED",
                  "watch_root_count": len(self.watch_roots), "recent_event_count": len(fresh), "last_event": fresh[-1] if fresh else None,
                  "coverage": {"processes": True, "file_changes": bool(self.watch_roots), "network_listeners": True,
                               "persistence": True, "usb": True, "firewall": True,
                               "authentication_log": bool(self._previous.get("authentication", {}).get("available")),
                               "download_attachment_metadata": any(path.name == "Downloads" for path in self.watch_roots),
                               "signed_threat_feed": bool(self.known_malware_hashes() or self.known_endpoint_hashes()), "kernel_edr": False}}
        self._write_json(self.root / "status.json", status)
        return status

    def run(self, interval: float = 5.0) -> None:
        lock = (self.root / "agent.lock").open("w")
        try: fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise SystemExit("sentinel_already_running")
        while True:
            try: self.cycle()
            except Exception as exc:
                self.emit("agent", "HIGH", "Sentinel observation failed", type(exc).__name__, "sentinel_runtime")
            time.sleep(max(2.0, interval))


if __name__ == "__main__":
    SecuritySentinel().run(float(os.environ.get("TESSARIS_SENTINEL_INTERVAL", "5")))
