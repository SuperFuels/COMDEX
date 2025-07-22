import sys
import os
import time
import logging
import subprocess
import asyncio

# ✅ Fix for ModuleNotFoundError: dynamically append the root project path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
os.environ["PYTHONPATH"] = ROOT_DIR

from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import uvicorn

# ✅ DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)  # Allow tracking + upgrades to this file

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

app.router.redirect_slashes = False  # Disable trailing slash redirects globally

# ── 10) GLOBAL CORS (must come before routers)
if ENV != "production":
    allow_origins = [
        "http://localhost:3000",
        "https://comdex-fawn.vercel.app",  # your frontend (Vercel)
    ]
else:
    raw = os.getenv("CORS_ALLOWED_ORIGINS", "")
    allow_origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not allow_origins:
        raise RuntimeError("CORS_ALLOWED_ORIGINS must be set in production.")

logger.info(f"✅ CORS allowed_origins = {allow_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 11) Import routers with consistent backend.routes prefix
from backend.routes.auth               import router as auth_router
from backend.routes.products           import router as products_router
from backend.routes.deal               import router as deal_router
from backend.routes.contracts          import router as contracts_router
from backend.routes.admin              import router as admin_router
from backend.routes.user               import router as user_router
from backend.routes.terminal           import router as terminal_router
from backend.routes.buyer              import router as buyer_router
from backend.routes.supplier           import router as supplier_router
from backend.routes.aion               import router as aion_router
from backend.routes.aion_goals         import router as aion_goals_router
from backend.routes.aion_plan          import router as aion_plan_router
from backend.routes.aion_dream         import router as aion_dream_router
from backend.routes.aion_gridworld     import router as aion_gridworld_router
from backend.routes.aion_game_dream    import router as aion_game_dream_router
from backend.routes.game               import router as game_router
from backend.routes.aion_game          import router as aion_game_router
from backend.routes.game_event         import router as game_event_router
from backend.routes.skill              import router as skill_router
from backend.routes.aion_strategy_plan import router as strategy_plan_router
from backend.routes import aion_prompt
from backend.routes import aion_command
from backend.routes import aion_suggest
from backend.routes import aion_core
from backend.routes import dna_chain
from backend.routes import dna_logs
from backend.routes import teleport_api
from backend.routes import aion_routes
from backend.routes import glyph_mutate
from backend.routes import ws_route
from backend.api.endpoints import submit_mutation
from backend.routes import aion_submit_mutation
from backend.routes import aion_score_mutation
from backend.routes import avatar_runtime
from backend.routes import aion_get_glyph_tick
from backend.api.aion.memory_trace import router as memory_trace_router
from backend.api.aion import get_memory_trace
from backend.api.aion import bundle_container  
from backend.routes import aion_glyph_trigger_log
from backend.modules.codex.codex_websocket_interface import start_codex_ws_server
from backend.routes import aion_tessaris_intents
from backend.routes import ws_codex_interface
from backend.routes import aion_synthesize_glyphs  # ✅ CORRECT
from backend.routes.ws import codex_ws
from backend.routes import codex_scroll

# ✅ WebSocket route
from backend.api import ws

# ── 12) Import standalone routers from backend.api (if used)
from backend.api.aion.status           import router as status_router
from backend.api.aion.grid_progress    import router as grid_progress_router
from backend.routes.aion_grid_progress import router as aion_grid_progress_router

# ── 13) Mount all routers under /api prefix
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
api.include_router(aion_goals_router)
api.include_router(aion_dream_router, prefix="/aion")
api.include_router(aion_gridworld_router)
api.include_router(aion_game_dream_router)
api.include_router(strategy_plan_router)

api.include_router(aion_game_router)
api.include_router(game_event_router)
api.include_router(game_router, prefix="/aion")
api.include_router(skill_router)

# ── 14) Include API router on main app
app.include_router(api)

# ── 15) Include standalone routers
app.include_router(aion_grid_progress_router)
app.include_router(status_router, prefix="/api")
app.include_router(grid_progress_router, prefix="/api")
app.include_router(aion_prompt.router, prefix="/api/aion")
app.include_router(aion_command.router, prefix="/api/aion")
app.include_router(aion_suggest.router)
app.include_router(aion_core.router, prefix="/api/aion")
app.include_router(dna_chain.router)
app.include_router(dna_logs.router)
app.include_router(ws.router)
app.include_router(teleport_api.router)
app.include_router(aion_routes.router)
app.include_router(glyph_mutate.router)
app.include_router(ws_route.router)
app.include_router(submit_mutation.router)
app.include_router(aion_submit_mutation.router)
app.include_router(aion_score_mutation.router)
app.include_router(avatar_runtime.router, prefix="/api")
app.include_router(aion_get_glyph_tick.router)
app.include_router(memory_trace_router, tags=["AION Traces"])
app.include_router(get_memory_trace.router)
app.include_router(bundle_container.router)
app.include_router(aion_glyph_trigger_log.router)
app.include_router(aion_tessaris_intents.router, prefix="/api")
app.include_router(ws_codex_interface.router)
app.include_router(aion_synthesize_glyphs.router)
app.include_router(codex_ws.router)
app.include_router(aion_tessaris_intents.router, prefix="/api")

# ── 16) Serve uploaded images
app.mount("/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images")

# ── 17) Serve static frontend if exists
if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="frontend")
else:
    logger.warning("⚠️ 'static' directory not found. Frontend must be built into /backend/static")

