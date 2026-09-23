import hashlib
from types import SimpleNamespace

import pytest

from backend.modules.aion_inference.gptoss_expert_frame_store import GptOssPersistentL2ExpertFrameStore as L2
from backend.scripts.run_aion_ranked_correction_reduction_gate import read_cached
from backend.scripts.run_aion_gptoss_local_c4_prototype_gate import digest


def frame(tmp_path):
    manifest = tmp_path / 'manifest.json'
    manifest.write_text('{}')
    parts = [bytes([i + 1]) * 4 for i in range(6)]
    addresses = {(12, 22, projection, kind): {
        'raw_bytes': len(raw), 'raw_sha256': hashlib.sha256(raw).hexdigest()
    } for (projection, kind), raw in zip(L2._ORDER, parts, strict=True)}
    path = tmp_path / digest(manifest) / 'layer-12-expert-022.aionraw'
    path.parent.mkdir()
    path.write_bytes(L2._HEADER.pack(L2._MAGIC, *map(len, parts)) + b''.join(parts))
    return SimpleNamespace(manifest_path=manifest, _addresses=addresses), path


def test_cached_read_is_verified_and_read_only(tmp_path):
    store, path = frame(tmp_path)
    before = path.read_bytes()
    mtime = path.stat().st_mtime_ns
    result = read_cached(store, tmp_path, 12, 22)
    assert len(result) == 3
    assert path.read_bytes() == before
    assert path.stat().st_mtime_ns == mtime


def test_corrupt_cached_component_is_preserved_and_rejected(tmp_path):
    store, path = frame(tmp_path)
    damaged = path.read_bytes()[:-1] + b'x'
    path.write_bytes(damaged)
    with pytest.raises(RuntimeError, match='differs'):
        read_cached(store, tmp_path, 12, 22)
    assert path.read_bytes() == damaged


def test_missing_cache_does_not_fetch_or_admit(tmp_path):
    store, path = frame(tmp_path)
    with pytest.raises(FileNotFoundError):
        read_cached(store, tmp_path, 12, 23)
    assert list(path.parent.iterdir()) == [path]
