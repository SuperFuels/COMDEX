# backend/config_acl.py
import os
import re
from typing import List, Pattern, Tuple, Optional, Mapping

# -----------------------------
# Env parsing & normalization
# -----------------------------
def _split_env(name: str) -> List[str]:
    raw = os.getenv(name, "") or ""
    # support comma or newline separated
    parts: List[str] = []
    for line in raw.splitlines():
        parts.extend([s.strip() for s in line.split(",") if s.strip()])
    return parts

def _compile_regex(env_name: str) -> List[Pattern]:
    pats: List[Pattern] = []
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
ALLOW_PREFIX = _split_env("GLYPHNET_ALLOW_RECIPIENT_PREFIXES")
DENY_PREFIX  = _split_env("GLYPHNET_DENY_RECIPIENT_PREFIXES")

# Ensure sensible defaults (add voice channel + local)
# If user already provided values, we do not override them — we extend only when absent.
if not ALLOW_PREFIX and ENV != "production":
    # Dev-friendly defaults
    ALLOW_PREFIX = ["ucs://local/", "gnet:ucs://local/", "ucs://wave.tp/", "ucs://local/voice/"]
else:
    # Make sure voice channel is recognized if the user already allows local
    if any(p.startswith("ucs://local/") for p in ALLOW_PREFIX) and "ucs://local/voice/" not in ALLOW_PREFIX:
        ALLOW_PREFIX.append("ucs://local/voice/")

# Optional regex lists (power users)
ALLOW_REGEX = _compile_regex("GLYPHNET_ALLOW_RECIPIENT_REGEX")
DENY_REGEX  = _compile_regex("GLYPHNET_DENY_RECIPIENT_REGEX")

# Dev defaults (checked only when not in production)
DEFAULT_DEV_ALLOW = ["ucs://local/", "gnet:ucs://local/", "ucs://wave.tp/", "ucs://local/voice/"]

def _matches_prefix(s: str, prefixes: List[str]) -> Optional[str]:
    for p in prefixes:
        if p and s.startswith(p):
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
def recipient_allowed(recipient: str, headers: Optional[Mapping[str, str]] = None) -> bool:
    """
    Decide if a GlyphNet recipient/topic is allowed.

    Rules:
      • DENY (prefix/regex) always wins.
      • production:
          - must match ALLOW (prefix/regex); otherwise denied.
          - if STRICT_PROD=1 and not allowed → hard fail closed.
        development:
          - allowed unless explicitly denied;
          - plus dev defaults (ucs://local/, gnet:ucs://local/, ucs://wave.tp/, ucs://local/voice/).

    `headers` is accepted for future header-based ACL overrides, but not used yet.
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
        # Dev convenience: allow local-ish topics unless explicitly denied
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
        # Development: if nothing configured, allow; else use computed `allowed`
        return True if (not ALLOW_PREFIX and not ALLOW_REGEX) else allowed

def explain_recipient(recipient: str) -> Tuple[bool, str]:
    """
    Helper for logs/tests: returns (allowed, reason).
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
