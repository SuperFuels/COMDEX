# File: backend/modules/codex/codex_context_tools.py

from typing import Optional, Dict, Any


class CodexContext:
    """
    Execution context for CodexLang commands.

    This can hold:
    - user/session metadata
    - container ID / file location
    - mutation flags
    - runtime memory reference
    - scoped variable bindings
    - WebSocket or feedback emitters (optional)
    """

    def __init__(self,
                 container_id: Optional[str] = None,
                 user_id: Optional[str] = None,
                 memory: Optional[Dict[str, Any]] = None,
                 variables: Optional[Dict[str, Any]] = None,
                 flags: Optional[Dict[str, bool]] = None):
        self.container_id = container_id
        self.user_id = user_id
        self.memory = memory or {}
        self.variables = variables or {}
        self.flags = flags or {}

    def get_var(self, name: str) -> Any:
        return self.variables.get(name)

    def set_var(self, name: str, value: Any):
        self.variables[name] = value

    def has_flag(self, flag: str) -> bool:
        return self.flags.get(flag, False)

    def set_flag(self, flag: str, value: bool = True):
        self.flags[flag] = value

    def __repr__(self):
        return f"<CodexContext container={self.container_id} user={self.user_id} vars={list(self.variables.keys())}>"