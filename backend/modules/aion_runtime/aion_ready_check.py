#!/usr/bin/env python3
from __future__ import annotations

import json
import socket
import time
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional


@dataclass
class ServiceCheck:
    name: str
    host: str
    port: int
    required: bool = True
    ok: bool = False
    latency_ms: Optional[float] = None
    error: Optional[str] = None


DEFAULT_SERVICES = [
    ServiceCheck("API", "127.0.0.1", 8000, required=True),
    ServiceCheck("SREL", "127.0.0.1", 8001, required=False),
    ServiceCheck("RAL", "127.0.0.1", 8002, required=False),
    ServiceCheck("AQCI", "127.0.0.1", 8004, required=False),
    ServiceCheck("TCFK", "127.0.0.1", 8005, required=True),
    # RQFS is listed as ws://localhost:8006/ws/rqfs_feedback in launcher output
    ServiceCheck("RQFS", "127.0.0.1", 8006, required=False),
]


def check_port(host: str, port: int, timeout: float = 0.8) -> tuple[bool, Optional[float], Optional[str]]:
    start = time.perf_counter()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        latency_ms = (time.perf_counter() - start) * 1000.0
        return True, latency_ms, None
    except Exception as e:
        return False, None, str(e)
    finally:
        try:
            s.close()
        except Exception:
            pass


def run_ready_check(services: List[ServiceCheck] | None = None) -> Dict[str, Any]:
    services = services or [ServiceCheck(**asdict(s)) for s in DEFAULT_SERVICES]
    for svc in services:
        ok, latency_ms, err = check_port(svc.host, svc.port)
        svc.ok = ok
        svc.latency_ms = round(latency_ms, 2) if latency_ms is not None else None
        svc.error = err

    required_ok = all(s.ok for s in services if s.required)
    all_ok = all(s.ok for s in services)

    summary = {
        "status": "ready" if required_ok else "not_ready",
        "required_ok": required_ok,
        "all_ok": all_ok,
        "timestamp": time.time(),
        "services": [asdict(s) for s in services],
    }
    return summary


if __name__ == "__main__":
    result = run_ready_check()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["required_ok"] else 1)