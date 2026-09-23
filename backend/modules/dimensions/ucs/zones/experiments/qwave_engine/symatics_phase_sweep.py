from __future__ import annotations

import argparse
import math

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.field_bridge import FieldBridge
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_engine import (
    build_hello_world_engine,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Sweep symbolic phase values for Symatics experiments.")
    parser.add_argument(
        "--start",
        type=float,
        default=0.0,
        help="Sweep start phase in radians.",
    )
    parser.add_argument(
        "--end",
        type=float,
        default=(2.0 * math.pi),
        help="Sweep end phase in radians.",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=9,
        help="Number of phase samples across the interval.",
    )
    parser.add_argument(
        "--frequency",
        type=float,
        default=1.0,
        help="Base symbolic frequency.",
    )
    parser.add_argument(
        "--amplitude",
        type=float,
        default=1.0,
        help="Base symbolic amplitude.",
    )
    parser.add_argument(
        "--ticks-per-phase",
        type=int,
        default=20,
        help="Max stabilization ticks for each phase.",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Force FieldBridge safe/simulation mode.",
    )
    args = parser.parse_args()

    if args.steps < 2:
        raise ValueError("--steps must be >= 2")

    bridge = FieldBridge(safe_mode=args.safe_mode)
    engine = build_hello_world_engine(field_bridge=bridge, safe_mode=args.safe_mode)

    phases = [
        args.start + ((args.end - args.start) * i / (args.steps - 1))
        for i in range(args.steps)
    ]

    try:
        results = engine.phase_sweep(
            phases=phases,
            frequency=args.frequency,
            amplitude=args.amplitude,
            ticks_per_phase=args.ticks_per_phase,
            reset_feedback_per_phase=True,
        )

        print("\n=== Symatics Phase Sweep Results ===")
        for row in results:
            phi = row["phi"]
            locked = row["locked"]
            drift = row["drift"]
            final_profile = row["final_profile"]
            last_feedback = row["last_feedback"]

            state = None
            if final_profile is not None:
                state = final_profile.metadata.get("semantic_phi_state")

            voltage = None
            stability = None
            if last_feedback is not None:
                voltage = last_feedback.measured_voltage
                stability = last_feedback.stability_score

            print(
                f"phi={phi:.6f} | "
                f"locked={locked} | "
                f"drift={drift:.6f} | "
                f"state={state} | "
                f"V={0.0 if voltage is None else voltage:.6f} | "
                f"S={0.0 if stability is None else stability:.6f}"
            )

    finally:
        bridge.shutdown()


if __name__ == "__main__":
    main()