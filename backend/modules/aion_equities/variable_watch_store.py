from __future__ import annotations

import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional


def _safe_segment(value: str) -> str:
    return str(value).replace("/", "_").replace("\\", "_").replace(":", "-").strip()


def _coerce_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _as_str(x: Any) -> str:
    return str(x).strip() if x is not None else ""


def _normalize_importance(v: Any) -> str:
    s = _as_str(v).lower()
    if s in {"high", "medium", "low"}:
        return s.capitalize()
    return "Medium"


def _clean_name(text: str) -> str:
    s = _as_str(text)
    if not s:
        return ""
    # strip common bullets/prefixes
    s = re.sub(r"^\s*[\-\*\u2022]+\s*", "", s)
    # collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _canonicalize_name_from_note(note: str) -> str:
    """
    For strings like:
      "Underlying Sales Growth (USG) - target 4%-6% in 2026"
    extract:
      "Underlying Sales Growth (USG)"
    """
    s = _clean_name(note)
    if not s:
        return ""
    # prefer " - " split, but allow en dash/em dash too
    for sep in (" - ", " – ", " — "):
        if sep in s:
            return s.split(sep, 1)[0].strip()
    return s


def _normalize_variable_dict(v: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize a variable dict into the minimal canonical shape:
      {
        "name": <str>,
        "importance": "High"|"Medium"|"Low",
        "notes": <str|optional>,
        ... passthrough extra fields ...
      }

    Accepts alternative keys:
      - name | variable_name | variable | title
      - importance | priority
      - notes | why_it_matters | description | details
    """
    if not isinstance(v, dict):
        return None

    name = (
        _as_str(v.get("name"))
        or _as_str(v.get("variable_name"))
        or _as_str(v.get("variable"))
        or _as_str(v.get("title"))
    )
    name = _clean_name(name)

    notes = v.get("notes")
    if notes is None:
        notes = v.get("why_it_matters")
    if notes is None:
        notes = v.get("description")
    if notes is None:
        notes = v.get("details")
    notes_s = _clean_name(notes) if notes is not None else ""

    # if name missing, try to derive from notes
    if not name and notes_s:
        name = _canonicalize_name_from_note(notes_s)

    if not name:
        return None

    out: Dict[str, Any] = {
        "name": name,
        "importance": _normalize_importance(v.get("importance") or v.get("priority")),
    }
    if notes_s:
        out["notes"] = notes_s

    # passthrough useful structured fields if present (safe, optional)
    passthrough_fields = [
        "data_source",
        "feed_id",
        "current_value",
        "current_value_unit",
        "current_state",
        "threshold_early",
        "threshold_confirm",
        "threshold_rule",
        "confirmation_rule",
        "direction",
        "lag_weeks",
        "impact_weight",
        "thesis_action_on_confirm",
        "thesis_action_on_break",
        "last_updated",
    ]
    for k in passthrough_fields:
        if k in v and v[k] is not None and k not in out:
            out[k] = deepcopy(v[k])

    return out


def _extract_variables(seed: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Accepts multiple legacy / runtime shapes and produces a list of dict variable objects.

    Supported input shapes:
      - {"variables":[{...}, ...]}
      - {"watch_variables":[{...}, ...]}
      - {"payload":{"variables":[{...}]}}
      - {"payload":{"key_variables":[<str>, ...]}}
      - {"key_variables":[<str>, ...]}
      - {"payload":{"key_variables":[<dict>, ...]}}  (tolerate dicts too)
    """
    # 1) direct structured variables
    variables = seed.get("variables")
    if variables is None and "watch_variables" in seed:
        variables = seed.get("watch_variables")

    # 2) nested payload structured variables
    payload = seed.get("payload") if isinstance(seed.get("payload"), dict) else None
    if variables is None and payload is not None:
        if payload.get("variables") is not None:
            variables = payload.get("variables")
        elif payload.get("watch_variables") is not None:
            variables = payload.get("watch_variables")

    out: List[Dict[str, Any]] = []
    if isinstance(variables, list):
        for item in variables:
            if isinstance(item, dict):
                norm = _normalize_variable_dict(item)
                if norm:
                    out.append(norm)
            elif item is not None:
                text = _clean_name(item)
                if not text:
                    continue
                out.append(
                    {
                        "name": _canonicalize_name_from_note(text) or text,
                        "importance": "Medium",
                        "notes": text,
                    }
                )
        if out:
            # de-dupe by name (case-insensitive) preserving order
            seen = set()
            deduped: List[Dict[str, Any]] = []
            for v in out:
                key = v.get("name", "").strip().lower()
                if not key or key in seen:
                    continue
                seen.add(key)
                deduped.append(v)
            return deduped

    # 3) fallback: promote key_variables -> minimal dict objects
    key_vars = seed.get("key_variables")
    if key_vars is None and payload is not None:
        key_vars = payload.get("key_variables")

    for item in _coerce_list(key_vars):
        if item is None:
            continue
        if isinstance(item, dict):
            norm = _normalize_variable_dict(item)
            if norm:
                out.append(norm)
            continue

        text = _clean_name(item)
        if not text:
            continue
        name = _canonicalize_name_from_note(text) or text
        out.append(
            {
                "name": name,
                "importance": "Medium",
                "notes": text,
            }
        )

    # de-dupe by name preserving order
    seen = set()
    deduped: List[Dict[str, Any]] = []
    for v in out:
        key = v.get("name", "").strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(v)
    return deduped


class VariableWatchStore:
    """
    Tiny file-backed store for variable-watch / watchlist payloads.

    Layout:
      <base_dir>/
        variable_watch/
          company_AHT.L/
            2026-Q1.json

    Canonical id:
      <company_ref>/variable_watch/<fiscal_period_ref>
    """

    def __init__(self, base_dir: str | Path):
        self.base_dir = Path(base_dir)
        self.watch_dir = self.base_dir / "variable_watch"
        self.watch_dir.mkdir(parents=True, exist_ok=True)

    def _company_dir(self, company_ref: str) -> Path:
        p = self.watch_dir / _safe_segment(company_ref)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def storage_path(self, company_ref: str, fiscal_period_ref: str) -> Path:
        return self._company_dir(company_ref) / f"{_safe_segment(fiscal_period_ref)}.json"

    def save_variable_watch(
        self,
        *,
        company_ref: str,
        fiscal_period_ref: str,
        variable_watch_seed: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        generated_by: str = "aion_equities.variable_watch_store",
        validate: bool = False,
        **aliases: Any,
    ) -> Dict[str, Any]:
        # allow many legacy entrypoints
        seed = deepcopy(
            variable_watch_seed
            or payload
            or aliases.get("watchlist")
            or aliases.get("variable_watch")
            or aliases.get("variable_watch_seed")
            or {}
        )
        if not isinstance(seed, dict):
            raise TypeError("variable_watch_seed/payload must be a dict")

        variables = _extract_variables(seed)

        watch_id = f"{company_ref}/variable_watch/{fiscal_period_ref}"

        stored: Dict[str, Any] = {
            "variable_watch_id": watch_id,
            "company_ref": str(company_ref),
            "fiscal_period_ref": str(fiscal_period_ref),
            "generated_by": str(generated_by),
            "variables": deepcopy(variables),
            # keep the original seed for audit/debug
            "payload": deepcopy(seed),
        }

        # NOTE: validate currently unused; kept for parity/future schema checks
        _ = validate

        path = self.storage_path(company_ref, fiscal_period_ref)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
        return deepcopy(stored)

    # aliases
    def save_watchlist(self, **kwargs: Any) -> Dict[str, Any]:
        return self.save_variable_watch(**kwargs)

    def load_variable_watch(self, company_ref: str, fiscal_period_ref: str) -> Dict[str, Any]:
        path = self.storage_path(company_ref, fiscal_period_ref)
        if not path.exists():
            raise FileNotFoundError(f"Variable watch not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def load_variable_watch_by_id(self, variable_watch_id: str) -> Dict[str, Any]:
        parts = str(variable_watch_id).split("/variable_watch/")
        if len(parts) != 2:
            raise ValueError(f"Invalid variable_watch_id: {variable_watch_id!r}")
        company_ref, fiscal_period_ref = parts
        return self.load_variable_watch(company_ref, fiscal_period_ref)

    def variable_watch_exists(self, company_ref: str, fiscal_period_ref: str) -> bool:
        return self.storage_path(company_ref, fiscal_period_ref).exists()

    def list_variable_watch(self, company_ref: str) -> List[str]:
        company_dir = self.watch_dir / _safe_segment(company_ref)
        if not company_dir.exists():
            return []
        return sorted(p.stem for p in company_dir.glob("*.json"))


__all__ = ["VariableWatchStore"]