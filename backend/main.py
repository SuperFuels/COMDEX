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

from fastapi import FastAPI, APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from sqlalchemy.exc import OperationalError
from sqlalchemy import text
import uvicorn
# ── Boot imports
from backend.modules.hexcore.boot_loader import load_boot_goals, preload_all_domain_packs, boot

# ── UCS template loader + optional Tesseract HQ
from backend.modules.dimensions.universal_container_system import container_loader
try:
    from backend.modules.dimensions.containers.tesseract_hub import ensure_tesseract_hub
except Exception:
    ensure_tesseract_hub = None

# DNA Switch
from backend.modules.dna_chain.dna_switch import DNA_SWITCH
DNA_SWITCH.register(__file__)

# ── Ensure uploads folder exists
os.makedirs("uploaded_images", exist_ok=True)

# ── Load .env.local if not production
ENV = os.getenv("ENV", "").lower()
if ENV != "production":
    from dotenv import load_dotenv
    if os.path.exists(".env.local"):
        load_dotenv(".env.local")
    else:
        print("⚠️ Warning: .env.local not found.")

# ── Warm up Cloud SQL socket
time.sleep(3)

# ── Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("comdex")

# ── Log DB URL
from backend.config import SQLALCHEMY_DATABASE_URL
logger.info(f"🔍 SQLALCHEMY_DATABASE_URL = {SQLALCHEMY_DATABASE_URL}")

# ── Import DB
from backend.database import engine, Base, get_db
import backend.models

# ── Auto-create tables
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables checked/created.")

# ── Instantiate FastAPI
app = FastAPI(title="COMDEX API", version="1.0.0", description="AION")
app.router.redirect_slashes = False

