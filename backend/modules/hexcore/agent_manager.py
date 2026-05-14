import random
import os
import importlib.util
from backend.modules.skills import skill_executor
from backend.modules.aion.sample_agent import SampleAgent
from backend.modules.dna_chain.switchboard import DNA_SWITCH

# ✅ DNA Switch Registration
DNA_SWITCH.register(__file__)

AGENT_DIR = "backend/modules/aion/agents"

class BaseAgent:
    def __init__(self, name):
        self.name = name
        self.energy = 100
        self.mood = "curious"
        self.skills_learned = []

    def decide_action(self, context=None):
        options = ["learn_skill", "idle"]
        return random.choice(options)

    def learn(self):
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

    def create_sample_agent(self, name):
        agent = SampleAgent(name)
        self.register_agent(name, agent)
        return agent

    def spawn_agent_from_file(self, name):
        file_path = os.path.join(AGENT_DIR, f"{name}.py")
        if not os.path.exists(file_path):
            print(f"⚠️ No custom agent file found for: {name}, using sample agent.")
            return self.create_sample_agent(name)

        spec = importlib.util.spec_from_file_location(name, file_path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            AgentClass = getattr(module, "Agent", None)
            if AgentClass:
                agent_instance = AgentClass(name)
                self.register_agent(name, agent_instance)
                return agent_instance
            else:
                print(f"⚠️ No 'Agent' class found in {file_path}, using sample.")
                return self.create_sample_agent(name)
        except Exception as e:
            print(f"❌ Failed to load agent from {file_path}: {e}")
            return self.create_sample_agent(name)

    def run_all_agents(self):
        print("\n🚀 Executing all agent cycles...")
        results = {}
        for name, agent in self.agents.items():
            print(f"\n=== Running {name} ===")
            result = agent.run_cycle()
            results[name] = result
        return results