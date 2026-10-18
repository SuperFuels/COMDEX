"""Quarantined induction and promotion of verified AtomSheet contracts.

The learner never treats a model response as proof.  It accepts only outcomes
that carry an independent verifier identity and a response hash, searches a
small audited operator library, challenges the surviving expression on held
out observations, and promotes only a unique exact match.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Optional, Sequence

from backend.modules.aion_learning.vault_store import AionLearningVaultStore


MAX_ABSOLUTE_INPUT = Decimal("1e12")
EXECUTOR_VERSION = "aion.learned_template_executor.v3"
INTENT_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
FIELD_PATTERN = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha(payload: Any) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def _decimal(value: Any) -> Decimal:
    number = Decimal(str(value).replace(",", ""))
    if not number.is_finite() or abs(number) > MAX_ABSOLUTE_INPUT:
        raise ValueError("numeric value is outside the learned-sheet boundary")
    return number


def _display(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


@dataclass(frozen=True)
class OperatorTemplate:
    template_id: str
    arity: int
    expression: str
    verification: str
    evaluate: Callable[[Sequence[Decimal]], Decimal]
    verify: Callable[[Sequence[Decimal], Decimal], bool]


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        raise ArithmeticError("division by zero")
    with localcontext() as context:
        context.prec = 50
        return numerator / denominator


TEMPLATES: tuple[OperatorTemplate, ...] = (
    OperatorTemplate("sum2.v1", 2, "a + b", "result - a == b", lambda v: v[0] + v[1], lambda v, r: r - v[0] == v[1]),
    OperatorTemplate("difference_ab.v1", 2, "a - b", "result + b == a", lambda v: v[0] - v[1], lambda v, r: r + v[1] == v[0]),
    OperatorTemplate("difference_ba.v1", 2, "b - a", "result + a == b", lambda v: v[1] - v[0], lambda v, r: r + v[0] == v[1]),
    OperatorTemplate("product2.v1", 2, "a * b", "result == a * b", lambda v: v[0] * v[1], lambda v, r: r == v[0] * v[1]),
    OperatorTemplate("ratio_ab.v1", 2, "a / b", "result * b == a", lambda v: _ratio(v[0], v[1]), lambda v, r: r * v[1] == v[0]),
    OperatorTemplate("ratio_ba.v1", 2, "b / a", "result * a == b", lambda v: _ratio(v[1], v[0]), lambda v, r: r * v[0] == v[1]),
    OperatorTemplate("percentage_of.v1", 2, "a * b / 100", "result * 100 == a * b", lambda v: v[0] * v[1] / Decimal("100"), lambda v, r: r * Decimal("100") == v[0] * v[1]),
    OperatorTemplate("increase_a_percent_b.v1", 2, "a * (1 + b / 100)", "result * 100 == a * (100 + b)", lambda v: v[0] * (Decimal("1") + v[1] / Decimal("100")), lambda v, r: r * Decimal("100") == v[0] * (Decimal("100") + v[1])),
    OperatorTemplate("decrease_a_percent_b.v1", 2, "a * (1 - b / 100)", "result * 100 == a * (100 - b)", lambda v: v[0] * (Decimal("1") - v[1] / Decimal("100")), lambda v, r: r * Decimal("100") == v[0] * (Decimal("100") - v[1])),
    OperatorTemplate("mean2.v1", 2, "(a + b) / 2", "result * 2 == a + b", lambda v: (v[0] + v[1]) / Decimal("2"), lambda v, r: r * Decimal("2") == v[0] + v[1]),
    OperatorTemplate("sum3.v1", 3, "a + b + c", "result - a - b == c", lambda v: v[0] + v[1] + v[2], lambda v, r: r - v[0] - v[1] == v[2]),
    OperatorTemplate("last_minus_first_two.v1", 3, "c - a - b", "result + a + b == c", lambda v: v[2] - v[0] - v[1], lambda v, r: r + v[0] + v[1] == v[2]),
    OperatorTemplate("product3.v1", 3, "a * b * c", "result == a * b * c", lambda v: v[0] * v[1] * v[2], lambda v, r: r == v[0] * v[1] * v[2]),
    OperatorTemplate("mean3.v1", 3, "(a + b + c) / 3", "result * 3 == a + b + c", lambda v: (v[0] + v[1] + v[2]) / Decimal("3"), lambda v, r: r * Decimal("3") == v[0] + v[1] + v[2]),
)
TEMPLATE_INDEX = {template.template_id: template for template in TEMPLATES}


@dataclass(frozen=True)
class VerifiedModelOutcome:
    intent: str
    inputs: Mapping[str, str]
    result: str
    verifier_id: str
    model_id: str
    response_sha256: str
    verifier_passed: bool = True
    human_approved: bool = False
    created_at: Optional[str] = None

    def normalized(self) -> "VerifiedModelOutcome":
        intent = self.intent.strip().upper()
        if not INTENT_PATTERN.fullmatch(intent):
            raise ValueError("intent must be an upper-case stable identifier")
        if not 2 <= len(self.inputs) <= 3:
            raise ValueError("the first learner supports exactly two or three inputs")
        fields = sorted(self.inputs)
        if any(not FIELD_PATTERN.fullmatch(field) for field in fields):
            raise ValueError("input names must be stable lower-case identifiers")
        normalized_inputs = {field: _display(_decimal(self.inputs[field])) for field in fields}
        result = _display(_decimal(self.result))
        verifier_id = self.verifier_id.strip()
        model_id = self.model_id.strip()
        response_hash = self.response_sha256.strip().lower()
        if not verifier_id or not model_id:
            raise ValueError("model and independent verifier identities are required")
        if not SHA256_PATTERN.fullmatch(response_hash):
            raise ValueError("response_sha256 must contain 64 lower-case hex characters")
        return VerifiedModelOutcome(
            intent=intent,
            inputs=normalized_inputs,
            result=result,
            verifier_id=verifier_id,
            model_id=model_id,
            response_sha256=response_hash,
            verifier_passed=bool(self.verifier_passed),
            human_approved=bool(self.human_approved),
            created_at=self.created_at or _utc_now(),
        )


@dataclass(frozen=True)
class LearningDecision:
    schema_version: str
    intent: str
    outcome_sha256: str
    observation_count: int
    distinct_input_count: int
    verifier_count: int
    candidate_template_ids: tuple[str, ...]
    status: str
    reason: str
    promoted_sheet: Optional[Mapping[str, Any]]
    contract_sha256: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LearnedExecutionResult:
    schema_version: str
    route: str
    intent: str
    answer: Optional[str]
    structured_result: Optional[Mapping[str, str]]
    model_call_required: bool
    proof_receipt: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class LearnedAtomSheetStore:
    """Durable quarantine, promotion and execution store."""

    def __init__(
        self,
        database_path: Path | None = None,
        promoted_dir: Path | None = None,
        *,
        minimum_observations: int = 6,
        holdout_observations: int = 2,
        minimum_verifiers: int = 2,
        vault_store: AionLearningVaultStore | None = None,
    ) -> None:
        if minimum_observations < 4 or holdout_observations < 1:
            raise ValueError("promotion requires at least four observations and one holdout")
        if minimum_observations <= holdout_observations:
            raise ValueError("training observations must remain after the holdout split")
        self.database_path = database_path
        self.promoted_dir = promoted_dir
        self.minimum_observations = minimum_observations
        self.holdout_observations = holdout_observations
        self.minimum_verifiers = minimum_verifiers
        self.vault_store = vault_store or AionLearningVaultStore()
        self._state_id = "aion_inference_learned_atomsheets_v1"
        saved = self.vault_store.get_state(
            self._state_id,
            {"outcomes": {}, "candidates": {}, "promoted": {}, "audit_sequence": 0},
        )
        self._outcomes: dict[str, dict[str, Any]] = {
            str(key): dict(value) for key, value in dict(saved.get("outcomes", {})).items()
        }
        self._candidates: dict[str, dict[str, Any]] = {
            str(key): dict(value) for key, value in dict(saved.get("candidates", {})).items()
        }
        self._promoted: dict[str, dict[str, Any]] = {
            str(key): dict(value) for key, value in dict(saved.get("promoted", {})).items()
        }
        self._audit_sequence = int(saved.get("audit_sequence", 0))

    def _persist(self) -> None:
        if not self.vault_store.enabled:
            return
        self.vault_store.put_state(
            self._state_id,
            {
                "schema_version": "aion.inference.learned-atomsheets.v2",
                "outcomes": self._outcomes,
                "candidates": self._candidates,
                "promoted": self._promoted,
                "audit_sequence": self._audit_sequence,
            },
        )

    def _audit(self, event_type: str, intent: str, payload: Mapping[str, Any]) -> None:
        raw = _canonical(payload).decode("utf-8")
        self._audit_sequence += 1
        timestamp = _utc_now()
        event = {
            "event_type": "learned_atomsheet_audit",
            "learning_event_type": event_type,
            "intent": intent,
            "payload_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            "payload": dict(payload),
            "sequence": self._audit_sequence,
            "timestamp": timestamp,
            "ts_utc": timestamp,
        }
        if self.vault_store.enabled:
            event_id = f"learned-atomsheet-{self._audit_sequence}-{_sha(event)[:24]}"
            self.vault_store.append_event(event_id, {**event, "event_id": event_id})
        self._persist()

    def observe(self, outcome: VerifiedModelOutcome, *, auto_promote: bool = True) -> LearningDecision:
        normalized = outcome.normalized()
        outcome_payload = asdict(normalized)
        outcome_hash = _sha(outcome_payload)
        self._outcomes.setdefault(outcome_hash, outcome_payload)
        self._audit("outcome_observed", normalized.intent, {"outcome_sha256": outcome_hash})
        return self.evaluate(normalized.intent, outcome_hash=outcome_hash, auto_promote=auto_promote)

    def _observations(self, intent: str) -> list[dict[str, Any]]:
        rows = [
            {
                "outcome_sha256": outcome_hash,
                "inputs": dict(row["inputs"]),
                "result": row["result"],
                "verifier_id": row["verifier_id"],
                "human_approved": bool(row["human_approved"]),
                "created_at": row["created_at"],
            }
            for outcome_hash, row in self._outcomes.items()
            if row["intent"] == intent and bool(row["verifier_passed"])
        ]
        return sorted(rows, key=lambda row: (str(row["created_at"]), row["outcome_sha256"]))

    @staticmethod
    def _matching_templates(observations: Sequence[Mapping[str, Any]]) -> list[OperatorTemplate]:
        if not observations:
            return []
        fields = sorted(observations[0]["inputs"])
        if any(sorted(observation["inputs"]) != fields for observation in observations):
            return []
        matches: list[OperatorTemplate] = []
        for template in TEMPLATES:
            if template.arity != len(fields):
                continue
            accepted = True
            for observation in observations:
                values = [_decimal(observation["inputs"][field]) for field in fields]
                expected = _decimal(observation["result"])
                try:
                    actual = template.evaluate(values)
                except ArithmeticError:
                    accepted = False
                    break
                if actual != expected or not template.verify(values, actual):
                    accepted = False
                    break
            if accepted:
                matches.append(template)
        return matches

    def evaluate(self, intent: str, *, outcome_hash: str = "", auto_promote: bool = True) -> LearningDecision:
        intent = intent.strip().upper()
        observations = self._observations(intent)
        distinct_inputs = {json.dumps(item["inputs"], sort_keys=True) for item in observations}
        verifiers = {item["verifier_id"] for item in observations}
        reason = "minimum_observations_not_met"
        status = "quarantined"
        candidate_ids: tuple[str, ...] = ()
        promoted_sheet: Optional[Mapping[str, Any]] = None
        contract_hash: Optional[str] = None

        existing = self.promoted(intent)
        if existing is not None:
            template = TEMPLATE_INDEX[existing["operator_template_id"]]
            still_valid = template in self._matching_templates(observations)
            candidate_ids = (template.template_id,)
            promoted_sheet = existing
            contract_hash = str(existing["contract_sha256"])
            status = "promoted" if still_valid else "promoted_drift_alert"
            reason = "existing_promotion_still_validated" if still_valid else "verified_outcome_conflicts_with_promoted_contract"
        elif len(observations) >= self.minimum_observations:
            if len(distinct_inputs) < self.minimum_observations:
                reason = "insufficient_input_diversity"
            elif len(verifiers) < self.minimum_verifiers:
                reason = "insufficient_verifier_diversity"
            else:
                training = observations[:-self.holdout_observations]
                challenge = observations[-self.holdout_observations:]
                candidates = self._matching_templates(training)
                survivors = [
                    candidate
                    for candidate in candidates
                    if candidate in self._matching_templates(challenge)
                ]
                candidate_ids = tuple(candidate.template_id for candidate in survivors)
                if not survivors:
                    reason = "no_exact_operator_template"
                elif len(survivors) > 1:
                    reason = "operator_template_ambiguous"
                else:
                    status = "promotion_ready"
                    reason = "unique_exact_template_passed_holdout"
                    if auto_promote:
                        promoted_sheet, contract_hash = self._promote(intent, observations, survivors[0])
                        status = "promoted"
                        reason = "automatic_promotion_gates_passed"

        candidate_payload = {
            "schema_version": "aion.learned_atomsheet.candidate.v1",
            "intent": intent,
            "observation_count": len(observations),
            "distinct_input_count": len(distinct_inputs),
            "verifier_count": len(verifiers),
            "candidate_template_ids": candidate_ids,
            "status": status,
            "reason": reason,
        }
        self._candidates[intent] = {**candidate_payload, "updated_at": _utc_now()}
        self._audit("candidate_evaluated", intent, candidate_payload)
        return LearningDecision(
            schema_version="aion.learned_atomsheet.decision.v1",
            intent=intent,
            outcome_sha256=outcome_hash,
            observation_count=len(observations),
            distinct_input_count=len(distinct_inputs),
            verifier_count=len(verifiers),
            candidate_template_ids=candidate_ids,
            status=status,
            reason=reason,
            promoted_sheet=promoted_sheet,
            contract_sha256=contract_hash,
        )

    def _promote(
        self,
        intent: str,
        observations: Sequence[Mapping[str, Any]],
        template: OperatorTemplate,
    ) -> tuple[Mapping[str, Any], str]:
        fields = sorted(observations[0]["inputs"])
        slug = intent.casefold().replace("_", ".")
        sheet = {
            "schema_version": "aion.atomsheet.learned.v1",
            "sheet_id": f"aion.learned.{slug}.v1",
            "intent": intent,
            "status": "promoted",
            "origin": "verified_model_outcomes",
            "executor_version": EXECUTOR_VERSION,
            "required_inputs": fields,
            "operator_template_id": template.template_id,
            "symbol_binding": {symbol: field for symbol, field in zip(("a", "b", "c"), fields)},
            "operation": template.expression,
            "verification": template.verification,
            "validity": {"maximum_absolute_input": str(MAX_ABSOLUTE_INPUT), "exact_decimal": True},
            "promotion_evidence": {
                "observation_count": len(observations),
                "distinct_input_count": len({json.dumps(item["inputs"], sort_keys=True) for item in observations}),
                "verifier_ids": sorted({item["verifier_id"] for item in observations}),
                "human_approved_count": sum(item["human_approved"] for item in observations),
                "outcome_sha256s": [item["outcome_sha256"] for item in observations],
                "holdout_observations": self.holdout_observations,
            },
        }
        sheet["validity"]["positive_inputs"] = [
            field for field in fields
            if all(_decimal(item["inputs"][field]) > 0 for item in observations)
        ]
        sheet["validity"]["percentage_inputs"] = [
            field for field in fields if field.endswith("_percent")
        ]
        contract_hash = _sha(sheet)
        envelope = {**sheet, "contract_sha256": contract_hash, "promoted_at": _utc_now()}
        existing = self._promoted.get(intent)
        if existing is not None and existing.get("contract_sha256") != contract_hash:
            raise RuntimeError("a promoted intent cannot be replaced without explicit version migration")
        self._promoted.setdefault(intent, envelope)
        self._audit("atomsheet_promoted", intent, {"contract_sha256": contract_hash})
        return envelope, contract_hash

    def promoted(self, intent: str) -> Optional[Mapping[str, Any]]:
        row = self._promoted.get(intent.strip().upper())
        return dict(row) if row is not None else None

    def execute(self, intent: str, inputs: Mapping[str, Any]) -> LearnedExecutionResult:
        normalized_intent = intent.strip().upper()
        sheet = self.promoted(normalized_intent)
        if sheet is None:
            return LearnedExecutionResult(
                schema_version="aion.learned_atomsheet.execution.v1",
                route="full_model",
                intent=normalized_intent,
                answer=None,
                structured_result=None,
                model_call_required=True,
                proof_receipt={"gate_passed": False, "gate_reason": "no_promoted_atomsheet"},
            )
        fields = list(sheet["required_inputs"])
        if sheet.get("executor_version") != EXECUTOR_VERSION:
            return LearnedExecutionResult(
                "aion.learned_atomsheet.execution.v1", "full_model", normalized_intent, None, None, True,
                {"gate_passed": False, "gate_reason": "learned_executor_version_mismatch", "contract_sha256": sheet["contract_sha256"]},
            )
        if set(inputs) != set(fields):
            reason = "required_inputs_do_not_match"
            return LearnedExecutionResult(
                "aion.learned_atomsheet.execution.v1", "full_model", normalized_intent, None, None, True,
                {"gate_passed": False, "gate_reason": reason, "contract_sha256": sheet["contract_sha256"]},
            )
        try:
            values = [_decimal(inputs[field]) for field in fields]
            normalized_by_field = dict(zip(fields, values))
            if any(normalized_by_field[field] <= 0 for field in sheet["validity"].get("positive_inputs", ())):
                raise ValueError("input violates learned positive-domain boundary")
            if any(
                normalized_by_field[field] < 0 or normalized_by_field[field] > 100
                for field in sheet["validity"].get("percentage_inputs", ())
            ):
                raise ValueError("input violates learned percentage-domain boundary")
            template = TEMPLATE_INDEX[sheet["operator_template_id"]]
            result = template.evaluate(values)
            verified = template.verify(values, result)
        except (ValueError, InvalidOperation, ArithmeticError, KeyError):
            verified = False
            result = Decimal("0")
        if not verified:
            return LearnedExecutionResult(
                "aion.learned_atomsheet.execution.v1", "full_model", normalized_intent, None, None, True,
                {"gate_passed": False, "gate_reason": "learned_sheet_verification_failed", "contract_sha256": sheet["contract_sha256"]},
            )
        structured = {"value": _display(result)}
        normalized_inputs = {field: _display(value) for field, value in zip(fields, values)}
        glyph_address = f"glyph:sha256:{_sha({'intent': normalized_intent, 'inputs': normalized_inputs})}"
        receipt = {
            "gate_passed": True,
            "gate_reason": "promoted_atomsheet_boundary",
            "sheet_id": sheet["sheet_id"],
            "contract_sha256": sheet["contract_sha256"],
            "operator_template_id": template.template_id,
            "inverse_verified": True,
            "result_sha256": _sha(structured),
            "glyph_address": glyph_address,
            "normalized_inputs": normalized_inputs,
            "model_calls": 0,
        }
        return LearnedExecutionResult(
            schema_version="aion.learned_atomsheet.execution.v1",
            route="verified_learned_atomsheet",
            intent=normalized_intent,
            answer=structured["value"],
            structured_result=structured,
            model_call_required=False,
            proof_receipt=receipt,
        )

    def route_text(self, text: str) -> LearnedExecutionResult:
        """Recognize a promoted arithmetic family from bounded ordinary English."""
        lowered = " ".join(text.casefold().split())
        if re.search(
            r"\b(?:and|then)\s+(?!(?:do\s+not|don't|never|not)\b)(?:book|schedule|send|email|pay|order|contact|write|create)\b",
            lowered,
        ):
            return LearnedExecutionResult(
                "aion.learned_atomsheet.execution.v1", "full_model", "UNKNOWN", None, None, True,
                {"gate_passed": False, "gate_reason": "compound_action_requires_orchestration"},
            )
        family_markers = sum((
            bool(re.search(r"\b(?:markup|mark-up|mark\s+up)\b", lowered)),
            bool(re.search(r"\b(?:discount|off)\b", lowered)),
            bool(re.search(r"\b(?:sales\s+)?tax\b", lowered)),
            bool(re.search(r"\b(?:labou?r|hours?|per\s+hour|an\s+hour)\b", lowered)),
        ))
        if family_markers > 1:
            return LearnedExecutionResult(
                "aion.learned_atomsheet.execution.v1", "full_model", "UNKNOWN", None, None, True,
                {"gate_passed": False, "gate_reason": "multiple_learned_families_detected"},
            )
        if len(re.findall(r"[+-]?\d[\d,]*(?:\.\d+)?", lowered)) != 2:
            return LearnedExecutionResult(
                "aion.learned_atomsheet.execution.v1", "full_model", "UNKNOWN", None, None, True,
                {"gate_passed": False, "gate_reason": "learned_text_numeric_ambiguity"},
            )
        number = r"[+-]?\d[\d,]*(?:\.\d+)?"
        route_patterns: tuple[tuple[str, Mapping[str, str], str], ...] = (
            ("CALCULATE_MARKED_UP_PRICE", {"cost": "base", "markup_percent": "percent"},
             rf"(?:add|apply)\s+(?P<percent>{number})\s*(?:%|percent)\s+(?:markup|mark-up)\s+(?:to|on)\s+(?P<base>{number})"),
            ("CALCULATE_MARKED_UP_PRICE", {"cost": "base", "markup_percent": "percent"},
             rf"mark\s*up\s+(?P<base>{number})\s+by\s+(?P<percent>{number})\s*(?:%|percent)"),
            ("CALCULATE_MARKED_UP_PRICE", {"cost": "base", "markup_percent": "percent"},
             rf"(?P<base>{number})\s+(?:with|at)\s+(?:a\s+)?(?P<percent>{number})\s*(?:%|percent)\s+(?:markup|mark-up)"),
            ("CALCULATE_DISCOUNTED_PRICE", {"cost": "base", "discount_percent": "percent"},
             rf"apply\s+(?P<percent>{number})\s*(?:%|percent)\s+discount\s+(?:to|on)\s+(?P<base>{number})"),
            ("CALCULATE_DISCOUNTED_PRICE", {"cost": "base", "discount_percent": "percent"},
             rf"(?:take|subtract)\s+(?P<percent>{number})\s*(?:%|percent)\s+off\s+(?P<base>{number})"),
            ("CALCULATE_DISCOUNTED_PRICE", {"cost": "base", "discount_percent": "percent"},
             rf"discount\s+(?P<base>{number})\s+by\s+(?P<percent>{number})\s*(?:%|percent)"),
            ("CALCULATE_DISCOUNTED_PRICE", {"cost": "base", "discount_percent": "percent"},
             rf"(?P<base>{number})\s+(?:with|at)\s+(?:a\s+)?(?P<percent>{number})\s*(?:%|percent)\s+discount"),
            ("CALCULATE_PRICE_WITH_TAX", {"subtotal": "base", "tax_percent": "percent"},
             rf"(?:add|apply)\s+(?P<percent>{number})\s*(?:%|percent)\s+(?:sales\s+)?tax\s+(?:to|on)\s+(?P<base>{number})"),
            ("CALCULATE_PRICE_WITH_TAX", {"subtotal": "base", "tax_percent": "percent"},
             rf"(?P<base>{number})\s+(?:with|plus)\s+(?P<percent>{number})\s*(?:%|percent)\s+(?:sales\s+)?tax"),
            ("CALCULATE_PRICE_WITH_TAX", {"subtotal": "base", "tax_percent": "percent"},
             rf"total\s+(?:price\s+)?including\s+(?P<percent>{number})\s*(?:%|percent)\s+(?:sales\s+)?tax\s+(?:on|for)\s+(?P<base>{number})"),
            ("CALCULATE_LABOUR_COST", {"hourly_rate": "rate", "hours": "hours"},
             rf"(?P<rate>{number})\s+(?:per|an)\s+hour\s+(?:for|over|and)\s+(?P<hours>{number})\s+hours?"),
            ("CALCULATE_LABOUR_COST", {"hourly_rate": "rate", "hours": "hours"},
             rf"(?P<hours>{number})\s+hours?\s+(?:at|for)\s+(?P<rate>{number})\s+(?:per|an)\s+hour"),
        )
        candidates: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
        for intent, bindings, pattern in route_patterns:
            for match in re.finditer(pattern, lowered):
                inputs = tuple(sorted(
                    (field, match.group(group).replace(",", ""))
                    for field, group in bindings.items()
                ))
                candidates.add((intent, inputs))
        if len(candidates) != 1:
            return LearnedExecutionResult(
                "aion.learned_atomsheet.execution.v1", "full_model", "UNKNOWN", None, None, True,
                {"gate_passed": False, "gate_reason": "no_unambiguous_promoted_text_match"},
            )
        intent, inputs = next(iter(candidates))
        return self.execute(intent, dict(inputs))

    def status(self) -> Mapping[str, Any]:
        observations = len(self._outcomes)
        verified = sum(bool(row["verifier_passed"]) for row in self._outcomes.values())
        candidates = len(self._candidates)
        promoted = len(self._promoted)
        last_sequence = self._audit_sequence
        return {
            "schema_version": "aion.learned_atomsheet.status.v1",
            "observed_outcomes": observations,
            "verified_outcomes": verified,
            "candidate_intents": candidates,
            "promoted_atomsheets": promoted,
            "last_audit_sequence": last_sequence,
            "minimum_observations": self.minimum_observations,
            "holdout_observations": self.holdout_observations,
            "minimum_verifiers": self.minimum_verifiers,
        }
