"""First deterministic Semantic Gateway and guarded AtomSheet bypass."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Optional


PROFIT_SHEET_PATH = Path(__file__).with_name("atomsheets") / "profit.v1.json"
_CURRENCY = r"(?P<currency>EUR|GBP|USD|€|£|\$)?\s*"
_NUMBER = r"(?P<value>\d[\d,]*(?:\.\d+)?)"


def _hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _normalise_currency(value: Optional[str]) -> Optional[str]:
    return {"€": "EUR", "£": "GBP", "$": "USD"}.get(value or "", value)


def _decimal(value: str) -> Decimal:
    return Decimal(value.replace(",", ""))


def _display(value: Decimal) -> str:
    rendered = format(value.quantize(Decimal("0.01")), "f")
    return rendered.rstrip("0").rstrip(".")


def _normalise_request_text(text: str) -> str:
    """Preserve public meaning while removing transport-only whitespace."""
    return " ".join(text.split())


@dataclass(frozen=True)
class MeaningCapsule:
    schema_version: str
    glyph_address: str
    intent: str
    entities: Mapping[str, str]
    currency: Optional[str]
    constraints: tuple[str, ...]
    ambiguity_score: float
    source_sha256: str


@dataclass(frozen=True)
class RouteCandidate:
    route: str
    score: float
    eligible: bool
    reason: str


@dataclass(frozen=True)
class GatewayResult:
    schema_version: str
    route: str
    model_call_required: bool
    answer: Optional[str]
    structured_result: Optional[Mapping[str, str]]
    meaning_capsule: MeaningCapsule
    candidates: tuple[RouteCandidate, ...]
    minimal_model_prompt: Optional[str]
    proof_receipt: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class SemanticGateway:
    """Compile natural language into a governed route without invoking a model."""

    _FIELD_PATTERNS = {
        "revenue": (
            rf"(?:revenue(?:\s+of)?|charg(?:e|ed)|selling\s+price|price)\s*(?:of|is|=|:)?\s*{_CURRENCY}{_NUMBER}",
            rf"{_CURRENCY}{_NUMBER}\s*(?:of\s+)?(?:revenue|charged|selling\s+price)",
        ),
        "materials": (
            rf"(?:materials?|material\s+cost)\s*(?:of|is|are|=|:)?\s*{_CURRENCY}{_NUMBER}",
            rf"{_CURRENCY}{_NUMBER}\s*(?:on|for)\s*materials?",
        ),
        "labour": (
            rf"(?:labou?r|labou?r\s+cost)\s*(?:of|is|are|=|:)?\s*{_CURRENCY}{_NUMBER}",
            rf"{_CURRENCY}{_NUMBER}\s*(?:on|for)\s*labou?r",
        ),
    }

    def __init__(self, profit_sheet_path: Path = PROFIT_SHEET_PATH) -> None:
        self.profit_sheet_path = profit_sheet_path
        self.profit_sheet_bytes = profit_sheet_path.read_bytes()
        self.profit_sheet = json.loads(self.profit_sheet_bytes)
        self.profit_sheet_sha256 = hashlib.sha256(self.profit_sheet_bytes).hexdigest()

    def _extract_field(self, text: str, field_name: str) -> Optional[tuple[Decimal, Optional[str]]]:
        for pattern in self._FIELD_PATTERNS[field_name]:
            match = re.search(pattern, text, re.I)
            if match:
                try:
                    return _decimal(match.group("value")), _normalise_currency(match.group("currency"))
                except InvalidOperation:
                    return None
        return None

    @staticmethod
    def _constraints(text: str) -> tuple[str, ...]:
        constraints: list[str] = []
        lowered = text.casefold()
        if re.search(r"(?:no|not|never|do not|don't).{0,24}book", lowered):
            constraints.append("BOOKING_PROHIBITED")
        if re.search(r"(?:no|not|never|do not|don't).{0,24}(?:pay|payment)", lowered):
            constraints.append("PAYMENT_PROHIBITED")
        if re.search(r"human.{0,24}(?:review|approv)|(?:review|approv).{0,24}human", lowered):
            constraints.append("HUMAN_REVIEW_REQUIRED")
        return tuple(sorted(set(constraints)))

    def compile(self, text: str) -> MeaningCapsule:
        extracted = {name: self._extract_field(text, name) for name in self._FIELD_PATTERNS}
        present = {name: item for name, item in extracted.items() if item is not None}
        lowered = text.casefold()
        if "profit" in lowered and present:
            intent = "CALCULATE_PROFIT"
        elif re.search(r"\b(quote|quotation|estimate)\b", lowered):
            intent = "PREPARE_QUOTATION"
        elif re.search(r"\b(book|booking|schedule|installation)\b", lowered):
            intent = "MANAGE_BOOKING"
        elif re.search(r"\b(customer|client)\b.*\b(response|reply)\b|\b(response|reply)\b.*\b(customer|client)\b", lowered):
            intent = "DRAFT_CUSTOMER_RESPONSE"
        elif re.search(r"\b(calculate|compute|percent|tax|discount|times|plus)\b", lowered):
            intent = "CALCULATION_REQUEST"
        elif re.search(r"\b(code|python|javascript|function|unit test|debug)\b", lowered):
            intent = "CODING_REQUEST"
        elif re.search(r"\b(plan|steps|organize|organise)\b", lowered):
            intent = "PLAN_REQUEST"
        else:
            intent = "GENERAL_REQUEST"
        currencies = {currency for _, currency in present.values() if currency}
        missing = len(self._FIELD_PATTERNS) - len(present)
        duplicate_role = any(
            len(re.findall(pattern, text, re.I)) > 1
            for pattern in (r"\brevenue\b", r"\bmaterials?\b", r"\blabou?r\b")
        )
        alternative_values = bool(re.search(r"\d[\d,.]*\s+or\s+(?:EUR|GBP|USD|€|£|\$)?\s*\d", text, re.I))
        if intent == "CALCULATE_PROFIT":
            ambiguity = min(
                1.0,
                missing / len(self._FIELD_PATTERNS)
                + (0.5 if len(currencies) > 1 else 0.0)
                + (0.5 if duplicate_role or alternative_values else 0.0),
            )
            entities = {name: _display(value) for name, (value, _) in present.items()}
        else:
            ambiguity = min(1.0, (0.5 if alternative_values else 0.0) + (0.25 if duplicate_role else 0.0))
            quantities = re.findall(
                r"(?<![a-z0-9])(?:EUR|GBP|USD|€|£|\$)?\s*(\d[\d,]*(?:\.\d+)?)\s*(%|percent|metres?|meters?|cm|mm|feet|ft|hours?|hrs?)?",
                text,
                re.I,
            )
            entities = {}
            for index, (value, unit) in enumerate(quantities[:8], start=1):
                entities[f"quantity_{index}"] = _display(_decimal(value))
                if unit:
                    entities[f"quantity_{index}_unit"] = unit.casefold()
            generic_currencies = {
                normalized for token in re.findall(r"EUR|GBP|USD|€|£|\$", text, re.I)
                if (normalized := _normalise_currency(token.upper()))
            }
            currencies = generic_currencies
        canonical = {
            "intent": intent,
            "entities": entities,
            "currency": next(iter(currencies)) if len(currencies) == 1 else None,
            "constraints": self._constraints(text),
            "ambiguity_score": ambiguity,
        }
        if intent == "GENERAL_REQUEST":
            canonical["normalized_request_sha256"] = hashlib.sha256(
                " ".join(lowered.split()).encode("utf-8")
            ).hexdigest()
        return MeaningCapsule(
            schema_version="aion.meaning_capsule.v1",
            glyph_address=f"glyph:sha256:{_hash(canonical)}",
            intent=intent,
            entities=entities,
            currency=canonical["currency"],
            constraints=canonical["constraints"],
            ambiguity_score=ambiguity,
            source_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        )

    def _atomsheet_gate(self, capsule: MeaningCapsule) -> tuple[bool, str]:
        required = set(self.profit_sheet["required_inputs"])
        if capsule.intent != self.profit_sheet["intent"]:
            return False, "intent_not_supported"
        if set(capsule.entities) != required:
            return False, "required_inputs_incomplete"
        if capsule.ambiguity_score != 0:
            return False, "meaning_is_ambiguous"
        values = {name: Decimal(value) for name, value in capsule.entities.items()}
        limit = Decimal(str(self.profit_sheet["validity"]["maximum_absolute_input"]))
        if values["revenue"] <= 0:
            return False, "revenue_not_positive"
        if values["materials"] < 0 or values["labour"] < 0:
            return False, "cost_is_negative"
        if any(abs(value) > limit for value in values.values()):
            return False, "input_exceeds_validity_limit"
        return True, "verified_atomsheet_boundary"

    @staticmethod
    def _minimal_prompt(capsule: MeaningCapsule, source_text: str) -> str:
        return json.dumps({
            "task": capsule.intent,
            "request": _normalise_request_text(source_text),
            "known_entities": capsule.entities,
            "currency": capsule.currency,
            "constraints": capsule.constraints,
            "instruction": "Resolve ambiguity, preserve constraints, and answer concisely.",
        }, sort_keys=True, separators=(",", ":"))

    def route(self, text: str) -> GatewayResult:
        capsule = self.compile(text)
        eligible, reason = self._atomsheet_gate(capsule)
        if eligible and re.search(
            r"\b(?:and|then)\s+(?!(?:do\s+not|don't|never|not)\b)(?:book|schedule|send|email|pay|order|contact|write|create)\b",
            text,
            re.I,
        ):
            eligible, reason = False, "compound_action_requires_orchestration"
        candidates = (
            RouteCandidate("verified_atomsheet", 1.0 if eligible else 0.0, eligible, reason),
            RouteCandidate("full_model", 0.25 if eligible else 1.0, True, "fallback_available"),
        )
        base_receipt = {
            "source_sha256": capsule.source_sha256,
            "glyph_address": capsule.glyph_address,
            "atomsheet_id": self.profit_sheet["sheet_id"],
            "atomsheet_sha256": self.profit_sheet_sha256,
            "gate_passed": eligible,
            "gate_reason": reason,
            "original_utf8_bytes": len(text.encode("utf-8")),
        }
        if not eligible:
            prompt = self._minimal_prompt(capsule, text)
            return GatewayResult(
                schema_version="aion.semantic_gateway.result.v1",
                route="full_model",
                model_call_required=True,
                answer=None,
                structured_result=None,
                meaning_capsule=capsule,
                candidates=candidates,
                minimal_model_prompt=prompt,
                proof_receipt={
                    **base_receipt,
                    "minimal_prompt_utf8_bytes": len(prompt.encode("utf-8")),
                    "minimal_prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "source_request_preserved": True,
                },
            )

        values = {name: Decimal(value) for name, value in capsule.entities.items()}
        profit = values["revenue"] - values["materials"] - values["labour"]
        margin = profit / values["revenue"] * Decimal("100")
        inverse_verified = profit + values["materials"] + values["labour"] == values["revenue"]
        structured = {
            "profit": _display(profit),
            "margin_percent": _display(margin),
            "currency": capsule.currency or "UNSPECIFIED",
        }
        unit = f" {capsule.currency}" if capsule.currency else ""
        answer = f"Estimated profit is {_display(profit)}{unit}; profit margin is {_display(margin)}%."
        result_hash = _hash(structured)
        return GatewayResult(
            schema_version="aion.semantic_gateway.result.v1",
            route="verified_atomsheet",
            model_call_required=False,
            answer=answer,
            structured_result=structured,
            meaning_capsule=capsule,
            candidates=candidates,
            minimal_model_prompt=None,
            proof_receipt={
                **base_receipt,
                "operator_graph": self.profit_sheet["operations"],
                "inverse_verified": inverse_verified,
                "result_sha256": result_hash,
                "model_calls": 0,
            },
        )
