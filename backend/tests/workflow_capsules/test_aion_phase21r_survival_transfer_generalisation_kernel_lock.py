import json

from backend.modules.aion_survival import run_survival_transfer_generalisation_kernel


def _write_hazard_memory(path):
    path.write_text(
        json.dumps(
            {
                "policy": {
                    "known_hazards": ["1,0"],
                    "avoid_hazard": 0.7,
                },
                "prediction_model": {
                    "hazard": -3.0,
                },
                "uses_llm_shortcut": False,
            }
        ),
        encoding="utf-8",
    )


def test_phase21r_transfers_hazard_concept_to_new_world(tmp_path):
    hazard_memory = tmp_path / "hazard_memory.json"
    transfer_memory = tmp_path / "transfer_memory.json"
    _write_hazard_memory(hazard_memory)

    result = run_survival_transfer_generalisation_kernel(
        hazard_memory_path=hazard_memory,
        transfer_memory_path=transfer_memory,
        max_ticks=10,
    )

    assert result.kernel_version == "phase21r_survival_transfer_generalisation_kernel_v1"
    assert result.source_hazard_memory_loaded is True
    assert result.evidence["uses_llm_shortcut"] is False
    assert result.evidence["uses_hazard_concept_transfer"] is True
    assert result.survived is True
    assert result.concept_generalised is True
    assert result.new_hazards_hit == 0
    assert result.new_hazards_avoided >= 1
    assert "1,0" in result.old_known_hazards
    assert "0,1" in result.new_hazard_positions
    assert transfer_memory.exists()


def test_phase21r_records_transfer_ticks(tmp_path):
    hazard_memory = tmp_path / "hazard_memory.json"
    transfer_memory = tmp_path / "transfer_memory.json"
    _write_hazard_memory(hazard_memory)

    result = run_survival_transfer_generalisation_kernel(
        hazard_memory_path=hazard_memory,
        transfer_memory_path=transfer_memory,
        max_ticks=5,
    )

    tick = result.ticks[0]
    assert "predicted_cell_type" in tick
    assert "actual_cell_type" in tick
    assert "concept_used" in tick
    assert "avoided_new_hazard" in tick
    assert "observation" in tick


def test_phase21r_without_source_memory_does_not_claim_generalisation(tmp_path):
    result = run_survival_transfer_generalisation_kernel(
        hazard_memory_path=tmp_path / "missing.json",
        transfer_memory_path=tmp_path / "transfer.json",
        max_ticks=5,
    )

    assert result.source_hazard_memory_loaded is False
    assert result.concept_generalised is False
