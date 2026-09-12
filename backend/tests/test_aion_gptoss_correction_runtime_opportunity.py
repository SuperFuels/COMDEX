import pytest

from backend.scripts.analyze_aion_gptoss_correction_runtime_opportunity import summarize_run


def run(n):
    return {'tokens': [{'position': 1, 'wall_seconds': 1., 'layers': [
        {'layer': i, 'route': list(range(n)), 'finish_process_seconds': .01,
         'expert_load_seconds': 0.} for i in range(36)]}]}


def test_three_expert_path_has_no_c4_opportunity():
    result = summarize_run(run(3), 1, 0)
    assert result['four_expert_call_share'] == 0
    assert result['hypothetical_full_e4_coverage_multiplier'] == 1
    assert result['hypothetical_last_expert_replacement_multiplier'] > 1


def test_four_expert_share_is_charged_once():
    result = summarize_run(run(4), 1, 0)
    assert result['equal_share_e4_time_fraction'] == pytest.approx(.09)
    assert result['hypothetical_full_e4_coverage_multiplier'] == pytest.approx(1 / .91)


def test_no_continuation_cannot_be_timed():
    with pytest.raises(ValueError, match='no continuation'):
        summarize_run(run(4), 2, 0)


def test_incomplete_backbone_rejected():
    data = run(4)
    data['tokens'][0]['layers'].pop()
    with pytest.raises(ValueError, match='36 layers'):
        summarize_run(data, 1, 0)
