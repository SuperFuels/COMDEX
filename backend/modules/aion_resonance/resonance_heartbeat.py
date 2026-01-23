#!/usr/bin/env python3
"""
⚛ ResonanceHeartbeat - Tessaris Adaptive Core (Phase 57a)
───────────────────────────────────────────────────────────────
Unified Θ-pulse generator driving resonant subsystems.

Key behaviors:
- Writes last pulse to: <DATA_ROOT>/aion_field/<namespace>_heartbeat_live.json
- Optional drift monitor writes: <DATA_ROOT>/aion_field/resonant_drift_log.jsonl
- Optional events write: <DATA_ROOT>/analysis/aion_live_dashboard.jsonl
- AION_SILENT_MODE=1 silences console spam, but heartbeat still runs.

Data-root discovery aligns with MRTC:
- $TESSARIS_DATA_ROOT if valid
- else .runtime/*/data if present
- else ./data
"""

from __future__ import annotations
import datetime
import argparse
import json
import logging
import os
import threading
import time
from collections import deque
from pathlib import Path
from statistics import fmean, mean
from typing import Any, Dict, List, Optional, Tuple

# ─────────────────────────────────────────────────────────────
# Logging / quiet mode
# ─────────────────────────────────────────────────────────────
log = logging.getLogger(__name__)
QUIET = os.getenv("AION_SILENT_MODE", "0") == "1"

if not log.handlers:
    # Don't stomp global logging; keep it local and tame.
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    log.addHandler(_h)
log.setLevel(logging.WARNING if QUIET else logging.INFO)

# ─────────────────────────────────────────────────────────────
# Data-root discovery (MRTC-aligned)
# ─────────────────────────────────────────────────────────────
ENV_DATA_ROOT = "TESSARIS_DATA_ROOT"
KNOWN_SENTINELS = [
    "control/aqci_log.jsonl",
    "control/rqfs_feedback.jsonl",
    "learning/fusion_state.jsonl",
    "aion_field/resonant_heartbeat.jsonl",
    "analysis/resonant_optimizer.jsonl",
    "analysis/state_resonance_log.jsonl",
]

def _pick_data_root() -> Path:
    # 1) explicit override
    env = os.environ.get(ENV_DATA_ROOT)
    if env:
        p = Path(env).expanduser()
        if (p / "control").exists() or any((p / s).exists() for s in KNOWN_SENTINELS):
            return p

    # 2) prefer runtime-moved data if present
    candidates: List[Path] = []
    rt = Path(".runtime")
    if rt.exists():
        candidates.extend(list(rt.glob("*/data")))

    # 3) include local ./data
    candidates.append(Path("data"))

    def score(d: Path) -> Tuple[int, float]:
        hits = 0
        newest = 0.0
        for s in KNOWN_SENTINELS:
            f = d / s
            if f.exists():
                hits += 1
                try:
                    newest = max(newest, f.stat().st_mtime)
                except Exception:
                    pass
        return (hits, newest)

    best = None
    best_score = (-1, -1.0)
    for d in candidates:
        sc = score(d)
        if sc > best_score:
            best = d
            best_score = sc

    return best if best else Path("data")

DATA_ROOT = _pick_data_root()

def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)

def _read_json(path: Path) -> Optional[dict]:
    try:
        if path.exists():
            j = json.loads(path.read_text(encoding="utf-8"))
            return j if isinstance(j, dict) else None
    except Exception:
        return None
    return None

def _phi_state_candidates(data_root: Path) -> list[Path]:
    return [
        data_root / "phi_reinforce_state.json",
        data_root / "data" / "phi_reinforce_state.json",
        Path("backend/data/phi_reinforce_state.json"),
        Path("data/phi_reinforce_state.json"),
        Path("data/data/phi_reinforce_state.json"),
    ]

