from __future__ import annotations

import argparse
import math
from typing import Optional

from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.field_bridge import FieldBridge
from backend.modules.dimensions.ucs.zones.experiments.qwave_engine.symatics_engine import (
    build_hello_world_engine,
    SymaticsCompiler,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Symatics Hello World emissions.")
    parser.add_argument(
        "--mode",
        choices=["constructive", "destructive", "beyond_boolean", "all"],
        default="all",
        help="Which Hello World state to run.",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=30,
        help="Maximum stabilization ticks per expression.",
    )
    parser.add_argument(
        "--safe-mode",
        action="store_true",
        help="Force FieldBridge safe/simulation mode.",
    )
    args = parser.parse_args()

    bridge = FieldBridge(safe_mode=args.safe_mode)
    engine = build_hello_world_engine(field_bridge=bridge, safe_mode=args.safe_mode)
    compiler: SymaticsCompiler = engine.compiler

    runs = []
    if args.mode == "constructive":
        runs.append(("Constructive", compiler.hello_world_constructive()))
    elif args.mode == "destructive":
        runs.append(("Destructive", compiler.hello_world_destructive()))
    elif args.mode == "beyond_boolean":
        runs.append(("Beyond Boolean", compiler.hello_world_beyond_boolean()))
    else:
        runs.extend(
            [
                ("Constructive", compiler.hello_world_constructive()),
                ("Destructive", compiler.hello_world_destructive()),
                ("Beyond Boolean", compiler.hello_world_beyond_boolean()),
            ]
        )

    try:
        for label, expr in runs:
            print(f"\n=== {label} ===")
            result = engine.run_expression(expr, max_ticks=args.ticks, reset_feedback=True)

            final_profile = result["final_profile"]
            last_feedback = result["last_feedback"]

            print(
                f"locked={result['locked']} | "
                f"ticks={result['ticks']} | "
                f"drift={result['drift']:.6f}"
            )

            if final_profile is not None:
                print(
                    f"final_profile: "
                    f"phi={final_profile.phi:.6f}, "
                    f"A={final_profile.amplitude:.6f}, "
                    f"f={final_profile.frequency:.6f}, "
                    f"harmonics={final_profile.harmonics}, "
                    f"state={final_profile.metadata.get('semantic_phi_state')}"
                )

            if last_feedback is not None:
                print(
                    f"feedback: "
                    f"V={last_feedback.measured_voltage:.6f}, "
                    f"phase={last_feedback.measured_phase:.6f}, "
                    f"stability={last_feedback.stability_score:.6f}"
                )

            print("recent events:")
            for event in result["events"]:
                print(f"  - {event}")

    finally:
        bridge.shutdown()


if __name__ == "__main__":
    main()