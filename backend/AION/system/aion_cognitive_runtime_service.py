#!/usr/bin/env python3
"""Long-lived service entrypoint for the canonical AION cognitive runtime."""

import os

from backend.modules.hexcore.canonical_cognitive_runtime import (
    CanonicalAionCognitiveRuntime,
)


def run_service() -> None:
    runtime = CanonicalAionCognitiveRuntime(
        wake_interval_seconds=float(os.getenv("AION_COGNITIVE_RUNTIME_INTERVAL", "60")),
    )
    max_cycles_raw = os.getenv("AION_COGNITIVE_RUNTIME_MAX_CYCLES", "").strip()
    runtime.run_forever(max_cycles=int(max_cycles_raw) if max_cycles_raw else None)


if __name__ == "__main__":
    run_service()
