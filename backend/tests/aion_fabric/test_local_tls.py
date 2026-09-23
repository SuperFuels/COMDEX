from __future__ import annotations

import json
import os
import ssl
import urllib.request

from backend.modules.aion_fabric import companion
from backend.modules.aion_fabric.local_tls import LocalTLSAuthority


def test_local_tls_generates_private_ca_and_ip_san(tmp_path):
    material = LocalTLSAuthority(tmp_path).ensure(address="127.0.0.1", hostname="pilot-test.local")

    assert material.ca_certificate_path.exists()
    assert material.server_certificate_path.exists()
    assert material.context().minimum_version == ssl.TLSVersion.TLSv1_2
    assert oct(os.stat(material.server_private_key_path).st_mode & 0o777) == "0o600"
    assert oct(os.stat(tmp_path / "tls" / "pilot-household-ca.key").st_mode & 0o777) == "0o600"
    assert len(material.ca_sha256) == 64
    decoded = ssl._ssl._test_decode_cert(str(material.server_certificate_path))
    sans = decoded["subjectAltName"]
    assert ("IP Address", "127.0.0.1") in sans
    assert ("DNS", "pilot-test.local") in sans


def test_local_tls_reuses_ca_and_leaf_for_same_address(tmp_path):
    authority = LocalTLSAuthority(tmp_path)
    first = authority.ensure(address="127.0.0.1", hostname="pilot-test.local")
    first_metadata = json.loads((tmp_path / "tls" / "metadata.json").read_text())
    second = authority.ensure(address="127.0.0.1", hostname="pilot-test.local")
    second_metadata = json.loads((tmp_path / "tls" / "metadata.json").read_text())

    assert first.ca_sha256 == second.ca_sha256
    assert first.server_sha256 == second.server_sha256
    assert first_metadata["generated_at"] == second_metadata["generated_at"]


def test_local_tls_rotates_leaf_not_household_ca_when_address_changes(tmp_path):
    authority = LocalTLSAuthority(tmp_path)
    first = authority.ensure(address="127.0.0.1", hostname="pilot-test.local")
    second = authority.ensure(address="127.0.0.2", hostname="pilot-test.local")

    assert first.ca_sha256 == second.ca_sha256
    assert first.server_sha256 != second.server_sha256
    assert second.address == "127.0.0.2"


def test_https_companion_uses_generated_chain_and_hsts(tmp_path, monkeypatch):
    monkeypatch.setattr(companion, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    material = LocalTLSAuthority(tmp_path).ensure(address="127.0.0.1", hostname="pilot-test.local")
    service = companion.CompanionService(
        lambda: {"controller": {"tv_name": "Test TV", "volume": 20}},
        lambda approval_id, approved: {},
        port=0,
        token="secure-controller-token",
        tls_context=material.context(),
        ca_certificate=material.ca_certificate_path.read_bytes(),
        ca_fingerprint=material.ca_sha256,
    )
    service.start()
    try:
        context = ssl.create_default_context(cafile=str(material.ca_certificate_path))
        with urllib.request.urlopen(service.public_url, context=context, timeout=3) as response:
            assert response.status == 200
            assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
            assert "Private TV controller" in response.read().decode("utf-8")
        with urllib.request.urlopen(f"{service.entry_url}/pilot-household-ca.crt", context=context, timeout=3) as response:
            assert response.headers["Content-Type"] == "application/x-x509-ca-cert"
            assert response.read() == material.ca_certificate_path.read_bytes()
    finally:
        service.stop()


def test_provider_telemetry_endpoint_exists_only_on_trusted_https(tmp_path, monkeypatch):
    monkeypatch.setattr(companion, "_lan_address", lambda preferred_peer=None: "127.0.0.1")
    material = LocalTLSAuthority(tmp_path).ensure(address="127.0.0.1", hostname="pilot-test.local")
    received = {}

    def accept(envelope, signature):
        received.update({"envelope": envelope, "signature": signature})
        return {"accepted": True}

    service = companion.CompanionService(
        lambda: {"controller": {"tv_name": "Test TV"}},
        lambda approval_id, approved: {},
        provider_telemetry_handler=accept,
        port=0,
        token="secure-controller-token",
        csrf_token="secure-csrf-token",
        tls_context=material.context(),
    )
    service.start()
    try:
        context = ssl.create_default_context(cafile=str(material.ca_certificate_path))
        request = urllib.request.Request(
            f"{service.public_url}/provider-telemetry",
            data=json.dumps({"schema_version": "test"}).encode(),
            headers={
                "Content-Type": "application/json",
                "X-AION-CSRF": "secure-csrf-token",
                "X-Pilot-Telemetry-Signature": "signed-envelope",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, context=context, timeout=3) as response:
            assert json.loads(response.read()) == {"accepted": True}
        assert received == {"envelope": {"schema_version": "test"}, "signature": "signed-envelope"}
    finally:
        service.stop()
