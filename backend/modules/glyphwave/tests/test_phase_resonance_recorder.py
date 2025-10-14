import asyncio
import os
import json
from backend.modules.glyphwave.vault.phase_resonance_recorder import PhaseResonanceRecorder
from backend.modules.encryption.glyph_vault import GlyphVault


async def async_test_recording(tmp_path):
    """Asynchronous end-to-end test for PhaseResonanceRecorder."""
    vault_dir = tmp_path / "vault"
    os.makedirs(vault_dir, exist_ok=True)

    # Create recorder and simulate data capture
    recorder = PhaseResonanceRecorder(vault_dir=str(vault_dir))
    recorder.start()
    for i in range(5):
        amp = 1.0 + 0.1 * i
        phase = 0.5 * i
        coherence = 1.0 - 0.05 * i
        recorder.record_sample(amp, phase, coherence)

    result = await recorder.persist_to_vault("TEST-CAPSULE")
    assert result["count"] == 5
    assert "checksum" in result

    # Verify file existence
    files = os.listdir(vault_dir)
    assert any(f.endswith(".gvx") for f in files)

    # Load back trace
    trace = recorder.load_trace("TEST-CAPSULE")
    assert trace["capsule_id"] == "TEST-CAPSULE"
    assert len(trace["resonance_trace"]) == 5

    # Basic data consistency check
    samples = trace["resonance_trace"]
    assert samples[0]["A"] == 1.0
    assert samples[-1]["C"] == 0.8


def test_sync_runner(tmp_path):
    """Wrapper to run async test synchronously."""
    asyncio.run(async_test_recording(tmp_path))