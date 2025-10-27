#!/usr/bin/env python3
"""
🧠 AION Full Lexical–Conceptual Trainer — Phase 17 (Safe Auto-Resume)
────────────────────────────────────────────────────────────────────
Trains Aion on enriched lexical capsules (~41 k) and
feeds them into LexMemory + ResonantMemoryCache.

Features:
  • Auto-detects enriched corpus (/tmp fallback)
  • Skips malformed or unreadable capsules
  • Auto-resumes from checkpoint
  • Periodic autosave of RMC + checkpoint
"""

import json, time, random, logging, gc
from pathlib import Path

from backend.modules.aion_cognition.cee_lex_memory import update_lex_memory, reinforce_field
from backend.modules.aion_language.resonant_memory_cache import ResonantMemoryCache
from backend.modules.aion_language.conversation_memory import MEM

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# 📂 Path setup
# ──────────────────────────────────────────────
LEX_ENRICHED = Path("data/knowledge/Lexicon_enriched").resolve()
if not LEX_ENRICHED.exists():
    LEX_ENRICHED = Path("/tmp/Lexicon_enriched")
    log.warning(f"⚠ Using fallback path: {LEX_ENRICHED}")

CHECKPOINT_PATH = Path("data/training/aion_autotrainer_checkpoint.json")
LOG_PATH = Path("data/training/aion_autotrainer_phase17.log")
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

RMC = ResonantMemoryCache()

# ──────────────────────────────────────────────
def parse_enriched_capsule(path: Path):
    """Read .phn capsule and extract lemma + short definition safely."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        lemma = path.stem.split(".")[0].strip().lower()
        if not text.strip():
            return None, None, None
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        defs = [l for l in lines if "definition" in l.lower() or "means" in l.lower()]
        examples = [l for l in lines if l.startswith("•") or "example" in l.lower()]
        definition = defs[0][:300] if defs else lines[0][:300]
        example = examples[0][:300] if examples else None
        return lemma, definition, example
    except Exception as e:
        log.warning(f"[ParseError] {path.name}: {e}")
        return None, None, None

# ──────────────────────────────────────────────
def train_from_capsules():
    """Main safe trainer loop with checkpoint + autosave."""
    files = sorted(LEX_ENRICHED.rglob("*.enriched.phn"))
    total = len(files)
    log.info(f"🧩 Found {total} enriched capsules to train.")

    # Resume from checkpoint if exists
    start_index = 0
    if CHECKPOINT_PATH.exists():
        try:
            ck = json.load(open(CHECKPOINT_PATH))
            start_index = ck.get("last_index", 0)
            log.info(f"⏩ Resuming from checkpoint #{start_index:,}")
        except Exception:
            pass

    stored = skipped = 0
    rho_sum = I_sum = SQI_sum = 0.0
    start_time = time.time()

    for i, path in enumerate(files[start_index:], start=start_index):
        lemma, definition, example = parse_enriched_capsule(path)
        if not lemma or not definition:
            skipped += 1
            continue

        try:
            resonance = {
                "ρ": round(random.uniform(0.6, 0.9), 3),
                "I": round(random.uniform(0.8, 1.0), 3),
                "SQI": round(random.uniform(0.7, 0.95), 3),
            }

            update_lex_memory(lemma, definition, resonance)
            reinforce_field(lemma, definition, resonance)
            RMC.update_from_photons([{"λ": lemma, "φ": resonance["ρ"], "μ": resonance["I"]}])
            MEM.remember(lemma, definition, semantic_field="lexical_training")

            rho_sum += resonance["ρ"]
            I_sum += resonance["I"]
            SQI_sum += resonance["SQI"]
            stored += 1

        except Exception as e:
            skipped += 1
            log.warning(f"[Trainer] Skipped {lemma}: {e}")
            continue

        # ── periodic save & checkpoint ──
        if (i + 1) % 500 == 0:
            avg = {
                "ρ̄": round(rho_sum / max(stored, 1), 3),
                "Ī̄": round(I_sum / max(stored, 1), 3),
                "SQĪ": round(SQI_sum / max(stored, 1), 3),
            }
            log.info(f"[{i+1}/{total}] ✅ Trained={stored}, Skipped={skipped}, Avg={avg}")
        if (i + 1) % 1000 == 0:
            json.dump({"last_index": i + 1}, open(CHECKPOINT_PATH, "w"))
            RMC.save()
            log.info(f"💾 Autosaved checkpoint #{i+1:,}")
            gc.collect()

    dur = round(time.time() - start_time, 2)
    summary = {
        "total_files": total,
        "stored": stored,
        "skipped": skipped,
        "avg_ρ": round(rho_sum / max(stored, 1), 3),
        "avg_I": round(I_sum / max(stored, 1), 3),
        "avg_SQI": round(SQI_sum / max(stored, 1), 3),
        "duration_s": dur,
    }

    json.dump(summary, open(LOG_PATH, "w"), indent=2)
    log.info(f"✅ Training complete in {dur}s — stored={stored}, skipped={skipped}")
    log.info(f"🧾 Summary → {LOG_PATH}")
    return summary

# ──────────────────────────────────────────────
if __name__ == "__main__":
    log.info("🔗 PhotonAKGBridge global instance initialized as PAB")
    summary = train_from_capsules()
    print(json.dumps(summary, indent=2))