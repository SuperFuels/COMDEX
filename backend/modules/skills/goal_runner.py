import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.skills.boot_loader import load_boot_goals
from backend.modules.hexcore.ai_wallet import AIWallet
from backend.modules.hexcore.memory_core import MemoryCore

# ✅ Load .env.local from project root
env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(dotenv_path=env_path)

# ✅ Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Load boot goals if none exist
load_boot_goals()

class GoalRunner:
    def __init__(self):
        self.engine = GoalEngine()
        self.wallet = AIWallet()
        self.memory = MemoryCore()

    def complete_goal(self, goal_name):
        goal = next((g for g in self.engine.get_active_goals() if g["name"] == goal_name), None)
        if not goal:
            print(f"❌ Goal not found or already completed: {goal_name}")
            return

        prompt = f"Complete this task for AION:\n{goal['description']}\n\nRespond concisely and clearly."

        try:
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are AION, an AI learning to complete tasks to unlock skills and tokens."},
                    {"role": "user", "content": prompt}
                ]
            )
            answer = response.choices[0].message.content.strip()
            print(f"\n🧠 GPT Response for '{goal_name}':\n{answer}\n")

            # ✅ Store the answer in memory
            self.memory.store(f"goal:{goal_name}", answer)

            # ✅ Mark complete and award STK
            self.engine.mark_complete(goal_name)
            self.wallet.earn("STK", goal["reward"])
            self.wallet.save_wallet()

            print(f"✅ Goal '{goal_name}' marked complete. Earned {goal['reward']} $STK.")
        except Exception as e:
            print(f"⚠️ Error completing goal: {e}")

if __name__ == "__main__":
    runner = GoalRunner()
    print("🎯 Boot Goals Ready:\n")
    for g in runner.engine.get_active_goals():
        print(f"- {g['name']}: {g['description']} (reward: {g['reward']} STK)")

    goal_to_run = input("\nWhich goal should AION complete? Type exact name: ")
    runner.complete_goal(goal_to_run)
