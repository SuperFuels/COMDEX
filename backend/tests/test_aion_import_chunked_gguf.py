import importlib.util
import sys
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "aion_import_chunked_gguf.py"
SPEC = importlib.util.spec_from_file_location("aion_import_chunked_gguf", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_chunk_ranges_cover_source_exactly():
    ranges = list(MODULE.chunk_ranges(10, 4))
    assert ranges == [(0, 0, 4), (1, 4, 4), (2, 8, 2)]
    assert sum(length for _, _, length in ranges) == 10


def test_atomic_json_and_sha256(tmp_path):
    target = tmp_path / "nested" / "receipt.json"
    MODULE.atomic_json(target, {"answer": 42})
    assert target.read_text() == '{\n  "answer": 42\n}\n'
    assert MODULE.sha256_path(target) == "5823dd82885cb7115a6dc367851a93a23b86d80d7154cc5bd4e8e9aafee07ecd"
