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
import asyncio
import readline  # noqa: F401
from pathlib import Path
from typing import Any, Dict, Optional, List

# Respect both flags (don’t clobber if user set them)
if os.getenv("AION_SILENT_MODE") == "1" and not os.getenv("AION_QUIET_MODE"):
    os.environ["AION_QUIET_MODE"] = "1"
os.environ.setdefault("AION_QUIET_MODE", "1")

# Stable session id (also used by actions.py)
SESSION_ID = os.getenv("AION_SESSION_ID") or f"S{int(time.time())}_{random.randint(1000,9999)}"
os.environ["AION_SESSION_ID"] = SESSION_ID  # ensure actions.py sees it

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
from backend.modules.aion.memory.store import _load as load_memory  # noqa: F401
from backend.modules.wiki_capsules.integration.kg_query_extensions import update_capsule_meta  # noqa: F401
from backend.modules.aion_cognition.cee_lex_memory import recall_from_memory
from backend.simulations import aion_bridge_commands as cmds

from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_thinking.theta_orchestrator import ThinkingLoop as ThetaOrchestrator
from backend.modules.aion_cognition.interruption_manager import InterruptionManager
from backend.modules.aion_cognition.cognitive_exercise_engine_dual import DualModeCEE as CognitiveExerciseEngine
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# SINGLE SOURCE OF TRUTH: dashboard actions
from backend.modules.aion_dashboard.actions import (
    ask as actions_ask,
    checkpoint as actions_checkpoint,
    homeostasis_lock as actions_homeostasis_lock,
    teach as actions_teach,
    query_resonance as actions_query_resonance,
    log_event as actions_log_event,
)

# ─────────────────────────────────────────────────────────────
# Paths
# ─────────────────────────────────────────────────────────────
DASHBOARD_LOG_PATH = Path(os.getenv("AION_DASHBOARD_JSONL", "data/analysis/aion_live_dashboard.jsonl"))
DASHBOARD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

MEM_PATH = Path("data/aion/memory_store.json")

PROMPT = "Aion🧠> "

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────
def _now() -> float:
    return time.time()


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and x == x


def _log_event(
    command: str,
    payload: Optional[Dict[str, Any]] = None,
    *,
    mode: str = "cognitive_bridge",
    typ: str = "cli",
    **extra: Any,
) -> None:
    """
    Thin wrapper: everything logs via actions.py so WS/UI/CLI stay consistent.
    Accepts extra fields like text=..., term=..., etc. (unknown keys are harmless).
    """
    p: Dict[str, Any] = dict(payload or {})
    for k, v in extra.items():
        if v is None:
            continue
        p[k] = v
    p.setdefault("session_id", SESSION_ID)
    try:
        actions_log_event(command, p, mode=mode, typ=typ)
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


# ─────────────────────────────────────────────────────────────
# Teaching helpers (Wordwall stays local)
# ─────────────────────────────────────────────────────────────
RMC = ResonantMemoryCache()
try:
    RMC.load()
except Exception:
    pass


def _simulate_wordwall(engine: CognitiveExerciseEngine, level: int = 1) -> Dict[str, Any]:
    print(f"🎯 Running Wordwall simulation (level {level})")
    summary = engine.simulate_session(level=level)
    print(summary)
    out: Dict[str, Any] = {}
    if isinstance(summary, dict):
        out["SQI"] = summary.get("avg_SQI") or summary.get("SQI")
        out["ΔΦ"] = summary.get("avg_drift") or summary.get("ΔΦ")
    return out


# ─────────────────────────────────────────────────────────────
# Optional: background “breathe” tick (demo mode)
# ─────────────────────────────────────────────────────────────
def _truthy(key: str, default: bool = False) -> bool:
    v = os.getenv(key, "1" if default else "0").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


