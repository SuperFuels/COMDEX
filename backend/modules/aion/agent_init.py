from modules.hexcore.agent_manager import AgentManager
from modules.aion.sample_agent import SampleAgent

def init_agents():
    manager = AgentManager()
    manager.register_agent("AION", SampleAgent("AION"))
    manager.register_agent("Explorer", SampleAgent("Explorer"))
    return manager
