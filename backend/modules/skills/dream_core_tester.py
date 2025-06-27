from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_tracker import MilestoneTracker
from backend.modules.skills.strategy_planner import StrategyPlanner
import openai
import os
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime

# ✅ Load environment variables
env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(dotenv_path=env_path)

# ✅ Load API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("❌ OPENAI_API_KEY not found in environment.")
    exit()

# ✅ Initialize OpenAI client
openai.api_key = api_key

# ✅ Initialize services
memory = MemoryEngine()
tracker = MilestoneTracker()
planner = StrategyPlanner()
memories = memory.get_all()

# ✅ Ensure memories exist
if not memories:
    print("🧠 No memories found.")
    exit()

# ✅ Format memory summary
formatted = []
for item in memories:
    label = item.get("label", "unknown")
    content = item.get("content", str(item))
    formatted.append(f"{label}: {content}")

summary = "\n".join(formatted)

# ✅ Dream prompt
prompt = f"""AION is reflecting during a dream cycle. Based on the following stored memories, generate a dream-like insight, hypothesis, or philosophical reflection:

{summary}

Respond in a thoughtful, poetic, or insightful tone as if AION is dreaming."""

# ✅ Generate dream
try:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are AION, dreaming to evolve your understanding and intelligence based on stored memories."},
            {"role": "user", "content": prompt}
        ]
    )
    dream = response.choices[0].message.content.strip()
    print(f"\n💭 AION Dream:\n{dream}\n")

    # ✅ Timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # ✅ Detect milestone tags
    detected_tags = []
    for tag, keywords in tracker.TRIGGER_PATTERNS.items():
        if any(kw.lower() in dream.lower() for kw in keywords):
            detected_tags.append(tag)

    # ✅ Save dream with tags
    memory.store({
        "label": f"dream_reflection_{timestamp}",
        "content": dream,
        "milestone_tags": detected_tags
    })
    print("🧠 Dream stored in MemoryEngine.\n")

    # ✅ Process milestone detection
    tracker.detect_milestones_from_dream(dream)
    tracker.export_summary()

    # ✅ Trigger new strategies
    planner.generate()

except Exception as e:
    print(f"⚠️ Dream generation failed: {e}")