# --- Host import syntax -------------------------------------------------
# Accepts either:
#   "host:python:photon_lib.demo"
# or
#   {"host": "python", "module": "photon_lib.demo", "as": "demo"}

import re
from typing import Optional, Dict, Any

_HOST_IMPORT_STR_RE = re.compile(
    r"^host:(?P<host>[a-z][\w-]*):(?P<module>[A-Za-z_][\w\.]*)$"
)

from typing import Any, Dict, Optional

def normalize_host_import(entry: Any) -> Optional[Dict[str, str]]:
    """
    Normalize a host import entry into a dict:
      {"host": "python", "module": "a.b.c"} or with alias {"as": "alias"}.

    Accepts ONLY the 'python' host. Returns None for anything else.
    Supported forms:
      - "host:python:a.b.c"
      - {"host":"python","module":"a.b.c"} (+ optional {"as":"alias"})
    """
    # String form: "host:python:a.b.c"
    if isinstance(entry, str):
        if not entry.startswith("host:"):
            return None
        parts = entry.split(":")
        if len(parts) != 3:
            return None
        _, host, module = parts
        host = host.strip()
        module = module.strip()
        if host != "python" or not module or any(ch.isspace() for ch in module):
            return None
        return {"host": "python", "module": module}

    # Object form: {"host":"python","module":"a.b.c", "as":"alias"?}
    if isinstance(entry, dict):
        host = entry.get("host")
        module = entry.get("module")
        alias = entry.get("as")
        if host != "python" or not isinstance(module, str) or not module.strip():
            return None
        out = {"host": "python", "module": module.strip()}
        if isinstance(alias, str) and alias.strip():
            out["as"] = alias.strip()
        return out

    return None