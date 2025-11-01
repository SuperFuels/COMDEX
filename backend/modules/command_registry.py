# ✅ AION Central Command Registry
# File: backend/modules/command_registry.py

from difflib import get_close_matches, SequenceMatcher
from typing import Optional, Dict, List, Tuple

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ------------------------------------------
# 🧠 Primary Command Definitions
# ------------------------------------------

COMMANDS: List[Dict] = [
    {
        "name": "run-learning-cycle",
        "description": "Run full memory -> dream -> goal -> skill cycle",
        "endpoint": "/api/aion/run-learning-cycle",
        "method": "POST",
        "aliases": ["learn", "cycle", "run-cycle"],
        "intent": "🧠 learning"
    },
    {
        "name": "run-dream",
        "description": "Trigger nightly dream reflection",
        "endpoint": "/api/aion/run-dream",
        "method": "POST",
        "aliases": ["dream", "reflect", "dream-reflect"],
        "intent": "🌙 dream"
    },
    {
        "name": "boot-skill",
        "description": "Boot the next queued skill from bootloader",
        "endpoint": "/api/aion/boot-skill",
        "method": "POST",
        "aliases": ["boot", "next-skill"],
        "intent": "🚀 boot"
    },
    {
        "name": "run-cycle",
        "description": "Run a full consciousness cycle (awareness, decision, action)",
        "endpoint": "/api/aion/run-cycle",
        "method": "POST",
        "aliases": ["cycle", "conscious-loop"],
        "intent": "♻️ loop"
    },
    {
        "name": "awareness",
        "description": "Check AION's awareness status",
        "endpoint": "/api/aion/awareness",
        "method": "GET",
        "aliases": ["status", "awareness-check"],
        "intent": "👁 awareness"
    },
    {
        "name": "identity",
        "description": "Get AION's current identity and personality",
        "endpoint": "/api/aion/identity",
        "method": "GET",
        "aliases": ["whoami", "self", "persona"],
        "intent": "🧬 identity"
    },
    {
        "name": "skill-reflect",
        "description": "Reflect on learned skills",
        "endpoint": "/api/aion/skill-reflect",
        "method": "POST",
        "aliases": ["skills", "reflect-skills"],
        "intent": "🧠 skill"
    },
    {
        "name": "goal",
        "description": "View current AION goals",
        "endpoint": "/api/aion/goal",
        "method": "GET",
        "aliases": ["goals", "target", "objectives"],
        "intent": "🎯 goal"
    },
    {
        "name": "status",
        "description": "Check AION system status",
        "endpoint": "/api/aion/status",
        "method": "GET",
        "aliases": ["system", "heartbeat"],
        "intent": "📟 status"
    },

    # 🪄 Stubbed Commands
    {
        "name": "show-boot-progress",
        "description": "View bootloader progress",
        "endpoint": "/api/aion/show-boot-progress",
        "method": "GET",
        "stub": True,
        "intent": "🧰 boot"
    },
    {
        "name": "sync-state",
        "description": "Synchronize AION state manager",
        "endpoint": "/api/aion/sync-state",
        "method": "POST",
        "stub": True,
        "intent": "🔄 sync"
    },
    {
        "name": "energy-check",
        "description": "Check current energy + compute budget",
        "endpoint": "/api/aion/energy-check",
        "method": "GET",
        "stub": True,
        "intent": "🔋 energy"
    },
    {
        "name": "show-dreams",
        "description": "Show recent dream logs",
        "endpoint": "/api/aion/show-dreams",
        "method": "GET",
        "stub": True,
        "intent": "🛌 dreams"
    }
]

# ------------------------------------------
# 🔍 Fuzzy + Alias Command Matching
# ------------------------------------------

def resolve_command(input_cmd: str) -> Optional[Dict]:
    """
    Fuzzy match a user command or alias to the closest valid command.
    Returns the command dict with optional match score.
    """
    input_cmd = input_cmd.strip().lower()

    all_matches = []
    for cmd in COMMANDS:
        all_names = [cmd["name"]] + cmd.get("aliases", [])
        for name in all_names:
            score = SequenceMatcher(None, input_cmd, name).ratio()
            all_matches.append((score, cmd))

    all_matches.sort(reverse=True, key=lambda x: x[0])
    best_score, best_cmd = all_matches[0] if all_matches else (0, None)

    if best_score >= 0.6:
        best_cmd["match_score"] = round(best_score, 3)
        return best_cmd
    return None

def list_commands() -> List[Dict]:
    """
    Return the full list of registered AION commands.
    """
    return COMMANDS