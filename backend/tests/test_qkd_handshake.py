# File: backend/tests/test_qkd_handshake.py

import pytest
from backend.modules.glyphwave.qkd_handshake import initiate_handshake, verify_handshake
from backend.modules.glyphwave.gkey_model import GKey


@pytest.mark.asyncio
async def test_initiate_handshake_generates_valid_gkey():
    wave_id = "wave-abc"
    origin_trace = "trace-xyz"
    entropy = 0.95

    gkey = await initiate_handshake(wave_id, origin_trace, entropy)

    assert isinstance(gkey, GKey)
    assert gkey.wave_id == wave_id
    assert gkey.origin_trace == origin_trace
    assert gkey.entropy == entropy
    assert 0.9 <= gkey.coherence_level <= 1.0
    assert gkey.collapse_hash is not None
    assert gkey.verified is False
    assert gkey.compromised is False


@pytest.mark.asyncio
async def test_verify_handshake_success():
    wave_id = "wave-test"
    origin_trace = "trace-123"
    entropy = 0.96

    gkey = await initiate_handshake(wave_id, origin_trace, entropy)
    result = await verify_handshake(gkey, observed_entropy=entropy, trace_signature=origin_trace)

    assert result is True
    assert gkey.verified is True
    assert gkey.compromised is False


@pytest.mark.asyncio
async def test_verify_handshake_tampered_entropy():
    wave_id = "wave-test"
    origin_trace = "trace-123"
    entropy = 0.96
    bad_entropy = 0.75  # Tampered

    gkey = await initiate_handshake(wave_id, origin_trace, entropy)
    result = await verify_handshake(gkey, observed_entropy=bad_entropy, trace_signature=origin_trace)

    assert result is False
    assert gkey.verified is False
    assert gkey.compromised is True


@pytest.mark.asyncio
async def test_verify_handshake_tampered_trace():
    wave_id = "wave-test"
    origin_trace = "trace-123"
    wrong_trace = "trace-hacked"
    entropy = 0.96

    gkey = await initiate_handshake(wave_id, origin_trace, entropy)
    result = await verify_handshake(gkey, observed_entropy=entropy, trace_signature=wrong_trace)

    assert result is False
    assert gkey.verified is False
    assert gkey.compromised is True