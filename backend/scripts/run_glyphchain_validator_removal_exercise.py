#!/usr/bin/env python3
"""Run a content-free GlyphChain compromised-validator removal exercise."""

from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import tempfile

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.modules.consensus.finality_checkpoint import CHECKPOINT_SCHEMA, normalize_checkpoint
from backend.modules.consensus.validator_governance import (
    FINALIZE_CONFIRMATION,
    PROPOSE_CONFIRMATION,
    ValidatorGovernanceError,
    ValidatorGovernanceStore,
    sign_approval,
    verify_transition_proof,
)


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _public(key: Ed25519PrivateKey) -> str:
    return base64.b64encode(key.public_key().public_bytes_raw()).decode("ascii")


def _checkpoint(keys: list[Ed25519PrivateKey], validator_ids: list[str], *, epoch: int, height: int) -> dict:
    return normalize_checkpoint({
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": "glyphchain-main",
        "network_id": "production-exercise",
        "epoch": epoch,
        "effective_height": height,
        "validator_set": [
            {"validator_id": validator_id, "power": 1, "public_key_base64": _public(keys[index])}
            for index, validator_id in enumerate(validator_ids)
        ],
    })


def run_exercise() -> dict:
    keys = [Ed25519PrivateKey.generate() for _ in range(5)]
    current_ids = ["val-1", "val-2", "val-3", "val-4"]
    current = _checkpoint(keys, current_ids, epoch=0, height=1)
    successor = _checkpoint(keys, current_ids[:3], epoch=1, height=120)

    with tempfile.TemporaryDirectory(prefix="glyphchain-validator-removal-") as temporary:
        store = ValidatorGovernanceStore(Path(temporary), current_checkpoint=current)
        proposal = store.propose(
            next_checkpoint=successor,
            action="emergency_removal",
            reason="exercise: retained incident evidence identifies val-4 as compromised",
            governance_reference="exercise-incident-GC-001",
            operator_id="exercise-incident-commander",
            confirmation=PROPOSE_CONFIRMATION,
            current_finalized_height=10,
        )["proposal"]

        accused_denied = False
        try:
            store.add_approval(
                sign_approval(proposal, validator_id="val-4", private_key=keys[3]),
                operator_id="accused-validator",
            )
        except ValidatorGovernanceError as exc:
            accused_denied = "being removed" in str(exc)

        for index in range(3):
            store.add_approval(
                sign_approval(proposal, validator_id=f"val-{index + 1}", private_key=keys[index]),
                operator_id=f"unaffected-operator-{index + 1}",
            )
        finalized = store.finalize(
            operator_id="exercise-incident-commander",
            confirmation=FINALIZE_CONFIRMATION,
        )
        proof = finalized["transition_proof"]
        verification = verify_transition_proof(
            proof,
            expected_previous_checkpoint_id=current["checkpoint_id"],
            expected_next_checkpoint_id=successor["checkpoint_id"],
        )
        persisted = ValidatorGovernanceStore(
            Path(temporary), current_checkpoint=current
        ).status()

    replacement = _checkpoint(keys, ["val-1", "val-2", "val-3", "val-5"], epoch=1, height=120)
    with tempfile.TemporaryDirectory(prefix="glyphchain-validator-replacement-") as temporary:
        replacement_store = ValidatorGovernanceStore(Path(temporary), current_checkpoint=current)
        replacement_proposal = replacement_store.propose(
            next_checkpoint=replacement,
            action="replacement",
            reason="exercise: separately reviewed replacement for compromised val-4",
            governance_reference="exercise-incident-GC-001/replacement",
            operator_id="exercise-incident-commander",
            confirmation=PROPOSE_CONFIRMATION,
            current_finalized_height=10,
        )["proposal"]
        joining_denied = False
        try:
            replacement_store.add_approval(
                sign_approval(replacement_proposal, validator_id="val-5", private_key=keys[4]),
                operator_id="joining-validator",
            )
        except ValidatorGovernanceError as exc:
            joining_denied = "signature" in str(exc)

    passed = all((accused_denied, joining_denied, verification["valid"], persisted["status"] == "FINALIZED"))
    report = {
        "schema_version": "glyphchain.validator-removal-exercise.v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "result": "PASS" if passed else "FAIL",
        "claim_boundary": "Local cryptographic governance exercise; not production operational approval",
        "incident_reference": "exercise-incident-GC-001",
        "checks": {
            "accused_validator_approval_denied": accused_denied,
            "joining_validator_approval_denied": joining_denied,
            "unaffected_current_quorum_finalized_transition": bool(verification["valid"]),
            "governance_state_survived_restart": persisted["status"] == "FINALIZED",
        },
        "current_checkpoint": current,
        "successor_checkpoint": successor,
        "transition_proof": proof,
        "verification": verification,
        "private_keys_exported": False,
        "legal_document_content_present": False,
    }
    body = dict(report)
    report["report_sha256"] = sha256(_canonical(body)).hexdigest()
    if not passed:
        raise RuntimeError("validator removal exercise failed")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = run_exercise()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output)
    print(report["report_sha256"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
