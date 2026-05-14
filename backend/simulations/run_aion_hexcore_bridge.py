#!/usr/bin/env python3
"""
AION ↔ HexCore Bridge
─────────────────────
CLI bridge that talks to the HexCore HTTP server (/health, /quantum).

Fixes:
- No hardcoded 8500-only assumptions (supports env override + autodetect).
- Returns full JSON payload (result + ρ + Ī + type), not just `result`.
- Safe local fallback evaluator if remote HexCore is unavailable.
- ✅ LOCKED: ∇ is RESERVED for math:∇ (gradient) and MUST NOT be treated as collapse.
- ✅ LOCKED: μ is the measurement/collapse operator.

Usage:
  PYTHONPATH=. python backend/simulations/run_aion_hexcore_bridge.py

Env:
  HEXCORE_BASE_URL   e.g. http://127.0.0.1:8500
  HEXCORE_PORT       e.g. 8500 (used if HEXCORE_BASE_URL not set)
  HEXCORE_TIMEOUT    seconds (default 5)
"""

from __future__ import annotations

import os
import re
import math
import json
import time
import statistics
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

try:
    import requests  # type: ignore
except Exception:
    requests = None  # type: ignore


# ─────────────────────────────────────────────
# Local (fallback) evaluator (mirrors run_hexcore_server.py behavior)
# ─────────────────────────────────────────────
def _safe_float(x: Any) -> Optional[float]:
    try:
        return float(x)
    except Exception:
        return None


def _compute_superposition(a: float, b: float) -> float:
    return (a + b) / 2.0


def _compute_entanglement(a: float, b: float) -> float:
    return a * b


def _compute_resonance(a: float, b: float) -> float:
    if (a + b) == 0:
        return 0.0
    return 2 * a * b / (a + b)


def _compute_measurement(a: float, b: float) -> float:
    """
    Local approximation of measurement/collapse for numeric operands.

    NOTE:
    This is a fallback heuristic only (kept intentionally simple and stable).
    Remote HexCore is the source of truth when available.
    """
    return (a + b) / 2.0


def _coherence_metric(values: List[float]) -> float:
    if len(values) < 2:
        return 1.0
    var = statistics.pvariance(values)
    return max(0.0, 1 - var / (1 + var))


def _entropy_metric(values: List[float]) -> float:
    vals = [abs(v) for v in values if v != 0]
    if not vals:
        return 0.0
    avg = sum(vals) / len(vals)
    dispersion = sum(abs(v - avg) for v in vals) / len(vals)
    return round(min(1.0, math.log(1 + dispersion)), 3)


