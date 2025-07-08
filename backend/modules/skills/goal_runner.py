import os
import openai
from dotenv import load_dotenv
from pathlib import Path

from backend.modules.skills.goal_engine import GoalEngine
from backend.modules.skills.boot_loader import load_boot_goals
from backend.modules.hexcore.ai_wallet import AIWallet
from backend.modules.hexcore.memory_engine import MemoryEngine as MemoryCore
from backend.modules.consciousness.personality_engine import PersonalityProfile  # 🔁 Add this

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# Load env vars
env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(dotenv_path=env_path)

openai.api_key = os.getenv("OPENAI_API_KEY")

load_boot_goals()

class GoalRunner:
    def __init__(self):
        self.engine = GoalEngine()
        self.wallet = AIWallet()
        self.memory = MemoryCore()
        self.personality = PersonalityProfile()  # 🔁 Initialize personality

    def complete_goal(self, goal_name: str):
        goal = next((g for g in self.engine.get_active_goals() if g.get("name") == goal_name), None)
        if not goal:
            print(f"❌ Goal not found or already completed: {goal_name}")
            return

        prompt = f"Complete this task for AION:\n{goal['description']}\n\nRespond concisely and clearly."

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are AION, an AI learning to complete tasks to unlock skills and tokens."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            answer = response.choices[0].message.content.strip()
            print(f"\n🧠 GPT Response for '{goal_name}':\n{answer}\n")

            # Store answer in memory
            self.memory.store(f"goal:{goal_name}", answer)

            # Mark goal complete and earn tokens
            self.engine.mark_complete(goal_name)
            reward = goal.get("reward", 0)
            self.wallet.earn("STK", reward)
            self.wallet.save_wallet()

            print(f"✅ Goal '{goal_name}' marked complete. Earned {reward} $STK.")

            # 🔁 Adjust traits based on success
            self.personality.adjust_trait("ambition", 0.03)  # Pushes growth
            self.personality.adjust_trait("discipline", min(0.1, reward / 1000))  # Scale with reward

            self.show_wallet()

        except Exception as e:
            print(f"⚠️ Error completing goal: {e}")

    def show_wallet(self):
        balances = self.wallet.get_all_balances()
        print("💰 Current wallet balances:")
        if not balances:
            print("  (empty)")
        else:
            for token, amount in balances.items():
                print(f"  - {token}: {amount}")


if __name__ == "__main__":
    runner = GoalRunner()
    active_goals = runner.engine.get_active_goals()
    if not active_goals:
        print("🎉 No active goals available.")
    else:
        print("🎯 Boot Goals Ready:\n")
        for g in active_goals:
            print(f"- {g.get('name')}: {g.get('description')} (reward: {g.get('reward', 0)} STK)")

        goal_to_run = input("\nWhich goal should AION complete? Type exact name: ")
        runner.complete_goal(goal_to_run)