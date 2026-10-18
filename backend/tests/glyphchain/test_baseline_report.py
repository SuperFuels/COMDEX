from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "backend" / "scripts" / "generate_glyphchain_baseline_report.py"


def _module():
    spec = importlib.util.spec_from_file_location("glyphchain_baseline_report", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _junit(path: Path, *, failures: int = 0) -> None:
    path.write_text(
        f'<testsuite name="glyphchain" tests="3" failures="{failures}" '
        'errors="0" skipped="0" time="1.25"></testsuite>',
        encoding="utf-8",
    )


def test_signed_baseline_report_verifies_against_separate_trust_anchor(tmp_path, monkeypatch):
    module = _module()
    junit = tmp_path / "results.xml"
    output = tmp_path / "baseline.json"
    private_key = tmp_path / "private.pem"
    public_key = tmp_path / "public.pem"
    _junit(junit)

    monkeypatch.setattr(
        "sys.argv",
        [
            str(SCRIPT),
            "--junit-xml",
            str(junit),
            "--output",
            str(output),
            "--key",
            str(private_key),
            "--public-key",
            str(public_key),
        ],
    )
    assert module.main() == 0
    module.verify_report(output, public_key)

    document = json.loads(output.read_text(encoding="utf-8"))
    document["result"] = "TAMPERED"
    output.write_text(json.dumps(document), encoding="utf-8")
    with pytest.raises(SystemExit, match="digest is invalid"):
        module.verify_report(output, public_key)


def test_failing_suite_cannot_be_signed(tmp_path):
    module = _module()
    junit = tmp_path / "results.xml"
    _junit(junit, failures=1)
    with pytest.raises(SystemExit, match="Refusing to sign"):
        module.junit_summary(junit)


def test_tracked_public_key_cannot_be_silently_replaced(tmp_path):
    module = _module()
    private_a = module.private_key(tmp_path / "a.pem")
    private_b = module.private_key(tmp_path / "b.pem")
    public_key = tmp_path / "public.pem"
    module.ensure_public_key(public_key, private_a)
    with pytest.raises(SystemExit, match="does not match"):
        module.ensure_public_key(public_key, private_b)


def test_baseline_key_and_report_paths_refuse_symlinks(tmp_path):
    module = _module()
    victim = tmp_path / "victim"
    victim.write_text("unchanged", encoding="utf-8")
    private_link = tmp_path / "private.pem"
    public_link = tmp_path / "public.pem"
    report_link = tmp_path / "report.json"
    private_link.symlink_to(victim)
    public_link.symlink_to(victim)
    report_link.symlink_to(victim)
    with pytest.raises(SystemExit, match="symbolic-link private key"):
        module.private_key(private_link)
    key = module.Ed25519PrivateKey.generate()
    with pytest.raises(SystemExit, match="symbolic-link public key"):
        module.ensure_public_key(public_link, key)
    with pytest.raises(SystemExit, match="symbolic-link output"):
        module._atomic_replace(report_link, b"replacement", mode=0o644)
    assert victim.read_text(encoding="utf-8") == "unchanged"


def test_baseline_report_replacement_is_atomic_and_public(tmp_path):
    module = _module()
    output = tmp_path / "baseline.json"
    output.write_text("old", encoding="utf-8")
    module._atomic_replace(output, b"new\n", mode=0o644)
    assert output.read_bytes() == b"new\n"
    assert output.stat().st_mode & 0o777 == 0o644


def test_source_manifest_binds_every_release_decision_component():
    module = _module()
    manifest = module.source_manifest()
    paths = {entry["path"] for entry in manifest["entries"]}
    assert {
        "backend/modules/aion_business/runtime/glyphchain_release_readiness.py",
        "backend/scripts/evaluate_glyphchain_legal_release_readiness.py",
        "backend/scripts/create_glyphchain_release_evidence.py",
        "backend/scripts/create_glyphchain_release_trust_roots.py",
        "backend/scripts/generate_glyphchain_baseline_report.py",
        "docs/aion/GLYPHCHAIN_RELEASE_EVIDENCE_ARTIFACT_CONTRACT_SECTION.tex",
        "docs/aion/GLYPHCHAIN_RELEASE_TRUST_ROOT_GOVERNANCE_SECTION.tex",
        "docs/aion/GLYPHCHAIN_TWO_PHASE_RELEASE_AUTHORIZATION_SECTION.tex",
    } <= paths
    expected_documentation = {
        str(path.relative_to(ROOT))
        for pattern in ("GLYPHCHAIN*.md", "GLYPHCHAIN*.tex")
        for path in (ROOT / "docs" / "aion").glob(pattern)
    }
    assert expected_documentation <= paths
