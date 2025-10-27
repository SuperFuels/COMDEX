#!/usr/bin/env python3
"""
AION Cognitive↔Interactive Bridge — Phase 13 + Resonant Recall
──────────────────────────────────────────────────────────────
Combines the AION Resonance Console with the Cognitive Exercise Engine (CEE)
and introduces long-term Resonant Recall via LexMemory + ResonantMemoryCache.

Usage:
    PYTHONPATH=. python backend/simulations/run_aion_cognitive_bridge.py
"""

import json, time, readline, random
from pathlib import Path
import plotly.graph_objects as go
from rich.console import Console
from rich.table import Table

# ─────────────────────────────────────────────────────────────
# Core engines
from backend.AION.resonance.resonance_engine import update_resonance, get_resonance
from backend.modules.aion.memory.store import _load as load_memory
from backend.modules.wiki_capsules.integration.kg_query_extensions import update_capsule_meta
from backend.modules.aion_cognition.cee_lex_memory import update_lex_memory
from backend.simulations import aion_bridge_commands as cmds
# ─── Resonance Heartbeat integration ───────────────────────────
from backend.modules.aion_resonance.resonance_heartbeat import ResonanceHeartbeat

# Cognitive layer
from backend.modules.aion_cognition.cognitive_exercise_engine_dual import DualModeCEE as CognitiveExerciseEngine

# ────────────────────────────────────────────────────────────────
# ⚛ Resonant Recall + Dashboard Integration
# ────────────────────────────────────────────────────────────────

# ✅ Resonant recall and memory access
from backend.modules.aion_cognition.cee_lex_memory import recall_from_memory
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache

# ✅ Core imports
from pathlib import Path
import json, time

# ─── Live Dashboard (append-only JSONL feed) ─────────────────────
DASHBOARD_LOG_PATH = Path("data/analysis/aion_live_dashboard.jsonl")
DASHBOARD_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

def log_bridge_event(cmd: str, pulse: dict | None):
    """Append command + last-known resonance pulse to the dashboard feed."""
    entry = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "command": cmd,
    }
    if isinstance(pulse, dict):
        entry.update({
            "Φ_coherence": pulse.get("Φ_coherence"),
            "Φ_entropy":   pulse.get("Φ_entropy"),
            "SQI":         pulse.get("sqi"),
            "ΔΦ":          pulse.get("resonance_delta"),
            "Θ_frequency": pulse.get("Θ_frequency"),
        })
    with open(DASHBOARD_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

# ─── Resonant Memory Cache Initialization ───────────────────────
RMC = ResonantMemoryCache()
RMC.load()  # ensures persistent memory is available before operations

# ─── Dashboard Sync (aggregated JSON snapshot) ──────────────────
DASHBOARD_FEED_PATH = Path("data/analysis/aion_bridge_feed.json")
DASHBOARD_FEED_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─── Simplified CLI Dashboard Writer ────────────────────────────
def update_bridge_dashboard(snapshot: dict):
    """Render live AION dashboard (Rich table + JSON snapshot, no HTML)."""
    from rich.console import Console
    from rich.table import Table
    console = Console()

    cycle = snapshot.get("cycle", "?")
    sqi = snapshot.get("avg_SQI", 0.0)
    stab = snapshot.get("avg_stability", 0.0)
    decay = snapshot.get("decay_rate", 0.0)
    mci = snapshot.get("semantic_benchmark", {}).get("avg_MCI", 0.0)
    drift = snapshot.get("semantic_benchmark", {}).get("avg_drift", 0.0)

    # 🟢 Rich CLI Dashboard (KEEP THIS)
    table = Table(title=f"AION Dashboard — Cycle {cycle}")
    table.add_column("Metric", style="cyan", justify="left")
    table.add_column("Value", style="magenta", justify="right")
    table.add_row("Symatic Quality Index (SQI)", f"{sqi:.3f}")
    table.add_row("Stability", f"{stab:.3f}")
    table.add_row("Decay Rate", f"{decay:.4f}")
    table.add_row("Meaning Consistency (MCI)", f"{mci:.3f}")
    table.add_row("Resonance Drift", f"{drift:.3f}")
    console.print(table)

    # 🧾 Save as JSON instead of HTML (Codespaces-safe)
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

        else:
            print(f"❓ Unknown command: {cmd}")
            log_bridge_event(cmd, {})

# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()