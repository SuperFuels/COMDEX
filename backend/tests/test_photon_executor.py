from pathlib import Path
from backend.modules.photon.photon_executor import parse_photon_file, execute_capsule

def test_parse_and_execute_example(tmp_path):
    content = "^capsule { ⊕ add { 1 2 } }"
    file = tmp_path / "example.phn"
    file.write_text(content)

    capsules = parse_photon_file(file)
    assert capsules
    cap = capsules[0]

    result = execute_capsule(cap)
    assert "capsule" in result
    assert "results" in result