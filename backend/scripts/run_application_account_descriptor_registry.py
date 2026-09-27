#!/usr/bin/env python3
"""Run the Tessaris public-descriptor registry as a separate service."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import secrets
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from backend.modules.aion_business.runtime.application_account_descriptor_registry import (
    ApplicationAccountDescriptorRegistry,
    ApplicationAccountDescriptorRegistryError,
)
from backend.modules.aion_business.runtime.request_body_limits import (
    ScopedRequestBodyLimitMiddleware,
)


ACCOUNT_PATTERN = re.compile(r"account_[0-9a-f]{40}")


def build_registry_app(
    registry: ApplicationAccountDescriptorRegistry,
    *,
    publish_token: str | None = None,
) -> FastAPI:
    protected_token = str(publish_token or "")
    if protected_token and len(protected_token) < 32:
        raise ValueError("account_registry_publish_token_too_short")
    app = FastAPI(
        title="Tessaris Account Descriptor Registry",
        version="1",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(ScopedRequestBodyLimitMiddleware)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/health")
    def health() -> dict[str, Any]:
        return registry.status()

    @app.put("/v1/accounts/{account_id}/descriptor")
    async def publish(account_id: str, request: Request):
        _validate_account_path(account_id)
        if protected_token:
            authorization = str(request.headers.get("authorization") or "")
            supplied = authorization[7:] if authorization.startswith("Bearer ") else ""
            if not supplied or not secrets.compare_digest(supplied, protected_token):
                raise HTTPException(status_code=401, detail="account_registry_publish_unauthorized")
        if str(request.headers.get("content-type") or "").split(";", 1)[0].strip().lower() != "application/json":
            raise HTTPException(status_code=415, detail="application_json_required")
        try:
            value = json.loads((await request.body()).decode("utf-8"))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="account_descriptor_json_invalid") from exc
        if not isinstance(value, dict) or str(value.get("account_id") or "") != account_id:
            raise HTTPException(status_code=400, detail="account_descriptor_path_mismatch")
        try:
            result = registry.publish(value)
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ApplicationAccountDescriptorRegistryError as exc:
            status = 507 if "capacity" in str(exc) else 400
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        return JSONResponse(result, status_code=200 if result["idempotent"] else 201)

    @app.get("/v1/accounts/{account_id}/descriptor")
    def current(account_id: str):
        _validate_account_path(account_id)
        try:
            descriptor = registry.current(account_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="account_descriptor_not_found") from exc
        return descriptor

    @app.get("/v1/accounts/{account_id}/history")
    def history(account_id: str):
        _validate_account_path(account_id)
        return {
            "account_id": account_id,
            "history": registry.history(account_id),
            "contains_private_recovery_material": False,
        }

    return app


def _validate_account_path(account_id: str) -> None:
    if not ACCOUNT_PATTERN.fullmatch(str(account_id or "")):
        raise HTTPException(status_code=400, detail="account_registry_account_id_invalid")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run the independent public-descriptor registry. The service stores "
            "root-signed public descriptors only and must be deployed separately "
            "from desktop recovery state."
        )
    )
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8743)
    parser.add_argument("--ssl-certfile", type=Path)
    parser.add_argument("--ssl-keyfile", type=Path)
    arguments = parser.parse_args()
    public_host = arguments.host not in {"127.0.0.1", "::1", "localhost"}
    if bool(arguments.ssl_certfile) != bool(arguments.ssl_keyfile):
        parser.error("--ssl-certfile and --ssl-keyfile are required together")
    if public_host and not (arguments.ssl_certfile and arguments.ssl_keyfile):
        parser.error("non-loopback registry binding requires TLS certificate and key files")
    publish_token = str(os.environ.get("TESSARIS_ACCOUNT_REGISTRY_PUBLISH_TOKEN") or "")
    if public_host and len(publish_token) < 32:
        parser.error(
            "non-loopback registry binding requires a 32-character or longer "
            "TESSARIS_ACCOUNT_REGISTRY_PUBLISH_TOKEN environment secret"
        )
    if arguments.port < 1 or arguments.port > 65535:
        parser.error("--port must be between 1 and 65535")

    import uvicorn

    registry = ApplicationAccountDescriptorRegistry(arguments.database)
    uvicorn.run(
        build_registry_app(registry, publish_token=publish_token or None),
        host=arguments.host,
        port=arguments.port,
        ssl_certfile=str(arguments.ssl_certfile) if arguments.ssl_certfile else None,
        ssl_keyfile=str(arguments.ssl_keyfile) if arguments.ssl_keyfile else None,
        server_header=False,
        proxy_headers=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
