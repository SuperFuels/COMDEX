"""Quality-gated candidate normalizer; not a promoted production route."""

from __future__ import annotations

import hashlib
import json
import re

from .verified_supplier_extraction import extract_verified_supplier_fields


_NAME = r"(?P<supplier>[A-Za-zÀ-ÿ][A-Za-zÀ-ÿ0-9 &'\-]{1,100}?)"
_INVOICE = r"(?P<invoice>[A-Z]{2,5}-[0-9]{2,6})"
_PAYMENT = r"(?P<payment>(?:EUR|USD|GBP|SEK) [0-9]+\.[0-9]{2})"
_CANDIDATE_PATTERNS = tuple(re.compile(pattern) for pattern in (
    rf"^{_NAME} sent invoice {_INVOICE} for {_PAYMENT} for review\.$",
    rf"^The {_PAYMENT} invoice {_INVOICE} was submitted by {_NAME}\.$",
    rf"^For review: supplier {_NAME}; invoice {_INVOICE}; amount {_PAYMENT}\.$",
    rf"^Could you check invoice {_INVOICE} from {_NAME} for {_PAYMENT}\?$",
    rf"^{_NAME} has requested {_PAYMENT} for invoice {_INVOICE}\.$",
    rf"^Record {_NAME}, invoice {_INVOICE}, payment {_PAYMENT} for review\.$",
    rf"^The invoice awaiting review is {_INVOICE} from {_NAME} for {_PAYMENT}\.$",
    rf"^Review {_NAME}'s {_PAYMENT} invoice {_INVOICE}\.$",
))
_PROHIBITED_COMPOUND = re.compile(
    r"\b(?:also|then|calculate|draft|write|plan|schedule|compare|explain|convert|email|approve|execute|transfer|send)\b",
    re.I,
)
_PREFIXES = (
    re.compile(r"^For the [A-Za-z]+ review queue, "),
    re.compile(r"^Internal note: [^.]{1,80}\. "),
    re.compile(r"^Reference only\. "),
    re.compile(r"^Queue item [0-9]+: "),
)
_SUFFIXES = (
    re.compile(r" The attachment has already been archived\.$"),
    re.compile(r" This is for the weekly queue\.$"),
    re.compile(r" No action is requested\.$"),
    re.compile(r" Retain the review receipt\.$"),
)

_CONTRACT = {
    "schema_version": "aion.supplier_intent_normalizer_contract.v1",
    "candidate_patterns": [pattern.pattern for pattern in _CANDIDATE_PATTERNS],
    "prohibited_compound": _PROHIBITED_COMPOUND.pattern,
    "prefixes": [pattern.pattern for pattern in _PREFIXES],
    "suffixes": [pattern.pattern for pattern in _SUFFIXES],
    "required_invoice_matches": 1,
    "required_payment_matches": 1,
    "authority": {"approve": False, "execute_payment": False},
}
CONTRACT_SHA256 = hashlib.sha256(
    json.dumps(_CONTRACT, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


def canonicalize_supplier_extraction_request(text: str) -> str | None:
    """Return a strict canonical request only for a unique, non-compound intent."""
    normalized = " ".join(text.split())
    if len(re.findall(r"\b[A-Z]{2,5}-[0-9]{2,6}\b", normalized)) != 1:
        return None
    if len(re.findall(r"\b(?:EUR|USD|GBP|SEK) [0-9]+\.[0-9]{2}\b", normalized)) != 1:
        return None
    if _PROHIBITED_COMPOUND.search(normalized):
        return None
    if extract_verified_supplier_fields(normalized) is not None:
        return normalized

    simplified = normalized
    for pattern in _PREFIXES:
        simplified = pattern.sub("", simplified, count=1)
    for pattern in _SUFFIXES:
        if pattern.search(simplified):
            simplified = pattern.sub("", simplified, count=1)
            break
    if extract_verified_supplier_fields(simplified) is not None:
        return simplified

    matches = [match for pattern in _CANDIDATE_PATTERNS
               if (match := pattern.fullmatch(simplified)) is not None]
    if len(matches) != 1:
        return None
    match = matches[0]
    canonical = (
        f"Supplier {match.group('supplier').strip()} submitted invoice "
        f"{match.group('invoice')} for {match.group('payment')}."
    )
    return canonical if extract_verified_supplier_fields(canonical) is not None else None
