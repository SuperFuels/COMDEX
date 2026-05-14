from __future__ import annotations

import os
import pytest

# Add any env vars here that tests may toggle.
_ENV_KEYS = [
    "P2P_REQUIRE_SIGNED_SYNC",
    "P2P_REQUIRE_SIGNED_BLOCK",
    "P2P_REQUIRE_HELLO_BINDING_SYNC",
    "P2P_REQUIRE_HELLO_BINDING_BLOCK",
    "P2P_REQUIRE_SIGNED_CONSENSUS",
    "P2P_REQUIRE_HELLO_BINDING_CONSENSUS",
]

@pytest.fixture(autouse=True)
def _glyphchain_env_isolation() -> None:
    """
    Prevent env var leakage across tests.
    Any test can set os.environ[...] and it will be restored automatically.
    """
    snap = {k: os.environ.get(k) for k in _ENV_KEYS}
    try:
        yield
    finally:
        for k, v in snap.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v