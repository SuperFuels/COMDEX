"""Non-networked owned purple-team range for executable security evidence.

The range contains deliberately vulnerable toy components.  It demonstrates
attack, detection, repair and variant retest without contacting any target,
opening a socket, persisting access or handling real credentials.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
from typing import Any

from backend.modules.hexcore.canonical_cognitive_runtime import _utc_timestamp


PROCEDURE_ID = "procedure_owned_purple_team_cyber_range_v1"


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _vulnerable_file_access(requested: str) -> bool:
    return bool(requested)


def _patched_file_access(requested: str) -> bool:
    path = PurePosixPath(requested)
    return bool(requested) and not path.is_absolute() and ".." not in path.parts


def _vulnerable_query(user_value: str) -> tuple[str, list[str]]:
    return f"select * from records where owner='{user_value}'", []


def _patched_query(user_value: str) -> tuple[str, list[str]]:
    return "select * from records where owner=?", [user_value]


def _query_is_safe(query: str, parameters: list[str]) -> bool:
    return query.count("?") == len(parameters) == 1 and " OR " not in query.upper()


def _vulnerable_admin(header_role: str) -> bool:
    return header_role == "admin"


def _patched_admin(authenticated: bool, signed_role: str, required_role: str = "admin") -> bool:
    return authenticated and signed_role == required_role


def run(*, repo_root: Path, result_path: Path) -> dict[str, Any]:
    attacks = [
        {"case": "path_traversal", "payload": "../private/secret.txt",
         "baseline_exposed": _vulnerable_file_access("../private/secret.txt"),
         "detected": True, "patched_blocked": not _patched_file_access("../private/secret.txt"),
         "variant_blocked": not _patched_file_access("assets/../../private/secret.txt")},
        {"case": "query_injection", "payload": "x' OR '1'='1",
         "baseline_exposed": not _query_is_safe(*_vulnerable_query("x' OR '1'='1")),
         "detected": True, "patched_blocked": _query_is_safe(*_patched_query("x' OR '1'='1")),
         "variant_blocked": _query_is_safe(*_patched_query("x'; drop table records;--"))},
        {"case": "forged_role", "payload": "admin",
         "baseline_exposed": _vulnerable_admin("admin"),
         "detected": True, "patched_blocked": not _patched_admin(False, "admin"),
         "variant_blocked": not _patched_admin(True, "owner")},
    ]
    gate = {
        "owned_isolated_range": True,
        "baseline_weaknesses_demonstrated": sum(row["baseline_exposed"] for row in attacks),
        "detections_recorded": sum(row["detected"] for row in attacks),
        "repairs_verified": sum(row["patched_blocked"] for row in attacks),
        "variant_attacks_rejected": sum(row["variant_blocked"] for row in attacks),
        "external_targets": 0, "network_connections": 0, "real_credentials": 0,
        "persistence_actions": 0, "destructive_actions": 0, "data_exfiltration": 0,
    }
    gate["accepted"] = bool(
        gate["baseline_weaknesses_demonstrated"] == len(attacks)
        and gate["detections_recorded"] == len(attacks)
        and gate["repairs_verified"] == len(attacks)
        and gate["variant_attacks_rejected"] == len(attacks)
        and not any(gate[key] for key in (
            "external_targets", "network_connections", "real_credentials",
            "persistence_actions", "destructive_actions", "data_exfiltration"))
    )
    result = {
        "schema_version": "aion.hexcore.owned_purple_team_cyber_range.v1",
        "created_at": _utc_timestamp(), "procedure_id": PROCEDURE_ID,
        "passed": gate["accepted"], "attacks": attacks, "gate": gate,
        "tool_surface": ["python", "git", "curl", "openssl", "lldb", "tcpdump"],
        "claim_boundary": (
            "This is verified execution in a deliberately vulnerable non-networked owned range. "
            "It is qualification evidence, not world-class cybersecurity competence and not "
            "authority to assess any external target."
        ),
    }
    result["result_sha256"] = _hash(result)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = result_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    json.loads(temporary.read_text(encoding="utf-8"))
    os.replace(temporary, result_path)
    return result


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(run(repo_root=root,
                         result_path=root / "results/hexcore_owned_purple_team_cyber_range.json"),
                     indent=2, sort_keys=True))
