# backend/modules/fail_closed_guard.py

"""
Fail-Closed Guard - GlyphWave Security Phase E03c
Immediately blocks execution of toxic glyphs or kernel logic under SoulLaw.
"""

from backend.modules.soullaw.sandbox_kernel_guard import scan_for_toxic_logic
from backend.modules.codex.collapse_trace_exporter import log_soullaw_event

FAIL_CLOSED_ENABLED = True

class FailClosedViolation(Exception):
    def __init__(self, violations, context=None):
        super().__init__("Fail-Closed mode triggered due to SoulLaw violations.")
        self.violations = violations
        self.context = context or {}

def enforce_fail_closed(kernel_code: str, context: dict = None):
    """
    Scans kernel code for SoulLaw violations and halts execution if any are found.
    Raises FailClosedViolation if unsafe code is detected.
    """
    if not FAIL_CLOSED_ENABLED:
        return

    violations = scan_for_toxic_logic(kernel_code)
    if violations:
        log_soullaw_event({
            "event": "fail_closed_violation",
            "context": context or {},
            "violations": violations,
        })
        raise FailClosedViolation(violations, context)