# ── 18) Legacy redirect for /products without trailing slash
@app.get("/products", include_in_schema=False)
def products_no_slash():
    return RedirectResponse(url="/products/", status_code=307)

# ── 19) Health check endpoint
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

# ── 20) Dream cycle endpoint for Cloud Scheduler
@app.post("/api/aion/run-dream")
async def run_dream_from_scheduler(request: Request):
    from backend.modules.skills.dream_core import DreamCore
    master_key = os.getenv("KEVIN_MASTER_KEY")
    auth_header = request.headers.get("X-Master-Key")

    if master_key and auth_header != master_key:
        raise HTTPException(status_code=403, detail="Unauthorized scheduler trigger")

    try:
        dream_core = DreamCore()
        result = dream_core.generate_dream()
        return {"status": "success", "dream": result or "No valid dream generated"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# ── 20b) List all .dc containers with status (loaded/unloaded)
@app.get("/api/aion/containers")
def list_available_containers():
    from backend.modules.consciousness.state_manager import STATE
    containers = STATE.list_containers_with_status()
    STATE.update_context("container_list", containers)
    return {"containers": containers}

# ── 21) Run via Uvicorn when executed directly
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=(ENV != "production"),
        forwarded_allow_ips="*",
        redirect_slashes=False,
    )

# ── 22) 💤 Start AION scheduler (best effort)
try:
    from backend.tasks.scheduler import start_scheduler
    start_scheduler()
except Exception as e:
    logger.warning(f"⚠️ Dream scheduler could not start: {e}")

# ── 23) Cloud Function: Stop Cloud Run if over budget
def shutdown_service(event, context):
    logger.info("🔔 Budget alert Pub/Sub triggered.")
    try:
        service = "comdex-api"
        region = "us-central1"

        result = subprocess.run([
            "gcloud", "run", "services", "update", service,
            "--region", region,
            "--platform", "managed",
            "--no-traffic"
        ], check=True, capture_output=True, text=True)

        logger.info("✅ Successfully disabled Cloud Run traffic.")
        logger.debug(result.stdout)
    except subprocess.CalledProcessError as e:
        logger.error("❌ Error disabling Cloud Run traffic.")
        logger.error(e.stderr)
    except Exception as e:
        logger.exception("❌ Unexpected error during Cloud Function shutdown.")

    for route in app.routes:
        print(f"[📡 ROUTE] {route.path} ({route.name})")