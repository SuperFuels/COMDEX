from __future__ import annotations

import json
import zipfile

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from backend.modules.aion_fabric.canonical import canonical_bytes
from backend.modules.aion_fabric.identity import DeviceIdentity
from backend.modules.pilot_unified.ownership import DEPLOYMENT_PROFILES, MotherOwnershipAuthority


def _authority(tmp_path):
    identity = DeviceIdentity(Ed25519PrivateKey.generate())
    return MotherOwnershipAuthority(tmp_path / "runtime", identity=identity, mother_id="mother_test"), identity


def test_all_customer_owned_deployment_profiles_keep_tessaris_out_of_data_path(tmp_path):
    authority, _ = _authority(tmp_path)
    assert set(DEPLOYMENT_PROFILES) == {"personal_computer", "home_server", "private_vps", "business"}
    for profile in DEPLOYMENT_PROFILES:
        plan = authority.deployment_plan(profile=profile, customer_cloud="Customer AWS")
        assert plan["data_controller"] == "customer"
        assert plan["mother_location"] == "customer_controlled"
        assert plan["tessaris_data_copy_required"] is False
        assert "single_writable_primary" in plan["required_controls"]


def test_clean_signed_deployment_packages_cover_all_profiles_without_private_state(tmp_path):
    authority, identity = _authority(tmp_path)
    source = tmp_path / "application"
    (source / "backend").mkdir(parents=True)
    (source / "backend" / "app.py").write_text("print('pilot')")
    (source / ".runtime").mkdir()
    (source / ".runtime" / "memory.json").write_text('{"private":"memory"}')
    (source / ".env").write_text("API_KEY=must-not-ship")
    (source / "private_token.txt").write_text("must-not-ship")

    for profile in DEPLOYMENT_PROFILES:
        package = tmp_path / "packages" / f"{profile}.zip"
        result = authority.build_deployment_package(
            profile=profile, application_source=source, destination=package, version="1.0.0",
        )
        assert result["verified"] is True
        assert result["customer_data_included"] is False
        with zipfile.ZipFile(package) as archive:
            names = archive.namelist()
            encoded = b"".join(archive.read(name) for name in names)
            assert "pilot/backend/app.py" in names
            assert b"must-not-ship" not in encoded
            assert not any(".runtime" in name or ".env" in name or "token" in name for name in names)
        assert authority.verify_deployment_package(
            package=package, signer_public_key=identity.public_key_b64,
        )["verified"] is True


def test_signed_connection_descriptor_contains_no_mother_secret(tmp_path):
    authority, identity = _authority(tmp_path)
    descriptor = authority.connection_descriptor(endpoints=["https://pilot.home.test:8770"])
    assert descriptor["contains_mother_secret"] is False
    assert MotherOwnershipAuthority.verify_connection_descriptor(descriptor, identity.public_key_b64) is True
    changed = {**descriptor, "endpoints": ["https://attacker.test"]}
    assert MotherOwnershipAuthority.verify_connection_descriptor(changed, identity.public_key_b64) is False


def test_rendezvous_exposes_only_sealed_descriptor_to_phone(tmp_path):
    authority, _ = _authority(tmp_path)
    descriptor = authority.connection_descriptor(endpoints=["https://private.example.test"])
    phone = X25519PrivateKey.generate()
    phone_public = phone.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    record = authority.sealed_rendezvous_record(
        descriptor=descriptor,
        phone_transport_public_key=__import__("base64").b64encode(phone_public).decode("ascii"),
    )
    encoded = json.dumps(record)
    assert "private.example.test" not in encoded
    assert record["readable_endpoint_exposed"] is False
    assert authority.open_rendezvous_record(record, phone) == descriptor


def test_encrypted_backup_verifies_and_restores_exact_files(tmp_path):
    authority, _ = _authority(tmp_path)
    source = tmp_path / "mother"
    (source / "identity").mkdir(parents=True)
    (source / "identity" / "key.pem").write_text("mother private key")
    (source / "memory.json").write_text('{"private":"business map"}')
    backup = tmp_path / "safe" / "mother.pilotbackup"

    receipt = authority.create_backup(source=source, destination=backup, passphrase="a sufficiently long phrase")
    assert receipt["verified"] is True
    assert "mother private key" not in backup.read_text()
    assert authority._read()["last_successful_backup_at"] == receipt["created_at"]

    restored = tmp_path / "restored"
    result = authority.restore_backup(backup=backup, destination=restored, passphrase="a sufficiently long phrase")
    assert result["verified"] is True
    assert (restored / "identity" / "key.pem").read_text() == "mother private key"
    assert (restored / "memory.json").read_text() == '{"private":"business map"}'
    with pytest.raises(PermissionError):
        authority.inspect_backup(destination=backup, passphrase="wrong password here")


