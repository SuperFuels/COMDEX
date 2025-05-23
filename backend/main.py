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

# 2) load .env locally (only when ENV != "production")
if os.getenv("ENV", "").lower() != "production":
    from dotenv import load_dotenv
    load_dotenv()

# 3) give Cloud SQL socket & VPC connector time on cold start
time.sleep(3)

# 4) set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# 5) log the actual DB URL
from config import SQLALCHEMY_DATABASE_URL
logger.info(f"🔍 SQLALCHEMY_DATABASE_URL = {SQLALCHEMY_DATABASE_URL}")

# 6) import engine, Base, session dependency
from database import engine, Base, get_db

# 7) import all models before creating tables
import models.user
import models.product
import models.deal
import models.contract
# …any other models

# 8) auto-create missing tables
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables checked/created.")

# 9) FastAPI app
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# ─── 10) GLOBAL CORS ────────────────────────────────────────────────
# Read a comma-separated list from the environment
raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
allowed_origins = [o.strip() for o in raw.split(",") if o.strip()]

# In non-prod, default to also allowing localhost:3000
if os.getenv("ENV", "").lower() != "production":
    allowed_origins += ["http://localhost:3000"]

# If nothing at all is configured, *fail closed* and require you to set it
if not allowed_origins:
    raise RuntimeError(
        "CORS_ALLOWED_ORIGINS must be set to at least one origin "
        "(e.g. https://your-frontend.app)"
    )

logger.info(f"✅ CORS allowed_origins = {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ──────────────────────────────────────────────────────────────────

# 11) serve user uploads
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# 12) include your routers
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

# 13) workaround: redirect no-slash /products → /products/
@app.get("/products", include_in_schema=False)
def products_no_slash():
    return RedirectResponse(url="/products/", status_code=307)

# 14) root endpoint
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "🚀 Welcome to the COMDEX API!"}

# 15) health check
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
        