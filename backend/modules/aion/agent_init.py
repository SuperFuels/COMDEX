from backend.modules.hexcore.agent_manager import AgentManager
from backend.modules.aion.sample_agent import SampleAgent

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

def init_agents():
    manager = AgentManager()
    manager.register_agent("AION", SampleAgent("AION"))
    manager.register_agent("Explorer", SampleAgent("Explorer"))
    return manager
