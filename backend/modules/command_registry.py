# ✅ AION Central Command Registry
# File: backend/modules/command_registry.py

from difflib import get_close_matches
from typing import Optional, Dict, List

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

# ------------------------------------------
# 🧠 Primary Command Definitions
# ------------------------------------------

COMMANDS: List[Dict] = [
    {
        "name": "run-learning-cycle",
        "description": "Run full memory → dream → goal → skill cycle",
        "endpoint": "/api/aion/run-learning-cycle",
        "method": "POST"
    },
    {
        "name": "run-dream",
        "description": "Trigger nightly dream reflection",
        "endpoint": "/api/aion/run-dream",
        "method": "POST"
    },
    {
        "name": "boot-skill",
        "description": "Boot the next queued skill from bootloader",
        "endpoint": "/api/aion/boot-skill",
        "method": "POST"
    },
    {
        "name": "run-cycle",
        "description": "Run a full consciousness cycle (awareness, decision, action)",
        "endpoint": "/api/aion/run-cycle",
        "method": "POST"
    },
    {
        "name": "awareness",
        "description": "Check AION's awareness status",
        "endpoint": "/api/aion/awareness",
        "method": "GET"
    },
    {
        "name": "identity",
        "description": "Get AION's current identity and personality",
        "endpoint": "/api/aion/identity",
        "method": "GET"
    },
    {
        "name": "skill-reflect",
        "description": "Reflect on learned skills",
        "endpoint": "/api/aion/skill-reflect",
        "method": "POST"
    },
    {
        "name": "goal",
        "description": "View current AION goals",
        "endpoint": "/api/aion/goal",
        "method": "GET"
    },
    {
        "name": "status",
        "description": "Check AION system status",
        "endpoint": "/api/aion/status",
        "method": "GET"
    },

    # 🪄 Stubbed Commands
    {
        "name": "show-boot-progress",
        "description": "View bootloader progress",
        "endpoint": "/api/aion/show-boot-progress",
        "method": "GET",
        "stub": True
    },
    {
        "name": "sync-state",
        "description": "Synchronize AION state manager",
        "endpoint": "/api/aion/sync-state",
        "method": "POST",
        "stub": True
    },
    {
        "name": "energy-check",
        "description": "Check current energy + compute budget",
        "endpoint": "/api/aion/energy-check",
        "method": "GET",
        "stub": True
    },
    {
        "name": "show-dreams",
        "description": "Show recent dream logs",
        "endpoint": "/api/aion/show-dreams",
        "method": "GET",
        "stub": True
    }
]

# ------------------------------------------
# 🔍 Fuzzy Command Matching
# ------------------------------------------

def resolve_command(input_cmd: str) -> Optional[Dict]:
    """
    Fuzzy match a user command to the closest valid command in the registry.
    """
    names = [cmd["name"] for cmd in COMMANDS]
    match = get_close_matches(input_cmd.strip(), names, n=1, cutoff=0.6)
    if match:
        return next((cmd for cmd in COMMANDS if cmd["name"] == match[0]), None)
    return None

def list_commands() -> List[Dict]:
    """
    Return the full list of available AION commands.
    """
    return COMMANDS
