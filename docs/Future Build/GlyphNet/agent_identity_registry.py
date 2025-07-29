"""
📇 Agent Identity Registry
Stores active agent identities, colors, and permissions for multi-agent KG collaboration.
"""

import uuid
from typing import Dict, Optional, List


class AgentIdentityRegistry:
    def __init__(self):
        self.agents: Dict[str, Dict] = {}

    def register_agent(self, name: str, public_key: str, color: str = None) -> str:
        agent_id = str(uuid.uuid4())
        self.agents[agent_id] = {
            "name": name,
            "public_key": public_key,
            "color": color or self._assign_color(),
            "permissions": ["kg_edit", "predict_fork", "entangle", "replay_view"],  # default perms
        }
        return agent_id

    def _assign_color(self) -> str:
        # Simple pool of colors for visualization
        palette = ["#FF6B6B", "#4ECDC4", "#FFD93D", "#6A4C93", "#00B4D8"]
        used = [agent["color"] for agent in self.agents.values()]
        for color in palette:
            if color not in used:
                return color
        return "#CCCCCC"

    def get_agent(self, agent_id: str) -> Optional[Dict]:
        return self.agents.get(agent_id)

    def get_agent_by_name(self, name: str) -> Optional[Dict]:
        for agent in self.agents.values():
            if agent["name"] == name:
                return agent
        return None

    def all_agents(self) -> Dict[str, Dict]:
        return self.agents

    def has_permission(self, agent_id: str, permission: str) -> bool:
        agent = self.agents.get(agent_id)
        return permission in agent.get("permissions", []) if agent else False

    def assign_permission(self, agent_id: str, permission: str):
        if agent_id in self.agents:
            if permission not in self.agents[agent_id]["permissions"]:
                self.agents[agent_id]["permissions"].append(permission)

    def revoke_permission(self, agent_id: str, permission: str):
        if agent_id in self.agents:
            if permission in self.agents[agent_id]["permissions"]:
                self.agents[agent_id]["permissions"].remove(permission)

    def can_view_glyph(self, agent_id: str, glyph_meta: Dict) -> bool:
        """
        Determine if an agent can view a glyph in replay context.
        - Owners always can.
        - 'system' agents bypass restrictions.
        - Private glyphs require ownership or explicit replay_view permission.
        """
        owner = glyph_meta.get("agent_id", "system")
        private = glyph_meta.get("private", False)

        if agent_id == owner or agent_id == "system":
            return True
        if private:
            return self.has_permission(agent_id, "replay_view")
        return True

    def permission_state(self, agent_id: str) -> Dict:
        """
        Return lightweight permission state for WebSocket sync.
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return {}
        return {
            "agent_id": agent_id,
            "permissions": agent["permissions"],
            "color": agent["color"],
            "name": agent["name"],
        }


# Singleton instance
agent_identity_registry = AgentIdentityRegistry()