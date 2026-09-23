from __future__ import annotations

import pytest
import json
import os
import sys
from types import SimpleNamespace

from backend.scripts.run_aion_gptoss_c4_coverage_queue import training_order, verify_capture, run_guarded_capture
from backend.scripts.run_aion_gptoss_first_token_gate import acquire_inference_lock
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical, digest


def test_queue_is_family_balanced_and_training_only():
    rows = [{'family': family, 'split': split, 'id': f'{family}{index}'} for family in ('a', 'b') for index, split in enumerate(('training', 'training', 'selection', 'holdout'))]
    assert [row['id'] for row in training_order(rows)] == ['a0', 'b0', 'a1', 'b1']


def test_queue_rejects_failed_receipts(tmp_path):
    with pytest.raises(RuntimeError):
        verify_capture({'status': 'FAILED'}, tmp_path, 1)


def test_capture_stops_when_disk_reserve_is_crossed(tmp_path, monkeypatch):
    monkeypatch.setattr('backend.scripts.run_aion_gptoss_c4_coverage_queue.shutil.disk_usage',
                        lambda path: SimpleNamespace(free=0))
    with pytest.raises(RuntimeError, match='partial data preserved'):
        run_guarded_capture([sys.executable, '-c', 'import time; time.sleep(60)'],
                            tmp_path, dict(os.environ), tmp_path, poll_seconds=.01)


def test_guarded_capture_finishes_normally(tmp_path):
    run_guarded_capture([sys.executable, '-c', 'pass'], tmp_path,
                        dict(os.environ), tmp_path, reserve_bytes=0, poll_seconds=.01)


def test_full_model_lock_prevents_competing_jobs(tmp_path):
    path = tmp_path / 'inference.lock'
    handle = acquire_inference_lock(path)
    try:
        with pytest.raises(SystemExit, match='runtime lock'):
            acquire_inference_lock(path)
    finally:
        handle.close()
    acquire_inference_lock(path).close()


def test_queue_checks_full_grid_and_binary_integrity(tmp_path):
    for layer in range(36):
        stem = tmp_path / f'position-3-layer-{layer}'
        metadata = {'position': 3, 'layer': layer, 'route': [0, 1, 2, 3]}
        for name in ('router', 'ffn', 'output', 'residual', 'router_logits', 'fourth_contribution'):
            path = tmp_path / f'{stem.name}-{name}.bin'
            path.write_bytes(bytes(512 if name == 'router_logits' else 11520))
            metadata[f'{name}_sha256'] = digest(path)
        stem.with_suffix('.json').write_text(json.dumps(metadata))
    receipt = {'status': 'PASSED', 'quality_track': False, 'routes_repeatable': True,
               'final_hidden_and_logits_bitwise_repeatable': True,
               'activation_capture_dir': str(tmp_path), 'capture_positions': [3]}
    vocabulary = tmp_path / 'position-3-vocabulary.bin'
    vocabulary.write_bytes(bytes(201088 * 4))
    receipt['run_a'] = {'tokens': [{}, {}, {}, {'logits_sha256': digest(vocabulary)}]}
    receipt['canonical_sha256'] = canonical(receipt)
    verify_capture(receipt, tmp_path, 36)
    metadata_path=tmp_path / 'position-3-layer-0.json'
    metadata=json.loads(metadata_path.read_text())
    for name in ('second_contribution','third_contribution'):
        target=tmp_path / f'position-3-layer-0-{name}.bin'
        target.write_bytes(bytes(11520))
        metadata[f'{name}_sha256']=digest(target)
    metadata_path.write_text(json.dumps(metadata))
    verify_capture(receipt,tmp_path,36)
    third=tmp_path / 'position-3-layer-0-third_contribution.bin'
    third.write_bytes(b'corrupt')
    with pytest.raises(RuntimeError,match='ranked correction target'):
        verify_capture(receipt,tmp_path,36)
    third.write_bytes(bytes(11520))
    (tmp_path / 'position-3-layer-0-router.bin').write_bytes(b'corrupt')
    with pytest.raises(RuntimeError, match='binary failed verification'):
        verify_capture(receipt, tmp_path, 36)
