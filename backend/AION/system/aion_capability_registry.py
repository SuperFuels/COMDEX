#!/usr/bin/env python3
"""Query AION's evidence-backed subject capability registry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.modules.hexcore.constitutional_north_star_mastery_registry import (
    MasteryRegistry,
)


def query(question: str, *, result_path: Path) -> dict:
    if not result_path.exists():
        return {
            "status": "registry_unavailable",
            "answer": "The capability registry must be reconstructed before this can be answered.",
        }
    state = json.loads(result_path.read_text(encoding="utf-8"))
    return MasteryRegistry.answer(state["subjects"], question)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument(
        "--registry", type=Path,
        default=Path("results/hexcore_constitutional_north_star_mastery_registry.json"),
    )
    args = parser.parse_args()
    print(json.dumps(query(args.question, result_path=args.registry.resolve()), indent=2))


if __name__ == "__main__":
    main()