# ── CORS
if ENV != "production":
    allow_origins = [
        "http://localhost:3000",
        "https://comdex-fawn.vercel.app",
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

# ── Unified startup event
@app.on_event("startup")
async def startup_event():
    # Ensure HQ first so others can wormhole-link to it
    if ensure_tesseract_hub:
        try:
            ensure_tesseract_hub(hub_id="tesseract_hq", name="Tesseract HQ", size=8)
            logger.info("[startup] Tesseract HQ ensured (tesseract_hq).")
        except Exception as e:
            logger.warning(f"[startup] Failed to ensure Tesseract HQ: {e}")
            # ✅ Seed pattern registry once at startup
        try:
            from backend.modules.patterns.seed_patterns import seed_builtin_patterns
            seed_builtin_patterns()
            logger.info("✅ Seeded built-in symbolic patterns.")
        except Exception as e:
            logger.warning(f"Failed to seed built-in patterns: {e}")

    # Preload UCS container templates (.dc.json) into runtime
    try:
        loaded = container_loader.auto_load_all_templates()
        logger.info(f"[startup] Preloaded {len(loaded)} UCS containers.")
    except Exception as e:
        logger.warning(f"[startup] Failed to auto-load UCS containers: {e}")

    # Existing boot steps
    try:
        load_boot_goals()
    except Exception as e:
        logger.warning(f"boot: load_boot_goals failed: {e}")
    try:
        preload_all_domain_packs()
    except Exception as e:
        logger.warning(f"boot: preload_all_domain_packs failed: {e}")
    try:
        boot()
    except Exception as e:
        logger.warning(f"boot() failed: {e}")

# ── Routers
from backend.routes.auth import router as auth_router
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
from backend.routes import aion_synthesize_glyphs
from backend.routes import codex_scroll
from backend.routes.ws import qglyph_ws
from backend.api.aion import codex_playground
from backend.routes.ws import glyphnet_ws
from backend.modules.gip.gip_adapter_http import router as gip_http_router
from backend.routes.glyphnet_command_api import router as glyphnet_command_router
from backend.api.aion import container_api
from backend.api.aion import vault_api
from backend.api import glyph_socket_api
from backend.routes.ws import glyph_socket_ws
from backend.routes.ws import ghx_ws
from backend.routes import replay_api
from backend.routes import sqi_drift
from backend.routes import sqi_kg
from backend.routes import ucs_api
from backend.routes import runtime as runtime_routes
from backend.routes import sqi as sqi_routes
from backend.routes.ghx_control import router as ghx_control_router
from backend.routes import sqi_edit
from backend.routes import sqi_packs
from backend.routes.ghx_encode import router as ghx_encode_router
from backend.routes.sqi_route import router as sqi_route_router
from backend.routes.sqi_kernels import router as sqi_kernels_router
from backend.routes.sqi_relink import router as sqi_relink_router
from backend.api import teleport_handler
from backend.routes.teleport_api import router as teleport_api
from backend.api import symbolic_ingestion_api
from backend.api.symbolic_ingestion_api import router as symbolic_router
from backend.routes import codex_mutate
from backend.api import symbol_tree
from backend.api import qfc_api
from backend.api import symbolic_tree_api
from backend.routes.api_collapse_trace import router as collapse_trace_router
from backend.routes import lean_inject_api
from backend.utils.deprecation_logger import install_deprecation_hook

# ===== Atomsheet / LightCone / QFC wiring =====
from backend.routes.dev import glyphwave_test_router        # dev-only routes (mounted elsewhere in your file)  # noqa: F401
from backend.api.workspace import workspace_router          # workspace API (mounted elsewhere in your file)    # noqa: F401
from backend.modules.patterns.seed_patterns import seed_builtin_patterns
from backend.api import api_sheets                          # exposes /api/sheets/list

# ── Optional routers (guarded so boot never breaks)
try:
    # ✅ Canonical AtomSheets router → /api/atomsheet, /api/atomsheet/execute, /api/atomsheet/export
    from backend.routers.atomsheets import router as atomsheets_router
except Exception as e:
    atomsheets_router = None
    logger.warning("[atomsheets] not mounted: %s", e)

try:
    # 🔭 LightCone router → /api/lightcone*
    from backend.api.api_lightcone import router as lightcone_router
except Exception as e:
    lightcone_router = None
    logger.warning("[lightcone] not mounted: %s", e)

try:
    # 🧪 Legacy AtomSheet API (no /api prefix). Mount under /legacy to avoid collisions.
    import backend.api.api_atomsheet as legacy_atomsheet_mod
except Exception as e:
    legacy_atomsheet_mod = None
    logger.warning("[legacy atomsheet] not mounted: %s", e)

try:
    # 🌐 QFC extras (stub HUD endpoints) → /api/qfc_entanglement, /api/qfc_entangled
    from backend.api.api_qfc_extras import router as qfc_extras_router
except Exception as e:
    qfc_extras_router = None
    logger.warning("[qfc_extras] not mounted: %s", e)

# ── Mount routers (order: canonical → optional → legacy)
if atomsheets_router:
    app.include_router(atomsheets_router)                  # /api/atomsheet*

if lightcone_router:
    app.include_router(lightcone_router)                   # /api/lightcone*

if qfc_extras_router:
    app.include_router(qfc_extras_router)                  # /api/qfc_* (stubbed safe responses)

# Keep legacy API but clearly namespaced to avoid confusion/collisions
if legacy_atomsheet_mod:
    app.include_router(legacy_atomsheet_mod.router, prefix="/legacy")  # /legacy/atomsheet

# Sheets listing utility already registers absolute /api/sheets/list; do NOT add a prefix here.
app.include_router(api_sheets.router)

# WebSocket routes module import (handlers mounted elsewhere)
from backend.api import ws  # noqa: F401

# ✅ Mount QGlyph WebSocket
from backend.routes.ws.qglyph_ws import start_qglyph_ws

@app.websocket("/ws/qglyph")
async def qglyph_socket(websocket: WebSocket):
    await start_qglyph_ws(websocket)

# ✅ HQCE WebSocket — live ψκT telemetry bridge
from backend.modules.holograms.hqce_ws_bridge import hqce_ws_bridge
from fastapi import WebSocketDisconnect  # ensure imported above or here
import asyncio

@app.websocket("/ws/hqce")
async def ws_hqce_endpoint(websocket: WebSocket):
    await hqce_ws_bridge.connect(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # keep connection alive
    except WebSocketDisconnect:
        await hqce_ws_bridge.disconnect(websocket)

# ✅ Optional: mount HQCE dashboard REST routes
from backend.tools.hqce_dashboard_routes import router as dashboard_router
app.include_router(dashboard_router, prefix="/dashboard")

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
app.include_router(codex_playground.router)
app.include_router(glyphnet_ws.router)
app.include_router(gip_http_router, prefix="/api")
app.include_router(glyphnet_command_router)
app.include_router(container_api.router, prefix="/api/aion")
app.include_router(vault_api.router, prefix="/api/aion")  # if vault_api exists
app.include_router(glyph_socket_api.router, prefix="/api")
app.include_router(glyph_socket_ws.router)
app.include_router(ghx_ws.router)
app.include_router(replay_api.router)
app.include_router(sqi_drift.router)
app.include_router(sqi_kg.router)
app.include_router(ucs_api.router)
app.include_router(auth_router, prefix="/auth")
app.include_router(qglyph_ws.router)
app.include_router(runtime_routes.router)
app.include_router(sqi_routes.router)
app.include_router(ghx_control_router)
app.include_router(sqi_edit.router)
app.include_router(sqi_packs.router)
app.include_router(ghx_encode_router)
app.include_router(sqi_route_router)
app.include_router(sqi_kernels_router)
app.include_router(sqi_relink_router)
app.include_router(teleport_handler.router)
app.include_router(teleport_api) 
app.include_router(symbolic_ingestion_api.router)
app.include_router(symbolic_router)
app.include_router(codex_mutate.router)
app.include_router(symbol_tree.router)
app.include_router(qfc_api.router)
app.include_router(symbolic_tree_api.router)
app.include_router(collapse_trace_router)
app.include_router(glyphwave_test_router.router)
app.include_router(workspace_router)
app.include_router(api_sheets.router)
app.include_router(qfc_extras_router)
app.include_router(lean_inject_api.router, prefix="/api")
seed_builtin_patterns()
install_deprecation_hook()

if atomsheets_router:
    app.include_router(atomsheets_router)
if lightcone_router:
    app.include_router(lightcone_router)

# ── 16) Serve uploaded images
app.mount("/uploaded_images", StaticFiles(directory="uploaded_images"), name="uploaded_images")

# ── 17) Serve static frontend if exists
if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="frontend")
else:
    logger.warning("⚠️ 'static' directory not found. Frontend must be built into /backend/static")


from backend.modules.sqi.sqi_container_registry import sqi_registry

@app.on_event("startup")
def _rehydrate_sqi_registry():
    try:
        n = sqi_registry.rehydrate_from_ucs()
        print(f"[SQI] Rehydrated {n} containers from UCS into registry.")
    except Exception as e:
        print(f"[SQI] Registry rehydrate skipped: {e}")

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

@app.websocket("/websocket/symbol_tree/{container_id}")
async def websocket_endpoint(websocket: WebSocket, container_id: str):
    await stream_symbol_tree(websocket, container_id)

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