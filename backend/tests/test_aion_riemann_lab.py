import importlib.util
import hashlib
import json
from pathlib import Path

import pytest


REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "aion_riemann_lab.py"
LIVE_SCRIPT = REPO / "scripts" / "aion_riemann_live_exam.py"
LAB = REPO / "research" / "riemann_lab"


def load_harness():
    spec = importlib.util.spec_from_file_location("aion_riemann_lab", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def load_live_harness():
    spec = importlib.util.spec_from_file_location("aion_riemann_live_exam", LIVE_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def test_proof_policy_rejects_no_local_incompleteness():
    policy = load_harness().proof_policy()
    assert policy["accepted"] is True
    assert policy["project_declared_incompleteness"] == []


def test_dependency_graph_keeps_rh_open_and_selects_prerequisite():
    graph = json.loads((LAB / "dependency_graph.json").read_text())
    statuses = {node["id"]: node["status"] for node in graph["nodes"]}
    assert statuses["critical_line"] == "open"
    assert graph["selected_target"]["id"] == "critical_strip"
    assert graph["selected_target"]["new_mathematics_claimed"] is False


def test_photon_algebra_is_not_a_lab_dependency():
    authored = [
        LAB / "README.md",
        LAB / "lakefile.toml",
        LAB / "lean-toolchain",
        LAB / "RiemannLab.lean",
        LAB / "dependency_graph.json",
    ]
    authored.extend(sorted((LAB / "RiemannLab").rglob("*.lean")))
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in authored
        if path.is_file()
    ).lower()
    assert "photon algebra" not in combined


def test_live_exam_is_matched_sealed_completed_and_not_self_awarded():
    packet = json.loads((LAB / "live_task_packet.json").read_text())
    assert packet["execution_status"] == "completed"
    assert packet["fixed_fixtures"] is False
    assert packet["same_proposer_required"] is True
    assert packet["budgets"]["max_attempts_per_task"] == 2
    assert [arm["id"] for arm in packet["arms"]] == [
        "proposer_alone",
        "aion_memory_repair",
        "aion_no_memory",
        "aion_no_repair",
    ]
    assert all(task["proof_body_disclosed"] is False for task in packet["source_closed_tasks"])
    assert packet["acceptance"]["self_awarded_success_forbidden"] is True

    assert len(packet["execution_history"]) == 1
    completed = packet["execution_history"][0]
    result_path = REPO / completed["result"]
    result_bytes = result_path.read_bytes()
    assert hashlib.sha256(result_bytes).hexdigest() == completed["result_sha256"]
    result = json.loads(result_bytes)
    assert result["task_packet_hash"] == completed["sealed_task_packet_sha256"]
    assert [arm["arm_id"] for arm in result["arms"]] == [
        "proposer_alone",
        "aion_memory_repair",
        "aion_no_memory",
        "aion_no_repair",
    ]
    assert "does not prove RH or claim new mathematics" in result["claim_boundary"]


@pytest.mark.parametrize(
    ("task_id", "proof"),
    [
        ("zeta_at_zero", "exact riemannZeta_zero"),
        ("trivial_zero_family", "exact riemannZeta_neg_two_mul_nat_add_one n"),
        ("zero_free_right_half_plane", "exact riemannZeta_ne_zero_of_one_lt_re hs"),
    ],
)
def test_exact_live_task_templates_accept_known_correct_proofs(task_id, proof):
    harness = load_live_harness()
    verification = harness.verify({"task_id": task_id}, proof)
    assert verification["passed"], verification["diagnostic"]


def test_verified_aion_memory_rejects_unverified_and_retrieves_compiler_evidence(tmp_path):
    harness = load_live_harness()
    from scripts.aion_riemann_verified_memory import AionVerifiedMathMemory

    memory = AionVerifiedMathMemory(tmp_path / "verified_memory.json")
    with pytest.raises(ValueError, match="only Lean-accepted"):
        memory.ingest_compiler_verified_method(
            task_id="zeta_at_zero",
            statement="riemannZeta 0 = -(1 : ℂ) / 2",
            theorem_signature="riemannZeta_zero",
            method_pattern="rewrite a verified special value",
            required_imports=["Mathlib.NumberTheory.LSeries.RiemannZeta"],
            verification={"passed": False, "returncode": 1, "source_hash": None},
            source_uri="test",
        )

    verification = harness.verify({"task_id": "zeta_at_zero"}, "exact riemannZeta_zero")
    promoted = memory.ingest_compiler_verified_method(
        task_id="zeta_at_zero",
        statement="riemannZeta 0 = -(1 : ℂ) / 2",
        theorem_signature="riemannZeta_zero : riemannZeta 0 = -(1 : ℂ) / 2",
        method_pattern="rewrite a verified special value",
        required_imports=["Mathlib.NumberTheory.LSeries.RiemannZeta"],
        verification=verification,
        source_uri="research/riemann_lab/CatalogProbe.lean",
    )
    recalled = memory.retrieve(
        task_id="zeta_at_zero",
        statement="riemannZeta 0 = -(1 : ℂ) / 2",
    )
    assert promoted["claim_ids"]
    assert recalled[0]["claim_id"] in promoted["claim_ids"]
    assert recalled[0]["method"]["proof_body_retained"] is False
    assert recalled[0]["method"]["method_pattern"] == "rewrite a verified special value"


def test_governed_repair_routes_unknown_theorems_without_self_grading():
    from scripts.aion_riemann_verified_memory import AionLeanRepairController

    repair = AionLeanRepairController().diagnose(
        task_id="zeta_at_zero",
        diagnostic="error(lean.unknownIdentifier): Unknown identifier `riemannZeta_zer0`",
        attempt=1,
    )
    assert repair["category"] == "unknown_theorem"
    assert repair["max_next_attempts"] == 1
    assert repair["repair_record_id"].startswith("lean_repair_")


def test_pinned_mathlib_discovery_returns_relevant_real_declarations():
    from scripts.aion_riemann_verified_memory import AionMathlibTheoremDiscovery

    discovery = AionMathlibTheoremDiscovery(
        LAB / ".lake" / "packages" / "mathlib" / "Mathlib" / "NumberTheory" / "LSeries"
    )
    right_half_plane = discovery.search(
        statement="For s : ℂ with 1 < s.re, riemannZeta s ≠ 0"
    )
    compact_zeros = discovery.search(
        statement="Every compact S : Set ℂ has finite intersection with riemannZetaZeros"
    )
    assert right_half_plane[0]["name"] == "riemannZeta_ne_zero_of_one_lt_re"
    assert compact_zeros[0]["name"] == "IsCompact.inter_riemannZetaZeros_finite"
    assert all(row["discovery_id"].startswith("mathlib_") for row in right_half_plane)


def test_completed_packet_blocks_live_exam_before_loading_api_key(monkeypatch):
    harness = load_live_harness()
    key_loaded = False

    def forbidden_key_load():
        nonlocal key_loaded
        key_loaded = True
        raise AssertionError("API key must not be loaded for a completed packet")

    monkeypatch.setattr(harness, "load_key", forbidden_key_load)
    with pytest.raises(RuntimeError, match="execution_status='ready'"):
        harness.main()
    assert key_loaded is False


def test_v3_packet_is_hash_frozen_multi_family_and_live_ready():
    packet_path = LAB / "live_task_packet_v3.json"
    packet = json.loads(packet_path.read_text())
    assert packet["execution_status"] == "ready"
    assert len(packet["source_closed_tasks"]) == 6
    assert len({task["family"] for task in packet["source_closed_tasks"]}) == 6
    cold = next(arm for arm in packet["arms"] if arm["id"] == "cold_aion")
    assert cold == {"id": "cold_aion", "memory": True, "repair": True, "isolated_state": True}
    assert packet["precommitted_scoring"]["full_aion_minimum_passed"] == 4
    assert packet["budgets"]["max_output_tokens_per_call"] == 1000
    for task in packet["source_closed_tasks"]:
        assert hashlib.sha256(task["statement"].encode()).hexdigest() == task["statement_sha256"]
        assert task["proof_body_disclosed"] is False

    environment = hashlib.sha256()
    for name in ("lean-toolchain", "lake-manifest.json", "lakefile.toml"):
        environment.update(name.encode() + b"\0" + (LAB / name).read_bytes())
    assert environment.hexdigest() == packet["environment_sha256"]

    harness = load_live_harness()
    harness.validate_packet(packet, packet_path=packet_path)
    tampered = json.loads(json.dumps(packet))
    tampered["source_closed_tasks"][0]["statement"] += " "
    with pytest.raises(RuntimeError, match="statement hash mismatch"):
        harness.validate_packet(tampered)


def test_latest_local_report_has_clean_verified_memory_and_no_paid_calls():
    report = json.loads(
        (REPO / "results" / "riemann_lab" / "local_verification_latest.json").read_text()
    )
    assert report["passed"] is True
    assert report["paid_api_calls"] == 0
    assert len(report["live_templates"]) == 6
    assert len(report["v2_held_out_templates"]) == 6
    assert all(row["passed"] for row in report["v2_held_out_templates"])
    assert report["aion_memory"]["active_claims"] == 6
    assert report["aion_memory"]["evidence_capsules"] == 6
    assert report["aion_memory"]["contradictions"] == 0


def test_harness_labels_fixed_candidates_as_smoke_test_only():
    source = SCRIPT.read_text()
    assert "PASS_TRUSTED_LAB_SMOKE_TEST" in source
    assert "PASS_BASELINE_AND_MECHANISM" not in source
    assert '"live_aion_invoked": False' in source
