# backend/modules/aion_cognition/demo6_mirror_reflection.py
from __future__ import annotations
import argparse, json, os, time
from pathlib import Path
from typing import Dict, Any, Optional

from .telemetry_io import write_qdata

ENV_DATA_ROOT = "TESSARIS_DATA_ROOT"

def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "backend").exists():
            return parent
    return Path.cwd()

def pick_data_root() -> Path:
    v = os.getenv(ENV_DATA_ROOT, "").strip()
    if v:
        return Path(v).expanduser()
    return _repo_root() / "data"

def _read_json(p: Path, default=None):
    try:
        if not p.exists():
            return default
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default

def _tail_jsonl(p: Path, max_bytes: int = 65536) -> Optional[dict]:
    try:
        if not p.exists():
            return None
        with p.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - max_bytes), 0)
            chunk = f.read().decode("utf-8", errors="ignore")
        lines = [l.strip() for l in chunk.splitlines() if l.strip()]
        for line in reversed(lines):
            try:
                return json.loads(line)
            except Exception:
                continue
        return None
    except Exception:
        return None

def read_phi(data_root: Path) -> Dict[str, Any]:
    # try both (data_root/phi...) and (data_root/data/phi...) for legacy nesting
    p1 = data_root / "phi_reinforce_state.json"
    p2 = data_root / "data" / "phi_reinforce_state.json"
    st = _read_json(p1, default=None) or _read_json(p2, default={}) or {}
    return st

def read_heartbeat(data_root: Path, namespace: str = "demo") -> Dict[str, Any]:
    live = data_root / "aion_field" / f"{namespace}_heartbeat_live.json"
    jsonl = data_root / "aion_field" / "resonant_heartbeat.jsonl"
    hb = _read_json(live, default=None)
    if isinstance(hb, dict):
        return hb
    j = _tail_jsonl(jsonl)
    return j if isinstance(j, dict) else {}

def read_adr_derived(data_root: Path) -> Dict[str, Any]:
    # demo_bridge writes these:
    p = data_root / "feedback" / "resonance_stream.jsonl"
    evt = _tail_jsonl(p) or {}
    # derive “zone” roughly
    rsi = evt.get("RSI", evt.get("stability"))
    try:
        rsi = float(rsi) if rsi is not None else None
    except Exception:
        rsi = None
    zone = "UNKNOWN"
    if rsi is not None:
        zone = "GREEN" if rsi >= 0.95 else "YELLOW" if rsi >= 0.60 else "RED"
    return {"zone": zone, "rsi": rsi}

def alignment_score(phi: Dict[str, Any], hb: Dict[str, Any], adr: Dict[str, Any], prev_coh: float | None) -> float:
    beliefs = phi.get("beliefs") or {}
    try:
        stability = float(beliefs.get("stability", 0.5))
    except Exception:
        stability = 0.5

    try:
        coh = float(phi.get("Φ_coherence", 0.5))
    except Exception:
        coh = 0.5

    drift = abs(coh - prev_coh) if prev_coh is not None else 0.0

    hb_ts = hb.get("timestamp")
    hb_fresh = 0.25
    try:
        if isinstance(hb_ts, (int, float)):
            age_s = max(0.0, time.time() - float(hb_ts))
            hb_fresh = max(0.0, min(1.0, 1.0 - age_s / 5.0))
    except Exception:
        pass

    zone = str((adr.get("zone") or "UNKNOWN")).upper()
    zone_penalty = 0.25 if zone == "RED" else 0.10 if zone == "YELLOW" else 0.0

    A = (0.45 * stability + 0.35 * coh + 0.20 * hb_fresh) - (0.40 * min(1.0, drift)) - zone_penalty
    return max(0.0, min(1.0, A))

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=12)
    ap.add_argument("--namespace", type=str, default="demo")
    ap.add_argument("--telemetry", type=str, default="data/telemetry/demo6_mirror_reflection.qdata.json")
    args = ap.parse_args()

    data_root = pick_data_root()
    session_id = f"DEMO6-{int(time.time())}"
    frames = []
    prev_coh = None

    for t in range(int(args.steps)):
        phi = read_phi(data_root)
        hb = read_heartbeat(data_root, namespace=args.namespace)
        adr = read_adr_derived(data_root)

        coh = None
        try:
            coh = float(phi.get("Φ_coherence"))
        except Exception:
            coh = None

        A = alignment_score(phi, hb, adr, prev_coh)
        prev_coh = coh if coh is not None else prev_coh

        narration = f"[{session_id}] MIRROR t={t:02d} | Φ_coh={phi.get('Φ_coherence', None)} | stability={(phi.get('beliefs') or {}).get('stability', None)} | ADR={adr.get('zone')} | A={A:.3f}"
        print(narration)

        frames.append({"t": t, "phi": phi, "heartbeat": hb, "adr": adr, "A": round(float(A), 4), "narration": narration})
        time.sleep(0.05)

    write_qdata(args.telemetry, {
        "demo": "demo6_mirror_reflection",
        "session_id": session_id,
        "steps": int(args.steps),
        "frames": frames,
        "A_final": frames[-1]["A"] if frames else None,
        "data_root": str(data_root),
    })

if __name__ == "__main__":
    main()