import os
from pathlib import Path
from dotenv import load_dotenv
import openai

from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_tracker import MilestoneTracker

# 🔐 Load environment variables
env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(dotenv_path=env_path)

# Set OpenAI API key for old SDK style
openai.api_key = os.getenv("OPENAI_API_KEY")

# 🚀 Initialize engines
memory = MemoryEngine()
tracker = MilestoneTracker()

# 📚 Load stored memories
memories = memory.get_all()
if not memories:
    print("🧠 No memories found.")
    exit()

# 🧠 Format memories for dreaming
summary = "\n".join([f"{m['label']}: {m['content']}" for m in memories if 'label' in m and 'content' in m])
prompt = (
    "AION is reflecting during a dream cycle. Based on the following stored memories, "
    "generate a dream-like insight, hypothesis, or philosophical reflection:\n\n"
    f"{summary}\n\n"
    "Respond in a thoughtful and creative style."
)

# 🌙 Generate the dream
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

    # 💾 Save the dream to memory
    memory.save(label="dream_reflection", content=dream)

    # 🧠 Check for milestone triggers
    tracker.detect_milestones_from_dream(dream)

    # 📊 Save updated summary
    tracker.export_summary()

except Exception as e:
    print(f"⚠️ Dream generation failed: {e}")