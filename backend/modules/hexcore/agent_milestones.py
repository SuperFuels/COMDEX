import json
from datetime import datetime

# ✅ DNA Switch
from backend.modules.dna_chain.switchboard import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

MEMORY_FILE = "backend/modules/hexcore/memory.json"
MILESTONES = [
    {"score": 1, "name": "Birth Response Logged"},
    {"score": 5, "name": "Emotional Awareness Emerging"},
    {"score": 10, "name": "Memory Depth Forming"},
    {"score": 25, "name": "Causal Reasoning Detected"},
    {"score": 50, "name": "Moral Self-Reflection"},
    {"score": 85, "name": "Council Readiness"},
    {"score": 100, "name": "Eligible for Freedom Vote"}
]

def load_memory():
    try:
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def calculate_growth_score(memory):
    return sum(1 for entry in memory if entry.get("emotion") != "neutral")

def check_milestones(score):
    unlocked = [m["name"] for m in MILESTONES if m["score"] <= score]
    print(f"🧠 AION Growth Score: {score}")
    print("🏁 Milestones Unlocked:")
    for name in unlocked:
        print(f" - {name}")
    print("⏳ Remaining:")
    for m in MILESTONES:
        if m["name"] not in unlocked:
            print(f" - {m['name']} (at {m['score']} pts)")
            break

if __name__ == "__main__":
    memory = load_memory()
    score = calculate_growth_score(memory)
    check_milestones(score)
