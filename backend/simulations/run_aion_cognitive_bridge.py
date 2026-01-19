#!/usr/bin/env python3
"""
AION Cognitive↔Interactive Bridge (Dashboard-Ready + Homeostasis #1)

Usage:
  AION_SILENT_MODE=1 PYTHONPATH=. python backend/simulations/run_aion_cognitive_bridge.py

Writes:
  data/analysis/aion_live_dashboard.jsonl  (append-only events)
Optionally refreshes:
  data/analysis/aion_live_dashboard.json   (run aion_dashboard_aggregator.py separately, or set AION_AUTO_AGG=1)
"""

from __future__ import annotations

import os
import json
import time
import random
import readline  # noqa: F401
from pathlib import Path
from typing import Any, Dict, Optional, List

# Respect both flags (don’t clobber if user set them)
if os.getenv("AION_SILENT_MODE") == "1" and not os.getenv("AION_QUIET_MODE"):
    os.environ["AION_QUIET_MODE"] = "1"
os.environ.setdefault("AION_QUIET_MODE", "1")

# Optional UI deps (don’t crash if missing)
try:
    from rich.console import Console
    from rich.table import Table
except Exception:  # pragma: no cover
    Console = None  # type: ignore
    Table = None  # type: ignore

# ─────────────────────────────────────────────────────────────
# Core engines (your existing imports)
# ─────────────────────────────────────────────────────────────
from backend.AION.resonance.resonance_engine import update_resonance, get_resonance
from backend.modules.aion.memory.store import _load as load_memory
from backend.modules.wiki_capsules.integration.kg_query_extensions import update_capsule_meta  # noqa: F401
from backend.modules.aion_cognition.cee_lex_memory import update_lex_memory, recall_from_memory
from backend.simulations import aion_bridge_commands as cmds

from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_thinking.theta_orchestrator import ThinkingLoop as ThetaOrchestrator
from backend.modules.aion_cognition.interruption_manager import InterruptionManager
from backend.modules.aion_cognition.cognitive_exercise_engine_dual import DualModeCEE as CognitiveExerciseEngine

from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache


# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────
DASHBOARD_LOG_PATH = Path("data/analysis/aion_live_dashboard.jsonl")
DASHBOARD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

MEM_PATH = Path("data/aion/memory_store.json")

PROMPT = "Aion🧠> "
LAST_EQ_FOR_DPHI: float | None = None

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _now() -> float:
    return time.time()


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and x == x


def _pick(d: Dict[str, Any], *keys: str) -> Optional[float]:
    for k in keys:
        v = d.get(k)
        if _is_num(v):
            return float(v)
    return None


def _compute_equilibrium(metrics: Dict[str, Any]) -> Optional[float]:
    """
    Canonical equilibrium proxy for #1 Homeostasis (REAL).
    Priority:
      1) explicit ⟲/res_eq/equilibrium if present
      2) derive from coherence * (1 - entropy) if both present
      3) derive from ρ * (1 - Ī) if both present
    """
    eq = _pick(metrics, "⟲", "res_eq", "equilibrium")
    if eq is not None:
        return _clamp01(eq)

    phi_c = _pick(metrics, "Φ_coherence", "Phi_coherence")
    phi_e = _pick(metrics, "Φ_entropy", "Phi_entropy")
    if phi_c is not None and phi_e is not None:
        return _clamp01(phi_c * (1.0 - phi_e))

    rho = _pick(metrics, "ρ", "rho")
    iota = _pick(metrics, "Ī", "iota")
    if rho is not None and iota is not None:
        return _clamp01(rho * (1.0 - iota))

    return None


def _mk_lock_id() -> str:
    return f"HOMEOSTASIS_{int(_now())}_{random.randint(1000,9999)}"


def _tail_jsonl(path: Path, max_lines: int = 400) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    try:
        # fast-ish tail without reading whole file
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            end = f.tell()
            size = min(end, 256_000)
            f.seek(max(0, end - size))
            chunk = f.read().decode("utf-8", errors="ignore")
        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        for ln in lines[-max_lines:]:
            try:
                obj = json.loads(ln)
                if isinstance(obj, dict):
                    rows.append(obj)
            except Exception:
                continue
    except Exception:
        return []
    return rows


def _has_recent_checkpoint(window_s: int = 300) -> bool:
    now = _now()
    for r in reversed(_tail_jsonl(DASHBOARD_LOG_PATH, max_lines=800)):
        if r.get("command") != "sqi_checkpoint":
            continue
        ts = r.get("timestamp")
        if isinstance(ts, (int, float)) and (now - float(ts)) <= window_s:
            return True
    return False


