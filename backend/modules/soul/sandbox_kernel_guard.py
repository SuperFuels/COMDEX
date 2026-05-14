# backend/modules/soul/sandbox_kernel_guard.py

import re
from typing import List, Dict, Tuple

# Define patterns that indicate unsafe or privileged execution paths
UNSAFE_PATH_PATTERNS = [
    r"eval\(",
    r"exec\(",
    r"open\([^)]*['\"]w['\"]",  # writing to disk
    r"import\s+os",
    r"import\s+subprocess",
    r"__import__",
    r"globals\(\)",
    r"locals\(\)",
    r"del\s+.*",
    r"[^\w]fork\(",
    r"[^\w]kill\("
]


class SandboxKernelGuard:
    def __init__(self, code_snippet: str, context: str = ""):
        self.code = code_snippet
        self.context = context
        self.violations: List[str] = []

    def scan(self) -> Tuple[bool, List[str]]:
        """Scan the code snippet for unsafe patterns."""
        for pattern in UNSAFE_PATH_PATTERNS:
            if re.search(pattern, self.code):
                self.violations.append(f"Unsafe pattern matched: `{pattern}`")

        is_safe = len(self.violations) == 0
        return is_safe, self.violations

    def to_dict(self) -> Dict:
        return {
            "context": self.context,
            "code_preview": self.code[:100],
            "is_safe": len(self.violations) == 0,
            "violations": self.violations,
        }


# Optional helper for integration

def is_kernel_code_safe(code: str, context: str = "") -> bool:
    guard = SandboxKernelGuard(code, context)
    safe, _ = guard.scan()
    return safe