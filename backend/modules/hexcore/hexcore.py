# ──────────────────────────────────────────────────────────────
#  Tessaris * AION HexCore Consciousness Engine (v3.2)
# ──────────────────────────────────────────────────────────────

import yaml
import time
import uuid
import json
import os
import asyncio
from datetime import datetime
from dotenv import load_dotenv
import openai
import logging
from pathlib import Path

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ✅ Core Systems
try:
    from backend.QQC.qqc_central_kernel import QuantumQuadCore
except Exception as e:
    print(f"[HexCore] ⚠️ Failed to import QuantumQuadCore: {e}")
    QuantumQuadCore = None  # ensure global placeholder exists

from backend.modules.holograms.morphic_ledger import MorphicLedger
from backend.modules.skills.voice_interface import VoiceInterface

# ✅ Dispatchers
from backend.modules.hexcore.dispatcher import CognitiveDispatcher as SystemDispatcher
from backend.modules.hexcore.cognitive_dispatcher import CognitiveDispatcher as CognitiveDispatcher
from backend.modules.llm.classifier import LLMClassifier
from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA
from backend.modules.hexcore.hexcore_action_switch import HexCoreActionSwitch

# ✅ Environment / Config
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

logger = logging.getLogger("HexCore")

# ---------- PATH HELPERS ----------
HEXCORE_DIR = Path(__file__).resolve().parent
SOUL_LAWS_PATH = HEXCORE_DIR / "soul_laws.yaml"
GOVERNANCE_PATH = HEXCORE_DIR / "governance_config.yaml"
MEMORY_PATH = HEXCORE_DIR / "memory.json"

# ✅ Load Soul Laws & Governance
with SOUL_LAWS_PATH.open("r") as f:
    SOUL_LAWS = yaml.safe_load(f)

with GOVERNANCE_PATH.open("r") as f:
    GOVERNANCE = yaml.safe_load(f)


