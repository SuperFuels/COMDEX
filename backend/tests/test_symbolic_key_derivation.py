import time
import pytest
from backend.modules.glyphnet.symbolic_key_derivation import symbolic_key_deriver

def test_normal_derivation():
    key1 = symbolic_key_deriver.derive_key(0.5, 0.5, 1234567890, "session1", use_salt=True)
    key2 = symbolic_key_deriver.derive_key(0.7, 0.3, 1234567890, "session2", use_salt=True)
    assert key1 is not None

def test_deterministic_same_input():
    # Disable salt and runtime entropy for deterministic result
    key1 = symbolic_key_deriver.derive_key(
        0.8, 0.2, 999999999, "same_session",
        seed_phrase="seedA", use_salt=False, fixed_entropy=""
    )
    key2 = symbolic_key_deriver.derive_key(
        0.8, 0.2, 999999999, "same_session",
        seed_phrase="seedA", use_salt=False, fixed_entropy=""
    )
    assert key1 == key2

def test_different_seed_phrase():
    key1 = symbolic_key_deriver.derive_key(
        0.8, 0.2, 999999999, "same_session",
        seed_phrase="seedA", use_salt=False, fixed_entropy=""
    )
    key2 = symbolic_key_deriver.derive_key(
        0.8, 0.2, 999999999, "same_session",
        seed_phrase="seedB", use_salt=False, fixed_entropy=""
    )
    assert key1 != key2

def test_lockout_enforcement():
    session = "lockout_session"
    # simulate max allowed failed attempts quickly by passing invalid trust_level type to cause failure
    for _ in range(symbolic_key_deriver.MAX_ATTEMPTS):
        key = symbolic_key_deriver.derive_key("invalid_trust", 0.5, time.time(), session)
        assert key is None
    # next call should hit lockout and return None
    locked_key = symbolic_key_deriver.derive_key(0.5, 0.5, time.time(), session)
    assert locked_key is None

def test_invalid_inputs():
    # Now expect None return instead of raising exception
    result = symbolic_key_deriver.derive_key("bad", 0.5, 123, "session")
    assert result is None

def test_edge_parameter_values():
    key_low = symbolic_key_deriver.derive_key(0.0, 0.0, 0, "", use_salt=False, fixed_entropy="")
    key_high = symbolic_key_deriver.derive_key(1.0, 1.0, 9999999999, "edge_session", use_salt=False, fixed_entropy="")
    assert key_low is not None
    assert key_high is not None