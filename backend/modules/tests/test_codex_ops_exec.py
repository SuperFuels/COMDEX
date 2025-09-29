# -*- coding: utf-8 -*-
"""
Smoke test for Codex Ops
──────────────────────────────────────────────
Iterates over codex_instruction_set.yaml and ensures each mapped
`execute_*` function exists and runs without raising an exception.

This confirms:
  • RegistryBridge sync loaded the op
  • The corresponding backend/modules/codex/ops/execute_*.py exists
  • Function executes safely (stub or real)
"""

import pytest

from backend.core.registry_bridge import registry_bridge
from backend.core.registry_bridge import _load_codex_instruction_set


@pytest.mark.parametrize("sym,meta", _load_codex_instruction_set().items())
def test_codex_op_executes(sym, meta):
    """Check that each YAML op executes via registry."""
    canonical = f"{meta.get('category', 'core')}:{sym}"
    fn_name = meta["function"]

    # Ensure handler registered
    assert registry_bridge.has_handler(canonical), f"{canonical} not registered"

    # Run handler through registry
    try:
        result = registry_bridge.resolve_and_execute(canonical, "a", "b")
    except Exception as e:
        pytest.fail(f"{canonical} → {fn_name} raised error: {e}")

    # Structured result check
    assert result is not None, f"{canonical} returned None"

    # Optional debug print for clarity
    print(f"[OK] {canonical} → {fn_name} → {result}")