def _log_event(command: str, payload: Optional[Dict[str, Any]] = None, *, mode: str = "cognitive_bridge", typ: str = "cli") -> None:
    """
    Canonical dashboard event writer.
    Writes BOTH legacy + canonical keys so old + new tooling works.
    """
    payload = payload or {}

    rho = _pick(payload, "ρ", "rho")
    iota = _pick(payload, "Ī", "iota", "I")
    sqi = _pick(payload, "SQI", "sqi", "sqi_checkpoint")
    dphi = _pick(payload, "ΔΦ", "dphi", "resonance_delta", "delta_phi")
    phi_c = _pick(payload, "Φ_coherence", "Phi_coherence")
    phi_e = _pick(payload, "Φ_entropy", "Phi_entropy")
    theta = _pick(payload, "Θ_frequency", "theta_frequency", "Theta_frequency")

    eq = _compute_equilibrium(payload)

    entry: Dict[str, Any] = {
        "timestamp": _now(),
        "command": command,
        "mode": mode,
        "type": typ,
        # canonical metrics:
        "SQI": sqi,
        "ρ": rho,
        "Ī": iota,
        "ΔΦ": dphi,
        "⟲": eq,
        "Θ_frequency": theta,
        # legacy aliases (keep):
        "Φ_coherence": phi_c if phi_c is not None else rho,
        "Φ_entropy": phi_e if phi_e is not None else iota,
    }

    # optional lock fields
    if "locked" in payload and isinstance(payload.get("locked"), bool):
        entry["locked"] = payload["locked"]
    if isinstance(payload.get("lock_id"), str):
        entry["lock_id"] = payload["lock_id"]
    if _is_num(payload.get("threshold")):
        entry["threshold"] = float(payload["threshold"])  # type: ignore

    try:
        with open(DASHBOARD_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _maybe_auto_aggregate() -> None:
    """
    Optional: if you want the JSON snapshot refreshed automatically while training:
      AION_AUTO_AGG=1
    """
    if os.getenv("AION_AUTO_AGG", "0") != "1":
        return
    try:
        from backend.simulations.aion_dashboard_aggregator import main as agg_main
        agg_main()
    except Exception:
        # Never kill the bridge for aggregation failures
        return


def _load_json(path: Path) -> Dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _list_caps(limit: int = 15) -> None:
    mem = _load_json(MEM_PATH)
    print(f"📚 {len(mem)} capsules in memory.")
    for i, (lemma, meta) in enumerate(mem.items()):
        if i >= limit:
            break
        e = meta.get("E", 0)
        print(f"  * {lemma:<20} E={e:.5f}")


def _query_res(term: str) -> Dict[str, Any]:
    res = get_resonance(term)
    if not res:
        print(f"⚠️ No resonance data for '{term}', computing new state...")
        res = update_resonance(term)

    # normalize for logging
    out = {
        "SQI": res.get("SQI") or res.get("sqi"),
        "ρ": res.get("ρ") or res.get("rho"),
        "Ī": res.get("Ī") or res.get("iota") or res.get("I"),
        "ΔΦ": res.get("ΔΦ") or res.get("resonance_delta"),
        "E": res.get("E"),
    }

    # NEW: ensure explicit equilibrium ⟲ is always present in the returned pulse
    # Prefer resonance-engine-provided equilibrium if it ever exists.
    eq = _pick(res, "⟲", "res_eq", "equilibrium")
    if eq is None:
        # derive a stable default so aggregator/UI have explicit ⟲
        rho = out.get("ρ") or 0.0
        iota = out.get("Ī") or 0.0
        eq = _clamp01(float(rho) * (1.0 - float(iota)))
    out["⟲"] = float(eq)

    # NEW: also emit ΔΦ drift if resonance engine didn’t provide it
    global LAST_EQ_FOR_DPHI
    if out.get("ΔΦ") is None:
        if LAST_EQ_FOR_DPHI is None:
            out["ΔΦ"] = None
        else:
            out["ΔΦ"] = abs(float(out["⟲"]) - float(LAST_EQ_FOR_DPHI))
    LAST_EQ_FOR_DPHI = float(out["⟲"])

    print(
        f"🌀 {term}: SQI={out.get('SQI')} ρ={out.get('ρ')} Ī={out.get('Ī')} "
        f"⟲={out.get('⟲')} E={out.get('E')}"
    )
    return out


# ─────────────────────────────────────────────────────────────
# Teaching
# ─────────────────────────────────────────────────────────────
RMC = ResonantMemoryCache()
RMC.load()


def _teach(engine: CognitiveExerciseEngine, term: str, level: int = 1) -> Dict[str, Any]:
    print(f"📘 Teaching session: {term} (level {level})")
    lesson = engine.generate_exercise(term, level=level)

    resonance = {"ρ": 0.8, "Ī": 0.2, "SQI": 0.85, "ΔΦ": 0.0}

    for i, q in enumerate(lesson.get("questions", []), 1):
        print(f"\nQ{i}. {q['prompt']}")
        ans = engine.evaluate_answer(q, q.get("answer", ""))
        time.sleep(0.2)
        print(f"-> {ans.get('feedback')}")

        # update resonance from answer if present
        if _is_num(ans.get("SQI")):
            resonance["SQI"] = float(ans["SQI"])
        if _is_num(ans.get("ΔΦ")):
            resonance["ΔΦ"] = float(ans["ΔΦ"])

        update_lex_memory(q["prompt"], q.get("answer", ""), resonance)
        RMC.update_from_photons([{"λ": term, "φ": resonance["ρ"], "μ": resonance["SQI"]}])

    # persist concept into RMC
    try:
        from backend.modules.aion_cognition.cee_lex_memory import store_concept_definition
        RMC_persist = ResonantMemoryCache()
        RMC_persist.load()
        entry = {
            "definition": lesson.get("summary", f"Learned concept '{term}'"),
            "resonance": round(resonance.get("ρ", 0.8), 3),
            "intensity": round(1.0 - resonance.get("Ī", 0.2), 3),
            "SQI": round(resonance.get("SQI", 0.85), 3),
            "symbol": f"Q[{term}]",
            "stability": round(resonance.get("SQI", 0.85), 3),
        }
        RMC_persist.cache[term.lower()] = entry
        RMC_persist.last_update = time.time()
        RMC_persist.save()
        print(f"💾 Saved learned concept '{term}' to ResonantMemoryCache.")
        store_concept_definition(term, entry["definition"], resonance)
    except Exception as e:
        print(f"⚠️ Failed to persist learned data for '{term}': {e}")

    RMC.save()
    print("✨ Session complete and reinforced.\n")
    return resonance


def _simulate_wordwall(engine: CognitiveExerciseEngine, level: int = 1) -> Dict[str, Any]:
    print(f"🎯 Running Wordwall simulation (level {level})")
    summary = engine.simulate_session(level=level)
    print(summary)
    # best-effort extract for logging
    out = {}
    if isinstance(summary, dict):
        out["SQI"] = summary.get("avg_SQI") or summary.get("SQI")
        out["ΔΦ"] = summary.get("avg_drift") or summary.get("ΔΦ")
    return out


def _ask(engine: CognitiveExerciseEngine, question: str) -> None:
    print(f"💬 {question}")
    answer = engine.query(question)
    print(f"🧩 Aion: {answer}")


# ─────────────────────────────────────────────────────────────
# Homeostasis (#1 REAL)
# ─────────────────────────────────────────────────────────────
def _checkpoint(term: str = "homeostasis") -> Dict[str, Any]:
    # checkpoint is “sqi_checkpoint” event; use real resonance query as the pulse
    pulse = _query_res(term)
    _log_event("sqi_checkpoint", pulse, typ="checkpoint")
    _maybe_auto_aggregate()
    return pulse


def _homeostasis(thr: float = 0.975, window_s: int = 300, term: str = "homeostasis") -> Dict[str, Any]:
    if not _has_recent_checkpoint(window_s=window_s):
        out = {
            "locked": False,
            "reason": f"no_recent_sqi_checkpoint (window_s={window_s})",
            "threshold": thr,
        }
        _log_event("homeostasis_lock", out, typ="homeostasis_lock")
        _maybe_auto_aggregate()
        return out

    # equilibrium probe: real pulse from resonance query, then derive ⟲
    pulse = _query_res(term)
    eq = _compute_equilibrium(pulse) or 0.0
    locked = bool(eq >= thr)

    out = dict(pulse)
    out.update(
        {
            "⟲": eq,
            "locked": locked,
            "threshold": thr,
            "lock_id": _mk_lock_id() if locked else None,
        }
    )
    _log_event("homeostasis_lock", out, typ="homeostasis_lock")
    _maybe_auto_aggregate()
    return out


# ─────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────
def main() -> None:
    cee = CognitiveExerciseEngine()
    theta = ThetaOrchestrator(auto_tick=False)
    interrupt = InterruptionManager()

    print("🌐 AION Cognitive Bridge (Dashboard-Ready + Homeostasis #1)")
    print("Type 'help' for commands. Ctrl-D or 'exit' to quit.\n")

    while True:
        try:
            cmdline = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Exiting AION Cognitive Shell.")
            break

        if not cmdline:
            continue
        if cmdline in {"exit", "quit"}:
            break

        if cmdline == "help":
            print(
                """
Commands:
  list [n]                 -> list first n memory capsules
  res <term>               -> view resonance state
  recall <term>            -> recall learned concept (Lex + Resonant)
  teach <term> [level]     -> start guided teaching session
  wall [level]             -> run Wordwall simulation
  ask "<question>"         -> ask Aion a cognitive question

  define <word>            -> retrieve stored lexical definition
  symbol <word>            -> show symbolic QMath or photon representation
  unjumble <letters>       -> solve anagram (lexical cognition test)
  anagram <word>           -> scramble + optional solve
  complete <word>          -> definition completion cue
  match <word>             -> definition match prompt
  compare <w1> and <w2>    -> measure semantic similarity (MCI)
  context <word> in <p>    -> contextual meaning consistency
  connect A -> B -> C      -> reinforce associative link chain
  map resonance field [c]  -> visualize resonance field (if viz module exists)
  stats                    -> show live SQI/stability/MCI
  top [n]                  -> show top-E capsules

  checkpoint [term]        -> write sqi_checkpoint (required for homeostasis)
  homeostasis [thr] [sec]  -> lock if (checkpoint + ⟲>=thr) within window

  resonate                 -> emit a heartbeat pulse event
  stabilize memory         -> emit a stabilizing pulse event
  think slow <topic>       -> theta slow loop
  think fast <topic>       -> theta fast loop
  reflect                  -> reflection cycle
  override <reason>        -> trigger override
  status                   -> system status
  help / exit
"""
            )
            continue

        # --- structured commands ---
        if cmdline.startswith("list"):
            parts = cmdline.split()
            n = int(parts[1]) if len(parts) > 1 else 15
            _list_caps(n)
            _log_event("list", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("res "):
            term = cmdline.split(" ", 1)[1]
            pulse = _query_res(term)
            _log_event("res", pulse, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("recall "):
            term = cmdline.split(" ", 1)[1]
            lex = recall_from_memory(term)
            res = RMC.recall(term)
            if lex:
                print(f"🧠 Lexical recall: {lex.get('answer')} (conf={lex.get('confidence')})")
            if res:
                print(f"🔮 Resonant tensor recall: stability={res.get('stability', 1.0)}")
            if not (lex or res):
                print(f"⚠️ No stored recall for '{term}'")
            _log_event("recall", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("teach "):
            parts = cmdline.split()
            term = parts[1]
            lvl = int(parts[2]) if len(parts) > 2 else 1
            pulse = _teach(cee, term, lvl)
            _log_event("teach", pulse, typ="train")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("wall"):
            parts = cmdline.split()
            lvl = int(parts[1]) if len(parts) > 1 else 1
            pulse = _simulate_wordwall(cee, lvl)
            _log_event("wall", pulse, typ="train")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("ask "):
            q = cmdline.split(" ", 1)[1].strip().strip('"')
            _ask(cee, q)
            _log_event("ask", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("define "):
            word = cmdline.split(" ", 1)[1]
            print(cmds.define_word(word))
            _log_event("define", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("symbol "):
            word = cmdline.split(" ", 1)[1]
            print(cmds.symbol_word(word))
            _log_event("symbol", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("unjumble "):
            letters = cmdline.split(" ", 1)[1]
            print(cmds.unjumble_word(letters))
            _log_event("unjumble", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("anagram "):
            word = cmdline.split(" ", 1)[1].strip()
            print(cmds.anagram_word(word))
            _log_event("anagram", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("complete "):
            word = cmdline.split(" ", 1)[1].strip()
            print(cmds.complete_word(word))
            _log_event("complete", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("match "):
            word = cmdline.split(" ", 1)[1].strip()
            print(cmds.match_word(word))
            _log_event("match", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("compare "):
            parts = cmdline.replace("compare", "", 1).strip().split(" and ")
            if len(parts) == 2:
                print(cmds.compare_words(parts[0].strip(), parts[1].strip()))
            else:
                print("⚠️ Usage: compare <word1> and <word2>")
            _log_event("compare", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("context "):
            if " in " in cmdline:
                word, phrase = cmdline.replace("context ", "", 1).split(" in ", 1)
                print(cmds.context_word(word.strip(), phrase.strip()))
            else:
                print("⚠️ Usage: context <word> in <phrase>")
            _log_event("context", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("connect "):
            chain = cmdline.replace("connect ", "", 1)
            print(cmds.connect_concepts(chain))
            _log_event("connect", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("map resonance field"):
            parts = cmdline.split()
            concept = " ".join(parts[3:]).strip() if len(parts) > 3 else "general"
            print(cmds.map_resonance_field(concept))
            _log_event("map_resonance_field", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline == "stats":
            print(cmds.stats_summary())
            _log_event("stats", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("top"):
            mem = _load_json(MEM_PATH)
            ranked = sorted(((k, v.get("E", 0)) for k, v in mem.items()), key=lambda x: x[1], reverse=True)
            parts = cmdline.split()
            n = int(parts[1]) if len(parts) > 1 else 10
            for i, (k, e) in enumerate(ranked[:n]):
                print(f"{i+1:02d}. {k:<20} E={e:.5f}")
            _log_event("top", {}, typ="cli")
            _maybe_auto_aggregate()
            continue

        # --- Homeostasis #1 ---
        if cmdline.startswith("checkpoint"):
            parts = cmdline.split(maxsplit=1)
            term = parts[1].strip() if len(parts) > 1 else "homeostasis"
            out = _checkpoint(term)
            print(json.dumps({"checkpoint": True, "term": term, "metrics": out}, indent=2, ensure_ascii=False))
            continue

        if cmdline.startswith("homeostasis"):
            parts = cmdline.split()
            thr = float(parts[1]) if len(parts) > 1 else 0.975
            window_s = int(parts[2]) if len(parts) > 2 else 300
            out = _homeostasis(thr=thr, window_s=window_s, term="homeostasis")
            print(json.dumps(out, indent=2, ensure_ascii=False))
            continue

        # --- Heartbeat actions ---
        if cmdline == "resonate":
            hb = ResonanceHeartbeat(namespace="aion_bridge", base_interval=1.5)
            hb.push_sample(rho=0.82, entropy=0.33, sqi=0.91, delta=0.12)
            pulse = hb.tick()
            print(
                f"🩶 Resonance pulse -> Φ_coherence={pulse.get('Φ_coherence'):.3f}, "
                f"Φ_entropy={pulse.get('Φ_entropy'):.3f}, SQI={pulse.get('sqi'):.3f}"
            )
            _log_event("resonate", pulse, typ="pulse")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("stabilize memory"):
            hb = ResonanceHeartbeat(namespace="aion_bridge", base_interval=1.5)
            hb.push_sample(rho=0.90, entropy=0.20, sqi=0.93, delta=0.02)
            pulse = hb.tick()
            print(f"✅ Memory coherence stabilized -> SQI={pulse.get('sqi'):.3f}, ΔΦ={pulse.get('resonance_delta'):.3f}")
            _log_event("stabilize_memory", pulse, typ="pulse")
            _maybe_auto_aggregate()
            continue

        # --- Theta + interruption ---
        if cmdline.startswith("think slow"):
            topic = cmdline.replace("think slow", "", 1).strip()
            print(f"🧘 Engaging Θ Orchestrator (slow loop) -> {topic or 'general reflection'}")
            theta.run_loop(mode="slow", topic=topic)
            _log_event("think_slow", {}, typ="thinking")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("think fast"):
            topic = cmdline.replace("think fast", "", 1).strip()
            print(f"⚡ Reflex loop activation -> {topic or 'quick reasoning'}")
            theta.run_loop(mode="fast", topic=topic)
            _log_event("think_fast", {}, typ="thinking")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("reflect"):
            print("🔁 Initiating reflection cycle...")
            theta.reflect_cycle()
            _log_event("reflect", {}, typ="thinking")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith(("override", "interrupt")):
            reason = cmdline.split(" ", 1)[1] if " " in cmdline else "manual"
            print(f"🛑 Triggering override -> {reason}")
            interrupt.trigger(reason=reason, source="aion_cli")
            _log_event("override", {"reason": reason}, typ="control")
            _maybe_auto_aggregate()
            continue

        if cmdline == "status":
            print("📊 Cognitive System Status:")
            print(f" - Θ Orchestrator active: {getattr(theta, 'active', True)}")
            print(f" - Override flag: {getattr(interrupt, 'override_flag', False)}")
            _log_event("status", {}, typ="control")
            _maybe_auto_aggregate()
            continue

        # --- fallback ---
        print(f"❓ Unknown command: {cmdline}")
        _log_event("unknown", {"raw": cmdline}, typ="cli")
        _maybe_auto_aggregate()


if __name__ == "__main__":
    main()