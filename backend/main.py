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

# 6) import the shared engine, Base, and session dependency
from database import engine, Base, get_db

# 7) import all models so they register on Base before we create tables
import models.user
import models.product
import models.deal
import models.contract
# …any others under models/

# 8) auto-create missing tables in your Cloud SQL database
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables checked/created.")

# 9) FastAPI app
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# ─── 10) APPLY CORS GLOBALLY WITH REGEX FALLBACK ───────────────────────────────
# Lock down via CORS_ALLOWED_ORIGINS (comma-sep list) or CORS_ALLOWED_ORIGINS_REGEX (single regex).
# If neither is set, we fall back to allow all origins (and reflect credentials properly).
raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]

allowed_regex = os.getenv("CORS_ALLOWED_ORIGINS_REGEX", "").strip() or None

# If no explicit origins and no regex, allow everything via regex
if not allowed_origins and not allowed_regex:
    allowed_regex = r".*"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,            # list of exact origins, or empty
    allow_origin_regex=allowed_regex,         # single regex, or None
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ───────────────────────────────────────────────────────────────────────────────

# 11) serve user uploads
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# 12) import & include routers
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

# 13) root endpoint
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "🚀 Welcome to the COMDEX API!"}

# 14) health check — uses only the socket-based engine
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
        