# File: backend/modules/glyphnet/agent_identity_registry.py
"""
📇 Agent Identity Registry
Stores active agent identities, colors, tokens, and permissions
for multi-agent KG collaboration.
"""

from __future__ import annotations

import os
import uuid
import logging
import threading
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

ENV = os.getenv("ENV", "development").lower()
ALLOW_DEV_TOKEN = os.getenv("GLYPHNET_ALLOW_DEV_TOKEN", "0").strip() not in ("", "0", "false", "False")
DEV_TOKEN_VALUE = os.getenv("GLYPHNET_DEV_TOKEN", "dev-token")

def _tok_disp(t: str) -> str:
    return (t[:6] + "…") if isinstance(t, str) and len(t) > 6 else (t or "<none>")

class AgentIdentityRegistry:
    def __init__(self):
        self.agents: Dict[str, Dict] = {}      # agent_id -> agent dict
        self.token_map: Dict[str, str] = {}    # token -> agent_id
        self._lock = threading.RLock()

        # Optional: pre-register a dev agent so /ws-test etc. work immediately
        if ALLOW_DEV_TOKEN:
            self.ensure_agent(
                name="dev",
                public_key="dev",
                color="#9CA3AF",
                token=DEV_TOKEN_VALUE,
                permissions=["kg_edit", "predict_fork", "entangle", "replay_view"],
            )
            logger.info("[AgentRegistry] Dev token enabled (%s)", _tok_disp(DEV_TOKEN_VALUE))

    # ---------- Registration ----------
    def register_agent(
        self,
        name: str,
        public_key: str,
        color: str | None = None,
        token: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ) -> str:
        with self._lock:
            agent_id = str(uuid.uuid4())
            assigned_token = token or str(uuid.uuid4())
            # avoid token collision
            while assigned_token in self.token_map:
                assigned_token = str(uuid.uuid4())

            self.agents[agent_id] = {
                "name": name,
                "public_key": public_key,
                "color": color or self._assign_color_unlocked(),
                "permissions": permissions or ["kg_edit", "predict_fork", "entangle", "replay_view"],
                "token": assigned_token,
            }
            self.token_map[assigned_token] = agent_id
            logger.info("[AgentRegistry] Registered agent %s (%s)", name, agent_id)
            return agent_id

    def ensure_agent(
        self,
        name: str,
        public_key: str,
        color: str | None = None,
        token: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ) -> str:
        """Idempotent: return existing agent with same name or register a new one."""
        with self._lock:
            existing = self.get_agent_by_name(name)
            if existing:
                return next((aid for aid, a in self.agents.items() if a is existing), self.register_agent(
                    name, public_key, color, token, permissions
                ))
            return self.register_agent(name, public_key, color, token, permissions)

    def unregister_agent(self, agent_id: str) -> bool:
        with self._lock:
            agent = self.agents.pop(agent_id, None)
            if not agent:
                return False
            tok = agent.get("token")
            if tok and self.token_map.get(tok) == agent_id:
                self.token_map.pop(tok, None)
            logger.info("[AgentRegistry] Unregistered agent %s", agent_id)
            return True

    def rotate_token(self, agent_id: str) -> str:
        with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                raise KeyError(f"Unknown agent_id: {agent_id}")
            old = agent.get("token")
            if old:
                self.token_map.pop(old, None)
            new_tok = str(uuid.uuid4())
            while new_tok in self.token_map:
                new_tok = str(uuid.uuid4())
            agent["token"] = new_tok
            self.token_map[new_tok] = agent_id
            logger.info("[AgentRegistry] Rotated token for %s (was %s)", agent_id, _tok_disp(old or ""))
            return new_tok

    # ---------- Color ----------
    def _assign_color_unlocked(self) -> str:
        palette = ["#FF6B6B", "#4ECDC4", "#FFD93D", "#6A4C93", "#00B4D8"]
        used = [agent.get("color") for agent in self.agents.values()]
        for color in palette:
            if color not in used:
                return color
        return "#CCCCCC"

    # ---------- Lookups ----------
    def get_agent(self, agent_id: str) -> Optional[Dict]:
        with self._lock:
            return self.agents.get(agent_id)

    def get_agent_by_name(self, name: str) -> Optional[Dict]:
        with self._lock:
            for agent in self.agents.values():
                if agent.get("name") == name:
                    return agent
            return None

    def all_agents(self) -> Dict[str, Dict]:
        with self._lock:
            return dict(self.agents)

    def resolve_agent_id(self, token: str) -> Optional[str]:
        """Return agent_id for token, honoring dev-token override if enabled."""
        if not token:
            return None
        if ALLOW_DEV_TOKEN and token == DEV_TOKEN_VALUE:
            # Prefer actual registered dev agent if present
            with self._lock:
                aid = self.token_map.get(token)
                if aid:
                    return aid
            return "dev"
        with self._lock:
            return self.token_map.get(token)

    # ---------- Permissions ----------
    def has_permission(self, agent_id: str, permission: str) -> bool:
        with self._lock:
            agent = self.agents.get(agent_id)
            return permission in agent.get("permissions", []) if agent else False

    def assign_permission(self, agent_id: str, permission: str):
        with self._lock:
            agent = self.agents.get(agent_id)
            if agent and permission not in agent.setdefault("permissions", []):
                agent["permissions"].append(permission)

    def revoke_permission(self, agent_id: str, permission: str):
        with self._lock:
            agent = self.agents.get(agent_id)
            if agent and permission in agent.get("permissions", []):
                agent["permissions"].remove(permission)

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
        """Return lightweight permission state for WebSocket sync."""
        with self._lock:
            agent = self.agents.get(agent_id)
            if not agent:
                return {}
            return {
                "agent_id": agent_id,
                "permissions": list(agent.get("permissions", [])),
                "color": agent.get("color"),
                "name": agent.get("name"),
            }

    # ---------- Tokens ----------
    def validate_token(self, token: str) -> bool:
        """
        Validate whether a token maps to a registered agent.
        Honors dev-token override if GLYPHNET_ALLOW_DEV_TOKEN is set.
        """
        if not token:
            return False
        if ALLOW_DEV_TOKEN and token == DEV_TOKEN_VALUE:
            return True
        with self._lock:
            ok = token in self.token_map
        if not ok:
            logger.warning("[AgentRegistry] Unauthorized token %s", _tok_disp(token))
        return ok


# Singleton instance
agent_identity_registry = AgentIdentityRegistry()

# ✅ Shim function so external imports keep working
def validate_agent_token(token: str) -> bool:
    return agent_identity_registry.validate_token(token)