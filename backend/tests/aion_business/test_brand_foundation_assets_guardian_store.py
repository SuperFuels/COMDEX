from __future__ import annotations

import asyncio
import base64
import io

from starlette.datastructures import Headers, UploadFile

from backend.modules.aion_business.api.brand_foundation_api import (
    get_brand_asset,
    upload_brand_asset,
)


def test_brand_asset_upload_and_readback_use_encrypted_vault_object(tmp_path, monkeypatch):
    vault_root = tmp_path / "customer-data" / "Acme.business-vault"
    environment = {
        "TESSARIS_BUSINESS_CONTAINER_BACKEND": "guardian",
        "TESSARIS_BUSINESS_VAULT_PATH": str(vault_root),
        "TESSARIS_BUSINESS_NAME": "Acme",
        "TESSARIS_BUSINESS_STABLE_ID": "acme",
        "TESSARIS_BUSINESS_VAULT_KEY_B64": base64.urlsafe_b64encode(b"g" * 32).decode().rstrip("="),
        "TESSARIS_APPLICATION_ROOT": str(tmp_path / "application"),
        "TESSARIS_UPDATE_ROOT": str(tmp_path / "updates"),
        "AION_BUSINESS_RUNTIME_ROOT": str(tmp_path / "legacy-runtime"),
    }
    for key, value in environment.items():
        monkeypatch.setenv(key, value)
    private_content = b"private brand logo binary content"
    upload = UploadFile(
        file=io.BytesIO(private_content), filename="company-logo.png",
        headers=Headers({"content-type": "image/png"}),
    )

    result = asyncio.run(upload_brand_asset("acme", role="primary_logo", file=upload))
    response = get_brand_asset("acme", result["asset"]["url"].rsplit("/", 1)[-1])

    assert result["asset"]["vaultObjectId"].startswith("brand_primary_logo_")
    assert response.body == private_content
    assert response.media_type == "image/png"
    assert not (tmp_path / "legacy-runtime" / "acme" / "brand_assets").exists()
    for path in vault_root.rglob("*"):
        if path.is_file():
            assert private_content not in path.read_bytes()
