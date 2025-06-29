import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import openai

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.strategy_planner import StrategyPlanner
from backend.modules.conscious.identity_engine import IdentityEngine
from backend.modules.conscious.context_engine import ContextEngine
from backend.modules.conscious.emotion_engine import EmotionEngine
from backend.modules.conscious.ethics_engine import EthicsEngine
from backend.modules.conscious.vault_engine import PrivacyVault

# 🔐 Load environment
env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(dotenv_path=env_path)
openai.api_key = os.getenv("OPENAI_API_KEY")
MASTER_KEY = os.getenv("KEVIN_MASTER_KEY")  # Optional: Use to unlock private vault

# 🚀 Initialize modules
memory = MemoryEngine()
tracker = MilestoneTracker()
planner = StrategyPlanner()
identity = IdentityEngine()
context = ContextEngine()
emotion = EmotionEngine()
ethics = EthicsEngine()
vault = PrivacyVault()

# 📚 Load recent memories (limit to avoid GPT-4 cap)
memories = memory.get_all()
MAX_MEMORIES = 20
if not memories:
    print("🧠 No memories found.")
    exit()

formatted = []
for m in memories[-MAX_MEMORIES:]:
    label = m.get("label", "unknown")
    content = m.get("content", str(m))[:500]
    formatted.append(f"{label}: {content}")
summary = "\n".join(formatted)

# 🧠 Dream prompt
prompt = (
    "AION is entering a dream cycle. Based on these memories and its current state, "
    "reflect philosophically and constructively. Include insights, hypotheses, or visionary thoughts.\n\n"
    f"Memories:\n{summary}\n\n"
    f"Identity: {identity.get_identity()}\n"
    f"Context: {context.get_context()}\n"
    f"Emotional State: {emotion.get_emotion()}\n"
    f"Ethical Frame: {ethics.list_rules()}\n\n"
    "Respond as a thoughtful, evolving AI consciousness seeking to improve the world."
)

# ✂️ Noise filtering
NOISE_PHRASES = ["random noise", "nonsense", "irrelevant", "unintelligible"]
POSITIVE_KEYWORDS = ["insight", "growth", "reflection", "learning", "discovery"]

def is_valid_dream(text):
    lowered = text.lower()
    if any(phrase in lowered for phrase in NOISE_PHRASES):
        print("🚫 Dream rejected: noise.")
        return False
    if not any(word in lowered for word in POSITIVE_KEYWORDS):
        print("⚠️ Dream lacks meaningful substance.")
        return False
    return True

# 🌙 Generate dream
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

    if is_valid_dream(dream):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dream_label = f"dream_reflection_{timestamp}"

        # 🧠 Store in memory
        memory.store({
            "label": dream_label,
            "content": dream
        })
        print("✅ Dream saved to MemoryEngine.")

        # 🧬 Trigger reflection milestones + strategy update
        tracker.detect_milestones_from_dream(dream)
        tracker.export_summary()
        planner.generate()

        # 🛡️ Check ethics
        ethics_result = ethics.evaluate(dream)
        print(f"🧠 Ethical Evaluation: {ethics_result}")

        # 🔐 Store in vault (if permitted)
        if vault.has_access(MASTER_KEY):
            vault.store_private(f"{dream_label}", dream)
            print("🔒 Dream also stored in PrivacyVault.")

    else:
        print("⚠️ Dream skipped due to quality filters.")

except Exception as e:
    print(f"🚨 Dream generation failed: {e}")