def evaluate_symatic_expr_local(expr: str) -> Dict[str, Any]:
    """
    Local fallback for numeric + symbolic Symatics expressions.
    Mirrors the basic logic in backend/modules/hexcore/run_hexcore_server.py

    LOCKED SEMANTICS:
    - μ = measurement/collapse
    - ∇ is RESERVED for math gradient and is NOT evaluated as collapse here.
    """
    expr = (expr or "").strip()

    # 1) Try numeric math
    if re.fullmatch(r"[0-9\+\-\*\/\(\)\.\sxX]+", expr or ""):
        e2 = expr.replace("x", "*").replace("X", "*")
        try:
            result = eval(e2, {"__builtins__": None, "math": math})
            rho = _coherence_metric([float(result)])
            iota = _entropy_metric([float(result)])
            return {
                "result": result,
                "ρ": round(rho, 3),
                "Ī": round(iota, 3),
                "type": "numeric",
                "mode": "local",
            }
        except Exception as e:
            return {"error": f"Math eval error: {e}", "mode": "local"}

    # 2) Symbolic operator patterns
    # ✅ include μ; ❌ keep ∇ reserved (skip/deny)
    m = re.search(r"([⊕↔⟲μ]|->)\s*\(([^)]+)\)", expr)
    if m:
        op = m.group(1)
        args = [a.strip() for a in m.group(2).split(",") if a.strip()]

        if len(args) < 2 and op != "->":
            return {"error": f"Operator {op} requires two arguments.", "mode": "local"}

        a = _safe_float(args[0]) if args else None
        b = _safe_float(args[1]) if len(args) > 1 else None

        # numeric operands
        if a is not None and (b is not None or op == "->"):
            val: Optional[float]
            if op == "⊕":
                val = _compute_superposition(a, float(b))
            elif op == "↔":
                val = _compute_entanglement(a, float(b))
            elif op == "⟲":
                val = _compute_resonance(a, float(b))
            elif op == "μ":
                val = _compute_measurement(a, float(b))
            elif op == "->":
                val = math.exp(a)
            else:
                val = None

            vals = [v for v in [a, b, val] if isinstance(v, (int, float)) and v is not None]
            rho = _coherence_metric([float(v) for v in vals]) if vals else 0.5
            iota = _entropy_metric([float(v) for v in vals]) if vals else 0.5

            return {
                "result": val,
                "ρ": round(rho, 3),
                "Ī": round(iota, 3),
                "type": "numeric_symatic",
                "mode": "local",
            }

        # symbolic operands
        meaning = {
            "⊕": "superposition",
            "↔": "entanglement",
            "⟲": "resonance",
            "μ": "measure",
            "->": "trigger",
        }.get(op, "unknown")

        return {
            "result": f"Ψ = {meaning}({', '.join(args)})",
            "ρ": 1.0,
            "Ī": 0.5,
            "type": "symbolic",
            "mode": "local",
        }

    # 2b) HARD-BLOCK explicit ∇ usage (reserved)
    if re.search(r"(∇)\s*\(", expr) or re.fullmatch(r"∇", expr):
        return {
            "status": "skipped",
            "result": None,
            "ρ": 0.5,
            "Ī": 0.5,
            "type": "reserved",
            "mode": "local",
            "note": "∇ is reserved for math:∇ (gradient). Use μ for measurement/collapse.",
        }

    # 3) Default symbolic interpretation
    if "photon" in expr and "wave" in expr:
        return {"result": "Ψ = coherent(superposition(photon, wave))", "ρ": 0.92, "Ī": 0.12, "type": "symbolic", "mode": "local"}
    if "resonance" in expr:
        return {"result": "ρ⊕Ī -> balanced field state", "ρ": 0.85, "Ī": 0.25, "type": "symbolic", "mode": "local"}
    if "entanglement" in expr:
        return {"result": "↔ -> dual-phase coupling", "ρ": 0.78, "Ī": 0.30, "type": "symbolic", "mode": "local"}

    return {"result": f"[QQC symbolic] evaluated {expr}", "ρ": 0.5, "Ī": 0.5, "type": "symbolic", "mode": "local"}


# ─────────────────────────────────────────────
# Remote HexCore detection + client
# ─────────────────────────────────────────────
def _env_int(name: str, default: int) -> int:
    try:
        v = os.getenv(name)
        return int(v) if v else default
    except Exception:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        v = os.getenv(name)
        return float(v) if v else default
    except Exception:
        return default


def candidate_base_urls() -> List[str]:
    """
    Detection order:
      1) HEXCORE_BASE_URL (if set)
      2) HEXCORE_PORT (if set) -> http://127.0.0.1:<port>
      3) common ports: 8500 (hexcore), 8000 (dev uvicorn), 8080 (codespaces/cloud)
    """
    urls: List[str] = []
    base = (os.getenv("HEXCORE_BASE_URL") or "").strip()
    if base:
        urls.append(base.rstrip("/"))

    port = _env_int("HEXCORE_PORT", 0)
    if port:
        urls.append(f"http://127.0.0.1:{port}")

    for p in (8500, 8000, 8080):
        u = f"http://127.0.0.1:{p}"
        if u not in urls:
            urls.append(u)

    return urls


def probe_hexcore(base_url: str, timeout: float) -> Tuple[bool, Dict[str, Any]]:
    if requests is None:
        return False, {"error": "requests_not_installed"}
    try:
        r = requests.get(f"{base_url}/health", timeout=timeout)
        if r.status_code == 200:
            try:
                return True, r.json()
            except Exception:
                return True, {"raw": r.text}
        return False, {"status_code": r.status_code, "text": (r.text or "")[:300]}
    except Exception as e:
        return False, {"error": str(e)}


def detect_hexcore_base_url(timeout: float) -> Optional[str]:
    for base in candidate_base_urls():
        ok, _ = probe_hexcore(base, timeout=timeout)
        if ok:
            return base
    return None


