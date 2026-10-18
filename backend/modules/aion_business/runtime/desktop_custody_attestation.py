"""Content-free desktop Business Vault custody attestation."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping


CUSTODY_ATTESTATION_SCHEMA = "tessaris.business-vault-custody-attestation.v1"


def desktop_custody_attestation(environment: Mapping[str, str]) -> dict[str, str]:
    mode = str(environment.get("TESSARIS_BUSINESS_CONTAINER_BACKEND", "")).strip().lower()
    business_stable_id = str(environment.get("TESSARIS_BUSINESS_STABLE_ID", "")).strip()
    return {
        "schema_version": CUSTODY_ATTESTATION_SCHEMA,
        "mode": mode,
        "business_stable_id_sha256": (
            hashlib.sha256(business_stable_id.encode("utf-8")).hexdigest()
            if business_stable_id else ""
        ),
    }
