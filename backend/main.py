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
# If you serve user‐uploaded images/files under "/uploaded_images", create that dir.
os.makedirs("uploaded_images", exist_ok=True)

# ─── 2) Load .env locally (only when ENV != "production") ───────────────
if os.getenv("ENV", "").lower() != "production":
    from dotenv import load_dotenv

    load_dotenv()

# ─── 3) Give Cloud SQL socket & VPC connector time on cold start ───────
# (Adjust the sleep time if your Cloud SQL takes longer on cold start.)
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
# Read comma‐separated CORS_ALLOWED_ORIGINS from environment (e.g.:
# CORS_ALLOWED_ORIGINS="https://your‐front.app,https://your‐preview.vercel.app")
raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in raw.split(",") if o.strip()]

# In non‐production, allow localhost:3000 by default
if os.getenv("ENV", "").lower() != "production":
    allowed_origins.append("http://localhost:3000")

# Always allow your Firebase‐hosted front end (if applicable)
allowed_origins.append("https://swift-area-459514-d1.web.app")

if not allowed_origins:
    raise RuntimeError(
        "CORS_ALLOWED_ORIGINS must be set to at least one origin "
        "(e.g. https://your-frontend.app)"
    )

logger.info(f"✅ CORS allowed_origins = {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,       # Only these origins can make requests
    allow_credentials=True,
    allow_methods=["*"],                 # GET, POST, PUT, DELETE, etc.
    allow_headers=["*"],                 # Any headers (e.g. Content-Type, Authorization)
)
# ──────────────────────────────────────────────────────────────────────────

# ─── 11) Serve user uploads at /uploaded_images ─────────────────────────
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# ─── 12) Serve Next.js “out” folder as static at the root path ──────────
# The Dockerfile (or your deployment script) must copy:
#   frontend/out/ → backend/static/
# so that a “static” folder exists here at runtime.
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

# ─── 13) Include your routers (mounted under /auth, /products, etc.) ─────
from .routes.auth import router as auth_router
from .routes.products import router as products_router
from .routes.deal import router as deal_router
from .routes.contracts import router as contracts_router
from .routes.admin import router as admin_router
from .routes.user import router as user_router

app.include_router(auth_router, tags=["Auth"])
app.include_router(products_router, tags=["Products"])
app.include_router(deal_router, tags=["Deals"])
app.include_router(contracts_router, tags=["Contracts"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(user_router, tags=["Users"])

# ─── 14) Redirect no‐slash endpoints (example: /products → /products/) ────
@app.get("/products", include_in_schema=False)
def products_no_slash():
    return RedirectResponse(url="/products/", status_code=307)

# ─── 15) Health check endpoint ───────────────────────────────────────────
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