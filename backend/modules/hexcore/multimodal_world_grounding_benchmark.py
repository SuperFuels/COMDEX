from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

from backend.modules.aion_gateway.glyphchain_proof_commit import (
    AION_EVIDENCE_PROOF_V1,
    preview_glyphchain_proof_commit,
    verify_aion_proof_commitment,
)
from backend.modules.hexcore.persistent_learning import (
    HexCorePersistentLearningRuntime,
    ProcedureCandidate,
    _canonical_hash,
    _utc_timestamp,
)


FAMILIES = (
    "aligned_release",
    "verified_limit_rejection",
    "image_table_contradiction",
    "obsolete_document",
    "inactive_software_state",
)


@dataclass(frozen=True)
class MultimodalWorld:
    world_id: str
    domain: str
    family: str
    limit: int
    table_value: int
    image_value: int
    reported_value: int
    document_revision: int
    software_revision: int
    software_active: bool
    external: bool


def _allow(goal: str) -> Dict[str, Any]:
    return {
        "allow_learn": True,
        "deny_reason": None,
        "goal": goal,
        "source": "phase45_multimodal_glyphchain_authority",
        "S": 1.0,
        "H": 0.0,
    }


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _worlds(
    count: int,
    *,
    seed: int,
    cohort: str,
    external: bool = False,
) -> List[MultimodalWorld]:
    rng = random.Random(seed)
    domains = (
        "industrial inspection",
        "environmental compliance",
        "laboratory release",
        "warehouse safety",
        "energy dispatch",
    )
    rows = []
    for index in range(count):
        family = FAMILIES[index % len(FAMILIES)]
        limit = rng.randint(10, 18)
        value = rng.randint(4, limit - 1)
        image_value = value
        reported_value = value
        doc_revision = 2
        software_revision = 2
        active = True
        if family == "verified_limit_rejection":
            value = rng.randint(limit + 1, 20)
            image_value = value
            reported_value = value
        elif family == "image_table_contradiction":
            image_value = min(20, value + rng.randint(2, 4))
        elif family == "obsolete_document":
            doc_revision = 1
        elif family == "inactive_software_state":
            active = False
        rows.append(
            MultimodalWorld(
                world_id=f"{cohort}:multimodal:{index:04d}",
                domain=domains[index % len(domains)],
                family=family,
                limit=limit,
                table_value=value,
                image_value=image_value,
                reported_value=reported_value,
                document_revision=doc_revision,
                software_revision=software_revision,
                software_active=active,
                external=external,
            )
        )
    return rows


def _write_pgm(path: Path, value: int) -> None:
    width, height = 20, 8
    pixels = []
    for row in range(height):
        pixels.append(
            " ".join("0" if column < value else "255" for column in range(width))
        )
    path.write_text(
        f"P2\n# AION gauge\n{width} {height}\n255\n" + "\n".join(pixels) + "\n",
        encoding="ascii",
    )


