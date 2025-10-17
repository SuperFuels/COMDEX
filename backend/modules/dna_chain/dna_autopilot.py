# backend/modules/dna_chain/dna_autopilot.py
# ──────────────────────────────────────────────────────────────
#  Tessaris • DNA Autopilot
#  Self-growth bridge between AION/QQC awareness ↔ DNA Chain
#  Monitors Φ/coherence + logs → proposes CRISPR mutations safely.
# ──────────────────────────────────────────────────────────────

import asyncio
import traceback
from datetime import datetime

from backend.modules.holograms.morphic_ledger import MorphicLedger
from backend.modules.dna_chain.switchboard import DNA_SWITCH, get_module_path, read_module_file
from backend.modules.dna_chain.crispr_ai import generate_mutation_proposal
from backend.modules.dna_chain.dna_switch import is_self_growth_enabled, enable_self_growth
from backend.modules.dna_chain.proposal_manager import load_proposals
from backend.modules.soul.soul_laws import validate_ethics

AUTOPILOT_INTERVAL = 10           # seconds between scans
PHI_THRESHOLD = 0.25              # below this, system is "unstable"
COHERENCE_THRESHOLD = 0.30
MAX_PROPOSALS_PER_RUN = 2         # to prevent runaway spawning


async def monitor_self_growth(aion_ref):
    """
    Continuous coroutine:
      • Reads recent Φ/coherence from Morphic Ledger
      • Detects degradation / drifts
      • Generates CRISPR mutation proposals via LLM interface
    """
    print("[🧬 DNA-Autopilot] Activated self-growth monitor.")
    while True:
        await asyncio.sleep(AUTOPILOT_INTERVAL)
        try:
            # Check if growth is enabled for this container
            if not is_self_growth_enabled(aion_ref.id):
                continue

            # Pull last few Morphic entries
            recent_logs = MorphicLedger().read_recent(limit=5)
            if not recent_logs:
                continue

            avg_phi = sum(e.get("phi", 0.0) for e in recent_logs) / len(recent_logs)
            avg_coh = sum(e.get("coherence", 0.0) for e in recent_logs) / len(recent_logs)

            # detect degradation
            if avg_phi < PHI_THRESHOLD or avg_coh < COHERENCE_THRESHOLD:
                print(f"[🧬 Autopilot] Low stability detected (Φ={avg_phi:.3f}, C={avg_coh:.3f})")
                await propose_repair_mutations(aion_ref, avg_phi, avg_coh)
        except Exception:
            print("[DNA-Autopilot] Exception in monitor loop:")
            traceback.print_exc()


async def propose_repair_mutations(aion_ref, phi_val: float, coherence_val: float):
    """
    Analyze registered modules and propose targeted improvements.
    Uses CRISPR-AI (LLM) for diff generation.
    """
    registry = DNA_SWITCH.get_registry()
    proposals = load_proposals()
    proposed_count = 0

    for file_path, meta in registry.items():
        if proposed_count >= MAX_PROPOSALS_PER_RUN:
            break

        # Skip non-backend modules for now
        if "frontend" in (meta.get("type") or ""):
            continue

        try:
            module_key = meta["dna_id"].split(".")[-1]
            current_code = read_module_file(module_key)

            reason = (
                f"Low Φ={phi_val:.3f}, Coherence={coherence_val:.3f} "
                f"detected by AION ({aion_ref.id[:8]}). "
                f"Attempting structural optimization."
            )

            proposal = generate_mutation_proposal(
                module_key=module_key,
                prompt_reason=reason,
                dry_run=True  # safe mode; just store proposal
            )

            if validate_ethics(proposal.get("new_code", "")):
                proposed_count += 1
                print(f"[DNA-Autopilot] 🧬 Proposed mutation for {module_key}")
            else:
                print(f"[DNA-Autopilot] ⚠️ Rejected unethical mutation in {module_key}")

        except Exception as e:
            print(f"[DNA-Autopilot] Error while proposing for {file_path}: {e}")

    if proposed_count > 0:
        print(f"[DNA-Autopilot] ✅ {proposed_count} proposals created "
              f"at {datetime.utcnow().isoformat()}")
    else:
        print("[DNA-Autopilot] No safe proposals generated this cycle.")