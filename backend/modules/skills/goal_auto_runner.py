import os
from pathlib import Path
from dotenv import load_dotenv
import openai

from modules.skills.goal_engine import GoalEngine
from modules.skills.boot_loader import load_boot_goals
from modules.hexcore.ai_wallet import AIWallet

# Load environment variables from .env.local if present
env_path = Path(__file__).resolve().parents[3] / ".env.local"
load_dotenv(dotenv_path=env_path)

# Set OpenAI API key for new SDK style
openai.api_key = os.getenv("OPENAI_API_KEY")

load_boot_goals()

class AutoGoalRunner:
    def __init__(self):
        self.engine = GoalEngine()
        self.wallet = AIWallet()

    def pick_best_goal(self):
        active = self.engine.get_active_goals()
        return max(active, key=lambda g: g["reward"], default=None)

    def run(self):
        goal = self.pick_best_goal()
        if not goal:
            print("🎉 All goals complete!")
            return

        prompt = f"Complete this task for AION:\n{goal['description']}\n\nRespond concisely and clearly."

        try:
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are AION, an AI learning to complete tasks to unlock skills and tokens."},
                    {"role": "user", "content": prompt}
                ]
            )
            answer = response.choices[0].message.content.strip()
            print(f"\n🧠 GPT Response for '{goal['name']}':\n{answer}\n")

            self.engine.mark_complete(goal["name"])
            self.wallet.earn("STK", goal["reward"])
            self.wallet.save_wallet()
            print(f"✅ Goal '{goal['name']}' complete. Earned {goal['reward']} $STK.")

        except Exception as e:
            print(f"⚠️ Error: {e}")

if __name__ == "__main__":
    AutoGoalRunner().run()