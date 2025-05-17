import os
import time
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Load .env for local development only
if os.getenv("ENV", "").lower() != "production":
    from dotenv import load_dotenv
    load_dotenv()

# Give VPC & socket a moment on cold start
time.sleep(3)

# Import routers
from routes.auth      import router as auth_router
from routes.products  import router as products_router
from routes.deal      import router as deal_router
from routes.contracts import router as contracts_router
from routes.admin     import router as admin_router
from routes.user      import router as user_router

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# FastAPI setup
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# ─── Leave the default trailing‐slash behavior so /foo → /foo/ still redirects ───
# (We removed app.router.redirect_slashes = False)

# ─── Whitelist origins for CORS ────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://swift-area-459514-d1.web.app",                       # your Firebase site
        "https://comdex-api-375760843948.us-central1.run.app",       # your live API
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploads
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# Include all your routers
app.include_router(auth_router,      prefix="/auth",      tags=["Auth"])
app.include_router(products_router,  prefix="/products",  tags=["Products"])
app.include_router(deal_router,      prefix="/deals",     tags=["Deals"])
app.include_router(contracts_router, prefix="/contracts", tags=["Contracts"])
app.include_router(admin_router,     prefix="/admin",     tags=["Admin"])
app.include_router(user_router,      prefix="/users",     tags=["Users"])

# Helpers to build DB URL via Cloud SQL socket
DB_USER        = os.getenv("DB_USER", "")
DB_PASS        = os.getenv("DB_PASS", "")
DB_NAME        = os.getenv("DB_NAME", "")
DB_SOCKET_PATH = os.getenv("DB_SOCKET_PATH", "")

def get_database_url():
    if DB_SOCKET_PATH:
        return (
            f"postgresql+psycopg2://{DB_USER}:{DB_PASS}@/{DB_NAME}"
            f"?host=/cloudsql/{DB_SOCKET_PATH}"
        )
    # fallback to full host/port URL
    return os.getenv(
        "DATABASE_URL",
        f"postgresql://{DB_USER}:{DB_PASS}@localhost:5432/{DB_NAME}"
    )

# Root & health endpoints
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "🚀 Welcome to the COMDEX API!"}

@app.get("/health", tags=["Health"])
def health_check():
    db_url = get_database_url()
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful.")
        return {"status": "ok", "database": "connected"}
    except OperationalError:
        logger.error("❌ Database connection failed.", exc_info=True)
        return {"status": "error", "database": "not connected"}

