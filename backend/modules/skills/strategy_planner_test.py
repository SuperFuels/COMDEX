from backend.modules.skills.strategy_planner import StrategyPlanner

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

planner = StrategyPlanner()
planner.generate()
planner.view()
