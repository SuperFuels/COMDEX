# backend/modules/glyphcore/action_policy_map.py

"""
Defines action → policy mappings for GlyphCore enforcement.

Each action can specify:
- require_qkd: whether QKD is mandatory
- require_auth: whether authenticated user context is required
- require_entropy: whether entropy tracking is required
"""

ACTION_POLICY_MAP = {
    "collapse": {
        "require_qkd": True,
        "require_auth": True,
        "require_entropy": True,
    },
    "teleport": {
        "require_qkd": True,
        "require_auth": True,
        "require_entropy": False,
    },
    "mutate": {
        "require_qkd": False,
        "require_auth": True,
        "require_entropy": True,
    },
    "observe": {
        "require_qkd": False,
        "require_auth": False,
        "require_entropy": False,
    },
    "entangle": {
        "require_qkd": True,
        "require_auth": True,
        "require_entropy": True,
    },
    # Add more as needed
}


def get_action_policy(action: str) -> dict:
    """
    Returns the policy dict for the given action.
    Defaults to all False if undefined.
    """
    return ACTION_POLICY_MAP.get(action, {
        "require_qkd": False,
        "require_auth": False,
        "require_entropy": False,
    })