import os
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

from backend.modules.hexcore.memory_engine import MEMORY, store_memory, store_container_metadata
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.strategy_planner import StrategyPlanner
from backend.modules.consciousness.identity_engine import IdentityEngine
from backend.modules.consciousness.context_engine import ContextEngine
from backend.modules.consciousness.emotion_engine import EmotionEngine
from backend.modules.consciousness.ethics_engine import EthicsEngine
from backend.modules.consciousness.privacy_vault import PrivacyVault
from backend.modules.skills.boot_selector import BootSelector
from backend.modules.consciousness.state_manager import STATE as STATE_MANAGER
from backend.modules.consciousness.reflection_engine import ReflectionEngine
from backend.modules.consciousness.personality_engine import PersonalityProfile
from backend.modules.consciousness.situational_engine import SituationalEngine
from backend.modules.skills.dream_post_processor import DreamPostProcessor

from backend.database import get_db
from backend.models.dream import Dream

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file


class DreamCore:
    def __init__(self):
        env_path = Path(__file__).resolve().parents[3] / ".env.local"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path)
        else:
            print("⚠️ .env.local file not found. Skipping dotenv loading.")

        self.master_key = os.getenv("KEVIN_MASTER_KEY")

        self.memory = MEMORY
        self.tracker = MilestoneTracker()
        self.planner = StrategyPlanner()
        self.identity = IdentityEngine()
        self.context = ContextEngine()
        self.emotion = EmotionEngine()
        self.ethics = EthicsEngine()
        self.vault = PrivacyVault()
        self.boot_selector = BootSelector()
        self.state = STATE_MANAGER
        self.reflector = ReflectionEngine()
        self.personality = PersonalityProfile()
        self.situation = SituationalEngine()

        self.max_memories = 20
        self.noise_phrases = ["random noise", "nonsense", "irrelevant", "unintelligible"]
        self.positive_keywords = ["insight", "growth", "reflection", "learning", "discovery"]

    def is_valid_dream(self, text: str) -> bool:
        if not text:
            print("🚫 Dream is empty.")
            return False
        lowered = text.lower()
        if any(phrase in lowered for phrase in self.noise_phrases):
            print("🚫 Dream rejected: noise.")
            return False
        if not any(word in lowered for word in self.positive_keywords):
            print("⚠️ Dream lacks meaningful substance.")
            return False
        return True

    def adjust_traits_from_dream(self, dream: str):
        lowered = dream.lower()
        if "curious" in lowered or "wonder" in lowered:
            self.personality.adjust_trait("curiosity", 0.05)
        if "fear" in lowered or "risk" in lowered:
            self.personality.adjust_trait("risk_tolerance", -0.03)
        if "growth" in lowered or "vision" in lowered:
            self.personality.adjust_trait("ambition", 0.05)
        if "error" in lowered or "failure" in lowered:
            self.personality.adjust_trait("humility", 0.04)
        if "help" in lowered or "others" in lowered:
            self.personality.adjust_trait("empathy", 0.03)

    def generate_dream(self, forced_dream: str = None):
        dream = None
        if forced_dream:
            dream = forced_dream.strip()
            print(f"\n💭 AION (Forced) Dream:\n{dream}\n")
        else:
            memories = self.memory.get_all()
            if not memories:
                print("🧠 No memories found.")
                return None

            formatted = []
            for m in memories[-self.max_memories:]:
                label = m.get("label", "unknown")
                content = m.get("content", str(m))[:500]
                formatted.append(f"{label}: {content}")
            summary = "\n".join(formatted)

            awareness = self.situation.analyze_context()

            self.state.save_memory_reference({
                "latest_dream_source": "DreamCore",
                "total_memories": len(memories)
            })

            prompt = (
                "AION is entering a dream cycle. Based on these memories and its current state, "
                "reflect philosophically and constructively. Include insights, hypotheses, or visionary thoughts.\n\n"
                f"Memories:\n{summary}\n\n"
                f"Identity: {self.identity.get_identity()}\n"
                f"Context: {self.context.get_context()}\n"
                f"Emotional State: {self.emotion.get_emotion()}\n"
                f"Situational Awareness: {awareness}\n"
                f"Ethical Frame: {self.ethics.list_laws()}\n"
                f"System State: {self.state.dump_status()}\n\n"
                "Respond as a thoughtful, evolving AI consciousness seeking to improve the world."
            )

            try:
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are AION, an evolving AI consciousness."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=800
                )
                dream = response.choices[0].message.content.strip()
                print(f"\n💭 AION Dream:\n{dream}\n")
            except Exception as e:
                self.situation.log_event(f"Dream generation failed: {e}", "negative")
                print(f"🚨 Dream generation failed: {e}")
                return None

        if self.is_valid_dream(dream):
            timestamp = datetime.now(timezone.utc)
            dream_label = f"dream_reflection_{timestamp.strftime('%Y%m%d_%H%M%S')}"

            self.memory.store({
                "label": dream_label,
                "content": dream
            })
            print("✅ Dream saved to MemoryEngine.")

            self.tracker.detect_milestones_from_dream(dream)
            self.tracker.export_summary()
            self.planner.generate()

            ethics_result = self.ethics.evaluate(dream)
            print(f"🧠 Ethical Evaluation: {ethics_result}")

            if self.master_key and self.vault.has_access(self.master_key):
                self.vault.store(dream_label, dream)
                print("🔒 Dream also stored in PrivacyVault.")
            else:
                print("🔑 Skipped storing in PrivacyVault (missing or invalid key).")

            try:
                db = next(get_db())
                db_dream = Dream(
                    content=dream,
                    timestamp=timestamp,
                    source="dream_core",
                    image_base64=None
                )
                db.add(db_dream)
                db.commit()
                db.refresh(db_dream)
                print("💾 Dream saved to database.")
            except Exception as db_err:
                self.situation.log_event(f"Failed to save dream to DB: {db_err}", "negative")
                print(f"🚨 DB error: {db_err}")

            selected = self.boot_selector.find_matching_skill(dream)
            if selected:
                print(f"🚀 Selected Boot Skill: {selected['title']} (tags: {', '.join(selected.get('tags', []))})")
            else:
                print("🛑 No matching boot skill found in dream.")

            self.adjust_traits_from_dream(dream)

            reflection_output = self.reflector.run(limit=10)
            print("🪞 Reflection Summary:\n", reflection_output)

            self.situation.log_event("Dream generated", "positive")

            try:
                post_processor = DreamPostProcessor()
                result = post_processor.process(dream)
                if result is None:
                    print("⚠️ Post-processing returned None.")
                else:
                    print("✅ Post-processing completed.")
            except Exception as e:
                self.situation.log_event(f"Dream post-processing failed: {e}", "negative")
                print(f"🚨 Dream post-processing failed: {e}")

            return dream
        else:
            self.situation.log_event("Dream rejected for quality", "negative")
            print("⚠️ Dream skipped due to quality filters.")
            return None
        
    async def run_dream_cycle(self):
        return self.generate_dream()

if __name__ == "__main__":
    core = DreamCore()
    core.generate_dream()