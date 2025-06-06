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

# ─── 1) Create “uploaded_images” folder for user uploads ────────────────
os.makedirs("uploaded_images", exist_ok=True)

# ─── 2) Load .env in non-production ─────────────────────────────────────
if os.getenv("ENV", "").lower() != "production":
    from dotenv import load_dotenv
    load_dotenv()

# ─── 3) Give Cloud SQL socket a few seconds on cold start ───────────────
time.sleep(3)

# ─── 4) Set up logging ───────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# ─── 5) Log the real database URL for debugging ─────────────────────────
from .config import SQLALCHEMY_DATABASE_URL  # noqa: F401
logger.info(f"🔍 SQLALCHEMY_DATABASE_URL = {SQLALCHEMY_DATABASE_URL}")

# ─── 6) Import engine, Base, get_db ─────────────────────────────────────
from .database import engine, Base, get_db  # noqa: F401

# ─── 7) Import all ORM models so SQLAlchemy knows about them ─────────────
import backend.models  # noqa: F401

# ─── 8) Create any missing tables automatically ─────────────────────────
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables checked/created.")

# ─── 9) Instantiate FastAPI ─────────────────────────────────────────────
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# ─── 10) GLOBAL CORS (allow everything for now) ──────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # For production change this to specific origins
    allow_credentials=True,
    allow_methods=["*"],      # GET, POST, PUT, DELETE, OPTIONS…
    allow_headers=["*"],      # Any header
)

# ─── 11) Include your routers under /api/auth, etc. ─────────────────────
from .routes.auth import router as auth_router
from .routes.products import router as products_router
from .routes.deal import router as deal_router
from .routes.contracts import router as contracts_router
from .routes.admin import router as admin_router
from .routes.user import router as user_router

# auth_router already has prefix="/api/auth"
app.include_router(auth_router)
app.include_router(products_router, tags=["Products"])
app.include_router(deal_router, tags=["Deals"])
app.include_router(contracts_router, tags=["Contracts"])
app.include_router(admin_router, tags=["Admin"])
app.include_router(user_router, tags=["Users"])

# ─── 12) Serve user uploads at /uploaded_images ─────────────────────────
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# ─── 13) Serve Next.js “out” folder under “/” ───────────────────────────
# (Your Dockerfile must copy frontend/out/ → backend/static/)
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

# ─── 14) Redirect no‐slash endpoints (e.g., /products → /products/) ─────
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