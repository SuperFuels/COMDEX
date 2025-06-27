import os
import openai
from dotenv import load_dotenv
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.hexcore.milestone_tracker import MilestoneTracker

# Load the .env file explicitly
load_dotenv(dotenv_path=".env")

# Initialize OpenAI client with key from environment
openai.api_key = os.getenv("OPENAI_API_KEY")

class MemoryReflector:
    def __init__(self):
        self.memory = MemoryEngine()
        self.milestones = MilestoneTracker()

    def reflect(self):
        if not self.milestones.is_unlocked("memory_access"):
            print("❌ AION does not have memory access unlocked.")
            return

        memories = self.memory.get_all()
        if not memories:
            print("🧠 No memories to reflect on.")
            return

        compiled = "\n".join([f"- {m['label']}: {m['content']}" for m in memories])

        prompt = f"AION, reflect on your current memories below and summarize your understanding or learning progress:\n\n{compiled}"

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are AION, an evolving AI using memory to improve."},
                    {"role": "user", "content": prompt}
                ]
            )
            output = response.choices[0].message.content.strip()
            print("\n💭 AION Reflection:\n" + output)
            self.milestones.unlock("memory_access")  # Unlock milestone after success
        except Exception as e:
            print(f"⚠️ Error during reflection: {e}")

if __name__ == "__main__":
    MemoryReflector().reflect()