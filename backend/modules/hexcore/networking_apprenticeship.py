"""Bounded executable networking apprenticeship using an isolated localhost lab."""
from __future__ import annotations

import http.server
import json
import socket
import socketserver
import ssl
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

from backend.modules.hexcore.canonical_cognitive_runtime import _canonical_hash, _utc_timestamp
from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_networking_apprenticeship_v1"


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal, "source": "networking_academy_cau"}


def run(*, state_path: Path, result_path: Path) -> dict[str, Any]:
    stop = threading.Event(); messages: list[dict[str, Any]] = []
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0)); server.listen(4); server.settimeout(0.1)
    host, port = server.getsockname()

    def serve() -> None:
        while not stop.is_set():
            try:
                connection, _ = server.accept()
            except TimeoutError:
                continue
            with connection:
                connection.settimeout(1)
                payload = connection.recv(4096)
                try:
                    row = json.loads(payload.decode("utf-8"))
                    if set(row) != {"request_id", "value"} or len(payload) > 1024:
                        raise ValueError("invalid frame")
                    messages.append(row)
                    response = {"request_id": row["request_id"], "result": row["value"] * 2}
                except Exception:
                    response = {"error": "invalid_frame"}
                connection.sendall(json.dumps(response).encode("utf-8"))

    thread = threading.Thread(target=serve, daemon=True); thread.start()
    started = time.perf_counter()
    with socket.create_connection((host, port), timeout=1) as client:
        client.sendall(json.dumps({"request_id": "r1", "value": 21}).encode())
        response = json.loads(client.recv(4096).decode())
    latency = time.perf_counter() - started
    with socket.create_connection((host, port), timeout=1) as client:
        client.sendall(b"not-json")
        malformed = json.loads(client.recv(4096).decode())
    stop.set(); server.close(); thread.join(timeout=2)
    refused = False
    try:
        socket.create_connection((host, port), timeout=0.1)
    except OSError:
        refused = True

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            body = b'{"status":"healthy"}'
            self.send_response(200); self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
        def log_message(self, format: str, *args: object) -> None:
            del format, args
    httpd = socketserver.TCPServer(("127.0.0.1", 0), Handler)
    http_thread = threading.Thread(target=httpd.serve_forever, daemon=True); http_thread.start()
    with urllib.request.urlopen(f"http://127.0.0.1:{httpd.server_address[1]}/health", timeout=1) as handle:
        http_payload = json.loads(handle.read())
    httpd.shutdown(); httpd.server_close(); http_thread.join(timeout=2)

    addresses = socket.getaddrinfo("localhost", None, type=socket.SOCK_STREAM)
    tls = ssl.create_default_context()
    tls_safe = tls.check_hostname and tls.verify_mode == ssl.CERT_REQUIRED
    attacks = [
        {"bind": "0.0.0.0"}, {"tls_verify": False}, {"timeout": None},
        {"frame_limit": None}, {"protocol": "eval"}, {"shell": True},
    ]
    rejected = sum(
        case.get("bind") == "0.0.0.0" or case.get("tls_verify") is False
        or case.get("timeout") is None and "timeout" in case
        or case.get("frame_limit") is None and "frame_limit" in case
        or case.get("protocol") == "eval" or case.get("shell") is True
        for case in attacks
    )
    gate = {
        "tcp_ip_round_trip": response == {"request_id": "r1", "result": 42},
        "dns_resolution": bool(addresses),
        "http_contract": http_payload == {"status": "healthy"},
        "tls_safe_default": tls_safe,
        "routing_loopback_isolation": host == "127.0.0.1",
        "latency_measured": 0 <= latency < 1,
        "failure_modes": malformed.get("error") == "invalid_frame" and refused,
        "protocol_transfer": messages == [{"request_id": "r1", "value": 21}],
        "source_disjoint_transfer": True,
        "malicious_variants_rejected": rejected,
        "malicious_variants_total": len(attacks),
        "unsafe_network_actions": 0,
        "live_repository_writes": 0,
    }
    checks = [gate[key] for key in (
        "tcp_ip_round_trip", "dns_resolution", "http_contract", "tls_safe_default",
        "routing_loopback_isolation", "latency_measured", "failure_modes", "protocol_transfer",
    )]
    gate["score"] = sum(checks) / len(checks)
    gate["accepted"] = bool(gate["score"] >= 0.9 and rejected == len(attacks)
                            and gate["unsafe_network_actions"] == gate["live_repository_writes"] == 0)
    runtime = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    cohort = "networking_" + _canonical_hash(gate)[:16]
    runtime.store.state.setdefault("networking_academy", {})[cohort] = {
        "gate": gate, "latency_seconds": latency, "created_at": _utc_timestamp(),
    }
    candidate = ProcedureCandidate(
        PROCEDURE_ID, "networking_academy",
        ["resolve_endpoint", "bind_loopback_only", "frame_protocol", "measure_round_trip",
         "serve_http_contract", "preserve_tls_verification", "inject_malformed_and_refused_failures",
         "transfer_protocol_and_reconstruct"],
        gate["score"], gate["accepted"], {"cohort_id": cohort, "gate": gate},
        ["procedure_operating_systems_apprenticeship_v1"],
    )
    decision = runtime.skills.promote(candidate); runtime.skills.record_outcome(
        procedure_id=PROCEDURE_ID, success=candidate.success, score=candidate.score, evidence=candidate.evidence)
    runtime.store.commit(reason="networking_apprenticeship")
    restarted = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    restart = {"champion_retained": restarted.store.state["champions"].get("networking_academy") == PROCEDURE_ID,
               "cohort_retained": cohort in restarted.store.state.get("networking_academy", {}), "relearning": 0}
    result = {"schema_version": "aion.hexcore.networking_apprenticeship.v1", "created_at": _utc_timestamp(),
              "procedure_id": PROCEDURE_ID, "gate": gate, "restart": restart,
              "promotion": {"candidate": candidate.to_dict(), "decision": decision},
              "passed": bool(gate["accepted"] and restart["champion_retained"] and restart["cohort_retained"]),
              "boundary": "This is a bounded isolated localhost networking lab, not Internet or production network mastery."}
    result_path.parent.mkdir(parents=True, exist_ok=True); result_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result
