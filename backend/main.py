# backend/main.py

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# Import routers via the local routes package
from routes.auth      import router as auth_router
from routes.products  import router as products_router
from routes.deal      import router as deal_router       # has prefix="/deals"
from routes.contracts import router as contracts_router  # has prefix="/contracts"
from routes.admin     import router as admin_router      # has prefix="/admin"
from routes.user      import router as user_router       # has prefix="/users"

# ─── Logging ───────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# ─── App setup ──────────────────────────────
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API"
)

# ─── CORS ───────────────────────────────────
# Allow your React frontend on localhost:3000 to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Serve uploaded images ───────────────────
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images"
)

# ─── Routers ───────────────────────────────
app.include_router(auth_router,      prefix="/auth",     tags=["Auth"])
app.include_router(products_router,  prefix="/products", tags=["Products"])
app.include_router(deal_router)      # → /deals
app.include_router(contracts_router) # → /contracts
app.include_router(admin_router)     # → /admin
app.include_router(user_router)      # → /users

# ─── Health & Root ─────────────────────────
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

