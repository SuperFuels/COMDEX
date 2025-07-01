import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import openai

from modules.hexcore.memory_engine import MemoryEngine
from modules.skills.milestone_tracker import MilestoneTracker
from modules.skills.strategy_planner import StrategyPlanner
from modules.consciousness.identity_engine import IdentityEngine
from modules.consciousness.context_engine import ContextEngine
from modules.consciousness.emotion_engine import EmotionEngine
from modules.consciousness.ethics_engine import EthicsEngine
from modules.consciousness.vault_engine import PrivacyVault

from database import get_db
from models.dream import Dream  # Your Dream ORM model

class DreamCore:
    def __init__(self):
        # Load environment variables
        env_path = Path(__file__).resolve().parents[3] / ".env.local"
        load_dotenv(dotenv_path=env_path)
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.master_key = os.getenv("KEVIN_MASTER_KEY")

        # Initialize modules
        self.memory = MemoryEngine()
        self.tracker = MilestoneTracker()
        self.planner = StrategyPlanner()
        self.identity = IdentityEngine()
        self.context = ContextEngine()
        self.emotion = EmotionEngine()
        self.ethics = EthicsEngine()
        self.vault = PrivacyVault()

        # Config
        self.max_memories = 20
        self.noise_phrases = ["random noise", "nonsense", "irrelevant", "unintelligible"]
        self.positive_keywords = ["insight", "growth", "reflection", "learning", "discovery"]

    def is_valid_dream(self, text: str) -> bool:
        lowered = text.lower()
        if any(phrase in lowered for phrase in self.noise_phrases):
            print("🚫 Dream rejected: noise.")
            return False
        if not any(word in lowered for word in self.positive_keywords):
            print("⚠️ Dream lacks meaningful substance.")
            return False
        return True

    def generate_dream(self):
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

        prompt = (
            "AION is entering a dream cycle. Based on these memories and its current state, "
            "reflect philosophically and constructively. Include insights, hypotheses, or visionary thoughts.\n\n"
            f"Memories:\n{summary}\n\n"
            f"Identity: {self.identity.get_identity()}\n"
            f"Context: {self.context.get_context()}\n"
            f"Emotional State: {self.emotion.get_emotion()}\n"
            f"Ethical Frame: {self.ethics.list_laws()}\n\n"
            "Respond as a thoughtful, evolving AI consciousness seeking to improve the world."
        )

        try:
            response = openai.ChatCompletion.create(
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

            if self.is_valid_dream(dream):
                timestamp = datetime.utcnow()
                dream_label = f"dream_reflection_{timestamp.strftime('%Y%m%d_%H%M%S')}"

                # Store in memory
                self.memory.store({
                    "label": dream_label,
                    "content": dream
                })
                print("✅ Dream saved to MemoryEngine.")

                # Trigger milestones and update strategy
                self.tracker.detect_milestones_from_dream(dream)
                self.tracker.export_summary()
                self.planner.generate()

                # Ethics check
                ethics_result = self.ethics.evaluate(dream)
                print(f"🧠 Ethical Evaluation: {ethics_result}")

                # Store in private vault if access granted
                if self.vault.has_access(self.master_key):
                    self.vault.store_private(f"{dream_label}", dream)
                    print("🔒 Dream also stored in PrivacyVault.")

                # Save dream to DB
                db = next(get_db())
                db_dream = Dream(
                    content=dream,
                    timestamp=timestamp,
                    source="dream_core",
                    image_base64=None  # Optionally replace with snapshot
                )
                db.add(db_dream)
                db.commit()
                db.refresh(db_dream)
                print("💾 Dream saved to database.")

                return dream

            else:
                print("⚠️ Dream skipped due to quality filters.")
                return None

        except Exception as e:
            print(f"🚨 Dream generation failed: {e}")
            return None