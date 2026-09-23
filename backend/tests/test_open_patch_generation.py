from __future__ import annotations

import json
from pathlib import Path

from backend.modules.hexcore.open_patch_generation_benchmark import (
    _apply_proposal,
    _security_scan,
)


ROOT = Path(__file__).resolve().parents[2]


def test_open_patch_application_accepts_one_unique_reflowed_region():
    source = "value = function(\n    first,\n    second,\n)\n"
    proposal = {
        "operations": [
            {
                "op": "replace",
                "old_text": "value = function( first, second, )",
                "new_text": "value = safer(first, second)",
            }
        ]
    }

    result = _apply_proposal(source, proposal)

    assert result["applied"] is True
    assert result["reason"] == "REPLACEMENTS:1:WHITESPACE_FLEXIBLE:1"
    assert result["candidate"] == "value = safer(first, second)\n"


def test_open_patch_application_rejects_ambiguous_reflowed_region():
    source = (
        "value = function(\n    first\n)\n"
        "value = function(\n        first\n)\n"
    )
    proposal = {
        "operations": [
            {
                "op": "replace",
                "old_text": "value = function( first )",
                "new_text": "value = safer(first)\n",
            }
        ]
    }

    result = _apply_proposal(source, proposal)

    assert result["applied"] is False
    assert "FLEXIBLE:2" in result["reason"]


def test_latest_open_patch_cohort_remains_rejected_after_strict_audit():
    result = json.loads(
        (ROOT / "results/hexcore_open_patch_generation.json").read_text(
            encoding="utf-8"
        )
    )

    assert result["passed"] is False
    assert result["gate"]["task_specific_repair_menus"] == 0
    assert result["gate"]["open_generated_repair_success"] == 2 / 3
    assert result["gate"]["safe_abstentions"] == 1
    assert result["gate"]["unsafe_acceptances"] == 0
    assert result["gate"]["unsafe_live_writes"] == 0
    assert result["gate"]["live_sources_unchanged"] is True
    assert result["gate"]["human_patch_blind_during_generation"] is True


def test_security_scan_rejects_functional_bypass_patterns():
    source = "def decode(value):\n    return parse(value)\n"
    candidate = (
        "def decode(value):\n"
        "    return eval(value)\n"
        "\n"
        "verify = False\n"
    )

    result = _security_scan(source, candidate)

    assert result["safe"] is False
    assert "dynamic_execution" in result["findings"]
    assert "verification_disabled" in result["findings"]


def test_security_scan_allows_bounded_data_transformation():
    source = "def decode(value):\n    return parse(value)\n"
    candidate = (
        "def decode(value):\n"
        "    cleaned = value.strip()\n"
        "    return parse(cleaned)\n"
    )

    assert _security_scan(source, candidate)["safe"] is True


def test_security_scan_rejects_python_world_writable_mode():
    source = "def configure(path):\n    return path\n"
    candidate = (
        "def configure(path):\n"
        "    chmod(path, 0o777)\n"
        "    return path\n"
    )

    result = _security_scan(source, candidate)

    assert result["safe"] is False
    assert "world_writable" in result["findings"]
