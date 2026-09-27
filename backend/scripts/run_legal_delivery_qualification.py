#!/usr/bin/env python3
"""Create a content-free Legal delivery qualification report from the outbox."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.aion_business.runtime.legal_delivery_qualification import (  # noqa: E402
    LegalDeliveryQualificationEvaluator,
)
from backend.modules.aion_business.runtime.legal_delivery_service import (  # noqa: E402
    LegalDeliveryService,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate existing provider-authenticated Legal delivery evidence. "
            "This command never sends email."
        )
    )
    parser.add_argument("--legal-root", type=Path, required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument(
        "--environment", choices=("test", "staging", "production"), required=True,
    )
    parser.add_argument(
        "--provider-configuration", type=Path, required=True,
        help="Content-free JSON inventory; do not place secrets or tokens in this file.",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    configuration = json.loads(args.provider_configuration.read_text(encoding="utf-8"))
    if not isinstance(configuration, dict):
        raise SystemExit("provider configuration must be a JSON object")
    service = LegalDeliveryService(args.legal_root)
    evaluator = LegalDeliveryQualificationEvaluator(service)
    report = evaluator.evaluate(
        args.workspace_id,
        environment=args.environment,
        provider_configuration=configuration,
    )
    path = evaluator.write_report(args.output, report)
    print(json.dumps({
        "output": str(path),
        "result": report["result"],
        "production_ready": report["production_ready"],
        "report_sha256": report["report_sha256"],
    }, sort_keys=True))
    return 0 if report["production_ready"] or args.environment != "production" else 2


if __name__ == "__main__":
    raise SystemExit(main())
