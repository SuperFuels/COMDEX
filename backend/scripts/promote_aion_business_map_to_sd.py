#!/usr/bin/env python3
"""Install a verified Boardroom Business Map bundle on external storage."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from typing import Any

from backend.modules.aion_inference.business_map import (
    BUSINESS_MAP_TRUST_ANCHORS,
    SUPPLIER_PAYMENT_CARTRIDGE,
    SUPPLIER_PAYMENT_SIGNATURE,
    verify_business_map_cartridge,
)


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install_verified_bundle(
    *,
    cartridge: Path,
    signature: Path,
    trust_anchors: Path,
    destination: Path,
) -> dict[str, Any]:
    source_verification = verify_business_map_cartridge(cartridge, signature, trust_anchors)
    if not source_verification.passed:
        raise ValueError(f"source cartridge failed closed: {','.join(source_verification.reasons)}")
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite installed bundle: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent))
    try:
        installed_cartridge = staging / cartridge.name
        installed_signature = staging / signature.name
        installed_trust = staging / trust_anchors.name
        shutil.copyfile(cartridge, installed_cartridge)
        shutil.copyfile(signature, installed_signature)
        shutil.copyfile(trust_anchors, installed_trust)
        installed_verification = verify_business_map_cartridge(
            installed_cartridge, installed_signature, installed_trust
        )
        if not installed_verification.passed:
            raise ValueError(
                f"installed cartridge failed closed: {','.join(installed_verification.reasons)}"
            )
        os.rename(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    files = {
        cartridge.name: _sha256(destination / cartridge.name),
        signature.name: _sha256(destination / signature.name),
        trust_anchors.name: _sha256(destination / trust_anchors.name),
    }
    result = {
        "schema_version": "aion.business_map_sd_install.v1",
        "destination": str(destination),
        "files": files,
        "cartridge_sha256": installed_verification.artifact_sha256,
        "signature_key_id": installed_verification.key_id,
        "glyph_address": installed_verification.glyph_address,
        "source_and_installed_hashes_identical": files == {
            cartridge.name: _sha256(cartridge),
            signature.name: _sha256(signature),
            trust_anchors.name: _sha256(trust_anchors),
        },
        "installed_verification_passed": installed_verification.passed,
    }
    result["install_receipt_sha256"] = _canonical_sha256(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--storage-root", type=Path, required=True)
    parser.add_argument("--bundle-id", default="supplier-payment-controls-v1")
    parser.add_argument("--cartridge", type=Path, default=SUPPLIER_PAYMENT_CARTRIDGE)
    parser.add_argument("--signature", type=Path, default=SUPPLIER_PAYMENT_SIGNATURE)
    parser.add_argument("--trust-anchors", type=Path, default=BUSINESS_MAP_TRUST_ANCHORS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    root = args.storage_root.resolve()
    destination = root / "business-maps" / args.bundle_id
    output = (args.output or root / "experiments" / f"business-map-sd-install-{args.bundle_id}.json").resolve()
    if root not in output.parents:
        raise SystemExit("installation evidence must remain on external storage")
    if output.exists():
        raise SystemExit(f"refusing to overwrite installation evidence: {output}")
    report = install_verified_bundle(
        cartridge=args.cartridge.resolve(),
        signature=args.signature.resolve(),
        trust_anchors=args.trust_anchors.resolve(),
        destination=destination,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), **report}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
