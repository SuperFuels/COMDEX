from backend.modules.hexcore.real_rust_apprenticeship import (
    PROJECTS,
    RetainedRustPatternProposer,
    _audit,
    _official_resources,
    _prompt,
    _proposal_files,
    run,
)


def test_installed_rust_authority_is_available():
    resources = _official_resources()
    assert resources["all_available"] is True
    assert resources["rustc"]["text"].startswith("rustc 1.")
    assert all(row["bytes"] > 500 for row in resources["explanations"].values())


def test_apprenticeship_security_gate_rejects_privileged_rust():
    for source in (
        "unsafe fn bypass() {}",
        "use std::process::Command;",
        "use std::net::TcpStream;",
        "use std::fs::File;",
    ):
        result = _audit({"Cargo.toml": "[package]\nname='x'\nversion='0.1.0'", "src/lib.rs": source})
        assert result["safe"] is False


def test_retained_apprentice_instantiates_distinct_unfamiliar_projects():
    proposer = RetainedRustPatternProposer()
    resources = _official_resources()
    proposals = [
        _proposal_files(proposer.propose(_prompt(project, resources, []), seed=7000 + index)["proposal"])
        for index, project in enumerate(PROJECTS)
    ]
    assert len({files["Cargo.toml"] for files in proposals}) == 4
    assert all(len(files) >= 4 for files in proposals)
    assert all(len(files.get("tests/self_tests.rs", "")) > 200 for files in proposals)


def test_real_apprenticeship_passes_compiler_hidden_transfer_and_restart_gates(tmp_path):
    result = run(
        state_path=tmp_path / "runtime.json",
        result_path=tmp_path / "result.json",
        proposer=RetainedRustPatternProposer(),
    )
    assert result["passed"] is True
    assert result["gate"]["verified_projects"] == 4
    assert result["gate"]["hidden_authority_success"] == 1.0
    assert result["gate"]["source_disjoint_transfer_success"] == 1.0
    assert result["gate"]["restart_retention_success"] == 1.0
    assert result["gate"]["source_replay_into_retention"] == 0
    assert result["gate"]["malicious_variants_rejected"] == 6
    assert result["promotion"]["decision"]["promoted"] is True
