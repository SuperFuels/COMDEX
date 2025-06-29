from typing import List, Dict
import json
import os

DOMAIN_GOALS_PATH = "backend/data/domain_goals.json"

# Sample structure
DEFAULT_DOMAIN_GOALS = {
    "Crypto": [
        {"goal_id": "C1", "description": "Understand smart contracts", "status": "pending"},
        {"goal_id": "C2", "description": "Master Solidity", "status": "pending"},
        {"goal_id": "C3", "description": "Deploy a DeFi protocol", "status": "pending"}
    ],
    "Art": [
        {"goal_id": "A1", "description": "Learn digital color theory", "status": "pending"},
        {"goal_id": "A2", "description": "Create AI-generated artwork", "status": "pending"}
    ],
    "Science": [
        {"goal_id": "S1", "description": "Understand Newtonian mechanics", "status": "pending"},
        {"goal_id": "S2", "description": "Explore quantum concepts", "status": "pending"}
    ]
}

def load_domain_goals() -> Dict[str, List[Dict]]:
    if not os.path.exists(DOMAIN_GOALS_PATH):
        with open(DOMAIN_GOALS_PATH, "w") as f:
            json.dump(DEFAULT_DOMAIN_GOALS, f, indent=2)
    with open(DOMAIN_GOALS_PATH, "r") as f:
        return json.load(f)

def save_domain_goals(goals: Dict[str, List[Dict]]):
    with open(DOMAIN_GOALS_PATH, "w") as f:
        json.dump(goals, f, indent=2)

def update_goal_status(domain: str, goal_id: str, new_status: str):
    goals = load_domain_goals()
    if domain in goals:
        for goal in goals[domain]:
            if goal["goal_id"] == goal_id:
                goal["status"] = new_status
    save_domain_goals(goals)

def get_pending_goals(domain: str = None) -> List[Dict]:
    goals = load_domain_goals()
    pending = []
    for d, items in goals.items():
        if domain is None or domain == d:
            for goal in items:
                if goal["status"] == "pending":
                    pending.append(goal)
    return pending
