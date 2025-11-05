# backend/config_acl.py
import os
import re
from typing import List, Pattern, Tuple, Optional

# -----------------------------
# Env parsing & normalization
# -----------------------------
def _split_env(name: str) -> List[str]:
    raw = os.getenv(name, "") or ""
    # support comma or newline separated
    parts = []
    for line in raw.splitlines():
        parts.extend([s.strip() for s in line.split(",") if s.strip()])
    return parts

def _compile_regex(env_name: str) -> List[Pattern]:
    pats = []
    for s in _split_env(env_name):
        try:
            pats.append(re.compile(s))
        except re.error:
            # Don't explode on bad regex in prod; just ignore the pattern.
            pass
    return pats

ENV = (os.getenv("ENV", "development") or "development").strip().lower()
STRICT_PROD = os.getenv("GLYPHNET_STRICT_PROD_ACL", "0") == "1"

# Prefix lists (fast path)
ALLOW_PREFIX = _split_env("GLYPHNET_ALLOW_RECIPIENT_PREFIXES")  # e.g. "ucs://local/,ucs://wave.tp/"
DENY_PREFIX  = _split_env("GLYPHNET_DENY_RECIPIENT_PREFIXES")   # optional

# Optional regex lists (power users)
ALLOW_REGEX = _compile_regex("GLYPHNET_ALLOW_RECIPIENT_REGEX")  # e.g. "^ucs://wave\\.tp/.+$"
DENY_REGEX  = _compile_regex("GLYPHNET_DENY_RECIPIENT_REGEX")

# Dev defaults help you out-of-the-box
DEFAULT_DEV_ALLOW = ["ucs://local/", "gnet:ucs://local/"]

def _matches_prefix(s: str, prefixes: List[str]) -> Optional[str]:
    for p in prefixes:
        if s.startswith(p):
            return p
    return None

def _matches_regex(s: str, regex_list: List[Pattern]) -> Optional[str]:
    for r in regex_list:
        if r.search(s):
            return r.pattern
    return None

# -----------------------------
# Public API
# -----------------------------
def recipient_allowed(recipient: str) -> bool:
    """
    Hard rule: DENY takes priority (prefix or regex).
    In production: must match ALLOW (prefix or regex). Otherwise denied.
    In development: allowed unless explicitly denied; also allow sensible dev defaults.
    """
    if not isinstance(recipient, str) or not recipient:
        return False

    # --- DENY first ---
    if _matches_prefix(recipient, DENY_PREFIX) or _matches_regex(recipient, DENY_REGEX):
        return False

    is_prod = (ENV == "production")

    # --- ALLOW checks ---
    allowed = False
    if _matches_prefix(recipient, ALLOW_PREFIX) or _matches_regex(recipient, ALLOW_REGEX):
        allowed = True
    elif not is_prod:
        # Dev convenience: allow local topics unless explicitly denied
        if _matches_prefix(recipient, DEFAULT_DEV_ALLOW):
            allowed = True

    if is_prod:
        # In production you must be explicitly allowed
        if not allowed and STRICT_PROD:
            # Fail closed hard only if explicitly requested
            raise RuntimeError(
                "[ACL] Recipient denied and STRICT_PROD enabled. "
                "Set GLYPHNET_ALLOW_RECIPIENT_PREFIXES or GLYPHNET_ALLOW_RECIPIENT_REGEX."
            )
        return allowed
    else:
        # Development: allow unless denied
        return True if allowed or (not ALLOW_PREFIX and not ALLOW_REGEX) else allowed

def explain_recipient(recipient: str) -> Tuple[bool, str]:
    """
    Small helper for logs/tests: returns (allowed, reason).
    """
    if not isinstance(recipient, str) or not recipient:
        return False, "invalid"
    mp = _matches_prefix(recipient, DENY_PREFIX)
    if mp:
        return False, f"deny_prefix:{mp}"
    mr = _matches_regex(recipient, DENY_REGEX)
    if mr:
        return False, f"deny_regex:{mr}"

    is_prod = (ENV == "production")

    mp = _matches_prefix(recipient, ALLOW_PREFIX)
    if mp:
        return True, f"allow_prefix:{mp}"
    mr = _matches_regex(recipient, ALLOW_REGEX)
    if mr:
        return True, f"allow_regex:{mr}"

    if not is_prod and _matches_prefix(recipient, DEFAULT_DEV_ALLOW):
        return True, "dev_default"

    return (False, "no_allow_match") if is_prod else (True, "dev_fallback")

def dump_acl_config() -> dict:
    """Useful for startup logging."""
    return {
        "env": ENV,
        "strict_prod": STRICT_PROD,
        "allow_prefix": ALLOW_PREFIX,
        "deny_prefix": DENY_PREFIX,
        "allow_regex": [r.pattern for r in ALLOW_REGEX],
        "deny_regex": [r.pattern for r in DENY_REGEX],
        "dev_defaults": DEFAULT_DEV_ALLOW,
    }