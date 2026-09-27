import json

import pytest

from backend.scripts.promote_aion_fused_router import _canonical_sha256, _load


def test_load_verifies_canonical_hash(tmp_path) -> None:
    value={"measurement":1};value["report_sha256"]=_canonical_sha256(value)
    path=tmp_path/"evidence.json";path.write_text(json.dumps(value))
    assert _load(path)["measurement"]==1
    value["measurement"]=2;path.write_text(json.dumps(value))
    with pytest.raises(ValueError,match="canonical hash failed"):_load(path)
