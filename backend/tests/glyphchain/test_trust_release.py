from __future__ import annotations

import base64
import json

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import pytest

from backend.modules.consensus.finality_checkpoint import CHECKPOINT_SCHEMA, normalize_checkpoint
from backend.modules.consensus.trust_release import (
    CHECKPOINT_FILENAME,
    MANIFEST_FILENAME,
    VERIFIER_FILENAME,
    TrustReleaseError,
    build_trust_release,
    verify_trust_release,
)


def _checkpoint(path):
    validators = []
    for index in range(3):
        key = Ed25519PrivateKey.generate()
        validators.append({
            "validator_id": f"validator-{index + 1}",
            "power": 1,
            "public_key_base64": base64.b64encode(key.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw,
            )).decode(),
        })
    value = normalize_checkpoint({
        "schema_version": CHECKPOINT_SCHEMA,
        "chain_id": "glyphchain-test",
        "network_id": "testnet",
        "epoch": 2,
        "effective_height": 100,
        "validator_set": validators,
    })
    path.write_text(json.dumps(value), encoding="utf-8")
    return value


def _build(tmp_path):
    checkpoint = _checkpoint(tmp_path / "source-checkpoint.json")
    verifier = tmp_path / "verifier.html"
    verifier.write_text(
        "<html><input id='checkpoint-pin'><script>const cpId='x',pin='y';"
        "if(pin!==cpId)throw Error('mismatch')</script></html>",
        encoding="utf-8",
    )
    output = tmp_path / "release-v1"
    result = build_trust_release(
        checkpoint_path=tmp_path / "source-checkpoint.json",
        verifier_path=verifier,
        output_directory=output,
        release_version="2026.09.27-rc1",
        release_manifest_sha256="ab" * 32,
        created_at="2026-09-27T10:00:00Z",
    )
    return checkpoint, output, result


def test_release_package_omits_pin_and_verifies_with_independent_value(tmp_path):
    checkpoint, output, result = _build(tmp_path)

    assert result["status"] == "BUILT_NOT_PUBLISHED"
    assert result["independent_pin_candidate"] == checkpoint["checkpoint_id"]
    assert result["pin_is_independently_published"] is False
    assert {item.name for item in output.iterdir()} == {
        CHECKPOINT_FILENAME, VERIFIER_FILENAME, MANIFEST_FILENAME,
    }
    manifest_text = (output / MANIFEST_FILENAME).read_text()
    assert "independent_pin_candidate" not in manifest_text
    assert checkpoint["checkpoint_id"] in manifest_text  # checkpoint identity is public

    verified = verify_trust_release(
        output,
        expected_checkpoint_id=checkpoint["checkpoint_id"],
        expected_release_manifest_sha256="ab" * 32,
    )
    assert verified["valid"] is True
    assert verified["trust_anchor_source"] == "independently_supplied_checkpoint_id"


def test_wrong_or_missing_independent_pin_fails_closed(tmp_path):
    _checkpoint, output, _result = _build(tmp_path)
    with pytest.raises(TrustReleaseError, match="trust_release_expected_checkpoint_id_invalid"):
        verify_trust_release(output, expected_checkpoint_id="")
    with pytest.raises(TrustReleaseError, match="trusted_checkpoint_id_mismatch"):
        verify_trust_release(output, expected_checkpoint_id="00" * 32)


@pytest.mark.parametrize("filename", [CHECKPOINT_FILENAME, VERIFIER_FILENAME, MANIFEST_FILENAME])
def test_release_detects_tampered_member(tmp_path, filename):
    checkpoint, output, _result = _build(tmp_path)
    path = output / filename
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(TrustReleaseError):
        verify_trust_release(output, expected_checkpoint_id=checkpoint["checkpoint_id"])


def test_release_rejects_unexpected_files_and_source_manifest_mismatch(tmp_path):
    checkpoint, output, _result = _build(tmp_path)
    (output / "pin.txt").write_text(checkpoint["checkpoint_id"], encoding="utf-8")
    with pytest.raises(TrustReleaseError, match="trust_release_file_set_invalid"):
        verify_trust_release(output, expected_checkpoint_id=checkpoint["checkpoint_id"])
    (output / "pin.txt").unlink()
    with pytest.raises(TrustReleaseError, match="trust_release_source_manifest_mismatch"):
        verify_trust_release(
            output,
            expected_checkpoint_id=checkpoint["checkpoint_id"],
            expected_release_manifest_sha256="cd" * 32,
        )


def test_release_output_is_immutable_and_symlink_sources_are_refused(tmp_path):
    _checkpoint_value, output, _result = _build(tmp_path)
    with pytest.raises(TrustReleaseError, match="trust_release_output_already_exists"):
        build_trust_release(
            checkpoint_path=tmp_path / "source-checkpoint.json",
            verifier_path=tmp_path / "verifier.html",
            output_directory=output,
            release_version="2026.09.27-rc1",
            release_manifest_sha256="ab" * 32,
        )

    link = tmp_path / "verifier-link.html"
    link.symlink_to(tmp_path / "verifier.html")
    with pytest.raises(TrustReleaseError, match="trust_release_symlink_refused"):
        build_trust_release(
            checkpoint_path=tmp_path / "source-checkpoint.json",
            verifier_path=link,
            output_directory=tmp_path / "release-v2",
            release_version="2026.09.27-rc2",
            release_manifest_sha256="ab" * 32,
        )


def test_release_rejects_verifier_without_independent_pin_gate(tmp_path):
    _checkpoint(tmp_path / "source-checkpoint.json")
    verifier = tmp_path / "unsafe-verifier.html"
    verifier.write_text("<html>no independent pin check</html>", encoding="utf-8")
    with pytest.raises(
        TrustReleaseError, match="trust_release_verifier_independent_pin_gate_missing",
    ):
        build_trust_release(
            checkpoint_path=tmp_path / "source-checkpoint.json",
            verifier_path=verifier,
            output_directory=tmp_path / "release",
            release_version="2026.09.27-rc1",
            release_manifest_sha256="ab" * 32,
        )
