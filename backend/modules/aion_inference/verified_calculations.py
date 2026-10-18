"""Strict, independently verified AtomSheet calculations for the gateway."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation, localcontext
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Optional


CATALOG_PATH = Path(__file__).with_name("atomsheets") / "calculations.v1.json"
NUMBER = r"([+-]?\d[\d,]*(?:\.\d+)?)"
UNIT = r"(millimet(?:re|er)s?|centimet(?:re|er)s?|met(?:re|er)s?|kilomet(?:re|er)s?|feet|foot|inches|inch|mm|cm|m|km|ft|in)"
UNIT_FACTORS = {
    "mm": Decimal("0.001"),
    "cm": Decimal("0.01"),
    "m": Decimal("1"),
    "km": Decimal("1000"),
    "ft": Decimal("0.3048"),
    "in": Decimal("0.0254"),
}
UNIT_ALIASES = {
    "millimetre": "mm", "millimetres": "mm", "millimeter": "mm", "millimeters": "mm",
    "centimetre": "cm", "centimetres": "cm", "centimeter": "cm", "centimeters": "cm",
    "metre": "m", "metres": "m", "meter": "m", "meters": "m",
    "kilometre": "km", "kilometres": "km", "kilometer": "km", "kilometers": "km",
    "foot": "ft", "feet": "ft", "inch": "in", "inches": "in",
}
MASS_UNIT = r"\b(kilograms?|kilogrammes?|kg|grams?|grammes?|g|milligrams?|milligrammes?|mg|tonnes?|metric\s+tons?)\b"
MASS_FACTORS = {
    "mg": Decimal("0.001"),
    "g": Decimal("1"),
    "kg": Decimal("1000"),
    "t": Decimal("1000000"),
}
MASS_ALIASES = {
    "milligram": "mg", "milligrams": "mg", "milligramme": "mg", "milligrammes": "mg",
    "gram": "g", "grams": "g", "gramme": "g", "grammes": "g",
    "kilogram": "kg", "kilograms": "kg", "kilogramme": "kg", "kilogrammes": "kg",
    "tonne": "t", "tonnes": "t", "metric ton": "t", "metric tons": "t",
}


def _decimal(raw: str) -> Decimal:
    return Decimal(raw.replace(",", ""))


def _display(value: Decimal) -> str:
    rendered = format(value, "f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    return rendered or "0"


def _unit(raw: str) -> str:
    lowered = raw.casefold()
    return UNIT_ALIASES.get(lowered, lowered)


def _sha(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class VerifiedCalculationResult:
    schema_version: str
    route: str
    model_call_required: bool
    intent: str
    glyph_address: str
    answer: Optional[str]
    structured_result: Optional[Mapping[str, str]]
    proof_receipt: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VerifiedCalculationRouter:
    def __init__(self, catalog_path: Path = CATALOG_PATH) -> None:
        self.catalog_bytes = catalog_path.read_bytes()
        self.catalog = json.loads(self.catalog_bytes)
        self.catalog_sha256 = hashlib.sha256(self.catalog_bytes).hexdigest()
        self.sheets = {sheet["intent"]: sheet for sheet in self.catalog["sheets"]}
        self.limit = Decimal(str(self.catalog["shared_validity"]["maximum_absolute_input"]))

    def _fallback(self, reason: str, source: str) -> VerifiedCalculationResult:
        return VerifiedCalculationResult(
            schema_version="aion.verified_calculation.result.v1",
            route="full_model",
            model_call_required=True,
            intent="UNKNOWN",
            glyph_address=f"glyph:sha256:{_sha({'source': source.casefold().strip()})}",
            answer=None,
            structured_result=None,
            proof_receipt={"gate_passed": False, "gate_reason": reason, "catalog_sha256": self.catalog_sha256},
        )

    def _success(
        self,
        *,
        intent: str,
        inputs: Mapping[str, str],
        result: Mapping[str, str],
        answer: str,
        verified: bool,
    ) -> VerifiedCalculationResult:
        sheet = self.sheets[intent]
        canonical = {"intent": intent, "inputs": dict(inputs)}
        return VerifiedCalculationResult(
            schema_version="aion.verified_calculation.result.v1",
            route="verified_atomsheet",
            model_call_required=False,
            intent=intent,
            glyph_address=f"glyph:sha256:{_sha(canonical)}",
            answer=answer,
            structured_result=result,
            proof_receipt={
                "gate_passed": verified,
                "gate_reason": "verified_atomsheet_boundary" if verified else "independent_verification_failed",
                "sheet_id": sheet["sheet_id"],
                "catalog_sha256": self.catalog_sha256,
                "operation": sheet["operation"],
                "verification": sheet["verification"],
                "inverse_verified": verified,
                "result_sha256": _sha(result),
                "model_calls": 0,
            },
        )

    def route(self, text: str) -> VerifiedCalculationResult:
        lowered = text.casefold().strip()
        if re.search(
            r"\b(?:and|then)\s+(?!(?:do\s+not|don't|never|not)\b)(?:book|schedule|send|email|pay|order|contact|write|create)\b",
            lowered,
        ):
            return self._fallback("compound_action_requires_orchestration", text)
        try:
            if (
                "revenue" in lowered
                and "cost" in lowered
                and re.search(r"\bgross[ _-]+margin(?:\b|_)", lowered)
            ):
                return self._gross_margin(lowered, text)
            if "convert" in lowered:
                if re.search(MASS_UNIT, lowered):
                    return self._convert_mass(lowered, text)
                return self._convert_length(lowered, text)
            if "%" in lowered or "percent" in lowered:
                return self._percentage(lowered, text)
            if "volume" in lowered:
                return self._volume(lowered, text)
            if "area" in lowered:
                return self._area(lowered, text)
        except (InvalidOperation, ArithmeticError):
            return self._fallback("invalid_numeric_input", text)
        return self._fallback("no_verified_calculation_match", text)

    def _gross_margin(self, lowered: str, source: str) -> VerifiedCalculationResult:
        revenue_matches = re.findall(
            rf"\brevenue(?:\s+is)?(?:\s+[a-z]{{3}})?\s+{NUMBER}\b", lowered
        )
        cost_matches = re.findall(
            rf"\bcost(?:\s+is)?(?:\s+[a-z]{{3}})?\s+{NUMBER}\b", lowered
        )
        if len(revenue_matches) != 1 or len(cost_matches) != 1:
            return self._fallback("gross_margin_inputs_ambiguous", source)
        revenue = _decimal(revenue_matches[0])
        cost = _decimal(cost_matches[0])
        if revenue == 0 or any(abs(value) > self.limit for value in (revenue, cost)):
            return self._fallback("gross_margin_outside_validity_boundary", source)
        with localcontext() as context:
            context.prec = 40
            gross_profit = revenue - cost
            unrounded_margin = gross_profit / revenue * Decimal("100")
            margin = unrounded_margin.quantize(Decimal("0.01"))
            verified = gross_profit + cost == revenue and (
                unrounded_margin * revenue / Decimal("100") == gross_profit
            )
        inputs = {"revenue": _display(revenue), "cost": _display(cost)}
        result = {
            "gross_profit": _display(gross_profit),
            "gross_margin_percent": format(margin, ".2f"),
        }
        return self._success(
            intent="CALCULATE_GROSS_MARGIN",
            inputs=inputs,
            result=result,
            answer=json.dumps(result, sort_keys=True, separators=(",", ":")),
            verified=verified,
        )

    def _percentage(self, lowered: str, source: str) -> VerifiedCalculationResult:
        matches = re.findall(rf"{NUMBER}\s*(?:%|percent)\s+of\s+{NUMBER}", lowered)
        if len(matches) != 1:
            return self._fallback("percentage_pattern_ambiguous", source)
        percent, base = map(_decimal, matches[0])
        if base == 0 or any(abs(value) > self.limit for value in (percent, base)):
            return self._fallback("percentage_outside_validity_boundary", source)
        with localcontext() as context:
            context.prec = 40
            value = base * percent / Decimal("100")
            verified = value / base * Decimal("100") == percent
        inputs = {"percent": _display(percent), "base": _display(base)}
        result = {"value": _display(value), "unit": "scalar"}
        return self._success(intent="CALCULATE_PERCENTAGE", inputs=inputs, result=result, answer=f"{_display(value)}", verified=verified)

    def _dimensions(self, lowered: str, count: int) -> Optional[list[tuple[Decimal, str]]]:
        matches = re.findall(rf"{NUMBER}\s*{UNIT}", lowered)
        if len(matches) != count:
            return None
        return [(_decimal(value), _unit(unit)) for value, unit in matches]

    def _area(self, lowered: str, source: str) -> VerifiedCalculationResult:
        dimensions = self._dimensions(lowered, 2)
        if not dimensions or not re.search(r"\b(?:by|x|×)\b", lowered):
            return self._fallback("area_dimensions_ambiguous", source)
        if any(value <= 0 or abs(value) > self.limit for value, _ in dimensions):
            return self._fallback("area_outside_validity_boundary", source)
        metres = [value * UNIT_FACTORS[unit] for value, unit in dimensions]
        area = metres[0] * metres[1]
        verified = area / metres[0] == metres[1]
        inputs = {"length_metres": _display(metres[0]), "width_metres": _display(metres[1])}
        result = {"area": _display(area), "unit": "m²"}
        return self._success(intent="CALCULATE_RECTANGLE_AREA", inputs=inputs, result=result, answer=f"{_display(area)} m²", verified=verified)

    def _volume(self, lowered: str, source: str) -> VerifiedCalculationResult:
        dimensions = self._dimensions(lowered, 3)
        if not dimensions or len(re.findall(r"\b(?:by|x|×)\b", lowered)) < 2:
            return self._fallback("volume_dimensions_ambiguous", source)
        if any(value <= 0 or abs(value) > self.limit for value, _ in dimensions):
            return self._fallback("volume_outside_validity_boundary", source)
        metres = [value * UNIT_FACTORS[unit] for value, unit in dimensions]
        volume = metres[0] * metres[1] * metres[2]
        verified = volume / metres[0] / metres[1] == metres[2]
        inputs = {name: _display(value) for name, value in zip(("length_metres", "width_metres", "height_metres"), metres)}
        result = {"volume": _display(volume), "unit": "m³"}
        return self._success(intent="CALCULATE_RECTANGULAR_VOLUME", inputs=inputs, result=result, answer=f"{_display(volume)} m³", verified=verified)

    def _convert_length(self, lowered: str, source: str) -> VerifiedCalculationResult:
        matches = re.findall(rf"convert\s+{NUMBER}\s*{UNIT}\s+(?:to|into)\s+{UNIT}\b", lowered)
        if len(matches) != 1:
            return self._fallback("conversion_pattern_ambiguous", source)
        raw_value, source_unit, target_unit = matches[0]
        value = _decimal(raw_value)
        source_unit, target_unit = _unit(source_unit), _unit(target_unit)
        if abs(value) > self.limit:
            return self._fallback("conversion_outside_validity_boundary", source)
        converted = value * UNIT_FACTORS[source_unit] / UNIT_FACTORS[target_unit]
        verified = converted * UNIT_FACTORS[target_unit] / UNIT_FACTORS[source_unit] == value
        inputs = {"value": _display(value), "source_unit": source_unit, "target_unit": target_unit}
        result = {"value": _display(converted), "unit": target_unit}
        return self._success(intent="CONVERT_LENGTH", inputs=inputs, result=result, answer=f"{_display(converted)} {target_unit}", verified=verified)

    def _convert_mass(self, lowered: str, source: str) -> VerifiedCalculationResult:
        matches = re.findall(
            rf"convert\s+{NUMBER}\s*{MASS_UNIT}\s+(?:to|into)\s+{MASS_UNIT}\b",
            lowered,
        )
        if len(matches) != 1:
            return self._fallback("mass_conversion_pattern_ambiguous", source)
        raw_value, source_unit, target_unit = matches[0]
        value = _decimal(raw_value)
        source_unit = MASS_ALIASES.get(source_unit.casefold(), source_unit.casefold())
        target_unit = MASS_ALIASES.get(target_unit.casefold(), target_unit.casefold())
        if abs(value) > self.limit:
            return self._fallback("mass_conversion_outside_validity_boundary", source)
        converted = value * MASS_FACTORS[source_unit] / MASS_FACTORS[target_unit]
        verified = converted * MASS_FACTORS[target_unit] / MASS_FACTORS[source_unit] == value
        inputs = {
            "value": _display(value),
            "source_unit": source_unit,
            "target_unit": target_unit,
        }
        result = {"value": _display(converted), "unit": target_unit}
        return self._success(
            intent="CONVERT_MASS",
            inputs=inputs,
            result=result,
            answer=f"{_display(converted)} {target_unit}",
            verified=verified,
        )
