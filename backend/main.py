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

# 1) ensure uploads folder exists
os.makedirs("uploaded_images", exist_ok=True)

# 2) load .env locally
if os.getenv("ENV", "").lower() != "production":
    from dotenv import load_dotenv
    load_dotenv()

# 3) give Cloud SQL socket & VPC connector time on cold start
time.sleep(3)

# 4) set up logging so we can debug early
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# 5) import and log the actual DB URL being used
from config import SQLALCHEMY_DATABASE_URL
logger.info(f"🔍 SQLALCHEMY_DATABASE_URL = {SQLALCHEMY_DATABASE_URL}")

# 6) import the single shared engine & session dependency
from database import engine, get_db

# 7) FastAPI app
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# 8) configure CORS
#    Read from env var or fall back to localhost & prod URL
raw_origins = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:3000,https://swift-area-459514-d1.web.app",
)
allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 9) serve user uploads
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# 10) import & include routers
from routes.auth      import router as auth_router
from routes.products  import router as products_router
from routes.deal      import router as deal_router
from routes.contracts import router as contracts_router
from routes.admin     import router as admin_router
from routes.user      import router as user_router

app.include_router(auth_router,      prefix="/auth",     tags=["Auth"])
app.include_router(products_router,  prefix="/products", tags=["Products"])
app.include_router(deal_router,      prefix="/deals",    tags=["Deals"])
app.include_router(contracts_router, prefix="/contracts",tags=["Contracts"])
app.include_router(admin_router,     prefix="/admin",    tags=["Admin"])
app.include_router(user_router,      prefix="/users",    tags=["Users"])

# — Workaround: catch GET /products (no trailing slash) to avoid 307 redirect —
@app.get("/products", include_in_schema=False)
def products_no_slash():
    return RedirectResponse(url="/products/", status_code=307)


# 11) root endpoint
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "🚀 Welcome to the COMDEX API!"}

# 12) health check — uses only the socket-based engine
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
