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

# 2) Load .env locally (only when ENV != "production")
ENV = os.getenv("ENV", "").lower()
if ENV != "production":
    from dotenv import load_dotenv
    load_dotenv()

# 3) Give Cloud SQL socket a moment on cold start
time.sleep(3)

# 4) Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# 5) Log DB URL for troubleshooting
from .config import SQLALCHEMY_DATABASE_URL  # noqa: F401
logger.info(f"🔍 SQLALCHEMY_DATABASE_URL = {SQLALCHEMY_DATABASE_URL}")

# 6) Bring in engine, Base, get_db
from .database import engine, Base, get_db  # noqa: F401

# 7) Register all models
import backend.models  # noqa: F401

# 8) Create tables
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables checked/created.")

# 9) Instantiate app
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# 10) CORS
if ENV != "production":
    allow_origins = ["*"]
else:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    allow_origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not allow_origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must be set in production")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info(f"✅ CORS allowed_origins = {allow_origins}")

# 11) Bring in all routers
from .routes.auth      import router as auth_router      # prefix="/api/auth"
from .routes.products  import router as products_router  # prefix="/products"
from .routes.deal      import router as deal_router      # prefix="/deals"
from .routes.contracts import router as contracts_router# prefix="/contracts"
from .routes.admin     import router as admin_router     # prefix="/admin"
from .routes.user      import router as user_router      # prefix="/users"
from .routes.terminal  import router as terminal_router  # prefix="/terminal"
from .routes.buyer     import router as buyer_router     # prefix="/buyer"
from .routes.supplier  import router as supplier_router  # prefix="/supplier"

# mount auth directly (its own `/api/auth` prefix)
app.include_router(auth_router)

# now create a single `/api` namespace for everything else
api_router = APIRouter(prefix="/api")

api_router.include_router(products_router,   tags=["Products"])
api_router.include_router(deal_router,       tags=["Deals"])
api_router.include_router(contracts_router,  tags=["Contracts"])
api_router.include_router(admin_router,      tags=["Admin"])
api_router.include_router(user_router,       tags=["Users"])
api_router.include_router(terminal_router,   tags=["Terminal"])
api_router.include_router(buyer_router,      tags=["Buyer"])
api_router.include_router(supplier_router,   tags=["Supplier"])

app.include_router(api_router)


# 12) Serve uploaded images
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# 13) Serve frontend `static/` if present
if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="frontend")
else:
    logger.warning(
        "⚠️ 'static' directory not found: copy your built Next.js into `backend/static`"
    )

# 14) Redirect no‐slash for /products
@app.get("/products", include_in_schema=False)
def products_no_slash():
    return RedirectResponse(url="/products/", status_code=307)

# 15) Health‐check
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