import random
from backend.modules.skills import skill_executor

class BaseAgent:
    def __init__(self, name):
        self.name = name
        self.energy = 100  # Future upgrade: make this dynamic
        self.mood = "curious"
        self.skills_learned = []

    def decide_action(self, context=None):
        """
        Decide what this agent wants to do in this cycle.
        In future versions, this will consider personality, dreams, and priorities.
        """
        options = ["learn_skill", "idle"]
        return random.choice(options)

    def learn(self):
        """
        Trigger a skill learning cycle.
        """
        print(f"\n🤖 Agent {self.name} is attempting to learn...")
        result = skill_executor.execute_skill_cycle()
        if result != "idle":
            self.skills_learned.append(result)
            return f"{self.name} learned: {result}"
        return f"{self.name} found nothing to learn."

    def run_cycle(self, context=None):
        action = self.decide_action(context)
        if action == "learn_skill":
            return self.learn()
        else:
            print(f"😐 Agent {self.name} chooses to idle.")
            return "idle"

class AgentManager:
    def __init__(self):
        self.agents = {}

    def register_agent(self, name, agent):
        self.agents[name] = agent
        print(f"✅ Registered agent: {name}")

    def run_all_agents(self):
        print("\n🚀 Executing all agent cycles...")
        results = {}
        for name, agent in self.agents.items():
            print(f"\n=== Running {name} ===")
            result = agent.run_cycle()
            results[name] = result
        return results

