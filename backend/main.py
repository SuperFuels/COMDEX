import os
import time
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

# ─── Temporary Cloud Run cold start fix ─────
time.sleep(3)  # Delay to let VPC and socket stabilize

# ─── Import your routers ───────────────────
from routes.auth      import router as auth_router
from routes.products  import router as products_router
from routes.deal      import router as deal_router
from routes.contracts import router as contracts_router
from routes.admin     import router as admin_router
from routes.user      import router as user_router

# ─── Logging setup ─────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# ─── FastAPI instantiation ─────────────────
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# ─── Global CORS middleware ────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Serve uploaded images ─────────────────
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# ─── Mount all routers under their prefixes ─
app.include_router(auth_router,      prefix="/auth",      tags=["Auth"])
app.include_router(products_router,  prefix="/products",  tags=["Products"])
app.include_router(deal_router,      prefix="/deals",     tags=["Deals"])
app.include_router(contracts_router, prefix="/contracts", tags=["Contracts"])
app.include_router(admin_router,     prefix="/admin",     tags=["Admin"])
app.include_router(user_router,      prefix="/users",     tags=["Users"])

# ─── Root & Health Endpoints ──────────────
@app.get("/", tags=["Root"])
def read_root():   
    return {"message": "🚀 Welcome to the COMDEX API!"}
        
@app.get("/health", tags=["Health"])
def health_check():
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

