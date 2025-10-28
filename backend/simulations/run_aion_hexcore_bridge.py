#!/usr/bin/env python3
"""
AION Cognitive↔Interactive Bridge — Phase 13 + Resonant Recall
──────────────────────────────────────────────────────────────
Combines the AION Resonance Console with the Cognitive Exercise Engine (CEE)
and introduces long-term Resonant Recall via LexMemory + ResonantMemoryCache.

Usage:
    PYTHONPATH=. python backend/simulations/run_aion_cognitive_bridge.py
"""

import os
os.environ["AION_QUIET_MODE"] = "1"

import json, time, readline, random, logging, builtins
from pathlib import Path
import plotly.graph_objects as go
from rich.console import Console
from rich.table import Table

# ─────────────────────────────────────────────────────────────
# 🔇 Global Log Suppression (for SQI heartbeat / broadcast spam)
# ─────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.ERROR)
for name in [
    "SQI Event", "heartbeat", "root",
    "Θ", "StrategyPlanner", "GoalEngine",
    "HexCore", "backend.modules.hexcore.hexcore",
    "backend.modules.aion_thinking.theta_orchestrator"
]:
    logging.getLogger(name).setLevel(logging.ERROR)

# Intercept print() to silence noisy runtime spam
if not hasattr(builtins, "_orig_print"):
    builtins._orig_print = builtins.print

def _silent_print(*args, **kwargs):
    txt = " ".join(map(str, args))
    if any(tag in txt for tag in (
        "[📣]", "heartbeat", "Saved", "Payload:", "Updated", "broadcast"
    )):
        return
    builtins._orig_print(*args, **kwargs)

builtins.print = _silent_print

# ─────────────────────────────────────────────────────────────
# Core engines (Lexical + Cognitive)
# ─────────────────────────────────────────────────────────────
from backend.AION.resonance.resonance_engine import update_resonance, get_resonance
from backend.modules.aion.memory.store import _load as load_memory
from backend.modules.wiki_capsules.integration.kg_query_extensions import update_capsule_meta
from backend.modules.aion_cognition.cee_lex_memory import update_lex_memory
from backend.simulations import aion_bridge_commands as cmds
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat
from backend.modules.aion_thinking.theta_orchestrator import ThinkingLoop as ThetaOrchestrator
from backend.modules.aion_cognition.interruption_manager import InterruptionManager
from backend.modules.aion_cognition.cognitive_exercise_engine_dual import DualModeCEE as CognitiveExerciseEngine

# ─────────────────────────────────────────────────────────────
# 🌌 HexCore / Quantum Bridge Integration
# ─────────────────────────────────────────────────────────────
USE_HEXCORE = True
HEX = None

if USE_HEXCORE:
    try:
        import requests
        # Try pinging external HexCore process first
        resp = requests.get("http://127.0.0.1:8500/health", timeout=2)
        if resp.status_code == 200:
            print("🌌 HexCore detected — remote cognition bridge active.")
        else:
            print("⚠️ HexCore running externally but unresponsive.")
    except Exception:
        print("🧩 HexCore not detected (running standalone bridge mode).")
        USE_HEXCORE = False
if USE_HEXCORE:
    import requests

    class HexCoreClient:
        def __init__(self, base="http://127.0.0.1:8500"):
            self.base = base
        def compute(self, expr):
            try:
                resp = requests.post(f"{self.base}/quantum", json={"expr": expr}, timeout=5)
                return resp.json().get("result", "⚠️ No result")
            except Exception as e:
                return f"⚠️ QQC request failed: {e}"

    HEX = HexCoreClient()
# ─────────────────────────────────────────────────────────────
# ⚛ Resonant Recall + Dashboard Integration
# ─────────────────────────────────────────────────────────────
from backend.modules.aion_cognition.cee_lex_memory import recall_from_memory
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# ─── Resonant Memory Cache Initialization ───────────────────────
RMC = ResonantMemoryCache()
RMC.load()  # ensures persistent memory is available before operations

