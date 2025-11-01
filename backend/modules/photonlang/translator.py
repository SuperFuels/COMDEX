"""
translator.py - MVP glyph->python expander used by the import hook.

Design constraints (for now):
- .photon files may freely use the glyph-ops in FUNCTION FORM ONLY:
    ⊕(a, b)   ↔(a, b)   ⟲(f, n)   μ(x)   π(seq, n)
- We'll translate these into: __OPS__["⊕"](...), etc.
- We DO NOT parse infix glyphs yet (e.g., a ⊕ b) - keep MVP simple & robust.
- We inject: from backend.symatics.operators import OPS as __OPS__
"""

import re
from typing import Optional

OPS_MAP = ["⊕","↔","⟲","μ","π"]  # extend later

CALL_PAT = re.compile(r"(?P<op>[⊕↔⟲μπ])\s*\(")  # op(...)

def _rewrite_calls(text: str) -> str:
    # Replace each ⊕(  ->  __OPS__["⊕"](
    def repl(m):
        op = m.group("op")
        return f'__OPS__["{op}"]('
    return CALL_PAT.sub(repl, text)

def expand(src: str, module_name: str = "", source_path: str = "") -> str:
    # Inject import once at top unless already present
    prolog = 'from backend.symatics.operators import OPS as __OPS__\n'
    body = _rewrite_calls(src)
    # If the source already imports __OPS__, don't double-insert
    if "__OPS__" in src:
        return body
    return prolog + body