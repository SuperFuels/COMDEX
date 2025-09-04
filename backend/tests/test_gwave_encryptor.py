import pytest
from backend.modules.glyphwave.qkd.gkey_encryptor import GWaveEncryptor


@pytest.fixture
def sample_gkey():
    return {
        "collapse_hash": "sample-collapse-hash-12345"
    }


@pytest.fixture
def sample_payload():
    return {
        "message": "This is a test payload",
        "metadata": {"important": True}
    }


def test_encrypt_decrypt_roundtrip(sample_gkey, sample_payload):
    encryptor = GWaveEncryptor(sample_gkey)
    encrypted = encryptor.encrypt_payload(sample_payload)
    assert encrypted["qkd_encrypted"] is True
    assert "payload" in encrypted
    assert "nonce" in encrypted
    assert "tag" in encrypted

    decrypted = encryptor.decrypt_payload(encrypted)
    assert decrypted == sample_payload


def test_different_keys_fail_decryption(sample_payload):
    gkey1 = {"collapse_hash": "hash-1"}
    gkey2 = {"collapse_hash": "hash-2"}

    encryptor1 = GWaveEncryptor(gkey1)
    encryptor2 = GWaveEncryptor(gkey2)

    encrypted = encryptor1.encrypt_payload(sample_payload)

    with pytest.raises(ValueError):
        _ = encryptor2.decrypt_payload(encrypted)


def test_missing_collapse_hash_raises():
    with pytest.raises(ValueError):
        _ = GWaveEncryptor({})  # Missing collapse_hash


def test_payload_tampering_fails(sample_gkey, sample_payload):
    encryptor = GWaveEncryptor(sample_gkey)
    encrypted = encryptor.encrypt_payload(sample_payload)

    # Tamper with ciphertext
    encrypted["payload"] = encrypted["payload"][:-4] + "AAAA"

    with pytest.raises(ValueError):
        _ = encryptor.decrypt_payload(encrypted)


def test_metadata_fields_present(sample_gkey, sample_payload):
    encryptor = GWaveEncryptor(sample_gkey)
    encrypted = encryptor.encrypt_payload(sample_payload)

    assert encrypted.get("qkd_encrypted") is True
    assert encrypted.get("encryption_scheme") == "AES-GCM"
    assert isinstance(encrypted.get("payload"), str)
    assert isinstance(encrypted.get("nonce"), str)
    assert isinstance(encrypted.get("tag"), str)