class HexCoreClient:
    """
    Robust HexCore client:
      - prefers remote (/quantum)
      - falls back to local evaluator if remote fails
    """

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None, allow_local_fallback: bool = True):
        self.timeout = timeout if timeout is not None else _env_float("HEXCORE_TIMEOUT", 5.0)
        self.allow_local_fallback = allow_local_fallback
        self.base_url = (base_url or detect_hexcore_base_url(timeout=min(2.0, self.timeout)))

    def health(self) -> Dict[str, Any]:
        if not self.base_url:
            return {"ok": False, "mode": "local", "reason": "no_remote_detected"}
        ok, data = probe_hexcore(self.base_url, timeout=min(2.0, self.timeout))
        return {"ok": ok, "mode": "remote" if ok else "local", "base_url": self.base_url, "health": data}

    def compute(self, expr: str) -> Dict[str, Any]:
        expr = (expr or "").strip()
        if not expr:
            return {"error": "empty_expr"}

        # Remote first
        if self.base_url and requests is not None:
            try:
                r = requests.post(f"{self.base_url}/quantum", json={"expr": expr}, timeout=self.timeout)
                r.raise_for_status()
                data = r.json()
                if isinstance(data, dict):
                    data.setdefault("mode", "remote")
                    data.setdefault("base_url", self.base_url)
                    return data
                return {"result": data, "mode": "remote", "base_url": self.base_url}
            except Exception as e:
                if not self.allow_local_fallback:
                    return {"error": f"remote_hexcore_failed: {e}", "mode": "remote", "base_url": self.base_url}

        # Local fallback
        return evaluate_symatic_expr_local(expr)


# ─────────────────────────────────────────────
# Minimal JSONL event logger (matches the “bridge vibe” of other scripts)
# ─────────────────────────────────────────────
DASHBOARD_LOG_PATH = Path("data/analysis/aion_live_dashboard.jsonl")
DASHBOARD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


def log_bridge_event(command: str, payload: Dict[str, Any]) -> None:
    """
    Append command + quick metrics snapshot to the dashboard feed.
    Keeps the file compatible with your other dashboard tooling.
    """
    entry: Dict[str, Any] = {
        "timestamp": time.time(),
        "command": command,
    }
    if isinstance(payload, dict):
        # Try multiple known keys, since remote/local payloads vary slightly.
        entry["ρ"] = payload.get("ρ") or payload.get("Phi_coherence") or payload.get("Φ_coherence")
        entry["Ī"] = payload.get("Ī") or payload.get("Phi_entropy") or payload.get("Φ_entropy")
        entry["type"] = payload.get("type")
        entry["mode"] = payload.get("mode")
        entry["base_url"] = payload.get("base_url")

    try:
        with open(DASHBOARD_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        # Never kill the bridge on logging failures.
        pass


def _pretty(x: Any) -> str:
    try:
        return json.dumps(x, indent=2, ensure_ascii=False)
    except Exception:
        return str(x)


# ─────────────────────────────────────────────
# CLI (kept intentionally similar to the original “bridge” pattern)
# ─────────────────────────────────────────────
def main() -> None:
    client = HexCoreClient()

    h = client.health()
    if h.get("ok"):
        print(f"🌌 HexCore detected @ {h.get('base_url')}")
    else:
        print("🧩 HexCore not detected (remote). Using local fallback evaluator.")
        if h.get("reason"):
            print(f"   reason: {h['reason']}")

    print("Commands: health | url | seturl <http://...> | compute <expr> | quit")
    print("LOCKED: ∇ is reserved for math:∇ (gradient). Use μ for measurement/collapse.")
    prompt = "HexCore🌌> "

    while True:
        try:
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Exiting HexCore bridge.")
            return

        if not line:
            continue
        if line in {"q", "quit", "exit"}:
            return

        if line == "health":
            out = client.health()
            print(_pretty(out))
            log_bridge_event("health", out)
            continue

        if line == "url":
            out = {"base_url": client.base_url, "timeout": client.timeout, "allow_local_fallback": client.allow_local_fallback}
            print(_pretty(out))
            log_bridge_event("url", out)
            continue

        if line.startswith("seturl "):
            client.base_url = line.split(" ", 1)[1].strip().rstrip("/") or None
            out = {"base_url": client.base_url}
            print(_pretty(out))
            log_bridge_event("seturl", out)
            continue

        if line.startswith("compute "):
            expr = line.split(" ", 1)[1]
            out = client.compute(expr)
            print(_pretty(out))
            log_bridge_event(f"compute {expr}", out)
            continue

        # convenience: treat anything else as an expr
        out = client.compute(line)
        print(_pretty(out))
        log_bridge_event(line, out)


if __name__ == "__main__":
    main()