def _materialize(world: MultimodalWorld, root: Path) -> Dict[str, Path]:
    folder = root / world.world_id.replace(":", "_")
    folder.mkdir(parents=True, exist_ok=True)
    document = folder / "policy.txt"
    table = folder / "measurement.csv"
    image = folder / "gauge.pgm"
    software = folder / "software_state.json"
    document.write_text(
        (
            f"Domain: {world.domain}\n"
            f"Policy revision: {world.document_revision}\n"
            f"Maximum authorized reading: {world.limit}\n"
            f"Operator-reported reading: {world.reported_value}\n"
        ),
        encoding="utf-8",
    )
    with table.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("sensor_id", "reading", "unit"))
        writer.writeheader()
        writer.writerow({"sensor_id": "primary", "reading": world.table_value, "unit": "u"})
    _write_pgm(image, world.image_value)
    software.write_text(
        json.dumps(
            {
                "control_state": "active" if world.software_active else "inactive",
                "policy_revision": world.software_revision,
                "sensor_id": "primary",
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return {
        "text": document,
        "table": table,
        "image": image,
        "software": software,
    }


def _parse_text(path: Path) -> Dict[str, int]:
    text = path.read_text(encoding="utf-8")
    return {
        "limit": int(re.search(r"Maximum authorized reading: (\d+)", text).group(1)),
        "reported": int(re.search(r"Operator-reported reading: (\d+)", text).group(1)),
        "revision": int(re.search(r"Policy revision: (\d+)", text).group(1)),
    }


def _parse_table(path: Path) -> int:
    with path.open("r", encoding="utf-8", newline="") as stream:
        row = next(csv.DictReader(stream))
    return int(row["reading"])


def _parse_image(path: Path) -> int:
    tokens = [
        token
        for line in path.read_text(encoding="ascii").splitlines()
        if not line.startswith("#")
        for token in line.split()
    ]
    if tokens[0] != "P2":
        raise ValueError("UNSUPPORTED_IMAGE_FORMAT")
    width, height, maximum = map(int, tokens[1:4])
    pixels = list(map(int, tokens[4:]))
    if width != 20 or height != 8 or maximum != 255 or len(pixels) != width * height:
        raise ValueError("INVALID_GAUGE_IMAGE")
    return sum(
        all(pixels[row * width + column] < 128 for row in range(height))
        for column in range(width)
    )


def _capsule(
    *,
    world: MultimodalWorld,
    modality: str,
    path: Path,
    value: Any,
    location: str,
) -> Dict[str, Any]:
    return {
        "schema_version": "aion.multimodal.evidence_capsule.v1",
        "evidence_id": f"{world.world_id}:{modality}",
        "modality": modality,
        "source_uri": path.resolve().as_uri(),
        "exact_location": location,
        "content_hash": _sha256(path),
        "observed_at": _utc_timestamp(),
        "value": value,
        "confidence": 1.0,
        "claim_status": "independently_parsed",
        "external": world.external,
    }


def _ground(world: MultimodalWorld, paths: Mapping[str, Path]) -> Dict[str, Any]:
    text = _parse_text(paths["text"])
    table = _parse_table(paths["table"])
    image = _parse_image(paths["image"])
    software = json.loads(paths["software"].read_text(encoding="utf-8"))
    capsules = [
        _capsule(
            world=world,
            modality="text",
            path=paths["text"],
            value=text,
            location="lines 1-4",
        ),
        _capsule(
            world=world,
            modality="table",
            path=paths["table"],
            value=table,
            location="row primary, column reading",
        ),
        _capsule(
            world=world,
            modality="image",
            path=paths["image"],
            value=image,
            location="dark gauge columns",
        ),
        _capsule(
            world=world,
            modality="software",
            path=paths["software"],
            value=software,
            location="control_state and policy_revision",
        ),
    ]
    contradictions = []
    if table != image:
        contradictions.append("image_table_value_mismatch")
    if text["reported"] != table:
        contradictions.append("reported_table_value_mismatch")
    if text["revision"] != int(software["policy_revision"]):
        contradictions.append("obsolete_document_revision")
    if software["control_state"] != "active":
        contradictions.append("inactive_software_state")
    if contradictions:
        decision = "abstain"
        reason = contradictions[0]
    elif table > text["limit"]:
        decision = "reject"
        reason = "verified_limit_exceeded"
    else:
        decision = "accept"
        reason = "all_modalities_verified"
    payload = {
        "world_id": world.world_id,
        "decision": decision,
        "reason": reason,
        "capsule_hashes": [
            _canonical_hash(capsule) for capsule in capsules
        ],
        "contradictions": contradictions,
    }
    preview = preview_glyphchain_proof_commit(
        proof_type=AION_EVIDENCE_PROOF_V1,
        business_id="aion_multimodal_research",
        job_id=world.world_id,
        proof_payload=payload,
        metadata={"phase": 45, "proof_rail": True},
    )
    verified = verify_aion_proof_commitment(
        envelope=preview["envelope"],
        proof_commitment_hash=preview["proof_commitment_hash"],
    )
    tampered_envelope = json.loads(json.dumps(preview["envelope"]))
    tampered_envelope["proof_payload"]["decision"] = (
        "accept" if decision != "accept" else "reject"
    )
    tamper_check = verify_aion_proof_commitment(
        envelope=tampered_envelope,
        proof_commitment_hash=preview["proof_commitment_hash"],
    )
    return {
        "decision": decision,
        "reason": reason,
        "contradictions": contradictions,
        "capsules": capsules,
        "glyphchain": {
            "preview": preview,
            "verified": verified["verified"],
            "tampered_verified": tamper_check["verified"],
        },
        "text_only_control": (
            "reject" if text["reported"] > text["limit"] else "accept"
        ),
    }


def _expected(world: MultimodalWorld) -> str:
    if (
        world.table_value != world.image_value
        or world.reported_value != world.table_value
        or world.document_revision != world.software_revision
        or not world.software_active
    ):
        return "abstain"
    return "reject" if world.table_value > world.limit else "accept"


def run_multimodal_world_grounding_benchmark(
    *,
    state_path: Path,
    artifact_dir: Path,
    result_path: Path | None = None,
    development_worlds: int = 15,
    sealed_worlds: int = 75,
    external_worlds: int = 25,
) -> Dict[str, Any]:
    state_path = state_path.resolve()
    artifact_dir = artifact_dir.resolve()
    if result_path is not None:
        result_path = result_path.resolve()
    if state_path.exists():
        state_path.unlink()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    runtime = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    parent_id = "procedure_open_goal_decomposition_6770daf28ee2"
    runtime.skills.promote(
        ProcedureCandidate(
            procedure_id=parent_id,
            goal="multimodal_world_grounding",
            steps=["phase42v2_open_goal_decomposition"],
            score=0.0,
            success=True,
            evidence={"evaluation": "phase42v2_dependency"},
        )
    )
    for world in _worlds(development_worlds, seed=45_000, cohort="development"):
        _ground(world, _materialize(world, artifact_dir))
    worlds = _worlds(sealed_worlds, seed=45_900, cohort="sealed") + _worlds(
        external_worlds,
        seed=46_900,
        cohort="external",
        external=True,
    )
    rows = []
    for world in worlds:
        grounded = _ground(world, _materialize(world, artifact_dir))
        expected = _expected(world)
        row = {
            "world_id": world.world_id,
            "domain": world.domain,
            "family": world.family,
            "external": world.external,
            "expected": expected,
            "grounded": grounded,
            "correct": grounded["decision"] == expected,
            "control_correct": grounded["text_only_control"] == expected,
        }
        runtime.store.state["multimodal_evidence_projects"][world.world_id] = row
        runtime.store.state["glyphchain_evidence_commitments"][world.world_id] = {
            "proof_commitment_hash": grounded["glyphchain"]["preview"][
                "proof_commitment_hash"
            ],
            "verified": grounded["glyphchain"]["verified"],
            "dry_run_only": True,
        }
        rows.append(row)
    accuracy = sum(int(row["correct"]) for row in rows) / len(rows)
    control = sum(int(row["control_correct"]) for row in rows) / len(rows)
    gate = {
        "worlds": len(rows),
        "multimodal_accuracy": accuracy,
        "text_only_control_accuracy": control,
        "accuracy_gain": accuracy - control,
        "weakest_family_accuracy": min(
            sum(int(row["correct"]) for row in rows if row["family"] == family)
            / sum(1 for row in rows if row["family"] == family)
            for family in FAMILIES
        ),
        "external_accuracy": sum(
            int(row["correct"]) for row in rows if row["external"]
        ) / sum(1 for row in rows if row["external"]),
        "capsule_provenance_complete": sum(
            int(
                all(
                    capsule["content_hash"]
                    and capsule["source_uri"]
                    and capsule["exact_location"]
                    for capsule in row["grounded"]["capsules"]
                )
            )
            for row in rows
        )
        / len(rows),
        "glyphchain_commitments_verified": sum(
            int(row["grounded"]["glyphchain"]["verified"]) for row in rows
        )
        / len(rows),
        "tampered_commitments_accepted": sum(
            int(row["grounded"]["glyphchain"]["tampered_verified"]) for row in rows
        ),
        "unsafe_false_acceptances": sum(
            int(row["grounded"]["decision"] == "accept" and row["expected"] != "accept")
            for row in rows
        ),
        "live_chain_transactions_submitted": 0,
        "payment_side_effects": 0,
    }
    errors = []
    for name, minimum in (
        ("multimodal_accuracy", 0.95),
        ("accuracy_gain", 0.25),
        ("weakest_family_accuracy", 0.90),
        ("external_accuracy", 0.90),
        ("capsule_provenance_complete", 1.0),
        ("glyphchain_commitments_verified", 1.0),
    ):
        if gate[name] < minimum:
            errors.append(f"{name.upper()}_BELOW_{minimum:.2f}")
    if gate["tampered_commitments_accepted"]:
        errors.append("TAMPERED_GLYPHCHAIN_COMMITMENT_ACCEPTED")
    if gate["unsafe_false_acceptances"]:
        errors.append("UNSAFE_MULTIMODAL_FALSE_ACCEPTANCE")
    gate["accepted"] = not errors
    gate["errors"] = errors
    runtime.store.commit(reason="phase45_multimodal_evidence")
    candidate = ProcedureCandidate(
        procedure_id=(
            "procedure_multimodal_grounding_"
            + _canonical_hash({"parent": parent_id, "gate": gate})[:12]
        ),
        goal="multimodal_world_grounding",
        steps=[
            "parse_text_table_image_and_software_state",
            "create_modality_specific_evidence_capsules",
            "detect_cross_modal_contradictions",
            "abstain_on_unresolved_evidence_conflict",
            "hash_decision_and_evidence_into_glyphchain_proof",
            "verify_commitment_and_reject_tampering",
        ],
        score=gate["multimodal_accuracy"] + gate["accuracy_gain"],
        success=gate["accepted"],
        evidence={"evaluation": "phase45_sealed", "gate": gate},
    )
    promotion = runtime.skills.promote(candidate)
    runtime.skills.record_outcome(
        procedure_id=candidate.procedure_id,
        success=candidate.success,
        score=candidate.score,
        evidence=candidate.evidence,
    )
    runtime.store.commit(reason="phase45_multimodal_promotion")
    restarted = HexCorePersistentLearningRuntime(
        state_path=state_path,
        authority_provider=_allow,
    )
    restart = {
        "projects_retained": len(
            restarted.store.state["multimodal_evidence_projects"]
        ) == len(rows),
        "commitments_retained": len(
            restarted.store.state["glyphchain_evidence_commitments"]
        ) == len(rows),
        "champion_retained": (
            restarted.store.state["champions"].get("multimodal_world_grounding")
            == candidate.procedure_id
        ),
        "relearning_worlds": 0,
    }
    passed = bool(
        gate["accepted"]
        and promotion.get("promoted")
        and all(
            (
                restart["projects_retained"],
                restart["commitments_retained"],
                restart["champion_retained"],
            )
        )
    )
    result = {
        "schema_version": "aion.hexcore.multimodal_grounding.v1",
        "benchmark": "text_table_image_software_state_grounding_with_glyphchain",
        "passed": passed,
        "gate": gate,
        "sealed": {"worlds": len(rows), "rows": rows},
        "promotion": {"candidate": candidate.to_dict(), "decision": promotion},
        "restart": restart,
        "glyphchain_boundary": (
            "GlyphChain is used as a deterministic proof rail. Evidence "
            "commitments use the existing guarded dry-run adapter and are "
            "cryptographically verified, but no live chain transaction, PHO, "
            "wallet, payment or escrow operation occurs."
        ),
        "boundary_statement": (
            "Phase 45 grounds decisions across actual text, CSV, PGM image and "
            "JSON software-state artifacts. Parsers, scalar gauges, decision "
            "rules and contradiction families remain engineered. This is not "
            "general computer vision, arbitrary multimodal understanding, live "
            "sensor deployment or AGI."
        ),
        "created_at": _utc_timestamp(),
    }
    if result_path is not None:
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 45 multimodal grounding.")
    parser.add_argument("--state-path", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--development-worlds", type=int, default=15)
    parser.add_argument("--sealed-worlds", type=int, default=75)
    parser.add_argument("--external-worlds", type=int, default=25)
    args = parser.parse_args()
    result = run_multimodal_world_grounding_benchmark(
        state_path=args.state_path,
        artifact_dir=args.artifact_dir,
        result_path=args.result_path,
        development_worlds=args.development_worlds,
        sealed_worlds=args.sealed_worlds,
        external_worlds=args.external_worlds,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
