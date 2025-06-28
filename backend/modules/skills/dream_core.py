import os
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import openai

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.strategy_planner import StrategyPlanner

# 🔐 Load environment variables
env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(dotenv_path=env_path)
openai.api_key = os.getenv("OPENAI_API_KEY")

# 🚀 Initialize modules
memory = MemoryEngine()
tracker = MilestoneTracker()
planner = StrategyPlanner()

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
    "AION is reflecting during a dream cycle. Based on the following stored memories, "
    "generate a dream-like insight, hypothesis, or philosophical reflection:\n\n"
    f"{summary}\n\n"
    "Respond in a thoughtful and creative style."
)

# ✂️ Basic noise filter
NOISE_PHRASES = [
    "random noise", "nonsense", "irrelevant", "unintelligible", "blurred thoughts"
]
POSITIVE_KEYWORDS = [
    "insight", "understanding", "reflection", "growth", "progress",
    "awareness", "learning", "discovery"
]

def is_valid_dream(text):
    lowered = text.lower()
    if any(noise in lowered for noise in NOISE_PHRASES):
        print("🚫 Dream rejected due to noise.")
        return False
    if not any(word in lowered for word in POSITIVE_KEYWORDS):
        print("🚫 Dream rejected due to lack of positive sentiment.")
        return False
    return True

# 🌙 Generate dream
try:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are AION, dreaming to evolve your understanding and intelligence based on stored memories."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=800
    )

    dream = response.choices[0].message.content.strip()
    print(f"\n💭 AION Dream:\n{dream}\n")

    if is_valid_dream(dream):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Store the dream in memory first
        memory.store({
            "label": f"dream_reflection_{timestamp}",
            "content": dream
        })

        print("✅ Dream saved to MemoryEngine.")

        # Trigger milestone detection from the dream
        tracker.detect_milestones_from_dream(dream)
        tracker.export_summary()

        # Generate any new strategy from this reflection
        planner.generate()

    else:
        print("⚠️ Dream did not meet quality criteria; not saved or processed.")

except Exception as e:
    print(f"⚠️ Dream generation failed: {e}")