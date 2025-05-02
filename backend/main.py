import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from routes import auth, product, deal, admin, user

# ─── Logging ────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# ─── App setup ───────────────────────────────
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # your frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve image files
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images"
)

# ─── Routers ─────────────────────────────────
app.include_router(auth.router,    prefix="/auth",    tags=["Auth"])
app.include_router(product.router, prefix="/products", tags=["Products"])
app.include_router(deal.router,    prefix="/deals",    tags=["Deals"])
app.include_router(admin.router,   prefix="/admin",    tags=["Admin"])
app.include_router(user.router,    prefix="/users",    tags=["Users"])

# ─── Health & Root ──────────────────────────
@app.get("/")
def read_root() -> dict:
    return {"message": "🚀 Welcome to the COMDEX API!"}


@app.get("/health")
def health_check() -> dict:
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://comdex:Wn8smx123@localhost:5432/comdex"
    )
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful.")
        return {"status": "ok", "database": "connected"}
    except OperationalError:
        logger.error("❌ Database connection failed.", exc_info=True)
        return {"status": "error", "database": "not connected"}

