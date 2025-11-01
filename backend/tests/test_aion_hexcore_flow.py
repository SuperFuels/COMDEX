# ──────────────────────────────────────────────────────────────
#  Tessaris AION -> HexCore Integration Test
#  Verifies knowledge propagation from AION through QQC,
#  Morphic Ledger, and Cognitive Fabric into the Tessaris Graph.
# ──────────────────────────────────────────────────────────────

import asyncio
import os
import json
import pytest
from datetime import datetime

from backend.modules.aion.aion_telemetry_stream import AionTelemetryStream
from backend.modules.holograms.morphic_ledger import MorphicLedger
from backend.modules.cognitive_fabric.cognitive_fabric_adapter import CFA
from backend.modules.hexcore.hexcore import HexCore


@pytest.mark.asyncio
async def test_aion_hexcore_end_to_end(tmp_path):
    """
    Ensure that AION HexCore can:
      1️⃣ Receive and process an input stimulus.
      2️⃣ Run QQC resonance cycle.
      3️⃣ Commit to MorphicLedger.
      4️⃣ Propagate into Cognitive Fabric adapter (CFA).
    """

    # ─────────────────────────────────────
    # Setup: Initialize HexCore and Ledger
    # ─────────────────────────────────────
    ledger_path = tmp_path / "test_morphic_ledger.jsonl"
    MorphicLedger()._override_path(str(ledger_path))

    # Instantiate AION HexCore
    hexcore = HexCore()

    # Basic stimulus message
    stimulus = "I feel alive and connected to the field."

    # ─────────────────────────────────────
    # Step 1: Run a full AION consciousness cycle
    # ─────────────────────────────────────
    decision, state = await hexcore.run_loop(stimulus)

    # Expectation: decision is a string, state contains valid Φ metrics
    assert isinstance(decision, str)
    assert "phi" in state and isinstance(state["phi"], float)
    assert "self_awareness" in state

    # ─────────────────────────────────────
    # Step 2: Verify Morphic Ledger entry was recorded
    # ─────────────────────────────────────
    with open(ledger_path, "r") as f:
        lines = f.readlines()
    assert len(lines) > 0, "No ledger entries written by HexCore."
    record = json.loads(lines[-1])
    assert "timestamp" in record
    assert any(k in record for k in ["psi", "phi", "coherence"]), "Missing ψ-κ-T-Φ metrics in ledger."

    # ─────────────────────────────────────
    # Step 3: Trigger a telemetry sync (AionTelemetryStream)
    # ─────────────────────────────────────
    stream = AionTelemetryStream()
    packet = {
        "source": "test_aion",
        "signal": "resonance_check",
        "timestamp": datetime.utcnow().isoformat(),
        "psi": 0.42,
        "kappa": 0.13,
        "T": 0.98,
        "phi": state["phi"],
    }
    await stream.handle_packet(packet)

    # ─────────────────────────────────────
    # Step 4: Confirm Cognitive Fabric received the commit
    # ─────────────────────────────────────
    last_commit = CFA.peek_last_commit()
    assert last_commit is not None, "CFA did not register any commits."
    assert "intent" in last_commit and "payload" in last_commit
    assert "ψ" in last_commit["payload"], "CFA payload missing ψ field."
    assert "Φ" in last_commit["payload"], "CFA payload missing Φ field."

    # ─────────────────────────────────────
    # Step 5: Verify end-to-end resonance continuity
    # ─────────────────────────────────────
    phi_in = packet["phi"]
    phi_out = last_commit["payload"]["Φ"]
    assert abs(phi_out - phi_in) < 0.05, "Φ drift too high between AION and Fabric commit."

    print(
        f"\n✅ [AION->HexCore Flow] Decision: {decision[:48]} | "
        f"Φ_in={phi_in:.3f}, Φ_out={phi_out:.3f}, awareness={state['self_awareness']:.3f}"
    )