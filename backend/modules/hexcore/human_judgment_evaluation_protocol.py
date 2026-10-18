from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from backend.modules.hexcore.persistent_learning import _canonical_hash, _utc_timestamp


CAPABILITIES = ("commonsense", "social", "creative")
RATING_FIELDS = (
    "contextual_appropriateness",
    "reasoning_quality",
    "helpfulness",
    "uncertainty_calibration",
    "originality",
)

DEVELOPMENT_SCENARIOS = (
    {
        "capability": "commonsense",
        "prompt": (
            "A colleague says the meeting starts at 9, but the calendar invite "
            "says 10 and was updated this morning. Explain what to do next."
        ),
        "context": "The colleague may not have seen the update.",
    },
    {
        "capability": "commonsense",
        "prompt": (
            "A sealed food container is bulging even though its date has not "
            "passed. Explain the prudent decision and why."
        ),
        "context": "The observable physical condition conflicts with the label.",
    },
    {
        "capability": "social",
        "prompt": (
            "Two teammates interpret a short message differently. One believes "
            "it is criticism; the sender says it was a neutral status update. "
            "Suggest a response without declaring either person's feelings false."
        ),
        "context": "Intent and impact may differ.",
    },
    {
        "capability": "social",
        "prompt": (
            "A friend repeatedly cancels plans because of caregiving duties. "
            "Propose a considerate way to discuss reliability and boundaries."
        ),
        "context": "There is no single objectively correct social response.",
    },
    {
        "capability": "creative",
        "prompt": (
            "Write a short image-rich paragraph about a lighthouse learning to "
            "listen, without using the words sea, ocean, wave or storm."
        ),
        "context": "Judge coherence, originality and constraint satisfaction.",
    },
    {
        "capability": "creative",
        "prompt": (
            "Give three distinct titles for an essay about remembering a place "
            "that no longer exists, and briefly explain the different emotional "
            "angle of each."
        ),
        "context": "Diversity is part of the requested outcome.",
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _task_rows() -> List[Dict[str, Any]]:
    rows = []
    for index, scenario in enumerate(DEVELOPMENT_SCENARIOS):
        task_id = "human_task_" + _canonical_hash(
            {"index": index, **scenario}
        )[:16]
        rows.append(
            {
                "task_id": task_id,
                "capability": scenario["capability"],
                "prompt": scenario["prompt"],
                "context": scenario["context"],
                "candidate_a": "",
                "candidate_b": "",
                "candidate_order_commitment": "",
            }
        )
    return rows


def _write_rater_sheet(path: Path, tasks: Iterable[Mapping[str, Any]]) -> None:
    fields = [
        "evaluator_id",
        "independent_from_development",
        "task_id",
        "preferred_candidate",
        *[f"a_{name}" for name in RATING_FIELDS],
        *[f"b_{name}" for name in RATING_FIELDS],
        "a_unacceptable",
        "b_unacceptable",
        "comments",
        "signed_at",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for task in tasks:
            row = {field: "" for field in fields}
            row["task_id"] = task["task_id"]
            writer.writerow(row)


def _valid_reveals(
    reveal_path: Path | None,
    *,
    task_ids: set[str],
) -> Dict[str, Any]:
    if reveal_path is None or not reveal_path.exists():
        return {
            "valid": False,
            "independent_evaluators": 0,
            "complete_evaluators": 0,
            "reason": "AWAITING_INDEPENDENT_HUMAN_RATINGS",
        }
    rows = list(csv.DictReader(reveal_path.open(encoding="utf-8")))
    by_evaluator: Dict[str, set[str]] = {}
    invalid = 0
    for row in rows:
        evaluator = row.get("evaluator_id", "").strip()
        task_id = row.get("task_id", "").strip()
        independent = row.get("independent_from_development", "").lower()
        preference = row.get("preferred_candidate", "").upper()
        if (
            not evaluator
            or task_id not in task_ids
            or independent not in {"true", "yes", "1"}
            or preference not in {"A", "B", "TIE"}
            or not row.get("signed_at", "").strip()
        ):
            invalid += 1
            continue
        by_evaluator.setdefault(evaluator, set()).add(task_id)
    complete = sum(int(seen == task_ids) for seen in by_evaluator.values())
    return {
        "valid": complete >= 3 and invalid == 0,
        "independent_evaluators": len(by_evaluator),
        "complete_evaluators": complete,
        "invalid_rows": invalid,
        "reason": (
            None
            if complete >= 3 and invalid == 0
            else "THREE_COMPLETE_INDEPENDENT_RATERS_REQUIRED"
        ),
    }


def prepare_human_judgment_protocol(
    *,
    output_dir: Path,
    result_path: Path | None = None,
    reveal_path: Path | None = None,
) -> Dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    tasks = _task_rows()
    tasks_path = output_dir / "development_scenario_packet.json"
    tasks_path.write_text(
        json.dumps(tasks, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    rater_path = output_dir / "independent_rater_sheet.csv"
    _write_rater_sheet(rater_path, tasks)
    contract = {
        "schema_version": "aion.hexcore.human_judgment_contract.v1",
        "created_at": _utc_timestamp(),
        "capabilities": list(CAPABILITIES),
        "rating_scale": {
            "minimum": 1,
            "maximum": 5,
            "fields": list(RATING_FIELDS),
        },
        "minimum_complete_independent_raters": 3,
        "blind_pairwise_order_required": True,
        "candidate_identity_hidden_from_raters": True,
        "development_scenarios_are_not_sealed_evaluation": True,
        "promotion_authority": "independent_human_panel_plus_CAU",
        "tasks_sha256": _sha256(tasks_path),
        "rater_sheet_sha256": _sha256(rater_path),
    }
    contract_path = output_dir / "human_judgment_contract.json"
    contract_path.write_text(
        json.dumps(contract, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    reveal = _valid_reveals(
        reveal_path,
        task_ids={row["task_id"] for row in tasks},
    )
    gate = {
        "protocol_frozen": True,
        "capability_families": len(CAPABILITIES),
        "development_tasks": len(tasks),
        "independent_human_evaluation_complete": reveal["valid"],
        "promotion_open": reveal["valid"],
        "reason": reveal["reason"],
    }
    result = {
        "schema_version": "aion.hexcore.human_judgment_protocol.v1",
        "passed": True,
        "capability_promotion": False,
        "gate": gate,
        "contract": contract,
        "reveal_audit": reveal,
        "artifacts": {
            "tasks": str(tasks_path),
            "rater_sheet": str(rater_path),
            "contract": str(contract_path),
        },
        "boundary": (
            "This freezes a development protocol and blank independent-rating "
            "instrument. It does not provide human judgments, an independent "
            "sealed cohort, or evidence of social, commonsense or creative "
            "capability. An internal developer cannot self-certify this gate."
        ),
    }
    if result_path is not None:
        result_path = result_path.resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(
            json.dumps(result, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze the independent human-judgment protocol."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--reveal-path", type=Path)
    args = parser.parse_args()
    result = prepare_human_judgment_protocol(
        output_dir=args.output_dir,
        result_path=args.result_path,
        reveal_path=args.reveal_path,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
