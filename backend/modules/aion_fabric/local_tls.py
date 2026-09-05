from __future__ import annotations

import ipaddress
import json
import os
import re
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from .canonical import canonical_bytes, utc_now_iso


@dataclass(frozen=True, slots=True)
class LocalTLSMaterial:
    ca_certificate_path: Path
    server_certificate_path: Path
    server_private_key_path: Path
    ca_sha256: str
    server_sha256: str
    address: str
    hostname: str

    def context(self) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(self.server_certificate_path), str(self.server_private_key_path))
        return context

    def public_status(self) -> Dict[str, Any]:
        return {
            "enabled": True,
            "address": self.address,
            "hostname": self.hostname,
            "ca_sha256": self.ca_sha256,
            "server_sha256": self.server_sha256,
            "private_keys_exposed": False,
            "trust_installation": "explicit_user_action_required",
        }


class LocalTLSAuthority:
    """Create a mother-local CA and a LAN leaf certificate with owner-only keys."""

    def __init__(self, runtime_dir: str | Path) -> None:
        self.root = Path(runtime_dir) / "tls"
        self.root.mkdir(parents=True, exist_ok=True)
        os.chmod(self.root, 0o700)

    @staticmethod
    def _fingerprint(path: Path) -> str:
        certificate = x509.load_pem_x509_certificate(path.read_bytes())
        return certificate.fingerprint(hashes.SHA256()).hex()

    @staticmethod
    def _safe_hostname(hostname: str) -> str:
        value = str(hostname or "pilot-mother").strip().lower().rstrip(".")
        if not re.fullmatch(r"[a-z0-9][a-z0-9.-]{0,251}[a-z0-9]", value):
            return "pilot-mother.local"
        return value if "." in value else f"{value}.local"

    def _valid_existing(self, *, address: str, hostname: str) -> bool:
        metadata_path = self.root / "metadata.json"
        certificate = self.root / "server.crt"
        key = self.root / "server.key"
        ca = self.root / "pilot-household-ca.crt"
        if not all(path.exists() for path in (metadata_path, certificate, key, ca)):
            return False
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return False
        if metadata.get("address") != address or metadata.get("hostname") != hostname:
            return False
        try:
            parsed = x509.load_pem_x509_certificate(certificate.read_bytes())
            expiry = parsed.not_valid_after_utc
        except (OSError, ValueError):
            return False
        return expiry > datetime.now(timezone.utc) + timedelta(days=30)

    @staticmethod
    def _write_private_key(path: Path, key: rsa.RSAPrivateKey) -> None:
        path.write_bytes(
            key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption(),
            )
        )
        os.chmod(path, 0o600)

    def ensure(self, *, address: str, hostname: str) -> LocalTLSMaterial:
        address = str(ipaddress.ip_address(address))
        hostname = self._safe_hostname(hostname)
        ca_key = self.root / "pilot-household-ca.key"
        ca_cert = self.root / "pilot-household-ca.crt"
        server_key = self.root / "server.key"
        server_cert = self.root / "server.crt"
        metadata_path = self.root / "metadata.json"

        if not self._valid_existing(address=address, hostname=hostname):
            if not ca_key.exists() or not ca_cert.exists():
                ca_private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
                self._write_private_key(ca_key, ca_private)
                ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Pilot Household Local CA")])
                now = datetime.now(timezone.utc)
                ca_certificate = (
                    x509.CertificateBuilder()
                    .subject_name(ca_name)
                    .issuer_name(ca_name)
                    .public_key(ca_private.public_key())
                    .serial_number(x509.random_serial_number())
                    .not_valid_before(now - timedelta(minutes=5))
                    .not_valid_after(now + timedelta(days=3650))
                    .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                    .add_extension(
                        x509.KeyUsage(
                            digital_signature=False, content_commitment=False, key_encipherment=False,
                            data_encipherment=False, key_agreement=False, key_cert_sign=True,
                            crl_sign=True, encipher_only=None, decipher_only=None,
                        ),
                        critical=True,
                    )
                    .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_private.public_key()), critical=False)
                    .sign(ca_private, hashes.SHA256())
                )
                ca_cert.write_bytes(ca_certificate.public_bytes(serialization.Encoding.PEM))
                os.chmod(ca_cert, 0o644)
            else:
                ca_private = serialization.load_pem_private_key(ca_key.read_bytes(), password=None)
                ca_certificate = x509.load_pem_x509_certificate(ca_cert.read_bytes())
                if not isinstance(ca_private, rsa.RSAPrivateKey):
                    raise RuntimeError("Pilot household CA key is not an RSA private key")

            server_private = rsa.generate_private_key(public_exponent=65537, key_size=3072)
            self._write_private_key(server_key, server_private)
            now = datetime.now(timezone.utc)
            server_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, hostname)])
            server_certificate = (
                x509.CertificateBuilder()
                .subject_name(server_name)
                .issuer_name(ca_certificate.subject)
                .public_key(server_private.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=5))
                .not_valid_after(now + timedelta(days=397))
                .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                .add_extension(
                    x509.KeyUsage(
                        digital_signature=True, content_commitment=False, key_encipherment=True,
                        data_encipherment=False, key_agreement=False, key_cert_sign=False,
                        crl_sign=False, encipher_only=None, decipher_only=None,
                    ),
                    critical=True,
                )
                .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                .add_extension(
                    x509.SubjectAlternativeName([
                        x509.IPAddress(ipaddress.ip_address(address)),
                        x509.DNSName(hostname),
                        x509.DNSName("localhost"),
                        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                    ]),
                    critical=False,
                )
                .add_extension(x509.SubjectKeyIdentifier.from_public_key(server_private.public_key()), critical=False)
                .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_private.public_key()), critical=False)
                .sign(ca_private, hashes.SHA256())
            )
            server_cert.write_bytes(server_certificate.public_bytes(serialization.Encoding.PEM))
            os.chmod(server_cert, 0o644)
            metadata = {
                "schema_version": "pilot.local-tls.v1",
                "address": address,
                "hostname": hostname,
                "generated_at": utc_now_iso(),
                "ca_sha256": self._fingerprint(ca_cert),
                "server_sha256": self._fingerprint(server_cert),
                "private_keys_exposed": False,
            }
            temporary = metadata_path.with_suffix(".tmp")
            temporary.write_bytes(canonical_bytes(metadata))
            os.chmod(temporary, 0o600)
            os.replace(temporary, metadata_path)

        os.chmod(ca_key, 0o600)
        os.chmod(server_key, 0o600)
        return LocalTLSMaterial(
            ca_certificate_path=ca_cert,
            server_certificate_path=server_cert,
            server_private_key_path=server_key,
            ca_sha256=self._fingerprint(ca_cert),
            server_sha256=self._fingerprint(server_cert),
            address=address,
            hostname=hostname,
        )
