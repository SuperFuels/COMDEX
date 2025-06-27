from backend.modules.hexcore.memory_engine import MemoryEngine
from openai import OpenAI
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment
env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(dotenv_path=env_path)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

memory = MemoryEngine()
memories = memory.get_all()

if not memories:
    print("🧠 No memories found.")
    exit()

# 🧠 Format list of memory entries into readable text
summary = "\n".join([f"{m['label']}: {m['content']}" for m in memories if 'label' in m and 'content' in m])
prompt = f"AION is reflecting during a dream cycle. Based on the following stored memories, generate a dream-like insight, hypothesis, or philosophical reflection:\n\n{summary}\n\nRespond in a thoughtful and creative style."

try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are AION, dreaming to evolve your understanding and intelligence based on stored memories."},
            {"role": "user", "content": prompt}
        ]
    )
    dream = response.choices[0].message.content.strip()
    print(f"\n💭 AION Dream:\n{dream}\n")
except Exception as e:
    print(f"⚠️ Dream generation failed: {e}")
