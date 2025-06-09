# backend/main.py

import os
import time
import logging
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# 1) Ensure uploads folder exists
os.makedirs("uploaded_images", exist_ok=True)

# 2) Load local .env
ENV = os.getenv("ENV", "").lower()
if ENV != "production":
    from dotenv import load_dotenv
    load_dotenv()

# 3) Cold-start delay for Cloud SQL
time.sleep(3)

# 4) Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# 5) Log DB URL
from .config import SQLALCHEMY_DATABASE_URL  # noqa: F401
logger.info(f"🔍 SQLALCHEMY_DATABASE_URL = {SQLALCHEMY_DATABASE_URL}")

# 6) Import engine, Base, get_db
from .database import engine, Base, get_db  # noqa: F401

# 7) Import all models so SQLAlchemy registers them
import backend.models  # noqa: F401

# 8) Auto-create missing tables
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables checked/created.")

# 9) Instantiate FastAPI
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# 10) Global CORS
if ENV != "production":
    allow_origins = ["*"]
else:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    allow_origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not allow_origins:
        raise RuntimeError(
            "CORS_ALLOWED_ORIGINS must be set in production "
            "(e.g. https://your-frontend.app)"
        )
logger.info(f"✅ CORS allowed_origins = {allow_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 11) Mount /api/auth separately (it already uses prefix="/api/auth")
from .routes.auth import router as auth_router
app.include_router(auth_router)  # GET/POST /api/auth/...

# 12) Create a single “/api” namespace for everyone else
api_router = APIRouter(prefix="/api")

# Import the rest of your routers (each now has prefix="/products", "/deals", etc.)
from .routes.products  import router as products_router
from .routes.deal      import router as deal_router
from .routes.contracts import router as contracts_router
from .routes.admin     import router as admin_router
from .routes.user      import router as user_router
from .routes.terminal  import router as terminal_router
from .routes.buyer     import router as buyer_router
from .routes.supplier  import router as supplier_router

api_router.include_router(products_router,   tags=["Products"])   # → /api/products
api_router.include_router(deal_router,       tags=["Deals"])      # → /api/deals
api_router.include_router(contracts_router,  tags=["Contracts"])  # → /api/contracts
api_router.include_router(admin_router,      tags=["Admin"])      # → /api/admin
api_router.include_router(user_router,       tags=["Users"])      # → /api/users
api_router.include_router(terminal_router,   tags=["Terminal"])   # → /api/terminal
api_router.include_router(buyer_router,      tags=["Buyer"])      # → /api/buyer
api_router.include_router(supplier_router,   tags=["Supplier"])   # → /api/supplier

app.include_router(api_router)

# 13) Serve uploaded images
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# 14) Serve Next.js “out” folder
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

# 15) Redirect no‐slash for products
@app.get("/products", include_in_schema=False)
def products_no_slash():
    return RedirectResponse(url="/products/", status_code=307)

# 16) Health check
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
        