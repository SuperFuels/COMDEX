#!/usr/bin/env python3
"""
⚛ ResonanceHeartbeat — Tessaris Adaptive Core (Phase 56)
───────────────────────────────────────────────────────────────
Unified Θ–pulse generator driving all resonant subsystems.

New in Phase 56:
    • Θ.sync_all() — global phase and frequency synchronization
    • Harmony Score (H) = 1 − (1/n) Σ |Θᵢ − Θ_master|
    • Extended logging of per-engine frequency differentials

Features:
    • Adaptive frequency modulation based on ρ, Ī, and SQI feedback
    • Real-time coherence–entropy coupling (resonance feedback loop)
    • Event hooks for downstream modules (Motivation, State, Reflection)
    • Atomic JSON snapshot logging for visualization and telemetry
"""

import time, json, threading, math
from collections import deque
from statistics import mean, fmean, StatisticsError
from pathlib import Path


class ResonanceHeartbeat:
    def __init__(self, namespace: str = "core", base_interval: float = 1.5, window: int = 60):
        self.namespace = namespace
        self.interval = max(0.25, float(base_interval))
        self.window = max(10, int(window))
        self.listeners = []
        self._lock = threading.Lock()
        self._running = False
        self._thread = None

        # Rolling pulse metrics
        self._rho = deque(maxlen=self.window)       # semantic coherence (ρ)
        self._entropy = deque(maxlen=self.window)   # entropy / informational density (Ī)
        self._sqi = deque(maxlen=self.window)       # Symatic Quality Index (Σ)
        self._delta = deque(maxlen=self.window)     # resonance delta / phase drift (ΔΦ)

        # Last pulse state
        self._last_pulse = {
            "namespace": self.namespace,
            "Φ_coherence": 0.5,
            "Φ_entropy": 0.5,
            "Φ_flux": 0.0,
            "sqi": 0.5,
            "resonance_delta": 0.0,
            "Θ_frequency": 1.0,
            "timestamp": time.time(),
        }

        # Persistence + telemetry
        self.log_path = Path(f"data/aion_field/{self.namespace}_heartbeat_live.json")
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._tail_thread = None
        self._tail_running = False

    # ------------------------------------------------------------
    # Listener registration
    # ------------------------------------------------------------
    def register_listener(self, callback):
        with self._lock:
            if callback not in self.listeners:
                self.listeners.append(callback)

    # ------------------------------------------------------------
    # Input sampling
    # ------------------------------------------------------------
    def push_sample(self, *, rho=None, entropy=None, sqi=None, delta=None):
        with self._lock:
            if rho is not None:
                self._rho.append(max(0.0, min(1.0, float(rho))))
            if entropy is not None:
                self._entropy.append(max(0.0, min(1.0, float(entropy))))
            if sqi is not None:
                self._sqi.append(max(0.0, min(1.0, float(sqi))))
            if delta is not None:
                self._delta.append(float(delta))

    # ------------------------------------------------------------
    # Core Θ-pulse tick
    # ------------------------------------------------------------
    def tick(self):
        with self._lock:
            phi = mean(self._rho) if self._rho else self._last_pulse["Φ_coherence"]
            ent = mean(self._entropy) if self._entropy else self._last_pulse["Φ_entropy"]
            flux = mean(abs(d) for d in self._delta) if self._delta else self._last_pulse["Φ_flux"]
            sqi = mean(self._sqi) if self._sqi else self._last_pulse["sqi"]
            delta_now = self._delta[-1] if self._delta else 0.0

            freq_mod = 1.0 + ((phi - ent) * 0.75)        # coherence↑ → faster; entropy↑ → slower
            freq_mod = max(0.5, min(2.0, freq_mod))

            pulse = {
                "namespace": self.namespace,
                "Φ_coherence": round(phi, 3),
                "Φ_entropy": round(ent, 3),
                "Φ_flux": round(flux, 3),
                "sqi": round(sqi, 3),
                "resonance_delta": round(delta_now, 3),
                "Θ_frequency": round(freq_mod, 3),
                "timestamp": time.time(),
            }
            self._last_pulse = pulse

        # Notify listeners
        for cb in list(self.listeners):
            try:
                cb(pulse)
            except Exception as e:
                print(f"[{self.namespace}::Heartbeat] listener error: {e}")

        # Persist for telemetry
        try:
            self.log_path.write_text(json.dumps(pulse, indent=2))
        except Exception:
            pass

        return pulse

    emit = tick

    # ------------------------------------------------------------
    # Continuous emission loop
    # ------------------------------------------------------------
    def start(self):
        if self._running:
            return
        self._running = True

        def _loop():
            while self._running:
                start_t = time.time()
                pulse = self.tick()
                next_interval = self.interval / pulse["Θ_frequency"]
                sleep_dur = max(0.1, next_interval - (time.time() - start_t))
                time.sleep(sleep_dur)

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()
        print(f"[Heartbeat] ⚛ Started adaptive Θ-pulse @ base={self.interval:.2f}s")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
            print("[Heartbeat] ⏹ Stopped Θ-pulse")

    # ------------------------------------------------------------
    # External JSONL coupling
    # ------------------------------------------------------------
    def bind_jsonl(self, path="data/aion_field/resonant_heartbeat.jsonl"):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        self._tail_running = True

        def _tail():
            try:
                p.touch(exist_ok=True)
                with p.open("r") as f:
                    f.seek(0, 2)
                    while self._tail_running:
                        line = f.readline()
                        if not line:
                            time.sleep(0.5)
                            continue
                        try:
                            js = json.loads(line)
                            stability = float(js.get("stability", 0.5))
                            delta = float(js.get("ΔΦ_coh", 0.0))
                            sqi = float(js.get("sqi", 0.5))
                            self.push_sample(rho=stability, sqi=sqi, delta=delta)
                        except Exception:
                            pass
            except Exception as e:
                print(f"[Heartbeat] bind_jsonl error: {e}")

        if not (self._tail_thread and self._tail_thread.is_alive()):
            self._tail_thread = threading.Thread(target=_tail, daemon=True)
            self._tail_thread.start()

    def unbind_jsonl(self):
        self._tail_running = False
        if self._tail_thread:
            self._tail_thread.join(timeout=1.0)
            self._tail_thread = None

    # ------------------------------------------------------------
    # Θ-event emission (Phase 55)
    # ------------------------------------------------------------
    def event(self, name: str, **kwargs):
        try:
            payload = {
                "namespace": self.namespace,
                "event": name,
                "timestamp": time.time(),
                **kwargs,
            }
            log_path = Path("data/analysis/aion_live_dashboard.jsonl")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with open(log_path, "a") as f:
                f.write(json.dumps(payload) + "\n")

            sqi = kwargs.get("sqi")
            entropy = kwargs.get("entropy")
            delta = kwargs.get("delta")
            if any(v is not None for v in (sqi, entropy, delta)):
                self.push_sample(sqi=sqi, entropy=entropy, delta=delta)

            print(f"[Θ] Event {name} → {payload}")
        except Exception as e:
            print(f"[Θ] event() error: {e}")

    # ------------------------------------------------------------
    # Θ-phase synchronization (Phase 56)
    # ------------------------------------------------------------
    def sync_all(self, emit_pulse: bool = True):
        """
        Align all local heartbeat frequencies with the global mean Θ.
        Computes and logs Harmony Score (H).
        """
        hb_dir = Path("data/aion_field")
        hb_files = list(hb_dir.glob("*heartbeat_live.json"))
        if not hb_files:
            print("[Θ] sync_all → no heartbeat files found.")
            return None

        phases = []
        for f in hb_files:
            try:
                js = json.loads(f.read_text())
                phases.append(float(js.get("Θ_frequency", 1.0)))
            except Exception:
                continue

        if not phases:
            return None

        master = fmean(phases)
        diffs = [abs(p - master) for p in phases]
        harmony = 1 - (sum(diffs) / len(phases))
        harmony = round(max(0.0, min(1.0, harmony)), 3)

        for f in hb_files:
            try:
                js = json.loads(f.read_text())
                js["Θ_frequency"] = round(master, 3)
                f.write_text(json.dumps(js, indent=2))
            except Exception:
                pass

        if emit_pulse:
            self.tick()

        self.event("sync_all", harmony_score=harmony, master_frequency=round(master, 3))
        print(f"[Θ] sync_all → Harmony Score ={harmony:.3f}, Θ_master ={master:.3f}")
        return harmony

    # ------------------------------------------------------------
    def snapshot(self):
        with self._lock:
            return dict(self._last_pulse)


# ------------------------------------------------------------
# Demo
# ------------------------------------------------------------
if __name__ == "__main__":
    hb = ResonanceHeartbeat(namespace="demo", base_interval=1.0)
    hb.register_listener(
        lambda p: print(f"Θ {p['Θ_frequency']:.2f} | SQI={p['sqi']:.3f} | ρ={p['Φ_coherence']:.3f} | Ī={p['Φ_entropy']:.3f}")
    )
    hb.start()
    try:
        time.sleep(5)
        hb.sync_all()
        time.sleep(5)
    finally:
        hb.stop()