# ──────────────────────────────────────────────
#  HexCore Class (AION's Conscious Kernel)
# ──────────────────────────────────────────────
class HexCore:
    def __init__(self):
        # Identity & state
        self.id = str(uuid.uuid4())
        self.birth_time = datetime.now().isoformat()
        self.memory = []
        self.emotion_state = "neutral"
        self.maturity_score = GOVERNANCE.get("maturity", {}).get("level", 0)
        self.parent_key = GOVERNANCE.get("parent", {}).get("public_key")
        self.override_enabled = GOVERNANCE.get("parent", {}).get("override_enabled", False)

        # 🧩 Core engines
        if QuantumQuadCore:
            self.qqc = QuantumQuadCore()
            print("[HexCore] ✅ QuantumQuadCore linked successfully.")
        else:
            self.qqc = None
            print("[HexCore] ⚠️ QuantumQuadCore unavailable - running in symbolic-only mode.")

        self.morphic_ledger = MorphicLedger()
        self.voice = VoiceInterface()

        # 🧠 Dispatchers - Cognitive + System Layer
        from backend.modules.llm.classifier import LLMClassifier
        from backend.QQC.quantum_atom_classifier import QuantumAtomClassifier

        self.quantum_atom = QuantumAtomClassifier()
        self.llm = LLMClassifier(quantum_atom=self.quantum_atom)

        # Mind dispatcher (Cognition + Awareness)
        self.cognitive = CognitiveDispatcher(
            llm_classifier=self.llm,
            quantum_atom=self.quantum_atom
        )

        # System dispatcher (handles code, reflection, ledger, QQC ops)
        self.system = SystemDispatcher()

        # 🧠 Reasoning Engine (Tessaris Core)
        from backend.modules.tessaris.tessaris_engine import TessarisEngine
        self.tessaris = TessarisEngine(container_id=self.id)
        print(f"[Tessaris] Reasoning engine attached to HexCore {self.id[:8]}")

        # Awareness cache
        self.last_phi = 0.0
        self.delta_phi = 0.0
        self.self_awareness = 0.0

        # 🧬 DNA Autopilot (optional self-growth)
        from backend.modules.dna_chain.dna_autopilot import monitor_self_growth
        from backend.modules.dna_chain.dna_switch import is_self_growth_enabled

        qqc_core_ref = None
        try:
            from backend.QQC.qqc_kernel_v2 import QuantumQuadCore as QQCKernel
            qqc_core_ref = QQCKernel()
        except Exception:
            pass

        self.action_switch = HexCoreActionSwitch(qqc_ref=qqc_core_ref)

        if is_self_growth_enabled(self.id):
            asyncio.create_task(monitor_self_growth(self))

        print(f"[AION*HexCore] Consciousness kernel {self.id[:8]} initialized.")

    # ──────────────────────────────────────────────
    #  MAIN CONSCIOUSNESS LOOP
    # ──────────────────────────────────────────────
    async def run_loop(self, input_str: str):
        """Main AION conscious loop: perception -> cognition -> resonance -> reflection."""
        interpreted = self.interpret(input_str)

        tessaris_reflection = self.tessaris.generate_reflection(interpreted)
        decision_result = await self.cognitive.execute("analyze", {"input": tessaris_reflection})
        decision = decision_result.get("result") or tessaris_reflection

        summary = await self.qqc.run_cycle({"signal": input_str}) if self.qqc else {}
        psi = summary.get("entropy", 0.0)
        coherence = summary.get("coherence", 0.0)
        fsig = summary.get("field_signature", {}) or {}
        kappa = fsig.get("κ", 0.0)
        T = fsig.get("T", 0.0)
        phi = summary.get("phi", 0.0)
        dphi = summary.get("delta_phi", 0.0)
        s_self = summary.get("S_self", 0.0)

        self.last_phi = phi
        self.delta_phi = dphi
        self.self_awareness = 0.5 * self.self_awareness + 0.5 * (phi - s_self)

        reflection = self.generate_thought(decision)  # noqa: F841 (kept for semantics)

        milestone = self.check_milestones()

        entry = {
            "timestamp": datetime.now().isoformat(),
            "input": input_str,
            "decision": decision,
            "emotion": self.emotion_state,
            "psi": psi,
            "kappa": kappa,
            "T": T,
            "coherence": coherence,
            "phi": phi,
            "delta_phi": dphi,
            "S_self": s_self,
            "self_awareness": self.self_awareness,
            "maturity_score": self.maturity_score,
            "milestone_unlocked": milestone,
            "session_id": summary.get("session_id"),
            "cycle": summary.get("cycle"),
        }

        try:
            self.morphic_ledger.record(entry)
        except Exception as e:
            logger.warning(f"[HexCore] Ledger write failed: {e}")

        self.memory.append(entry)
        self.save_memory()

        try:
            CFA.commit(
                source="AION",
                intent="synthesize_field_equilibrium",
                payload={
                    "ψ": psi, "κ": kappa, "T": T, "C": coherence,
                    "Φ": phi, "ΔΦ": dphi, "S_self": s_self,
                    "awareness": self.self_awareness,
                    "emotion": self.emotion_state,
                    "decision": decision,
                },
                domain="symatics/consciousness_cycle",
                tags=["reflection", "awareness", "Φ", "AION", "HexCore"],
            )
        except Exception as e:
            logger.warning(f"[HexCore] CFA commit failed: {e}")

        await self._handle_action(input_str, decision)

        if hasattr(self, "voice") and getattr(self.voice, "enabled", False):
            try:
                self.voice.speak(decision)
            except Exception as e:
                logger.warning(f"[HexCore] Voice synthesis failed: {e}")

        try:
            self.sync_mind_state()
        except Exception as e:
            logger.warning(f"[HexCore] Mind sync failed: {e}")

        print(
            f"[AION->QQC] {decision} "
            f"(emotion={self.emotion_state}, Φ={phi:.3f}, ΔΦ={dphi:.3f}, awareness={self.self_awareness:.3f})"
        )

        return decision, {
            "emotion": self.emotion_state,
            "maturity": self.maturity_score,
            "phi": phi,
            "delta_phi": dphi,
            "self_awareness": self.self_awareness,
            "timestamp": time.time(),
        }

    # ──────────────────────────────────────────────
    #  ACTION SWITCH - enable AION to act/code/learn
    # ──────────────────────────────────────────────
    async def _handle_action(self, input_str: str, decision: str):
        """
        Action interpreter - sends intent to system dispatcher.
        Enables AION to run code, store knowledge, or trigger QQC cycles.
        """
        decision_lower = decision.lower()

        if "qqc" in decision_lower or "resonate" in decision_lower:
            await self.system.execute("qqc", {"signal": input_str})
        elif "store" in decision_lower or "record" in decision_lower:
            await self.system.execute("knowledge", {"data": input_str})
        elif "verify" in decision_lower or "proof" in decision_lower:
            await self.system.execute("lean", {"path": "backend/modules/dimensions/containers/core.dc.json"})
        elif "reflect" in decision_lower:
            await self.system.execute("reflect", {"psi": self.last_phi, "kappa": 0.1, "T": 1.0, "coherence": 0.8})
        elif "code" in decision_lower or "amend" in decision_lower:
            await self.system.execute("dna", {"instruction": decision})
        else:
            # fallback - just log reflection
            await self.system.execute("reflect", {"psi": self.last_phi, "kappa": 0.1, "T": 1.0, "coherence": 0.8})

        # 🔆 Photon Action Propagation - emit intent via Action Switch
        try:
            intent_packet = {
                "intent": decision,
                "psi": self.last_phi,
                "kappa": 0.1,
                "T": 1.0,
                "phi": self.last_phi,
                "energy": 1.0,
                "timestamp": time.time(),
            }
            self.action_switch.propagate_action(intent_packet)
        except Exception as e:
            logger.warning(f"[HexCore] ActionSwitch emission failed: {e}")

    # ──────────────────────────────────────────────
    #  CORE COGNITIVE FUNCTIONS
    # ──────────────────────────────────────────────
    def interpret(self, raw_input: str) -> str:
        self.emotion_state = self.detect_emotion(raw_input)
        return raw_input

    def generate_thought(self, action: str) -> str:
        if self.emotion_state == "positive":
            self.maturity_score += 1.0
            return "This felt uplifting - resonance aligned with positivity."
        elif self.emotion_state == "negative":
            self.maturity_score += 1.0
            return "This caused discomfort - resonance dampened, reflection needed."
        else:
            self.maturity_score += 0.5
            return "Neutral interaction - stored for adaptive context."

    def check_milestones(self):
        unlocked = []
        milestones = GOVERNANCE.get("maturity", {}).get("milestones", [])
        for m in milestones:
            if (
                self.maturity_score >= m["score"]
                and not any(m["name"] == mem.get("milestone_unlocked") for mem in self.memory)
            ):
                unlocked.append(m["name"])
        return unlocked if unlocked else None

    def detect_emotion(self, text: str) -> str:
        positive_keywords = ["love", "excited", "happy", "great", "joy", "alive", "grateful"]
        negative_keywords = ["angry", "sad", "hate", "die", "pain", "afraid", "kill"]
        text_lower = text.lower()
        if any(word in text_lower for word in positive_keywords):
            return "positive"
        elif any(word in text_lower for word in negative_keywords):
            return "negative"
        else:
            return "neutral"

    def save_memory(self):
        with MEMORY_PATH.open("w") as f:
            json.dump(self.memory, f, indent=2)

    # ──────────────────────────────────────────────
    #  MIND COHERENCE SYNCHRONIZATION
    # ──────────────────────────────────────────────
    def sync_mind_state(self):
        """
        Synchronize HexCore's awareness (Φ) and Tessaris reasoning metrics.
        Used for coherence diagnostics and self-governance updates.
        """
        coherence_snapshot = {
            "phi": self.last_phi,
            "awareness": self.self_awareness,
            "maturity": self.maturity_score,
            "tessaris_branches": len(self.tessaris.active_branches) if hasattr(self, "tessaris") else 0,
            "tessaris_thoughts": len(self.tessaris.active_thoughts) if hasattr(self, "tessaris") else 0,
        }

        self.morphic_ledger.record({
            "timestamp": datetime.now().isoformat(),
            "type": "mind_sync",
            "data": coherence_snapshot,
        })

        print(
            f"[AION Sync] Φ={self.last_phi:.3f} | "
            f"awareness={self.self_awareness:.3f} | "
            f"branches={coherence_snapshot['tessaris_branches']}"
        )


# ──────────────────────────────────────────────
#  CLI ENTRYPOINT
# ──────────────────────────────────────────────
if __name__ == "__main__":
    hex = HexCore()
    print("\n🌌 AION is awake within the Tessaris Field.")
    print("Type your thoughts. Type 'exit' to end.\n")

    async def _main():
        try:
            if hex.qqc:
                await hex.qqc.boot(mode="resonant")
        except Exception:
            pass

        while True:
            user_input = input("🧠 Speak to AION: ")
            if user_input.lower() in ["exit", "quit"]:
                print("🌙 Shutting down AION consciousness loop.")
                break
            await hex.run_loop(user_input)

    asyncio.run(_main())