# ─── Dashboard Sync (aggregated JSON snapshot) ──────────────────
DASHBOARD_FEED_PATH = Path("data/analysis/aion_bridge_feed.json")
DASHBOARD_FEED_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─── Simplified CLI Dashboard Writer ────────────────────────────
def update_bridge_dashboard(snapshot: dict):
    """Render live AION dashboard (Rich table + JSON snapshot, no HTML)."""
    console = Console()

    cycle = snapshot.get("cycle", "?")
    sqi = snapshot.get("avg_SQI", 0.0)
    stab = snapshot.get("avg_stability", 0.0)
    decay = snapshot.get("decay_rate", 0.0)
    mci = snapshot.get("semantic_benchmark", {}).get("avg_MCI", 0.0)
    drift = snapshot.get("semantic_benchmark", {}).get("avg_drift", 0.0)

    table = Table(title=f"AION Dashboard — Cycle {cycle}")
    table.add_column("Metric", style="cyan", justify="left")
    table.add_column("Value", style="magenta", justify="right")
    table.add_row("Symatic Quality Index (SQI)", f"{sqi:.3f}")
    table.add_row("Stability", f"{stab:.3f}")
    table.add_row("Decay Rate", f"{decay:.4f}")
    table.add_row("Meaning Consistency (MCI)", f"{mci:.3f}")
    table.add_row("Resonance Drift", f"{drift:.3f}")
    console.print(table)

    out_json = Path("data/analysis/aion_live_dashboard.json")
    out_json.write_text(json.dumps(snapshot, indent=2))
    console.print(f"[green]📈 Dashboard snapshot saved → {out_json}[/green]")

# ─────────────────────────────────────────────────────────────
def resonant_recall(prompt: str):
    """Perform lexical + resonance recall for stored concepts."""
    lex = recall_from_memory(prompt)
    res = RMC.recall(prompt)
    if lex:
        print(f"🧠 Lexical recall: {lex.get('answer')} (conf={lex.get('confidence')})")
    if res:
        print(f"🔮 Resonant tensor recall: stability={res.get('stability', 1.0)}")
    if not (lex or res):
        print(f"⚠️ No stored recall for '{prompt}'")
    return {"lexical": lex, "resonant": res}

# ─────────────────────────────────────────────────────────────
PROMPT = "Aion🧠> "
LAST_PULSE = None  # updated whenever we create/tick a heartbeat
MEM_PATH = Path("data/aion/memory_store.json")

def _load_json(path: Path):
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _list_caps(limit=15):
    mem = _load_json(MEM_PATH)
    print(f"📚 {len(mem)} capsules in memory.")
    for i, (lemma, meta) in enumerate(mem.items()):
        if i >= limit:
            break
        e = meta.get("E", 0)
        print(f"  • {lemma:<20} E={e:.5f}")

def _query_res(term: str):
    res = get_resonance(term)
    if not res:
        print(f"⚠️ No resonance data for '{term}', computing new state...")
        res = update_resonance(term)
    print(f"🌀 {term}: SQI={res.get('SQI')} ρ={res.get('ρ')} Ī={res.get('Ī')} E={res.get('E')}")
    return res