# ─────────────────────────────────────────────────────────────
# Heartbeat
# ─────────────────────────────────────────────────────────────
class ResonanceHeartbeat:
    """
    Rolling Φ metrics -> emits Θ pulses; persists last pulse to JSON file.
    """

    def __init__(
        self,
        namespace: str = "core",
        base_interval: float = 1.5,
        window: int = 60,
        auto_tick: bool = True,
        enable_events: bool = True,
    ):
        self.namespace = namespace
        self.interval = max(0.10, float(base_interval))
        self.window = max(10, int(window))
        self.auto_tick = bool(auto_tick)
        self.enable_events = bool(enable_events)

        # Threading + state
        self.listeners = []
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._drift_thread: Optional[threading.Thread] = None
        self._drift_running = False

        # Rolling metrics
        self._rho = deque(maxlen=self.window)
        self._entropy = deque(maxlen=self.window)
        self._sqi = deque(maxlen=self.window)
        self._delta = deque(maxlen=self.window)

        # Paths (DATA_ROOT aligned)
        self.log_path = DATA_ROOT / "aion_field" / f"{self.namespace}_heartbeat_live.json"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self.event_log_path = DATA_ROOT / "analysis" / "aion_live_dashboard.jsonl"
        self.drift_log_path = DATA_ROOT / "aion_field" / "resonant_drift_log.jsonl"

        # Restore last pulse if present (persistence across restarts)
        self._last_pulse = self._load_last_pulse() or {
            "namespace": self.namespace,
            "Φ_coherence": 0.5,
            "Φ_entropy": 0.5,
            "Φ_flux": 0.0,
            "sqi": 0.5,
            "resonance_delta": 0.0,
            "Θ_frequency": 1.0,
            "timestamp": time.time(),
            "data_root": str(DATA_ROOT),
        }

        # Initialize according to mode
        if self.auto_tick:
            self.start()
            if not QUIET:
                log.info(f"[Θ] Heartbeat ACTIVE -> {self.namespace} (DATA_ROOT={DATA_ROOT})")
        else:
            if not QUIET:
                log.info(f"[Θ] Heartbeat PASSIVE -> {self.namespace} (DATA_ROOT={DATA_ROOT})")

    # ------------------------------------------------------------
    def _load_last_pulse(self) -> Optional[Dict[str, Any]]:
        try:
            if self.log_path.exists():
                js = json.loads(self.log_path.read_text(encoding="utf-8"))
                if isinstance(js, dict):
                    # ensure namespace matches
                    js["namespace"] = self.namespace
                    js.setdefault("data_root", str(DATA_ROOT))
                    return js
        except Exception:
            pass
        return None

    # ------------------------------------------------------------
    def register_listener(self, callback) -> None:
        with self._lock:
            if callback not in self.listeners:
                self.listeners.append(callback)

    # ------------------------------------------------------------
    def push_sample(self, *, rho=None, entropy=None, sqi=None, delta=None, source="unknown") -> None:
        with self._lock:
            if rho is not None:
                self._rho.append(max(0.0, min(1.0, float(rho))))
            if entropy is not None:
                self._entropy.append(max(0.0, min(1.0, float(entropy))))
            if sqi is not None:
                self._sqi.append(max(0.0, min(1.0, float(sqi))))
            if delta is not None:
                self._delta.append(float(delta))

        if (not self.auto_tick) and (not QUIET):
            log.debug(f"[Θ] sample({self.namespace}) SQI={sqi} ΔΦ={delta} src={source}")

    # ------------------------------------------------------------
    def tick(self) -> Dict[str, Any]:
        with self._lock:
            # 1) Prefer authoritative φ from disk (metabolism state), else fall back to buffers/last_pulse
            st = None
            candidates = [
                DATA_ROOT / "phi_reinforce_state.json",
                DATA_ROOT / "data" / "phi_reinforce_state.json",
                Path("backend/data/phi_reinforce_state.json"),
                Path("data/phi_reinforce_state.json"),
                Path("data/data/phi_reinforce_state.json"),
            ]
            for p in candidates:
                try:
                    if p.exists():
                        j = json.loads(p.read_text(encoding="utf-8"))
                        if isinstance(j, dict) and any(k in j for k in ("Φ_coherence", "Φ_entropy", "Φ_flux")):
                            st = j
                            break
                except Exception:
                    continue

            if st:
                phi = float(st.get("Φ_coherence", self._last_pulse.get("Φ_coherence", 0.5)))
                ent = float(st.get("Φ_entropy",   self._last_pulse.get("Φ_entropy", 0.5)))
                flux = float(st.get("Φ_flux",     self._last_pulse.get("Φ_flux", 0.0)))
            else:
                phi  = mean(self._rho)     if self._rho     else float(self._last_pulse.get("Φ_coherence", 0.5))
                ent  = mean(self._entropy) if self._entropy else float(self._last_pulse.get("Φ_entropy", 0.5))
                flux = mean(abs(d) for d in self._delta) if self._delta else float(self._last_pulse.get("Φ_flux", 0.0))

            sqi = mean(self._sqi) if self._sqi else float(self._last_pulse.get("sqi", 0.5))
            delta_now = self._delta[-1] if self._delta else 0.0

            # Θ frequency modulation (bounded)
            freq_mod = 1.0 + ((phi - ent) * 0.75)
            freq_mod = max(0.5, min(2.0, float(freq_mod)))

            # timestamps (both machine + human)
            now_epoch = float(time.time())
            now_iso = datetime.datetime.now(datetime.UTC).isoformat().replace("+00:00", "Z")

            pulse = {
                "namespace": self.namespace,

                # computed values
                "Φ_coherence": round(float(phi), 3),
                "Φ_entropy": round(float(ent), 3),
                "Φ_flux": round(float(flux), 3),
                "sqi": round(float(sqi), 3),

                # derived
                "resonance_delta": round(float(delta_now), 3),
                "Θ_frequency": round(float(freq_mod), 3),

                # freshness markers
                "timestamp": now_epoch,
                "last_update": now_iso,

                # source/debug
                "phi_source_file": str(p) if st else None,
                "data_root": str(DATA_ROOT),
            }
            self._last_pulse = pulse

        # listeners
        for cb in list(self.listeners):
            try:
                cb(pulse)
            except Exception as e:
                if not QUIET:
                    log.warning(f"[{self.namespace}::Heartbeat] listener error: {e}")

        # persist (atomic)
        try:
            _atomic_write_text(self.log_path, json.dumps(pulse, indent=2, ensure_ascii=False))
        except Exception as e:
            if not QUIET:
                log.debug(f"[Θ] persist failed: {e}")

        return pulse

    emit = tick

    # ------------------------------------------------------------
    def start(self) -> None:
        if self._running:
            return
        self._running = True

        def _loop() -> None:
            # schedule with monotonic clock
            next_t = time.monotonic()
            while self._running:
                pulse = self.tick()
                interval = self.interval / max(0.25, float(pulse.get("Θ_frequency", 1.0)))
                next_t += max(0.05, interval)
                # sleep until next tick
                dt = next_t - time.monotonic()
                if dt > 0:
                    time.sleep(dt)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

        if not QUIET:
            print(f"[Heartbeat] ⚛ running ({self.namespace}) base={self.interval:.2f}s data_root={DATA_ROOT}")

    # ------------------------------------------------------------
    def stop(self) -> None:
        self._running = False
        self._drift_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self._drift_thread:
            self._drift_thread.join(timeout=1.0)
        if not QUIET:
            log.info(f"[Heartbeat] stopped ({self.namespace})")

    # ------------------------------------------------------------
    def event(self, name: str, **kwargs) -> None:
        if not self.enable_events:
            return
        payload = {
            "namespace": self.namespace,
            "event": name,
            "timestamp": time.time(),
            **kwargs,
        }
        try:
            self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.event_log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        except Exception as e:
            if not QUIET:
                log.warning(f"[Θ] event() error: {e}")

    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._last_pulse)

    # ------------------------------------------------------------
    def sync_all(self, emit_pulse: bool = True) -> Optional[float]:
        hb_dir = DATA_ROOT / "aion_field"
        hb_files = list(hb_dir.glob("*_heartbeat_live.json"))
        if not hb_files:
            if not QUIET:
                print("[Θ] sync_all -> no heartbeat files found.")
            return None

        phases = []
        for f in hb_files:
            try:
                js = json.loads(f.read_text(encoding="utf-8"))
                phases.append(float(js.get("Θ_frequency", 1.0)))
            except Exception:
                continue

        if not phases:
            return None

        master = fmean(phases)
        harmony = 1 - (sum(abs(p - master) for p in phases) / len(phases))
        harmony = round(max(0.0, min(1.0, harmony)), 3)

        # write back master Θ (best-effort)
        for f in hb_files:
            try:
                js = json.loads(f.read_text(encoding="utf-8"))
                js["Θ_frequency"] = round(master, 3)
                js["timestamp"] = time.time()
                js["data_root"] = str(DATA_ROOT)
                _atomic_write_text(f, json.dumps(js, indent=2, ensure_ascii=False))
            except Exception:
                pass

        if emit_pulse:
            self.tick()

        self.event("sync_all", harmony_score=harmony, master_frequency=round(master, 3))
        if not QUIET:
            print(f"[Θ] sync_all -> Harmony={harmony:.3f}, Θ_master={master:.3f}")
        return harmony

    # ------------------------------------------------------------
    def monitor_drift(self, interval: float = 5.0, threshold: float = 0.05, correction_rate: float = 0.2) -> None:
        if self._drift_running:
            return
        self._drift_running = True
        self.drift_log_path.parent.mkdir(parents=True, exist_ok=True)

        def _drift_loop() -> None:
            hb_dir = DATA_ROOT / "aion_field"
            while self._drift_running:
                try:
                    files = list(hb_dir.glob("*_heartbeat_live.json"))
                    phases: List[Tuple[Path, float]] = []
                    for f in files:
                        try:
                            js = json.loads(f.read_text(encoding="utf-8"))
                            phases.append((f, float(js.get("Θ_frequency", 1.0))))
                        except Exception:
                            continue

                    if not phases:
                        time.sleep(interval)
                        continue

                    master = fmean(p[1] for p in phases)

                    for f, theta in phases:
                        drift = theta - master
                        if abs(drift) > threshold:
                            corrected = theta - (correction_rate * drift)
                            try:
                                js = json.loads(f.read_text(encoding="utf-8"))
                                js["Θ_frequency"] = round(corrected, 3)
                                js["timestamp"] = time.time()
                                js["data_root"] = str(DATA_ROOT)
                                _atomic_write_text(f, json.dumps(js, indent=2, ensure_ascii=False))
                            except Exception:
                                continue

                            payload = {
                                "namespace": f.stem,
                                "event": "drift_corrected",
                                "ΔΦ": round(drift, 4),
                                "corrected_to": round(corrected, 3),
                                "timestamp": time.time(),
                            }
                            with self.drift_log_path.open("a", encoding="utf-8") as df:
                                df.write(json.dumps(payload, ensure_ascii=False) + "\n")
                            self.event("drift_corrected", **payload)

                    time.sleep(interval)
                except Exception as e:
                    if not QUIET:
                        print(f"[Θ] drift monitor error: {e}")
                    time.sleep(interval)

        self._drift_thread = threading.Thread(target=_drift_loop, daemon=True)
        self._drift_thread.start()

        if not QUIET:
            print(f"[Θ] drift monitor ON (interval={interval}s threshold={threshold})")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Run Tessaris ResonanceHeartbeat")
    ap.add_argument("--namespace", default="demo", help="heartbeat namespace (file prefix)")
    ap.add_argument("--base-interval", type=float, default=1.0, help="base tick interval seconds")
    ap.add_argument("--window", type=int, default=60, help="rolling window size")
    ap.add_argument("--no-auto-tick", action="store_true", help="do not start background ticking")
    ap.add_argument("--once", action="store_true", help="emit one pulse and exit")
    ap.add_argument("--duration", type=float, default=0.0, help="run for N seconds then exit (0=forever)")
    ap.add_argument("--enable-drift-monitor", action="store_true", help="enable drift monitor thread")
    ap.add_argument("--drift-interval", type=float, default=5.0)
    ap.add_argument("--drift-threshold", type=float, default=0.05)
    ap.add_argument("--drift-correction-rate", type=float, default=0.2)
    ap.add_argument("--sync-all-every", type=float, default=0.0, help="periodically sync_all (0=off)")

    args = ap.parse_args()

    hb = ResonanceHeartbeat(
        namespace=args.namespace,
        base_interval=args.base_interval,
        window=args.window,
        auto_tick=(not args.no_auto_tick),
        enable_events=True,
    )

    if args.enable_drift_monitor:
        hb.monitor_drift(
            interval=args.drift_interval,
            threshold=args.drift_threshold,
            correction_rate=args.drift_correction_rate,
        )

    if args.once:
        hb.tick()
        return 0

    # Optional periodic sync_all
    last_sync = time.monotonic()
    start = time.monotonic()

    try:
        while True:
            time.sleep(0.25)

            if args.sync_all_every and (time.monotonic() - last_sync) >= args.sync_all_every:
                hb.sync_all(emit_pulse=True)
                last_sync = time.monotonic()

            if args.duration and (time.monotonic() - start) >= args.duration:
                break
    except KeyboardInterrupt:
        pass
    finally:
        hb.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())