async def _maybe_start_phi_breathe() -> None:
    """
    If enabled, periodically calls update_beliefs({}) without crashing the shell.
    Set: AION_DEMO_PHI_BREATHE=1 (and optionally AION_DEMO_PHI_BREATHE_S=0.75)
    """
    if not _truthy("AION_DEMO_PHI_BREATHE", False):
        return
    try:
        from backend.modules.aion_resonance.phi_reinforce import update_beliefs
    except Exception:
        return

    async def _phi_breathe_loop() -> None:
        while True:
            try:
                update_beliefs({})
                _log_event("phi_breathe", {}, typ="pulse", text="phi breathe tick")
                _maybe_auto_aggregate()
            except Exception:
                pass
            await asyncio.sleep(float(os.getenv("AION_DEMO_PHI_BREATHE_S", "0.75")))

    asyncio.create_task(_phi_breathe_loop())


# ─────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────
def main() -> None:
    cee = CognitiveExerciseEngine()
    theta = ThetaOrchestrator(auto_tick=False)
    interrupt = InterruptionManager()

    print("🌐 AION Cognitive Bridge (Dashboard-Ready + Homeostasis #1)")
    print(f"Session: {SESSION_ID}")
    print("Type 'help' for commands. Ctrl-D or 'exit' to quit.\n")

    # If you want breathe ticks, we need an event loop; run best-effort.
    try:
        loop = asyncio.get_event_loop()
        if not loop.is_running():
            loop.create_task(_maybe_start_phi_breathe())
    except Exception:
        pass

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
  teach <term> [level]     -> start guided teaching session (actions.py)
  wall [level]             -> run Wordwall simulation
  ask "<question>"         -> ask Aion a cognitive question (actions.py)

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

  checkpoint [term]        -> write sqi_checkpoint (actions.py)
  homeostasis [thr] [sec]  -> lock if (checkpoint + ⟲>=thr) within window (actions.py)

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
            _log_event("help", {}, typ="cli", text="help")
            _maybe_auto_aggregate()
            continue

        # --- structured commands ---
        if cmdline.startswith("list"):
            parts = cmdline.split()
            n = int(parts[1]) if len(parts) > 1 else 15
            _list_caps(n)
            _log_event("list", {"limit": n}, typ="cli", text=f"list {n}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("res "):
            term = cmdline.split(" ", 1)[1].strip()
            pulse = actions_query_resonance(term)
            print(
                f"🌀 {term}: SQI={pulse.get('SQI')} ρ={pulse.get('ρ')} Ī={pulse.get('Ī')} "
                f"⟲={pulse.get('⟲')} ΔΦ={pulse.get('ΔΦ')} E={pulse.get('E')}"
            )
            _log_event("res", {"term": term, **pulse}, typ="cli", text=f"res {term}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("recall "):
            term = cmdline.split(" ", 1)[1].strip()
            lex = recall_from_memory(term)
            res = None
            try:
                res = RMC.recall(term)
            except Exception:
                res = None

            if lex:
                print(f"🧠 Lexical recall: {lex.get('answer')} (conf={lex.get('confidence')})")
            if res:
                print(f"🔮 Resonant tensor recall: stability={res.get('stability', 1.0)}")
            if not (lex or res):
                print(f"⚠️ No stored recall for '{term}'")

            _log_event("recall", {"term": term}, typ="cli", text=f"recall {term}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("teach "):
            parts = cmdline.split()
            term = parts[1].strip()
            lvl = int(parts[2]) if len(parts) > 2 else 1
            out = actions_teach(term, lvl, typ="train", mode="cognitive_bridge")
            if isinstance(out, dict) and out.get("summary"):
                print(out["summary"])
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("wall"):
            parts = cmdline.split()
            lvl = int(parts[1]) if len(parts) > 1 else 1
            pulse = _simulate_wordwall(cee, lvl)
            _log_event("wall", {"level": lvl, **pulse}, typ="train", text=f"wall lvl={lvl}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("ask "):
            q = cmdline.split(" ", 1)[1].strip().strip('"')
            out = actions_ask(q, typ="cli", mode="cognitive_bridge")
            if isinstance(out, dict):
                print(f"🧩 Aion: {out.get('answer')}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("define "):
            word = cmdline.split(" ", 1)[1].strip()
            out = cmds.define_word(word)
            print(out)
            _log_event("define", {"word": word, "result": str(out)}, typ="cli", text=f"define {word}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("symbol "):
            word = cmdline.split(" ", 1)[1].strip()
            out = cmds.symbol_word(word)
            print(out)
            _log_event("symbol", {"word": word, "result": str(out)}, typ="cli", text=f"symbol {word}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("unjumble "):
            letters = cmdline.split(" ", 1)[1].strip()
            out = cmds.unjumble_word(letters)
            print(out)
            _log_event("unjumble", {"letters": letters, "result": str(out)}, typ="cli", text=f"unjumble {letters}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("anagram "):
            word = cmdline.split(" ", 1)[1].strip()
            out = cmds.anagram_word(word)
            print(out)
            _log_event("anagram", {"word": word, "result": str(out)}, typ="cli", text=f"anagram {word}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("complete "):
            word = cmdline.split(" ", 1)[1].strip()
            out = cmds.complete_word(word)
            print(out)
            _log_event("complete", {"word": word, "result": str(out)}, typ="cli", text=f"complete {word}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("match "):
            word = cmdline.split(" ", 1)[1].strip()
            out = cmds.match_word(word)
            print(out)
            _log_event("match", {"word": word, "result": str(out)}, typ="cli", text=f"match {word}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("compare "):
            parts = cmdline.replace("compare", "", 1).strip().split(" and ")
            if len(parts) == 2:
                w1 = parts[0].strip()
                w2 = parts[1].strip()
                out = cmds.compare_words(w1, w2)
                print(out)
                _log_event("compare", {"w1": w1, "w2": w2, "result": str(out)}, typ="cli", text=f"compare {w1} and {w2}")
            else:
                print("⚠️ Usage: compare <word1> and <word2>")
                _log_event("compare", {"bad_usage": True}, typ="cli", text="compare (bad usage)")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("context "):
            if " in " in cmdline:
                word, phrase = cmdline.replace("context ", "", 1).split(" in ", 1)
                word = word.strip()
                phrase = phrase.strip()
                out = cmds.context_word(word, phrase)
                print(out)
                _log_event("context", {"word": word, "phrase": phrase, "result": str(out)}, typ="cli", text=f"context {word} in ...")
            else:
                print("⚠️ Usage: context <word> in <phrase>")
                _log_event("context", {"bad_usage": True}, typ="cli", text="context (bad usage)")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("connect "):
            chain = cmdline.replace("connect ", "", 1).strip()
            out = cmds.connect_concepts(chain)
            print(out)
            _log_event("connect", {"chain": chain, "result": str(out)}, typ="cli", text=f"connect {chain}")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("map resonance field"):
            parts = cmdline.split()
            concept = " ".join(parts[3:]).strip() if len(parts) > 3 else "general"
            out = cmds.map_resonance_field(concept)
            print(out)
            _log_event("map_resonance_field", {"concept": concept, "result": str(out)}, typ="cli", text=f"map resonance field {concept}")
            _maybe_auto_aggregate()
            continue

        if cmdline == "stats":
            out = cmds.stats_summary()
            print(out)
            _log_event("stats", {"result": str(out)}, typ="cli", text="stats")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("top"):
            mem = _load_json(MEM_PATH)
            ranked = sorted(((k, v.get("E", 0)) for k, v in mem.items()), key=lambda x: x[1], reverse=True)
            parts = cmdline.split()
            n = int(parts[1]) if len(parts) > 1 else 10
            for i, (k, e) in enumerate(ranked[:n]):
                print(f"{i+1:02d}. {k:<20} E={e:.5f}")
            _log_event("top", {"limit": n}, typ="cli", text=f"top {n}")
            _maybe_auto_aggregate()
            continue

        # --- Homeostasis #1 (ACTIONS) ---
        if cmdline.startswith("checkpoint"):
            parts = cmdline.split(maxsplit=1)
            term = parts[1].strip() if len(parts) > 1 else "homeostasis"
            out = actions_checkpoint(term, typ="checkpoint", mode="cognitive_bridge")
            print(json.dumps({"checkpoint": True, "term": out["term"], "metrics": out["metrics"]}, indent=2, ensure_ascii=False))
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("homeostasis"):
            parts = cmdline.split()
            thr = float(parts[1]) if len(parts) > 1 else 0.975
            window_s = int(parts[2]) if len(parts) > 2 else 300
            out = actions_homeostasis_lock(
                threshold=thr,
                window_s=window_s,
                term="homeostasis",
                typ="homeostasis_lock",
                mode="cognitive_bridge",
            )
            print(
                json.dumps(
                    {
                        "locked": out.get("locked"),
                        "threshold": out.get("threshold"),
                        "lock_id": out.get("lock_id"),
                        "metrics": out.get("metrics"),
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
            _maybe_auto_aggregate()
            continue

        # --- Heartbeat actions ---
        if cmdline == "resonate":
            hb = ResonanceHeartbeat(namespace="aion_bridge", base_interval=1.5)
            hb.push_sample(rho=0.82, entropy=0.33, sqi=0.91, delta=0.12)
            pulse = hb.tick()
            try:
                print(
                    f"🩶 Resonance pulse -> Φ_coherence={pulse.get('Φ_coherence'):.3f}, "
                    f"Φ_entropy={pulse.get('Φ_entropy'):.3f}, SQI={pulse.get('sqi'):.3f}"
                )
            except Exception:
                print(f"🩶 Resonance pulse -> {pulse}")
            _log_event("resonate", pulse, typ="pulse", text="resonate")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("stabilize memory"):
            hb = ResonanceHeartbeat(namespace="aion_bridge", base_interval=1.5)
            hb.push_sample(rho=0.90, entropy=0.20, sqi=0.93, delta=0.02)
            pulse = hb.tick()
            try:
                print(f"✅ Memory coherence stabilized -> SQI={pulse.get('sqi'):.3f}, ΔΦ={pulse.get('resonance_delta'):.3f}")
            except Exception:
                print(f"✅ Memory coherence stabilized -> {pulse}")
            _log_event("stabilize_memory", pulse, typ="pulse", text="stabilize memory")
            _maybe_auto_aggregate()
            continue

        # --- Theta + interruption ---
        if cmdline.startswith("think slow"):
            topic = cmdline.replace("think slow", "", 1).strip()
            print(f"🧘 Engaging Θ Orchestrator (slow loop) -> {topic or 'general reflection'}")
            theta.run_loop(mode="slow", topic=topic)
            _log_event("think_slow", {"topic": topic}, typ="thinking", text=f"think slow {topic}".strip())
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("think fast"):
            topic = cmdline.replace("think fast", "", 1).strip()
            print(f"⚡ Reflex loop activation -> {topic or 'quick reasoning'}")
            theta.run_loop(mode="fast", topic=topic)
            _log_event("think_fast", {"topic": topic}, typ="thinking", text=f"think fast {topic}".strip())
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith("reflect"):
            print("🔁 Initiating reflection cycle...")
            theta.reflect_cycle()
            _log_event("reflect", {}, typ="thinking", text="reflect")
            _maybe_auto_aggregate()
            continue

        if cmdline.startswith(("override", "interrupt")):
            reason = cmdline.split(" ", 1)[1] if " " in cmdline else "manual"
            print(f"🛑 Triggering override -> {reason}")
            interrupt.trigger(reason=reason, source="aion_cli")
            _log_event("override", {"reason": reason}, typ="control", text=f"override {reason}")
            _maybe_auto_aggregate()
            continue

        if cmdline == "status":
            print("📊 Cognitive System Status:")
            print(f" - Θ Orchestrator active: {getattr(theta, 'active', True)}")
            print(f" - Override flag: {getattr(interrupt, 'override_flag', False)}")
            _log_event("status", {}, typ="control", text="status")
            _maybe_auto_aggregate()
            continue

        # --- fallback ---
        print(f"❓ Unknown command: {cmdline}")
        _log_event("unknown", {"raw": cmdline}, typ="cli", text=cmdline)
        _maybe_auto_aggregate()


if __name__ == "__main__":
    main()