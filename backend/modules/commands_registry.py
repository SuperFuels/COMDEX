# ✅ STEP 1: Central Command Registry (Python)
# File: backend/modules/command_registry.py

COMMANDS = [
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

# -------------------------
# 🔍 Fuzzy Matching Utility
# -------------------------

from difflib import get_close_matches

def resolve_command(input_cmd: str):
    names = [cmd['name'] for cmd in COMMANDS]
    match = get_close_matches(input_cmd, names, n=1, cutoff=0.6)
    if match:
        return next((cmd for cmd in COMMANDS if cmd['name'] == match[0]), None)
    return None

def list_commands():
    return COMMANDS