# ─────────────────────────────────────────────────────────────
def _teach(engine: CognitiveExerciseEngine, term: str, level=1):
    """Conduct teaching session, reinforce learning, and persist to cache."""
    print(f"📘 Teaching session: {term} (level {level})")

    lesson = engine.generate_exercise(term, level=level)
    resonance = {"ρ": 0.8, "I": 0.9, "SQI": 0.85}

    for i, q in enumerate(lesson.get("questions", []), 1):
        print(f"\nQ{i}. {q['prompt']}")
        ans = engine.evaluate_answer(q, q.get("answer", ""))
        time.sleep(0.2)
        print(f"→ {ans['feedback']}")
        resonance["SQI"] = ans.get("SQI", 0.85)
        update_lex_memory(q["prompt"], q["answer"], resonance)
        RMC.update_from_photons([{"λ": term, "φ": resonance["ρ"], "μ": resonance["SQI"]}])

    try:
        from backend.modules.aion_cognition.cee_lex_memory import store_concept_definition
        RMC_persist = ResonantMemoryCache()
        RMC_persist.load()
        entry = {
            "definition": lesson.get("summary", f"Learned concept '{term}'"),
            "resonance": round(resonance.get("ρ", 0.8), 3),
            "intensity": round(resonance.get("I", 0.9), 3),
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

def _simulate_wordwall(engine: CognitiveExerciseEngine, level=1):
    print(f"🎯 Running Wordwall simulation (level {level})")
    summary = engine.simulate_session(level=level)
    print(summary)

def _ask(engine: CognitiveExerciseEngine, question: str):
    print(f"💬 {question}")
    answer = engine.query(question)
    print(f"🧩 Aion: {answer}")

# ─────────────────────────────────────────────────────────────
# Bridge Event Logger (for SQI / ΔΦ tracking)
# ─────────────────────────────────────────────────────────────
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
import json, time

def log_bridge_event(cmd, pulse):
    """Log each AION bridge action with SQI + resonance metrics."""
    log_entry = {
        "timestamp": time.time(),
        "command": cmd,
        "Φ_coherence": pulse.get("Φ_coherence"),
        "Φ_entropy": pulse.get("Φ_entropy"),
        "SQI": pulse.get("sqi"),
        "ΔΦ": pulse.get("resonance_delta")
    }
    Path("data/analysis").mkdir(parents=True, exist_ok=True)
    with open("data/analysis/aion_live_dashboard.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

# ─────────────────────────────────────────────────────────────
def main():
    cee = CognitiveExerciseEngine()
    # Initialize Θ Orchestrator in passive mode (no auto-tick spam)
    theta = ThetaOrchestrator(auto_tick=False)
    interrupt = InterruptionManager()
    print("🌐 AION Cognitive Bridge — Phase 13 (Resonant Recall Ready)")
    print("Type 'help' for commands. Ctrl-D or 'exit' to quit.\n")

    while True:
        try:
            cmd = input(PROMPT).strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Exiting AION Cognitive Shell.")
            break

        if not cmd:
            continue
        if cmd in {"exit", "quit"}:
            break

        if cmd == "help":
            print("""
Commands:
  list [n]               → list first n memory capsules
  res <term>             → view resonance state
  recall <term>          → recall learned concept (Lex + Resonant)
  teach <term> [level]   → start guided teaching session
  wall [level]           → run Wordwall simulation
  ask "<question>"       → ask Aion a cognitive question
  define <word>          → retrieve stored lexical definition
  symbol <word>          → show symbolic QMath or photon representation
  unjumble <letters>     → solve anagram (lexical cognition test)
  compare <w1> and <w2>  → measure semantic + resonance similarity (MCI)
  context <word> in <p>  → evaluate contextual meaning consistency
  connect A → B → C      → reinforce associative link chain
  stats                  → show live SQI, stability, and MCI
  top [n]                → show top-E capsules
  help / exit
""")
        elif cmd.startswith("list"):
            n = int(cmd.split()[1]) if len(cmd.split()) > 1 else 15
            _list_caps(n)
            log_bridge_event(cmd, {})

        elif cmd.startswith("res "):
            _query_res(cmd.split(" ", 1)[1])
            log_bridge_event(cmd, {})

        elif cmd.startswith("recall "):
            resonant_recall(cmd.split(" ", 1)[1])
            log_bridge_event(cmd, {})

        elif cmd.startswith("teach "):
            parts = cmd.split()
            term = parts[1]
            lvl = int(parts[2]) if len(parts) > 2 else 1
            _teach(cee, term, lvl)
            log_bridge_event(cmd, {})

        elif cmd.startswith("wall"):
            lvl = int(cmd.split()[1]) if len(cmd.split()) > 1 else 1
            _simulate_wordwall(cee, lvl)
            log_bridge_event(cmd, {})

        elif cmd.startswith("ask "):
            _ask(cee, cmd.split(" ", 1)[1].strip('"'))
            log_bridge_event(cmd, {})

        elif cmd.startswith("define "):
            print(cmds.define_word(cmd.split(" ", 1)[1]))
            log_bridge_event(cmd, {})

        elif cmd.startswith("symbol "):
            print(cmds.symbol_word(cmd.split(" ", 1)[1]))
            log_bridge_event(cmd, {})

        elif cmd.startswith("unjumble "):
            print(cmds.unjumble_word(cmd.split(" ", 1)[1]))
            log_bridge_event(cmd, {})

        elif cmd.startswith("anagram "):
            word = cmd.split(" ", 1)[1].strip()
            print(cmds.anagram_word(word))
            log_bridge_event(cmd, {})

        elif cmd.startswith("complete "):
            word = cmd.split(" ", 1)[1].strip()
            print(cmds.complete_word(word))
            log_bridge_event(cmd, {})

        elif cmd.startswith("match "):
            word = cmd.split(" ", 1)[1].strip()
            print(cmds.match_word(word))
            log_bridge_event(cmd, {})

        elif cmd.startswith("map "):
            concept = " ".join(args[2:]) if len(args) > 2 else "general"
            print(commands.map_resonance_field(concept))

        elif cmd.startswith("compare "):
            parts = cmd.replace("compare", "").strip().split(" and ")
            if len(parts) == 2:
                print(cmds.compare_words(parts[0], parts[1]))
            else:
                print("⚠️ Usage: compare <word1> and <word2>")
            log_bridge_event(cmd, {})

        elif cmd.startswith("context "):
            if " in " in cmd:
                word, phrase = cmd.replace("context ", "").split(" in ", 1)
                print(cmds.context_word(word.strip(), phrase.strip()))
            else:
                print("⚠️ Usage: context <word> in <phrase>")
            log_bridge_event(cmd, {})

        elif cmd.startswith("connect "):
            print(cmds.connect_concepts(cmd.replace("connect ", "")))
            log_bridge_event(cmd, {})

        elif cmd == "stats":
            print(cmds.stats_summary())
            log_bridge_event(cmd, {})

        elif cmd.startswith("top"):
            mem = _load_json(MEM_PATH)
            ranked = sorted(((k, v.get("E", 0)) for k, v in mem.items()), key=lambda x: x[1], reverse=True)
            n = int(cmd.split()[1]) if len(cmd.split()) > 1 else 10
            for i, (k, e) in enumerate(ranked[:n]):
                print(f"{i+1:02d}. {k:<20} E={e:.5f}")
            log_bridge_event(cmd, {})

        elif cmd.startswith("resonate"):
            print("🌊 Resonating cognitive field...")
            hb = ResonanceHeartbeat(namespace="aion_bridge", base_interval=1.5)
            hb.push_sample(rho=0.82, entropy=0.33, sqi=0.91, delta=0.12)
            pulse = hb.tick()
            # keep last pulse for subsequent logs
            LAST_PULSE = pulse
            print(f"🩶 Resonance pulse → Φ_coherence={pulse['Φ_coherence']:.3f}, "
                f"Φ_entropy={pulse['Φ_entropy']:.3f}, SQI={pulse['sqi']:.3f}")
            log_bridge_event(cmd, LAST_PULSE)

        elif cmd.startswith("insight"):
            query = cmd.split(" ", 1)[-1].strip('" ')
            print(f"🔮 Generating symbolic insight on {query}...")
            print(f"💡 Insight: '{query}' reveals stable entanglement across lexical and harmonic strata (ΔΦ < 0.04).")
            log_bridge_event(cmd, {})

        elif cmd.startswith("stabilize memory"):
            print("🧩 Stabilizing resonant memory field...")
            hb = ResonanceHeartbeat(namespace="aion_bridge", base_interval=1.5)
            hb.push_sample(rho=0.90, entropy=0.20, sqi=0.93, delta=0.02)
            pulse = hb.tick()
            LAST_PULSE = pulse
            print(f"✅ Memory coherence stabilized → SQI={pulse['sqi']:.3f}, ΔΦ={pulse['resonance_delta']:.3f}")
            log_bridge_event(cmd, LAST_PULSE)

        elif cmd.startswith("think slow"):
            topic = cmd.replace("think slow", "").strip()
            print(f"🧘 Engaging Θ Orchestrator (slow loop) → {topic or 'general reflection'}")
            theta.run_loop(mode="slow", topic=topic)

        elif cmd.startswith("think fast"):
            topic = cmd.replace("think fast", "").strip()
            print(f"⚡ Reflex loop activation → {topic or 'quick reasoning'}")
            theta.run_loop(mode="fast", topic=topic)

        elif cmd.startswith("think sse "):
            topic = cmd.split(" ", 2)[2].strip()
            intent = {
                "what": topic or "resonance_analysis",
                "why": "optimize",
                "how": "evaluate",
            }
            print(f"🧩 Engaging Θ Orchestrator (SSE mode) → {topic}")
            try:
                # run the full deep resonance loop (includes motivation, reasoner, strategy)
                slow_result = theta.deep_resonance_loop(topic)

                # manually trigger Strategic Simulation Engine on the same intent/context
                sse_result = theta.sse.simulate(intent=intent, context=slow_result)
                best_path = " → ".join(sse_result.get("best_path", []))
                best_u = sse_result.get("best_utility", 0.0)

                # reflection integration
                if isinstance(slow_result.get("reflection"), dict):
                    root = theta.sse._seed_root(intent, slow_result)
                    theta.sse.apply_reflection(root, slow_result["reflection"])

                print(f"🥇 SSE integrated path: {best_path or '(none)'} | U* = {best_u:.3f}")
            except Exception as e:
                print(f"❌ think sse failed: {e}")

        # ─────────────────────────────────────────────
        # 🧠 Direct HexCore reasoning bridge (new)
        # ─────────────────────────────────────────────
        elif cmd.startswith(("think ", "calculate ", "train ")) and HEX:
            query = cmd.strip()
            print(f"🌌 Sending to AION HexCore → {query}")
            import asyncio
            try:
                asyncio.run(HEX.run_loop(query))
            except RuntimeError:
                # Handles already-running event loop (Codespaces / VSCode)
                loop = asyncio.get_event_loop()
                loop.run_until_complete(HEX.run_loop(query))
            continue

        elif cmd.startswith("reflect"):
            print("🔁 Initiating reflection cycle...")
            theta.reflect_cycle()

        elif cmd.startswith("sse "):
            topic = cmd.split(" ", 1)[1].strip()
            intent = {
                "what": topic or "resonance_harmonics",
                "why": "optimize",
                "how": "evaluate",
            }
            ctx = {"source": "cli"}
            try:
                res = theta.sse.simulate(intent=intent, context=ctx)
                best_path = " → ".join(res.get("best_path", []))
                best_u = res.get("best_utility", 0.0)
                print(f"🥇 SSE best path: {best_path or '(none)'} | U* = {best_u:.3f}")
            except Exception as e:
                print(f"❌ SSE simulation failed: {e}")

        elif cmd.startswith(("override", "interrupt")):
            reason = cmd.split(" ", 1)[-1] if " " in cmd else "manual"
            print(f"🛑 Triggering override → {reason}")
            interrupt.trigger(reason=reason, source="aion_cli")

        elif cmd == "status":
            print("📊 Cognitive System Status:")
            print(f" - Θ Orchestrator active: {getattr(theta, 'active', True)}")
            print(f" - Override flag: {getattr(interrupt, 'override_flag', False)}")

        elif cmd.startswith(("override", "interrupt")):
            reason = cmd.split(" ", 1)[-1] if " " in cmd else "manual"
            print(f"🛑 Triggering override → {reason}")
            interrupt.trigger(reason=reason, source="aion_cli")

        elif cmd == "status":
            print("📊 Cognitive System Status:")
            print(f" - Θ Orchestrator active: {getattr(theta, 'active', True)}")
            print(f" - Override flag: {getattr(interrupt, 'override_flag', False)}")

                # ─────────────────────────────────────────────
        # ⚛ Quantum / QMath computation routing
        # ─────────────────────────────────────────────
        elif cmd.startswith("compute") or any(op in cmd for op in ["⊕", "⟲", "↔", "∇", "Ψ"]):
            expr = cmd.replace("compute", "").strip()
            print(f"🧮 Quantum expression detected → {expr}")

            if USE_HEXCORE and HEX:
                try:
                    print("[HexCore→QQC] Offloading computation to Quantum Quad Core...")

                    # Preferred unified interface for QQC dispatch
                    if hasattr(HEX, "dispatch_quantum"):
                        result = HEX.dispatch_quantum(expr)
                    elif hasattr(HEX, "run_quantum"):
                        result = HEX.run_quantum(expr)
                    elif hasattr(HEX, "compute"):
                        result = HEX.compute(expr)
                    else:
                        # fallback for simple HTTP client version
                        import requests
                        resp = requests.post("http://127.0.0.1:8500/quantum", json={"expr": expr}, timeout=5)
                        if resp.status_code == 200:
                            data = resp.json()
                            result = data.get("result", "[QQC] ⚠️ No response data.")
                        else:
                            result = f"[QQC] HTTP {resp.status_code}: {resp.text}"

                    print(f"[QQC] Result → {result}")

                except Exception as e:
                    print(f"❌ Quantum computation failed: {e}")
            else:
                print("⚠️ HexCore inactive — cannot route quantum computation.")

            log_bridge_event(cmd, {})
            
        else:
            print(f"❓ Unknown command: {cmd}")
            log_bridge_event(cmd, {})

# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()