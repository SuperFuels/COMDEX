from __future__ import annotations

import json
import sys

import pytest

from backend.scripts.evaluate_aion_gptoss_frozen_c4_local import main
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import canonical


def configure(monkeypatch, tmp_path, teacher):
    receipt = tmp_path / 'teacher.json'
    receipt.write_text(json.dumps(teacher))
    monkeypatch.setattr(sys, 'argv', ['evaluate', '--manifest', str(tmp_path / 'manifest'),
                                     '--cartridge', str(tmp_path / 'cartridge'),
                                     '--capture-dir', str(tmp_path / 'captures'),
                                     '--teacher-receipt', str(receipt),
                                     '--output', str(tmp_path / 'output.json')])


def test_local_evaluation_rejects_unbound_teacher(monkeypatch, tmp_path):
    configure(monkeypatch, tmp_path, {'canonical_sha256': 'not-the-hash'})
    with pytest.raises(SystemExit, match='teacher receipt hash mismatch'):
        main()


def test_local_evaluation_requires_repeatable_teacher(monkeypatch, tmp_path):
    teacher = {'status': 'FAILED', 'routes_repeatable': False}
    teacher['canonical_sha256'] = canonical(teacher)
    configure(monkeypatch, tmp_path, teacher)
    with pytest.raises(SystemExit, match='exact repeatability'):
        main()