def test_complete_signed_mother_migration_preserves_private_state(tmp_path):
    source_authority, source_identity = _authority(tmp_path / "source-authority")
    mother = tmp_path / "source-mother"
    (mother / "identity").mkdir(parents=True)
    (mother / "identity" / "mother.key").write_text("source mother identity")
    (mother / "permissions").mkdir()
    (mother / "permissions" / "leases.json").write_text('{"tv":"approved"}')
    (mother / "messages.json").write_text('[{"body":"private"}]')
    (mother / "proofs.json").write_text('[{"hash":"abc"}]')
    package = tmp_path / "exports" / "mother.pilotmigration"

    exported = source_authority.create_migration_export(
        source=mother, destination=package, passphrase="migration passphrase long enough",
    )
    assert exported["verified"] is True
    assert "source mother identity" not in package.read_bytes().decode("latin1")

    target_authority, _ = _authority(tmp_path / "target-authority")
    restored_dir = tmp_path / "restored-mother"
    restored = target_authority.restore_migration_export(
        package=package, destination=restored_dir,
        passphrase="migration passphrase long enough",
        source_public_key=source_identity.public_key_b64,
    )
    assert restored["verified"] is True
    assert restored["identity_permissions_messages_proofs_preserved"] is True
    assert restored["destination_primary_activation_required"] is True
    assert (restored_dir / "identity" / "mother.key").read_text() == "source mother identity"
    assert (restored_dir / "permissions" / "leases.json").read_text() == '{"tv":"approved"}'
    assert (restored_dir / "messages.json").read_text() == '[{"body":"private"}]'
    assert (restored_dir / "proofs.json").read_text() == '[{"hash":"abc"}]'

    with pytest.raises(PermissionError):
        target_authority.restore_migration_export(
            package=package, destination=tmp_path / "wrong-passphrase",
            passphrase="wrong migration phrase",
            source_public_key=source_identity.public_key_b64,
        )


def test_primary_lease_prevents_two_writable_instances(tmp_path):
    authority, _ = _authority(tmp_path)
    first = authority.acquire_primary(instance_id="instance-one", ttl_seconds=30)
    assert first["instance_id"] == "instance-one"
    with pytest.raises(PermissionError, match="Another Pilot"):
        authority.acquire_primary(instance_id="instance-two", ttl_seconds=30)
    authority.release_primary(instance_id="instance-one")
    assert authority.acquire_primary(instance_id="instance-two", ttl_seconds=30)["instance_id"] == "instance-two"


def test_signed_update_stages_then_rolls_back_on_failed_health(tmp_path):
    authority, signer = _authority(tmp_path)
    artifact = tmp_path / "pilot-update.bin"
    artifact.write_bytes(b"signed update content")
    digest = __import__("hashlib").sha256(artifact.read_bytes()).hexdigest()
    signature = signer.sign(canonical_bytes({"version": "1.2.3", "sha256": digest}))
    staged = authority.stage_update(
        artifact=artifact, signature=signature, signer_public_key=signer.public_key_b64, version="1.2.3"
    )
    assert staged["status"] == "staged"
    assert authority.verify_or_rollback_update(version="1.2.3", health_check=lambda: False)["status"] == "rolled_back"
    assert not __import__("pathlib").Path(staged["path"]).exists()


def test_update_rejects_unsigned_artifact(tmp_path):
    authority, signer = _authority(tmp_path)
    artifact = tmp_path / "bad.bin"
    artifact.write_bytes(b"bad")
    with pytest.raises(PermissionError):
        authority.stage_update(
            artifact=artifact, signature=signer.sign(b"different"),
            signer_public_key=signer.public_key_b64, version="9.9.9",
        )


def test_support_bundle_redacts_credentials_and_tokens(tmp_path):
    authority, _ = _authority(tmp_path)
    bundle = authority.diagnostic_bundle({
        "status": "healthy", "api_key": "super-secret", "nested": {"password": "pw"},
        "log": "request failed Authorization: Bearer abc.def.ghi",
    })
    encoded = json.dumps(bundle)
    assert bundle["secrets_included"] is False
    assert "super-secret" not in encoded
    assert '"pw"' not in encoded
    assert "abc.def.ghi" not in encoded
    assert bundle["diagnostics"]["status"] == "healthy"
