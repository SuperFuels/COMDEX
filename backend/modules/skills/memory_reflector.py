import os
import json
import openai
from datetime import datetime
from dotenv import load_dotenv
from backend.modules.hexcore.memory_engine import MemoryEngine
from backend.modules.skills.milestone_goal_integration import tracker  # Use wired-up tracker instance
from backend.modules.skills.strategy_planner import StrategyPlanner

# Load environment variables from .env file
load_dotenv(dotenv_path=".env")
openai.api_key = os.getenv("OPENAI_API_KEY")

class MemoryReflector:
    def __init__(self):
        self.memory = MemoryEngine()
        self.milestones = tracker  # Shared milestone tracker with goal creation callback
        self.strategy_planner = StrategyPlanner()

    def reflect(self):
        # Check if memory access milestone unlocked
        if not self.milestones.is_unlocked("memory_access"):
            print("❌ AION does not have memory access unlocked.")
            return

        memories = self.memory.get_all()
        if not memories:
            print("🧠 No memories to reflect on.")
            return

        # Take last 10 memories to avoid too long prompt
        recent_memories = memories[-10:]
        compiled = "\n".join([f"- {m['label']}: {m['content']}" for m in recent_memories])

        prompt = (
            "AION, reflect on your current memories below and:\n"
            "1. Summarize your understanding or learning progress.\n"
            "2. Identify any new milestones with short descriptions.\n"
            "3. Suggest actionable strategies related to these milestones.\n\n"
            f"Memories:\n{compiled}\n\n"
            "Respond ONLY with a valid JSON object with keys: 'summary', 'milestones', 'strategies'.\n"
            "Example:\n"
            "{\n"
            "  \"summary\": \"...\",\n"
            "  \"milestones\": [{\"name\": \"milestone_name\", \"description\": \"desc\"}],\n"
            "  \"strategies\": [{\"goal\": \"goal_name\", \"action\": \"action_desc\"}]\n"
            "}\n"
        )

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are AION, an evolving AI using memory to improve."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )

            output = response.choices[0].message["content"].strip()
            print("\n💭 AION Reflection Output:\n" + output)

            data = json.loads(output)

            # Save summary to memory if present
            summary = data.get("summary", "")
            if summary:
                self.memory.save(label="reflection_summary", content=summary)

            # Add new milestones from reflection to milestone tracker
            for milestone in data.get("milestones", []):
                name = milestone.get("name")
                desc = milestone.get("description", "")
                if name:
                    print(f"🔍 Adding milestone from reflection: {name}")
                    self.milestones.add_milestone(name, source="reflection", excerpt=desc)

            # Add new strategies to strategy planner
            for strat in data.get("strategies", []):
                goal = strat.get("goal")
                action = strat.get("action")
                if goal and action:
                    print(f"📋 Adding strategy from reflection: {goal}")
                    self.strategy_planner.strategies.append({
                        "goal": goal,
                        "action": action,
                        "timestamp": datetime.now().isoformat()
                    })

            self.strategy_planner.save()

        except json.JSONDecodeError:
            print("⚠️ Failed to parse reflection JSON output.")
        except Exception as e:
            print(f"⚠️ Error during reflection: {e}")

if __name__ == "__main__":
    MemoryReflector().reflect()