from __future__ import annotations

from hashlib import sha256
import json
from typing import Any


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return "sha256:" + sha256(_canonical_json(value).encode("utf-8")).hexdigest()


VALID_LEDGER_ENTRY_TYPES = {
    "capability_receipt",
    "mission_trace",
    "proof_update",
    "replay_update",
    "cache_eviction",
    "state_summary",
}

VALID_CACHE_SCOPES = {
    "mission_vfs",
    "browser_session",
    "provider_context",
    "staged_state",
    "temporary_vector_workspace",
    "runtime_scratchpad",
}


def create_ledger_entry(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    entry_type: str,
    source_hash: str,
    sequence_number: int,
    previous_entry_hash: str = "sha256:genesis",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if entry_type not in VALID_LEDGER_ENTRY_TYPES:
        raise ValueError(f"invalid ledger entry type: {entry_type}")

    if sequence_number < 0:
        raise ValueError("sequence_number must be non-negative")

    if not source_hash.startswith("sha256:"):
        raise ValueError("source_hash must be sha256-prefixed")

    if not previous_entry_hash.startswith("sha256:"):
        raise ValueError("previous_entry_hash must be sha256-prefixed")

    entry = {
        "schema_version": "aion.cross_mission_state_ledger.entry.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "entry_type": entry_type,
        "source_hash": source_hash,
        "sequence_number": sequence_number,
        "previous_entry_hash": previous_entry_hash,
        "payload": payload or {},
        "entry_hash": "",
    }
    entry["entry_hash"] = _hash({k: v for k, v in entry.items() if k != "entry_hash"})
    return entry


def verify_ledger_chain(entries: list[dict[str, Any]]) -> dict[str, Any]:
    reasons: list[str] = []

    sorted_entries = sorted(entries, key=lambda item: item["sequence_number"])

    for idx, entry in enumerate(sorted_entries):
        expected_hash = _hash({k: v for k, v in entry.items() if k != "entry_hash"})
        if entry.get("entry_hash") != expected_hash:
            reasons.append(f"entry_hash_mismatch:{entry.get('sequence_number')}")

        if idx == 0:
            if entry.get("previous_entry_hash") != "sha256:genesis":
                reasons.append("first_entry_previous_hash_not_genesis")
        else:
            previous = sorted_entries[idx - 1]
            if entry.get("previous_entry_hash") != previous.get("entry_hash"):
                reasons.append(f"ledger_chain_break:{entry.get('sequence_number')}")

        if idx > 0 and entry["sequence_number"] <= sorted_entries[idx - 1]["sequence_number"]:
            reasons.append("non_increasing_sequence_number")

    valid = not reasons

    result = {
        "schema_version": "aion.cross_mission_state_ledger.verification.v0",
        "entry_count": len(sorted_entries),
        "ledger_valid": valid,
        "verification_state": "ledger_chain_valid" if valid else "ledger_chain_invalid",
        "latest_entry_hash": sorted_entries[-1]["entry_hash"] if sorted_entries else "sha256:genesis",
        "reasons": reasons,
        "verification_hash": "",
    }
    result["verification_hash"] = _hash({k: v for k, v in result.items() if k != "verification_hash"})
    return result


def create_consensus_snapshot(
    *,
    business_id: str,
    entries: list[dict[str, Any]],
) -> dict[str, Any]:
    ordered = sorted(entries, key=lambda item: (item["sequence_number"], item["entry_hash"]))
    entry_hashes = [entry["entry_hash"] for entry in ordered]
    mission_ids = sorted({entry["mission_id"] for entry in ordered})
    run_ids = sorted({entry["mission_run_id"] for entry in ordered})

    snapshot = {
        "schema_version": "aion.cross_mission_state_ledger.consensus_snapshot.v0",
        "business_id": business_id,
        "entry_count": len(ordered),
        "mission_ids": mission_ids,
        "mission_run_ids": run_ids,
        "entry_hashes": entry_hashes,
        "consensus_state": "cross_mission_ledger_consensus_formed",
        "consensus_hash": "",
    }
    snapshot["consensus_hash"] = _hash({k: v for k, v in snapshot.items() if k != "consensus_hash"})
    return snapshot


def create_cache_eviction_contract(
    *,
    mission_id: str,
    mission_run_id: str,
    business_id: str,
    cache_scope: str,
    cache_key_hash: str,
    reason: str,
    dependent_hashes: list[str] | None = None,
) -> dict[str, Any]:
    if cache_scope not in VALID_CACHE_SCOPES:
        raise ValueError(f"invalid cache scope: {cache_scope}")

    if not cache_key_hash.startswith("sha256:"):
        raise ValueError("cache_key_hash must be sha256-prefixed")

    deps = sorted(dependent_hashes or [])

    for dep in deps:
        if not dep.startswith("sha256:"):
            raise ValueError("dependent hashes must be sha256-prefixed")

    contract = {
        "schema_version": "aion.cache_eviction_contract.v0",
        "mission_id": mission_id,
        "mission_run_id": mission_run_id,
        "business_id": business_id,
        "cache_scope": cache_scope,
        "cache_key_hash": cache_key_hash,
        "reason": reason,
        "dependent_hashes": deps,
        "eviction_state": "eviction_required",
        "eviction_contract_hash": "",
    }
    contract["eviction_contract_hash"] = _hash(
        {k: v for k, v in contract.items() if k != "eviction_contract_hash"}
    )
    return contract


def assert_cache_eviction_completed(
    *,
    contract: dict[str, Any],
    observed_evicted_hash: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    if observed_evicted_hash != contract.get("cache_key_hash"):
        reasons.append("evicted_hash_mismatch")

    if contract.get("eviction_state") != "eviction_required":
        reasons.append("invalid_eviction_contract_state")

    completed = not reasons

    result = {
        "schema_version": "aion.cache_eviction_assertion.v0",
        "mission_id": contract.get("mission_id"),
        "mission_run_id": contract.get("mission_run_id"),
        "business_id": contract.get("business_id"),
        "cache_scope": contract.get("cache_scope"),
        "cache_key_hash": contract.get("cache_key_hash"),
        "observed_evicted_hash": observed_evicted_hash,
        "eviction_completed": completed,
        "assertion_state": "cache_eviction_confirmed" if completed else "cache_eviction_failed",
        "reasons": reasons,
        "eviction_assertion_hash": "",
    }
    result["eviction_assertion_hash"] = _hash(
        {k: v for k, v in result.items() if k != "eviction_assertion_hash"}
    )
    return result


def bind_ledger_to_replay(
    *,
    consensus_snapshot: dict[str, Any],
    replay_hash: str,
    proof_hash: str,
) -> dict[str, Any]:
    reasons: list[str] = []

    for name, value in {
        "consensus_hash": consensus_snapshot.get("consensus_hash"),
        "replay_hash": replay_hash,
        "proof_hash": proof_hash,
    }.items():
        if not isinstance(value, str) or not value.startswith("sha256:"):
            reasons.append(f"invalid_{name}")

    allowed = not reasons

    binding = {
        "schema_version": "aion.cross_mission_ledger_replay_binding.v0",
        "business_id": consensus_snapshot.get("business_id"),
        "consensus_hash": consensus_snapshot.get("consensus_hash"),
        "replay_hash": replay_hash,
        "proof_hash": proof_hash,
        "allowed": allowed,
        "binding_state": "ledger_bound_to_replay" if allowed else "ledger_replay_binding_blocked",
        "reasons": reasons,
        "binding_hash": "",
    }
    binding["binding_hash"] = _hash({k: v for k, v in binding.items() if k != "binding_hash"})
    return binding
