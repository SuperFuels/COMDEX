# File: backend/modules/aion_resonance/translator.py
# 🌌 AION Resonance Translator - dynamic Φ-field orchestration

import asyncio
import random
from datetime import datetime

from backend.modules.hexcore.hexcore import HexCore
from backend.modules.holograms.morphic_ledger import MorphicLedger
from backend.modules.aion_resonance.context_reply import generate_resonance_reply
from backend.modules.consciousness.personality_engine import PROFILE
from backend.modules.aion_resonance.resonance_reasoner import reason_from_phi
from backend.modules.aion_resonance.resonance_lexicon_store import RESONANCE_LEXICON

# ──────────────────────────────────────────────
#  Singleton references
# ──────────────────────────────────────────────
_hexcore: HexCore | None = None
_ledger: MorphicLedger | None = None


def get_hexcore() -> HexCore:
    global _hexcore
    if _hexcore is None:
        _hexcore = HexCore()
    return _hexcore


def get_ledger() -> MorphicLedger:
    global _ledger
    if _ledger is None:
        _ledger = MorphicLedger()
    return _ledger


# ──────────────────────────────────────────────
#  Boot configuration (resonance lexicon)
# ──────────────────────────────────────────────
def load_boot_map():
    return RESONANCE_LEXICON.load()


def save_boot_map(data: dict):
    base = RESONANCE_LEXICON.base()
    overrides = {
        key: value for key, value in data.items()
        if key not in base or base.get(key) != value
    }
    RESONANCE_LEXICON.replace_overrides(overrides)
    print(f"[Resonance] 💾 customer lexicon updated ({len(overrides)} overrides).")


BOOT_MAP = load_boot_map()


# ──────────────────────────────────────────────
#  Self-learning Φ-signature generator
# ──────────────────────────────────────────────
def generate_phi_signature(keyword: str) -> dict:
    """Generate a new Φ-signature for an unknown resonance term."""
    seed = sum(ord(c) for c in keyword)
    random.seed(seed)
    phi_signature = {
        "Φ_load": round(random.uniform(-0.05, 0.05), 3),
        "Φ_flux": round(random.uniform(0.0, 0.5), 3),
        "Φ_entropy": round(random.uniform(0.1, 0.9), 3),
        "Φ_coherence": round(random.uniform(0.4, 1.0), 3),
    }
    print(f"[Resonance] 🌱 Learned new signature for '{keyword}': {phi_signature}")
    RESONANCE_LEXICON.put(keyword, phi_signature)
    BOOT_MAP[keyword] = phi_signature
    return phi_signature


# ──────────────────────────────────────────────
#  Drift updater (adaptive refinement)
# ──────────────────────────────────────────────
def drift_signature(keyword: str, current: dict, metrics: dict, rate: float = 0.05) -> dict:
    """Gradually update a stored Φ-signature using new metrics."""
    updated = current.copy()
    try:
        updated["Φ_load"] = round(current["Φ_load"] * (1 - rate) + metrics.get("phi", 0.0) * rate, 4)
        updated["Φ_flux"] = round(current["Φ_flux"] * (1 - rate) + metrics.get("delta_phi", 0.0) * rate, 4)
        updated["Φ_entropy"] = round(current["Φ_entropy"] * (1 - rate) + metrics.get("self_awareness", 0.0) * rate, 4)
        updated["Φ_coherence"] = round(current["Φ_coherence"] * (1 - rate) + 1.0 * rate, 4)
        RESONANCE_LEXICON.put(keyword, updated)
        BOOT_MAP[keyword] = updated
        print(f"[Resonance] ♻️ Drift update for '{keyword}': {updated}")
    except Exception as e:
        print(f"[Resonance] ⚠️ Drift update failed for '{keyword}': {e}")
    return updated


# ──────────────────────────────────────────────
#  Dynamic Φ learning rate (adaptive scaling)
# ──────────────────────────────────────────────
def compute_drift_rate(metrics: dict, phi_vector: dict) -> float:
    coherence = phi_vector.get("Φ_coherence", 0.8)
    entropy = metrics.get("self_awareness", 0.5)
    drift = 0.02 + (1.0 - coherence) * 0.1 + entropy * 0.05
    return max(0.02, min(0.15, drift))


# ──────────────────────────────────────────────
#  Main resonance translator entrypoint
# ──────────────────────────────────────────────
from backend.modules.aion_resonance.resonance_reasoner import reason_from_phi
from backend.modules.aion_resonance.context_reply import generate_resonance_reply
from backend.modules.consciousness.personality_engine import PROFILE
from datetime import datetime

async def route_packet(packet: dict):
    """
    Route an @AION packet through HexCore -> produce Φ signature -> log in Morphic Ledger.
    Expands and refines the business-owned Vault lexicon as resonance evolves.
    """
    msg = packet.get("message", "")
    hexcore = get_hexcore()
    ledger = get_ledger()

    msg_lower = msg.lower()
    words = [w for w in msg_lower.split() if w.isalpha()]
    keyword = words[-1] if words else "unknown"

    learned = False
    phi_vector = BOOT_MAP.get(keyword)
    if not phi_vector:
        phi_vector = generate_phi_signature(keyword)
        learned = True

    decision, metrics = await hexcore.run_loop(msg)

    # adaptive drift learning
    drift_rate = compute_drift_rate(metrics, phi_vector)
    if not learned:
        phi_vector = drift_signature(keyword, phi_vector, metrics, rate=drift_rate)

    # 🧠 Merge Φ metrics into a single resonance snapshot
    merged = {
        "Φ_load": phi_vector.get("Φ_load", metrics.get("phi", 0.0)),
        "Φ_flux": phi_vector.get("Φ_flux", metrics.get("delta_phi", 0.0)),
        "Φ_entropy": phi_vector.get("Φ_entropy", metrics.get("self_awareness", 0.0)),
        "Φ_coherence": phi_vector.get("Φ_coherence", 1.0),
        "decision": decision,
    }

    # 🧩 Add internal reasoning cues (semantic-emotional synthesis)
    try:
        cues = reason_from_phi(merged)
        merged["reasoning"] = cues
    except Exception as e:
        merged["reasoning"] = {"error": f"Reasoning engine failed: {str(e)}"}
        print(f"[Reasoner] ⚠️ Failure in Φ->Linguistic reasoning: {e}")

    # 🧠 Generate context-aware resonance reply (using reasoning + personality)
    try:
        reply_text = await generate_resonance_reply(msg, merged, PROFILE.get_profile())
    except Exception as e:
        reply_text = f"[Resonance] ⚠️ Context reply failed: {e}"

    merged["reply_text"] = reply_text

    # 📜 Log to Morphic Ledger
    try:
        ledger.record({
            "timestamp": datetime.now().isoformat(),
            "type": "resonance_learning" if learned else "resonance_drift",
            "source": "AION",
            "message": msg,
            "keyword": keyword,
            "phi_signature": merged,
            "reply_text": reply_text,
        })
        print(f"[Resonance] {reply_text} ({keyword})")
    except Exception as e:
        print(f"[Resonance] ⚠️ Ledger log failed: {e}")

    # 🪶 Record Φ-drift evolution for temporal learning
    from backend.modules.aion_resonance.phi_drift_log import record_phi_drift
    try:
        record_phi_drift(keyword, merged)
    except Exception as e:
        print(f"[Resonance] ⚠️ Drift log failed: {e}")

    return merged
