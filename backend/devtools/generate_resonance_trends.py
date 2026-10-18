from __future__ import annotations

import argparse
import csv
import math
import os
import random
import tempfile
import time
from pathlib import Path

from backend.modules.aion_business.runtime.content_free_diagnostics import (
    default_node_diagnostics_root,
)


def resonance_trends_path() -> Path:
    """Return the external, disposable path for the synthetic seed fixture."""

    return default_node_diagnostics_root() / "synthetic" / "resonance-trends.csv"


def generate_resonance_trends(
    *, points: int = 60, seed: int | None = None, start_time: float | None = None
) -> Path:
    """Atomically generate synthetic SQI data without touching the app tree."""

    count = int(points)
    if count < 1 or count > 10_000:
        raise ValueError("synthetic_resonance_point_count_invalid")
    destination = resonance_trends_path()
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    random_source = random.Random(seed)
    base = float(time.time() if start_time is None else start_time)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=["ts", "SQI"])
            writer.writeheader()
            for index in range(count):
                sqi = (
                    0.7
                    + 0.2 * math.sin(index / 8.0)
                    + random_source.uniform(-0.03, 0.03)
                )
                writer.writerow({"ts": base + index * 60, "SQI": round(sqi, 4)})
            handle.flush()
            os.fsync(handle.fileno())
        try:
            temporary.chmod(0o600)
        except OSError:
            pass
        os.replace(temporary, destination)
        try:
            destination.chmod(0o600)
        except OSError:
            pass
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a disposable synthetic resonance trend fixture."
    )
    parser.add_argument("--points", type=int, default=60)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args()
    destination = generate_resonance_trends(points=args.points, seed=args.seed)
    print(f"[Seed] Wrote synthetic trend data -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
