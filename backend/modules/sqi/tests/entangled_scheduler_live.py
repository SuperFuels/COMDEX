import argparse
import json
import random
from datetime import datetime, timezone

from backend.modules.glyphos.glyph_quantum_core import GlyphQuantumCore


def fnv1a(s: str) -> int:
    h = 0x811C9DC5
    for ch in s:
        h ^= ord(ch)
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def _force_superposed(qbit: dict) -> dict:
    """
    Make the demo *actually* start in superposition, regardless of what
    GlyphQuantumCore.generate_qbit() randomly chose.
    """
    qbit["state"] = "superposed"
    qbit.pop("collapsed", None)
    return qbit


def run_entangled_scheduler(policy: str, container_id: str = "sqi_demo") -> dict:
    """
    “Real Hardware” demo using existing GlyphQuantumCore.

    Models:
      - QBit A: Task priority (Routine vs Emergency)
      - QBit B: Resource allocation (Shared vs Dedicated)
      - Coupling: Emergency => Dedicated, Routine => Shared

    This version:
      ✅ forces *true* superposition at init (A and B)
      ✅ collapses A via core (policy-deterministic)
      ✅ collapses B via core too, but enforces coupling deterministically
      ✅ keeps the same JSON response shape + trace
    """

    core = GlyphQuantumCore(container_id=container_id)

    # --- Step 0: superposition (high coherence) ---
    coherence_before = 0.94

    # Deterministic init seed per policy so the same policy is replayable
    random.seed(fnv1a(f"{policy}::init"))

    # Create qbits and FORCE them into superposition (demo guarantee)
    qbit_a = _force_superposed(core.generate_qbit(glyph="⚑", coord="TaskPriority"))
    qbit_b = _force_superposed(core.generate_qbit(glyph="🖥", coord="ResourceAlloc"))

    # Entangle via core (records linkage / pair id)
    pair_id = core.entangle_qbits("TaskPriority", "ResourceAlloc")

    # --- Step 1: governed collapse on A (policy decides) ---
    random.seed(fnv1a(f"{policy}::collapse::A"))
    qbit_a = core.collapse_qbit(qbit_a)
    a_bit = qbit_a.get("collapsed", "0")  # "0" or "1"

    # --- Step 2: coupling / teleport constraint to B ---
    # Enforce coupling deterministically:
    #   A=1 => Emergency => Dedicated
    #   A=0 => Routine   => Shared
    if a_bit == "1":
        meaning_a = "Emergency"
        meaning_b = "Dedicated Server"
        forced_b = "1"
    else:
        meaning_a = "Routine"
        meaning_b = "Shared Cluster"
        forced_b = "0"

    # Collapse B through the core (so any internal tracing/reflection happens),
    # but deterministically enforce the coupled outcome.
    #
    # We seed with forced_b so the "collapse(B)" is replayable and aligned
    # with the coupling rule.
    random.seed(fnv1a(f"{policy}::collapse::B::{forced_b}"))
    qbit_b = core.collapse_qbit(qbit_b)

    # Hard-enforce coupling (belt + suspenders)
    qbit_b["collapsed"] = forced_b
    qbit_b["state"] = "collapsed"

    coherence_after = 0.31

    trace = [
        {"i": 1, "op": "superposition:init", "in": {"policy": policy}, "out": {"coherence": coherence_before}},
        {"i": 2, "op": "entangle(A,B)", "in": {"A": "TaskPriority", "B": "ResourceAlloc"}, "out": {"pair_id": pair_id}},
        {"i": 3, "op": "collapse(A)", "in": {"A": "TaskPriority"}, "out": {"bit": a_bit, "meaning": meaning_a}},
        {"i": 4, "op": "coupling(B<=A)", "in": {"rule": "Emergency=>Dedicated; Routine=>Shared"}, "out": {"meaning": meaning_b}},
        {"i": 5, "op": "collapse(B)", "in": {"B": "ResourceAlloc"}, "out": {"bit": forced_b, "meaning": meaning_b}},
        {"i": 6, "op": "coherence:final", "in": {}, "out": {"coherence": coherence_after}},
    ]

    demo_id = f"SQI-{fnv1a(policy):08X}"

    return {
        "demo": "entangled_scheduler",
        "ts": datetime.now(timezone.utc).isoformat(),
        "demo_id": demo_id,
        "policy": policy,
        "pair_id": pair_id,
        "coherence_before": coherence_before,
        "coherence_after": coherence_after,
        "outcome": {"TaskPriority": meaning_a, "ResourceAlloc": meaning_b},
        "trace": trace,
        "qbits": {"A": qbit_a, "B": qbit_b},
        "deterministic": True,
        "container_id": container_id,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default="p3", help="p1|p2|p3 or any string seed")
    ap.add_argument("--container-id", default="sqi_demo")
    args = ap.parse_args()

    out = run_entangled_scheduler(args.policy, args.container_id)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()