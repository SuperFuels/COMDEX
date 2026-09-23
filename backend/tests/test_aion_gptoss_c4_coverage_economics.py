import json

import pytest

from backend.scripts.analyze_aion_gptoss_c4_coverage_economics import speed_bound, summarize
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical


def test_full_equal_cost_fourth_expert_removal_is_not_fourfold():
    assert speed_bound(1, 0, .25)['speed_multiplier_bound'] == pytest.approx(4 / 3)


def test_small_coverage_has_small_gain():
    bound = speed_bound(.025, .0773, .25)
    assert bound['hypothetical_tps_bound'] == pytest.approx(7.0406039338)
    assert speed_bound(1, 1, .25)['speed_multiplier_bound'] == 1


@pytest.mark.parametrize('values', [(-1, 0, .25), (1, 2, .25), (1, 0, float('nan'))])
def test_invalid_economics_rejected(values):
    with pytest.raises(ValueError):
        speed_bound(*values)


def test_partial_captures_never_count_as_evidence(tmp_path):
    corpus = {'rows': [{'capture_id': 'train', 'split': 'training'}]}
    corpus['canonical_sha256'] = canonical(corpus)
    path = tmp_path / 'corpus.json'
    path.write_text(json.dumps(corpus))
    root = tmp_path / 'queue'
    (root / 'train').mkdir(parents=True)
    (root / 'train' / 'teacher.json').write_text('{}')
    report = summarize(root, path)
    assert report['status'] == 'WAITING_FOR_VERIFIED_CAPTURE'
    assert report['continuation_e4_calls'] == 0
    assert report['certified_traffic_share'] is None
    assert report['partial_capture_directories_excluded'] == ['train']


def test_corrupt_seal_stops_analysis(tmp_path):
    corpus = {'rows': []}
    corpus['canonical_sha256'] = canonical(corpus)
    path = tmp_path / 'corpus.json'
    path.write_text(json.dumps(corpus))
    root = tmp_path / 'queue'
    (root / 'bad').mkdir(parents=True)
    (root / 'bad' / 'COMPLETE_VERIFIED.json').write_text('{}')
    with pytest.raises(RuntimeError, match='hash mismatch'):
        summarize(root, path)
