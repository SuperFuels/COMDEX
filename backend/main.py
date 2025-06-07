# backend/main.py

import os
import time
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# ─── 1) Ensure uploads folder exists ─────────────────────────────────────
os.makedirs("uploaded_images", exist_ok=True)

# ─── 2) Load .env locally (only when ENV != "production") ───────────────
ENV = os.getenv("ENV", "").lower()
if ENV != "production":
    from dotenv import load_dotenv
    load_dotenv()

# ─── 3) Give Cloud SQL socket & VPC connector time on cold start ───────
time.sleep(3)

# ─── 4) Set up logging ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# ─── 5) Log the actual DB URL (for troubleshooting) ─────────────────────
from .config import SQLALCHEMY_DATABASE_URL  # noqa: F401
logger.info(f"🔍 SQLALCHEMY_DATABASE_URL = {SQLALCHEMY_DATABASE_URL}")

# ─── 6) Import engine, Base, get_db dependency ──────────────────────────
from .database import engine, Base, get_db  # noqa: F401

# ─── 7) Import models so all ORM classes register ───────────────────────
import backend.models  # noqa: F401

# ─── 8) Auto‐create missing tables ──────────────────────────────────────
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables checked/created.")

# ─── 9) Instantiate FastAPI ─────────────────────────────────────────────
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# ─── 10) GLOBAL CORS ─────────────────────────────────────────────────────
if ENV != "production":
    # DEV: allow every origin
    allow_origins = ["*"]
else:
    # PRODUCTION: lock down to your list
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    allow_origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not allow_origins:
        raise RuntimeError(
            "CORS_ALLOWED_ORIGINS must be set in production (e.g. https://your-front.app)"
        )

logger.info(f"✅ CORS allowed_origins = {allow_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 11) Include your routers ────────────────────────────────────────────
from .routes.auth import router as auth_router
from .routes.products import router as products_router
from .routes.deal import router as deal_router
from .routes.contracts import router as contracts_router
from .routes.admin import router as admin_router
from .routes.user import router as user_router

# auth_router already has prefix="/api/auth"
app.include_router(auth_router)

# other routers (ensure their prefixes/tags are set inside each file)
app.include_router(products_router, tags=["Products"])
app.include_router(deal_router, tags=["Deals"])
app.include_router(contracts_router, tags=["Contracts"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(user_router, tags=["Users"])

# ─── 12) Serve user uploads ──────────────────────────────────────────────
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# ─── 13) Serve Next.js “out” folder as static ───────────────────────────
if os.path.isdir("static"):
    app.mount(
        "/",
        StaticFiles(directory="static", html=True),
        name="frontend",
    )
else:
    logger.warning(
        "⚠️ 'static' directory not found: frontend/out must be copied to backend/static"
    )

# ─── 14) Redirect no‐slash endpoints ────────────────────────────────────
@app.get("/products", include_in_schema=False)
def products_no_slash():
    return RedirectResponse(url="/products/", status_code=307)

# ─── 15) Health check ────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful.")
        return {"status": "ok", "database": "connected"}
    except OperationalError:
        logger.error("❌ Database connection failed.", exc_info=True)
        return {"status": "error", "database": "not connected"}