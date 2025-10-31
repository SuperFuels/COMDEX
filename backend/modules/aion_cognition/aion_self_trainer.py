#!/usr/bin/env python3
"""
🧠 AION Self-Trainer — Phase 47D
────────────────────────────────────────────
Adaptive reinforcement for weak or low-stability
concepts across LexMemory and ResonantMemoryCache.

Integrations:
  • SQI trend persistence and plotting
  • Live dashboard JSONL logging
  • Bridge sync via aion_bridge_feed.json (for Aion🧠 dashboard)
"""

import json, random, time, logging
from statistics import mean
from pathlib import Path
import matplotlib.pyplot as plt

# ✅ SCI optional overlay
try:
    from backend.modules.aion_language.sci_overlay import sci_emit
except Exception:
    def sci_emit(*a, **k): pass

from backend.modules.aion_cognition.cee_lex_memory import update_lex_memory, recall_from_memory
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_language.harmonic_memory_profile import HarmonicMemoryProfile
from backend.modules.aion_language.conversation_memory import MEM

# ─── Logging ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

# ─── Core Instances ───────────────────────────────────────
RMC = ResonantMemoryCache()
HMP = HarmonicMemoryProfile()

# ─── Paths ────────────────────────────────────────────────
REPORT_PATH = Path("data/analysis/aion_selftrain_report.json")
PROGRESS_PATH = Path("data/analysis/aion_sqi_progress.json")
PLOT_PATH = Path("data/analysis/aion_sqi_progress.png")
DASHBOARD_LOG = Path("data/analysis/aion_live_dashboard.jsonl")
BRIDGE_FEED = Path("data/analysis/aion_bridge_feed.json")
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

# ─── Persistent SQI History ───────────────────────────────
if PROGRESS_PATH.exists():
    try:
        SQI_HISTORY = json.loads(PROGRESS_PATH.read_text())
    except Exception:
        SQI_HISTORY = []
else:
    SQI_HISTORY = []


def paraphrase(text: str) -> str:
    """Light local paraphrase generator."""
    if not text:
        return ""
    tokens = text.split()
    if len(tokens) > 6:
        random.shuffle(tokens)
    tweaks = ["concept of", "state of", "form of", "property of"]
    if random.random() > 0.7:
        text = f"{random.choice(tweaks)} {text}"
    return " ".join(tokens[:30])


def log_dashboard_event(cycle: int, sqi: float, stability: float, success_rate: float):
    """Append live training event to dashboard stream and bridge feed."""
    event = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cycle": cycle,
        "avg_SQI": round(sqi, 3),
        "avg_stability": round(stability, 3),
        "success_rate": round(success_rate, 3),
        "event": "self_training_update"
    }

    with open(DASHBOARD_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")

    BRIDGE_FEED.write_text(json.dumps(event, indent=2))
    log.info(f"[Dashboard] 📡 Synced training event → {DASHBOARD_LOG}")


def reinforce_entry(lemma: str, definition: str, sqi: float, stability: float):
    """Reinforce weak entry through synthetic resonance."""
    try:
        para = paraphrase(definition)
        resonance = {
            "ρ": round(random.uniform(0.65, 0.9), 3),
            "I": round(random.uniform(0.7, 1.0), 3),
            "SQI": round(random.uniform(0.7, 0.95), 3)
        }

        update_lex_memory(lemma, para or definition, resonance)
        RMC.update_from_photons([{"λ": lemma, "φ": resonance["ρ"], "μ": resonance["I"]}])
        MEM.remember(lemma, para or definition, semantic_field="self_training")

        if HMP:
            HMP.log_event({
                "target": lemma,
                "gain": resonance["ρ"],
                "drift_mag": abs(resonance["I"] - resonance["ρ"]),
                "time": time.time()
            })

        # ✅ SCI emit reinforcement
        sci_emit("selftrain_reinforce", {
            "lemma": lemma,
            "rho": resonance["ρ"],
            "I": resonance["I"],
            "SQI": resonance["SQI"],
            "t": time.time()
        })

        log.info(f"[SelfTrainer] 🔁 Reinforced '{lemma}' (SQI={resonance['SQI']})")
        return resonance["SQI"], resonance["ρ"]

    except Exception as e:
        log.warning(f"[SelfTrainer] ⚠ Failed to reinforce {lemma}: {e}")
        sci_emit("selftrain_error", {"stage": "reinforce", "lemma": lemma, "error": str(e)[:200]})
        return None, None


def run_self_training(limit: int = 500):
    """Main adaptive self-training loop."""

    # ✅ SCI cycle begin
    sci_emit("selftrain_start", {"limit": limit, "timestamp": time.time()})

    cache = RMC.cache
    weak = [
        (k, v) for k, v in cache.items()
        if isinstance(v, dict)
        and (v.get("SQI", 0.0) < 0.7 or v.get("stability", 1.0) < 0.8)
    ]
    random.shuffle(weak)
    log.info(f"[SelfTrainer] Detected {len(weak)} weak entries (reinforcing ≤ {limit})")

    sqi_samples, stab_samples = [], []
    count = success = 0

    for lemma, entry in weak[:limit]:
        rec = recall_from_memory(lemma) or {}
        definition = rec.get("definition") or rec.get("content") or ""
        if not definition:
            continue

        new_sqi, new_stab = reinforce_entry(
            lemma,
            definition,
            entry.get("SQI", 0.5),
            entry.get("stability", 0.8)
        )
        if new_sqi:
            sqi_samples.append(new_sqi)
            stab_samples.append(new_stab)
            success += 1

        count += 1
        if count % 50 == 0:
            RMC.save()
            log.info(f"[SelfTrainer] Progress {count}/{limit}")

    RMC.save()

    avg_sqi = round(mean(sqi_samples), 3) if sqi_samples else 0.0
    avg_stab = round(mean(stab_samples), 3) if stab_samples else 0.0
    success_rate = round(success / max(count, 1), 3)

    summary = {
        "total_weak": len(weak),
        "attempted": count,
        "successful": success,
        "avg_SQI": avg_sqi,
        "avg_stability": avg_stab,
        "success_rate": success_rate,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    REPORT_PATH.write_text(json.dumps(summary, indent=2))
    SQI_HISTORY.append(avg_sqi)
    PROGRESS_PATH.write_text(json.dumps(SQI_HISTORY, indent=2))

    plt.figure()
    plt.plot(range(1, len(SQI_HISTORY) + 1), SQI_HISTORY, marker="o")
    plt.title("AION Self-Training SQI Progress")
    plt.xlabel("Cycle")
    plt.ylabel("Symatic Quality Index (SQI)")
    plt.grid(True)
    plt.savefig(PLOT_PATH)
    log.info(f"📈 SQI progress plot saved → {PLOT_PATH}")

    log_dashboard_event(len(SQI_HISTORY), avg_sqi, avg_stab, success_rate)

    # ✅ SCI cycle complete
    sci_emit("selftrain_cycle", summary)

    log.info(f"[SelfTrainer] ✅ Completed → {REPORT_PATH}")
    return summary


if __name__ == "__main__":
    log.info("🧠 AION Self-Trainer — Phase 47D starting...")
    run_self_training(limit=400)