import os
import time
import logging

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import uvicorn

# ── 1) Ensure uploads folder exists
os.makedirs("uploaded_images", exist_ok=True)

# ── 2) Load .env.local (only when ENV != "production")
ENV = os.getenv("ENV", "").lower()
if ENV != "production":
    from dotenv import load_dotenv
    if os.path.exists(".env.local"):
        load_dotenv(".env.local")
    else:
        print("⚠️ Warning: .env.local not found.")

# ── 3) Warm up Cloud SQL socket on cold starts
time.sleep(3)

# ── 4) Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# ── 5) Log the DB URL for troubleshooting
from backend.config import SQLALCHEMY_DATABASE_URL
logger.info(f"🔍 SQLALCHEMY_DATABASE_URL = {SQLALCHEMY_DATABASE_URL}")

# ── 6) Import engine, Base, get_db
from backend.database import engine, Base, get_db

# ── 7) Register all ORM models
import backend.models

# ── 8) Auto-create tables
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables checked/created.")

# ── 9) Instantiate FastAPI
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="Global Commodity Marketplace API",
)

# Disable automatic trailing-slash redirects
app.router.redirect_slashes = False

# ── 10) GLOBAL CORS (must come before including any routers)
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

# ── 11) Import routers
from backend.routes.auth         import router as auth_router
from backend.routes.products     import router as products_router
from backend.routes.deal         import router as deal_router
from backend.routes.contracts    import router as contracts_router
from backend.routes.admin        import router as admin_router
from backend.routes.user         import router as user_router
from backend.routes.terminal     import router as terminal_router
from backend.routes.buyer        import router as buyer_router
from backend.routes.supplier     import router as supplier_router
from backend.routes.aion         import router as aion_router
from backend.routes.aion_goals   import router as aion_goals_router
from backend.routes.aion_plan    import router as aion_plan_router
from backend.routes.aion_dream   import router as aion_dream_router
from backend.routes.aion_gridworld import router as aion_gridworld_router
from backend.routes              import aion_grid_progress
from backend.api.aion            import status, grid_progress

# ── 12) Mount all routers under /api with correct prefixes
api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(products_router)
api.include_router(deal_router)
api.include_router(contracts_router)
api.include_router(admin_router)
api.include_router(user_router)
api.include_router(terminal_router)
api.include_router(buyer_router)
api.include_router(supplier_router)
api.include_router(aion_router, prefix="/aion")
api.include_router(aion_plan_router, prefix="/aion")

# 🔁 Mount special-case AION routers (external)
app.include_router(aion_goals_router, prefix="/api")
app.include_router(aion_dream_router, prefix="/api")
app.include_router(api)
app.include_router(aion_gridworld_router, prefix="/api")
app.include_router(aion_grid_progress.router)
app.include_router(status.router)
app.include_router(grid_progress.router)

# ── 13) Serve uploaded images
app.mount(
    "/uploaded_images",
    StaticFiles(directory="uploaded_images"),
    name="uploaded_images",
)

# ── 14) Serve static Next.js build if exists
if os.path.isdir("static"):
    app.mount(
        "/",
        StaticFiles(directory="static", html=True),
        name="frontend",
    )
else:
    logger.warning("⚠️ 'static' directory not found: frontend/out must be copied to backend/static")

# ── 15) Legacy redirect
@app.get("/products", include_in_schema=False)
def products_no_slash():
    return RedirectResponse(url="/products/", status_code=307)

# ── 16) Health check
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

# ── 17) Uvicorn entrypoint
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=(ENV != "production"),
        forwarded_allow_ips="*",
        redirect_slashes=False,
    )

# ── 18) 💤 Start AION dream scheduler
try:
    from backend.tasks.scheduler import start_scheduler
    start_scheduler()
except Exception as e:
    logger.warning(f"⚠️ Dream scheduler could not start: {e}")