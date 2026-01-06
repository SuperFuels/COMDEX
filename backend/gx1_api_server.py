from __future__ import annotations

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.genome_engine.web_gx1_upload import build_fastapi_router


def create_app() -> FastAPI:
    app = FastAPI(title="GX1 API", version="0.1.0")

    # dev-friendly CORS (tighten later)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(build_fastapi_router(), prefix="/api")

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("GX1_API_HOST", "0.0.0.0")
    port = int(os.getenv("GX1_API_PORT", "8080"))
    uvicorn.run("backend.gx1_api_server:app", host=host, port=port, reload=False)
