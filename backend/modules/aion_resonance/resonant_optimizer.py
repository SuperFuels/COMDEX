# backend/modules/aion_resonance/resonant_optimizer.py
#!/usr/bin/env python3
"""
🧠 Resonant Optimizer Loop (ROL)
- Collects resonance snapshots from registered engines (via mixin).
- Applies small runtime deltas (exploration, learning_rate, risk_bias, etc.).
- Persists longitudinal traces for dashboard.
- (Optional) Emits advisories for DNA_SWITCH (logged; no code changes).
"""

import threading, time, json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

TRACE_PATH = Path("data/analysis/resonant_optimizer.jsonl")
TRACE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Singleton holder
_OPTIMIZER: Optional["ResonantOptimizer"] = None

class ResonantOptimizer:
    def __init__(self, tick_seconds: float = 30.0, window: int = 6):
        """
        tick_seconds: how often to poll engines
        window: how many recent snapshots to keep per engine (rolling)
        """
        self.tick_seconds = tick_seconds
        self.window = window
        self._running = False
        self._lock = threading.Lock()

        self.rmc = ResonantMemoryCache()
        self.engines: Dict[str, Any] = {}
        self.history: Dict[str, List[Dict[str, Any]]] = {}  # per-engine rolling window

        # policy thresholds (tune as needed)
        self.thresholds = {
            "low_coherence": 0.55,
            "high_entropy": 0.60,
            "improving_sqi_delta": 0.02,
        }

    # ---------- Registration ----------
    def register(self, name: str, engine: Any):
        """
        Engines must implement:
          - get_resonance_snapshot() -> Dict[str, float]
          - apply_optimizer_delta(deltas: Dict[str, float]) -> None
        (Both already provided by ResonantReinforcementMixin defaults.)
        """
        with self._lock:
            self.engines[name] = engine
            self.history.setdefault(name, [])
        print(f"🧠 ROL: registered '{name}'")

    # ---------- Loop control ----------
    def start(self):
        if self._running: return
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        print("🧠 ROL started.")

    def stop(self):
        self._running = False
        print("🧠 ROL stopped.")

    # ---------- Core loop ----------
    def _loop(self):
        while self._running:
            try:
                self.tick()
            except Exception as e:
                print(f"[ROL] tick failed: {e}")
            time.sleep(self.tick_seconds)

    def tick(self):
        snapshots = {}
        with self._lock:
            for name, eng in self.engines.items():
                snap = self._safe_snapshot(eng)
                if snap:
                    self._push_history(name, snap)
                    snapshots[name] = snap

        corrections = self._assess_and_plan(snapshots)
        self._apply(corrections)
        self._persist(snapshots, corrections)

    # ---------- Helpers ----------
    def _safe_snapshot(self, eng) -> Optional[Dict[str, Any]]:
        try:
            snap = eng.get_resonance_snapshot()  # mixin default provides this
            # expected keys: coherence, entropy, sqi, extras...
            return {
                "coherence": float(snap.get("coherence", 0.5)),
                "entropy": float(snap.get("entropy", 0.5)),
                "sqi": float(snap.get("sqi", 0.5)),
                "extras": {k: v for k, v in snap.items() if k not in {"coherence","entropy","sqi"}},
                "ts": time.time(),
            }
        except Exception as e:
            print(f"[ROL] snapshot failed: {e}")
            return None

    def _push_history(self, name: str, snap: Dict[str, Any]):
        hist = self.history[name]
        hist.append(snap)
        if len(hist) > self.window:
            del hist[0]

    def _trend(self, series: List[float]) -> float:
        # simple last-minus-first (tiny, robust)
        if len(series) < 2: return 0.0
        return float(series[-1] - series[0])

    # ---------- Policy ----------
    def _assess_and_plan(self, snaps: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
        """
        Returns per-engine deltas to apply, e.g.:
          {"decision_engine": {"exploration": +0.03}, "strategy_planner": {"branch_temp": +0.05}}
        """
        plan: Dict[str, Dict[str, float]] = {}
        for name, snap in snaps.items():
            hist = self.history.get(name, [])
            coh_series = [h["coherence"] for h in hist]
            ent_series = [h["entropy"] for h in hist]
            sqi_series = [h["sqi"] for h in hist]

            coh_trend = self._trend(coh_series)
            ent_trend = self._trend(ent_series)
            sqi_trend = self._trend(sqi_series)

            low_coh = snap["coherence"] < self.thresholds["low_coherence"]
            high_ent = snap["entropy"] > self.thresholds["high_entropy"]
            improving = sqi_trend > self.thresholds["improving_sqi_delta"]

            deltas: Dict[str, float] = {}

            # Generic knobs (engines may or may not use each; mixin applies if present)
            if low_coh and not improving:
                # explore a bit more, reduce risk aversion
                deltas["exploration"] = +0.03
                deltas["risk_bias"] = -0.02

            if high_ent and not improving:
                # slow down branching temperature / search temp
                deltas["branch_temp"] = -0.03
                deltas["search_temp"] = -0.03

            if improving:
                # very small consolidation (less randomness)
                deltas["exploration"] = deltas.get("exploration", 0.0) - 0.01
                deltas["search_temp"] = deltas.get("search_temp", 0.0) - 0.01

            # Only add if we actually have something to do
            if deltas:
                plan[name] = deltas

            # Advisory (DNA switch hint) - log only
            if low_coh and high_ent and sqi_trend < 0:
                self._log_advisory(name,
                    "coherence<low & entropy>high & sqi falling",
                    hint="Consider refactor of scoring function or validation gating")

        return plan

    def _apply(self, plan: Dict[str, Dict[str, float]]):
        with self._lock:
            for name, deltas in plan.items():
                eng = self.engines.get(name)
                if not eng: continue
                try:
                    eng.apply_optimizer_delta(deltas)  # mixin default handles common knobs
                    print(f"🧠 ROL applied -> {name}: {deltas}")
                except Exception as e:
                    print(f"[ROL] apply failed for {name}: {e}")

    def _persist(self, snaps: Dict[str, Dict[str, Any]], plan: Dict[str, Dict[str, float]]):
        row = {"ts": time.time(), "snapshots": snaps, "plan": plan}
        with TRACE_PATH.open("a") as f:
            f.write(json.dumps(row) + "\n")
        # Also publish a compact state for the dashboard
        self.rmc.set("resonant_optimizer_last", row)

    def _log_advisory(self, name: str, condition: str, hint: str):
        advisories = self.rmc.get("resonant_optimizer_advisories") or []
        advisories.append({
            "engine": name, "condition": condition, "hint": hint, "ts": time.time()
        })
        self.rmc.set("resonant_optimizer_advisories", advisories)

# ---------- Singleton accessor ----------
def get_optimizer(tick_seconds: float = 30.0) -> ResonantOptimizer:
    global _OPTIMIZER
    if _OPTIMIZER is None:
        _OPTIMIZER = ResonantOptimizer(tick_seconds=tick_seconds)
    return _OPTIMIZER