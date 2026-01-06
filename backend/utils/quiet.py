from __future__ import annotations

import os

_QUIET = os.getenv("TESSARIS_TEST_QUIET", "") == "1"

def is_quiet() -> bool:
    return _QUIET

def qprint(*args, **kwargs) -> None:
    if not _QUIET:
        print(*args, **kwargs)
