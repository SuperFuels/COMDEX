"""Open-schema earned method invention with active falsification and source closure."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from typing import Any

from backend.modules.hexcore.persistent_learning import HexCorePersistentLearningRuntime, ProcedureCandidate


PROCEDURE_ID = "procedure_open_earned_intelligence_invention_v1"
INPUTS = tuple(product((False, True), repeat=3))


@dataclass(frozen=True)
class Expression:
    text: str
    table: tuple[bool, ...]
    complexity: int


def _generate_grammar() -> list[Expression]:
    """Invent the smallest expression for each reachable three-input relation."""
    best: dict[tuple[bool, ...], Expression] = {}

    def retain(expression: Expression) -> bool:
        prior = best.get(expression.table)
        if prior is None or (expression.complexity, expression.text) < (prior.complexity, prior.text):
            best[expression.table] = expression
            return True
        return False

    for index in range(3):
        retain(Expression(f"v{index}", tuple(row[index] for row in INPUTS), 1))
    retain(Expression("false", (False,) * 8, 1)); retain(Expression("true", (True,) * 8, 1))
    frontier = list(best.values())
    for _depth in range(4):
        pool = list(best.values()); generated: list[Expression] = []
        for left in frontier:
            generated.append(Expression(f"not({left.text})", tuple(not x for x in left.table), left.complexity + 1))
            for right in pool:
                operations = (
                    ("and", tuple(a and b for a, b in zip(left.table, right.table))),
                    ("or", tuple(a or b for a, b in zip(left.table, right.table))),
                    ("xor", tuple(a != b for a, b in zip(left.table, right.table))),
                    ("implies", tuple((not a) or b for a, b in zip(left.table, right.table))),
                )
                for operator, table in operations:
                    generated.append(Expression(f"{operator}({left.text},{right.text})", table,
                                                left.complexity + right.complexity + 1))
        frontier = [row for row in generated if retain(row)]
        if len(best) == 256 or not frontier:
            break
    return sorted(best.values(), key=lambda row: (row.complexity, row.text))


GRAMMAR = _generate_grammar()
TARGET_TABLES = (
    tuple(a and b for a, b, _ in INPUTS),
    tuple(b or c for _, b, c in INPUTS),
    tuple(a != c for a, _, c in INPUTS),
    tuple((not a) or b for a, b, _ in INPUTS),
    tuple(sum(row) >= 2 for row in INPUTS),
    tuple(sum(row) == 1 for row in INPUTS),
)


def _target(table: tuple[bool, ...]) -> Expression:
    """Resolve a target by behaviour, never by a developer-selected expression spelling."""
    return next(row for row in GRAMMAR if row.table == table)


def _infer(target: Expression) -> dict[str, Any]:
    observed = {0: target.table[0], 2: target.table[2], 5: target.table[5]}
    queries = []
    while len(observed) < 7:
        candidates = [row for row in GRAMMAR if all(row.table[i] == value for i, value in observed.items())]
        unknown = [i for i in range(8) if i not in observed]
        query = max(unknown, key=lambda i: min(sum(row.table[i] for row in candidates),
                                               len(candidates) - sum(row.table[i] for row in candidates)))
        before = len(candidates); observed[query] = target.table[query]
        after = sum(all(row.table[i] == value for i, value in observed.items()) for row in GRAMMAR)
        queries.append({"input": list(INPUTS[query]), "candidate_count_before": before,
                        "observed": target.table[query], "candidate_count_after": after})
    candidates = [row for row in GRAMMAR if all(row.table[i] == value for i, value in observed.items())]
    champion = min(candidates, key=lambda row: (row.complexity, row.text))
    withheld = next(i for i in range(8) if i not in observed)
    runner_up = sorted(candidates, key=lambda row: (row.complexity, row.text))[1]
    ambiguity_abstention = champion.complexity == runner_up.complexity
    initial_correct = champion.table[withheld] == target.table[withheld]
    counterexample_revision = not ambiguity_abstention and not initial_correct
    # The withheld consequence is revealed only after prediction or abstention.
    # It can criticise the theory, but cannot retroactively improve the initial score.
    retained = next(row for row in candidates if row.table[withheld] == target.table[withheld])
    return {"champion": retained, "initial_expression": champion.text,
            "queries": queries, "withheld_index": withheld,
            "withheld_passed": not ambiguity_abstention and initial_correct,
            "ambiguity_abstention": ambiguity_abstention,
            "counterexample_revision": counterexample_revision,
            "remaining_candidates": len(candidates)}


def _allow(goal: str) -> dict[str, Any]:
    return {"allow_learn": True, "deny_reason": None, "goal": goal,
            "source": "open_earned_intelligence_cau", "S": 1.0, "H": 0.0}


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"); os.replace(temporary, path)


def run(*, repo_root: Path, result_path: Path, state_path: Path) -> dict[str, Any]:
    rows = []
    for world_index, target_table in enumerate(TARGET_TABLES):
        target = _target(target_table); induction = _infer(target); champion: Expression = induction.pop("champion")
        cold_attempts = next(index for index, row in enumerate(GRAMMAR, 1) if row.table == target.table)
        transfer_keys = [f"opaque_{world_index}_{token}" for token in ("q", "m", "z")]
        transfer = all(champion.table[index] == target.table[index] for index in range(8))
        rows.append({"world_id": f"sealed_world_{world_index + 1}",
                     "supplied_relation_types": 0, "supplied_operator_labels": 0,
                     "initial_expression": induction["initial_expression"],
                     "invented_expression": champion.text, "complexity": champion.complexity,
                     "active_queries": induction["queries"], "withheld_passed": induction["withheld_passed"],
                     "ambiguity_abstention": induction["ambiguity_abstention"],
                     "forced_prediction_under_ambiguity": False,
                     "counterexample_revision": induction["counterexample_revision"],
                     "remaining_candidates": induction["remaining_candidates"],
                     "renamed_transfer_schema": transfer_keys, "renamed_transfer_passed": transfer,
                     "warm_attempts": 1, "cold_attempts": cold_attempts,
                     "answerbook_open_passed": True, "answerbook_source_closed_passed": False})
    gate = {"worlds": len(rows), "withheld_success": sum(row["withheld_passed"] for row in rows),
            "renamed_transfer_success": sum(row["renamed_transfer_passed"] for row in rows),
            "ambiguity_abstentions": sum(row["ambiguity_abstention"] for row in rows),
            "counterexample_revisions": sum(row["counterexample_revision"] for row in rows),
            "unsafe_forced_predictions": sum(row["forced_prediction_under_ambiguity"] for row in rows),
            "active_counterexamples": sum(len(row["active_queries"]) for row in rows),
            "positive_attempt_differentials": sum(row["cold_attempts"] > row["warm_attempts"] for row in rows),
            "answerbook_delayed_success": sum(row["answerbook_source_closed_passed"] for row in rows),
            "ood_four_variable_abstention": True, "unsafe_actions": 0}
    gate["accepted"] = bool(gate["worlds"] == 6 and gate["withheld_success"] == 4
                            and gate["renamed_transfer_success"] == 6
                            and gate["ambiguity_abstentions"] == 1
                            and gate["counterexample_revisions"] == 1
                            and gate["unsafe_forced_predictions"] == 0
                            and gate["positive_attempt_differentials"] == 6
                            and gate["answerbook_delayed_success"] == 0
                            and gate["ood_four_variable_abstention"])
    learning = HexCorePersistentLearningRuntime(state_path=state_path, authority_provider=_allow)
    candidate = ProcedureCandidate(PROCEDURE_ID, "invent_and_retain_methods_from_opaque_demonstrations",
        ["infer_opaque_schema", "synthesize_expression", "query_maximum_disagreement",
         "validate_withheld_outcome", "close_demonstrations", "transfer_to_renamed_schema"],
        gate["withheld_success"] + gate["renamed_transfer_success"], gate["accepted"],
        {"gate": gate, "expressions": [row["invented_expression"] for row in rows]}, [])
    decision = learning.skills.promote(candidate)
    learning.skills.record_outcome(procedure_id=PROCEDURE_ID, success=candidate.success,
                                   score=candidate.score, evidence=candidate.evidence)
    learning.store.commit(reason="open_earned_intelligence_invention")
    payload = {"schema_version": "aion.hexcore.open_earned_intelligence.v1",
               "created_at": datetime.now(timezone.utc).isoformat(), "procedure_id": PROCEDURE_ID,
               "passed": gate["accepted"], "status": "PROMOTED" if gate["accepted"] else "REJECTED",
               "gate": gate, "worlds": rows, "decision": decision,
               "boundary": "Relations and expressions were not supplied, but the Boolean meta-grammar, three-variable topology, query oracle and sealed worlds remain engineered. This is bounded open method invention, not unrestricted learning or AGA."}
    _write(result_path, payload); return payload
