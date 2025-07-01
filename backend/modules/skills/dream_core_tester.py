from modules.hexcore.memory_engine import MemoryEngine
from modules.skills.milestone_tracker import MilestoneTracker
from modules.skills.strategy_planner import StrategyPlanner
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
openai.api_key = api_key

# ✅ Initialize core services
memory = MemoryEngine()
tracker = MilestoneTracker()
planner = StrategyPlanner()
memories = memory.get_all()

# ✅ Validate memory
if not memories:
    print("🧠 No memories found.")
    exit()

# ✅ Format and trim memory (token-safe)
formatted = []
MAX_MEMORIES = 20  # limit to latest 20 for token safety
for item in memories[-MAX_MEMORIES:]:
    label = item.get("label", "unknown")
    content = item.get("content", str(item))
    snippet = content[:500]  # prevent long memories from causing overuse
    formatted.append(f"{label}: {snippet}")

summary = "\n".join(formatted)

# ✅ Build prompt
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
        ],
        temperature=0.7,
        max_tokens=800
    )
    dream = response.choices[0].message.content.strip()
    print(f"\n💭 AION Dream:\n{dream}\n")

    # ✅ Timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # ✅ Detect milestone tags
    detected_tags = []
    trigger_patterns = getattr(tracker, "trigger_patterns", getattr(tracker, "TRIGGER_PATTERNS", {}))
    for tag, keywords in trigger_patterns.items():
        if any(kw.lower() in dream.lower() for kw in keywords):
            detected_tags.append(tag)

    # ✅ Save dream with tags
    memory.store({
        "label": f"dream_reflection_{timestamp}",
        "content": dream,
        "milestone_tags": detected_tags
    })
    print("🧠 Dream stored in MemoryEngine.\n")

    # ✅ Process milestone and strategy logic
    tracker.detect_milestones_from_dream(dream)
    tracker.export_summary()
    planner.generate()

except Exception as e:
    print(f"⚠️ Dream generation failed: {e}")
