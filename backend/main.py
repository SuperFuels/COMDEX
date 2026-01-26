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

# ✅ ADD THIS RIGHT HERE (before any backend imports)
from pathlib import Path

def _ensure_data_root():
    root = Path(ROOT_DIR)
    data = root / "data"
    target = root / ".runtime" / "COMDEX_MOVE" / "data"

    if data.is_symlink() and not data.exists():
        target.mkdir(parents=True, exist_ok=True)
        data.unlink()
        data.symlink_to(target)

    if not data.exists():
        data.mkdir(parents=True, exist_ok=True)

    (data / "personality").mkdir(parents=True, exist_ok=True)
    (data / "memory").mkdir(parents=True, exist_ok=True)
    (data / "goals").mkdir(parents=True, exist_ok=True)
    (data / "aion_field").mkdir(parents=True, exist_ok=True)
    (data / "knowledge").mkdir(parents=True, exist_ok=True)
    (data / "akg").mkdir(parents=True, exist_ok=True)
    (data / "telemetry").mkdir(parents=True, exist_ok=True)

_ensure_data_root()

# ✅ Force a single DATA_ROOT for everything (bridge + generators + producers)
from pathlib import Path

DATA_DIR = str((Path(ROOT_DIR) / "data").resolve())
os.environ.setdefault("TESSARIS_DATA_ROOT", DATA_DIR)
os.environ.setdefault("DATA_ROOT", DATA_DIR)

from fastapi import FastAPI, APIRouter, Request, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from sqlalchemy.exc import OperationalError
from backend.AION.trace_bus import trace_emit, subscribe
from backend.replay.reducer import ReplayReducer
from sqlalchemy import text
from contextlib import asynccontextmanager
import uvicorn
# ── Boot imports
from backend.modules.hexcore.boot_loader import load_boot_goals, preload_all_domain_packs, boot

from fastapi import Query  # add if not present
from backend.modules.teleport.wormhole_resolver import resolve_wormhole
# ── UCS template loader + optional Tesseract HQ
from backend.modules.dimensions.containers import container_loader as container_loader_mod
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

# ── Warm up Cloud SQL socket (make opt-in in dev; on in prod if you want)
from contextlib import asynccontextmanager

def _truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}

from contextlib import asynccontextmanager
import asyncio
import os

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup (single place) ---

    # ✅ Start GlyphOS registry rebuild in background (non-blocking, safe for tests)
    try:
        if (os.getenv("GLYPHOS_REBUILD_ON_STARTUP", "0") or "").strip().lower() in ("1", "true", "yes", "on"):
            from backend.modules.glyphos.glyph_instruction_set import maybe_update_glyph_registry
            maybe_update_glyph_registry()
    except Exception as e:
        logger.warning("[GlyphOS] maybe_update_glyph_registry skipped: %s", e)

    # chain_sim replay first, then async ingest
    try:
        await chain_sim_replay_startup()
    except Exception as e:
        if (os.getenv("CHAIN_SIM_REPLAY_STRICT", "0") or "").strip().lower() in ("1", "true", "yes", "on"):
            raise
        logger.warning("[chain_sim] replay startup failed (continuing): %s", e)

    try:
        asyncio.create_task(chain_sim_async_startup())
        await asyncio.sleep(0)
    except Exception as e:
        logger.warning("[chain_sim] async startup failed (continuing): %s", e)


    # ✅ consensus (PR2): start once, on the running loop
    if _truthy("GLYPHCHAIN_CONSENSUS_ENABLE", True):
        try:
            from backend.modules.consensus.engine import get_engine
            eng = get_engine()
            eng.start()
            logger.warning(
                "[consensus] started node_id=%s val_id=%s chain_id=%s base_url=%s",
                os.getenv("GLYPHCHAIN_NODE_ID"),
                os.getenv("GLYPHCHAIN_SELF_VAL_ID"),
                os.getenv("GLYPHCHAIN_CHAIN_ID"),
                os.getenv("GLYPHCHAIN_BASE_URL"),
            )
            app.state.consensus_engine = eng
            logger.info("[consensus] engine started")
        except Exception as e:
            logger.warning("[consensus] start failed (continuing): %s", e)

    # ✅ AION DEMO: Φ breathing tick (env-gated)
    # --- optional Φ breathe tick (demo) ---
    try:
        if _truthy("AION_DEMO_PHI_BREATHE", False):
            from backend.modules.aion_resonance.phi_reinforce import update_beliefs

            async def _phi_breathe_loop():
                while True:
                    try:
                        update_beliefs({})  # equilibrium pull
                    except Exception:
                        pass
                    await asyncio.sleep(float(os.getenv("AION_DEMO_PHI_BREATHE_S", "0.75")))

            asyncio.create_task(_phi_breathe_loop())
            logger.warning("[phi] breathe tick enabled")
    except Exception as e:
        logger.warning("[phi] breathe tick not started: %s", e)

    # ✅ START FUSION IN-PROCESS (PUT THIS HERE)
    if _truthy("AION_ENABLE_FUSION", True):
        try:
            from backend.modules.aion_cognition.tessaris_cognitive_fusion_kernel import main as fusion_main
            asyncio.create_task(fusion_main())
            logger.warning("[fusion] TCFK started in-process on :8005")
        except Exception as e:
            logger.warning("[fusion] failed to start: %s", e)

    yield

    # ✅ stop Φ breathing loop
    t = getattr(app.state, "_phi_breathe_task", None)
    if t is not None:
        t.cancel()

    # --- shutdown ---
    try:
        eng = getattr(app.state, "consensus_engine", None)
        if eng is not None:
            await eng.stop()
            logger.info("[consensus] engine stopped")
    except Exception:
        pass

    try:
        await chain_sim_async_shutdown()
    except Exception:
        pass

ENABLE_CLOUDSQL_WARMUP = _truthy("AION_ENABLE_CLOUDSQL_WARMUP", ENV == "production")
if ENABLE_CLOUDSQL_WARMUP:
    time.sleep(3)

# ── Logging setup
# ── Logging setup (env-controlled + silence high-frequency loops)
LOG_LEVEL = (os.getenv("AION_LOG_LEVEL") or "WARNING").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.WARNING),
    format="%(levelname)s:%(name)s:%(message)s",
)
logger = logging.getLogger("comdex")

# Quiet the known noisy loop loggers (does NOT disable the loops themselves)
NOISY_LOGGERS = [
    "backend.modules.skills.strategy_planner",
    "backend.modules.aion_language.resonant_memory_cache",
    "SQI Event",
    "heartbeat",
    "Θ",
]
for _name in NOISY_LOGGERS:
    logging.getLogger(_name).setLevel(logging.WARNING)

from fastapi import APIRouter, Request
# ... your other imports ...
from backend.modules.glyphnet.dedup import (
    canon_id_for_capsule,
    already_seen,
    mark_seen,
)

# ── Log DB URL
from backend.config import SQLALCHEMY_DATABASE_URL
logger.info(f"🔍 SQLALCHEMY_DATABASE_URL = {SQLALCHEMY_DATABASE_URL}")

# ── Import DB
from backend.database import engine, Base, get_db
import backend.models

# ── Auto-create tables
Base.metadata.create_all(bind=engine)
logger.info("✅ Database tables checked/created.")

# ── Instantiate FastAPI (ensure docs & schema are always visible)
# ── Instantiate FastAPI
app = FastAPI(
    title="COMDEX API",
    version="1.0.0",
    description="AION Cognitive Runtime",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)
app.router.redirect_slashes = False

@app.get("/health", tags=["Health"])
def health_check():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except OperationalError:
        return {"status": "error", "database": "not connected"}

@app.get("/api/health", include_in_schema=False)
def api_health_alias():
    return health_check()

try:
    from backend.modules.cognitive_fabric.ghx_telemetry_adapter import GHX_TELEMETRY
    GHX_TELEMETRY.start()
    logger.warning("[GHXTelemetry] started")
except Exception as e:
    logger.warning("[GHXTelemetry] not started: %s", e)

# ✅ AION Live Dashboard WS only
try:
    from backend.api.aion_dashboard import ws_router as aion_dashboard_ws_router

    app.include_router(aion_dashboard_ws_router)  # /ws/aion/dashboard
    logger.warning("[aion-dashboard] mounted: /ws/aion/dashboard")
except Exception as e:
    logger.warning("[aion-dashboard] not mounted: %s", e)


# ✅ AION Live Dashboard API + WS (REAL)  <<< PUT IT HERE
try:
    from backend.api.aion_dashboard_ws import router as aion_dashboard_router
    app.include_router(aion_dashboard_router)  # /api/aion/dashboard (+ actions + /api/aion/dashboard/ws)
    logger.warning("[aion-dashboard] mounted: /api/aion/dashboard (+ actions)")
except Exception as e:
    logger.warning("[aion-dashboard] API not mounted: %s", e)

# ✅ Mount AION Demo Bridge under a safe prefix (no route collisions)
try:
    from backend.modules.aion_demo import demo_bridge as aion_demo_bridge
    app.mount("/aion-demo", aion_demo_bridge.app)
    logger.warning("[aion-demo] mounted at /aion-demo")
except Exception as e:
    logger.warning("[aion-demo] not mounted: %s", e)

# ============================================================
# RQC Awareness WebSocket: /resonance
# Streams telemetry from: RQC_LEDGER_PATH (env/runtime/root)
# ============================================================

import os
import json
import asyncio
from datetime import datetime, UTC
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

# ---- ledger path (runtime + env override) ----
_env = (os.getenv("RQC_LEDGER_FILE") or "").strip()
if _env:
    RQC_LEDGER_PATH = Path(_env)
else:
    _runtime = Path(ROOT_DIR) / ".runtime" / "COMDEX_MOVE" / "data" / "ledger" / "rqc_live_telemetry.jsonl"
    _root = Path(ROOT_DIR) / "data" / "ledger" / "rqc_live_telemetry.jsonl"
    RQC_LEDGER_PATH = _runtime if _runtime.exists() else _root


def _ensure_rqc_ledger_file() -> None:
    RQC_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not RQC_LEDGER_PATH.exists():
        RQC_LEDGER_PATH.write_text("", encoding="utf-8")


def _parse_line(line: str) -> Optional[Dict[str, Any]]:
    s = (line or "").strip()
    if not s:
        return None
    try:
        entry = json.loads(s)
    except Exception:
        return None
    return entry if isinstance(entry, dict) else None


def _pick(entry: Dict[str, Any], *keys, default=None):
    for k in keys:
        v = entry.get(k)
        if v is not None:
            return v
    return default


def _has_any_metric(entry: Dict[str, Any]) -> bool:
    # accept both v2 and legacy keys; if none present, skip
    return any(
        entry.get(k) is not None
        for k in (
            "Φ", "phi", "Φ_mean", "phi_mean",
            "ψ", "psi", "ψ_mean", "psi_mean",
            "resonance_index", "coherence_energy", "coherence", "C",
            "κ", "kappa", "T", "T_mean",
        )
    )


def _to_event(entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not _has_any_metric(entry):
        return None

    Φ = _pick(entry, "Φ", "phi", "Φ_mean", "phi_mean", default=0.0) or 0.0
    ψ = _pick(entry, "ψ", "psi", "ψ_mean", "psi_mean", default=None)
    κ = _pick(entry, "κ", "kappa", default=0.0) or 0.0
    T = _pick(entry, "T", "T_mean", default=0.0) or 0.0

    coherence = _pick(entry, "coherence", "C", "coherence_energy", "resonance_index", default=0.0) or 0.0
    source = _pick(entry, "operator", "event", "source_pair", "source", default="?")

    try:
        Φf = float(Φ or 0.0)
    except Exception:
        Φf = 0.0
    try:
        Cf = float(coherence or 0.0)
    except Exception:
        Cf = 0.0

    return {
        "type": "telemetry",
        "timestamp": datetime.now(UTC).isoformat(),
        "ψ": ψ,
        "κ": float(κ) if κ is not None else 0.0,
        "T": float(T) if T is not None else 0.0,
        "Φ": Φf,
        "coherence": Cf,
        "source": source,
    }


@app.websocket("/resonance")
async def resonance_ws(websocket: WebSocket):
    """
    Cloud Run + FastAPI WS endpoint for the frontend:
      wss://<cloudrun-host>/resonance

    Tails the RQC telemetry JSONL ledger and pushes:
      - type=telemetry
      - type=awareness_pulse when Φ >= 0.999

    Also replays the last valid telemetry frame immediately on connect.
    """
    await websocket.accept()
    _ensure_rqc_ledger_file()

    # hello handshake
    try:
        await websocket.send_text(json.dumps({
            "type": "hello",
            "timestamp": datetime.now(UTC).isoformat(),
            "message": "Connected to Tessaris RQC WebSocket Bridge",
            "path": str(RQC_LEDGER_PATH),
        }, ensure_ascii=False))
    except Exception:
        return

    async def _send_event_and_pulse(event: Dict[str, Any]) -> None:
        await websocket.send_text(json.dumps(event, ensure_ascii=False))
        Φf = float(event.get("Φ") or 0.0)
        if Φf >= 0.999:
            pulse = {
                "type": "awareness_pulse",
                "timestamp": datetime.now(UTC).isoformat(),
                "message": f"🧠 Awareness resonance closure detected ({event.get('source', '?')})",
                "Φ": Φf,
                "coherence": float(event.get("coherence") or 0.0),
            }
            await websocket.send_text(json.dumps(pulse, ensure_ascii=False))

    # ------------------------------------------------------------
    # REPLAY: send the last valid telemetry line immediately
    # ------------------------------------------------------------
    try:
        last_event: Optional[Dict[str, Any]] = None
        if RQC_LEDGER_PATH.exists():
            with open(RQC_LEDGER_PATH, "rb") as fb:
                try:
                    fb.seek(-8192, os.SEEK_END)
                except OSError:
                    fb.seek(0)
                tail = fb.read().decode("utf-8", errors="ignore")

            for ln in reversed([x for x in tail.splitlines() if x.strip()]):
                ent = _parse_line(ln)
                if not ent:
                    continue
                ev = _to_event(ent)
                if ev:
                    last_event = ev
                    break

        if last_event:
            await _send_event_and_pulse(last_event)
    except Exception:
        # best-effort only
        pass

    # ------------------------------------------------------------
    # TAIL: seek end, then stream new lines
    # ------------------------------------------------------------
    try:
        with open(RQC_LEDGER_PATH, "r", encoding="utf-8") as f:
            f.seek(0, os.SEEK_END)

            while True:
                line = f.readline()
                if not line:
                    await asyncio.sleep(0.25)
                    continue

                entry = _parse_line(line)
                if not entry:
                    continue

                event = _to_event(entry)
                if not event:
                    continue

                await _send_event_and_pulse(event)

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await websocket.send_text(json.dumps({
                "type": "error",
                "timestamp": datetime.now(UTC).isoformat(),
                "message": "RQC resonance stream stopped",
                "error": str(e),
            }, ensure_ascii=False))
        except Exception:
            pass
        return
        
# 🧠 Attach AION Trace Bus subscriber -> Replay Reducer
_TRACE_SUBSCRIBED = False

# ============================================================
# Start GHX telemetry poller on app startup (feeds /resonance)
# ============================================================

@app.on_event("startup")
async def _start_ghx_telemetry():
    try:
        from backend.modules.cognitive_fabric.ghx_telemetry_adapter import GHX_TELEMETRY, LEDGER_PATH
        GHX_TELEMETRY.start()
        logger.warning("[ghx-telemetry] started (ledger=%s)", LEDGER_PATH)
    except Exception as e:
        logger.warning("[ghx-telemetry] NOT started: %s", e)

@app.on_event("shutdown")
async def _stop_ghx_telemetry():
    try:
        from backend.modules.cognitive_fabric.ghx_telemetry_adapter import GHX_TELEMETRY
        GHX_TELEMETRY.stop()
        logger.warning("[ghx-telemetry] stopped")
    except Exception as e:
        logger.warning("[ghx-telemetry] stop failed: %s", e)

def on_trace_event(event: dict):
    """
    Called whenever a cognition event is emitted.
    Used to feed ReplayReducer or live HUD updates.
    """
    try:
        ReplayReducer.journal_event(event)
    except Exception as e:
        print(f"[TraceBus] ⚠️ Replay journal failed: {e}")

# Guard against duplicate subscriptions in reload/worker edge-cases
if not _TRACE_SUBSCRIBED:
    subscribe(on_trace_event)
    _TRACE_SUBSCRIBED = True
    print("✅ AION Trace Bus attached to ReplayReducer")
else:
    print("💤 AION Trace Bus already attached - skipping duplicate subscribe()")

# ── Manually re-enable OpenAPI + ReDoc routes
from fastapi.openapi.docs import get_redoc_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

@app.get("/api/wormhole/resolve")
def api_resolve(name: str = Query(..., min_length=1)):
    return resolve_wormhole(name)

@app.get("/openapi.json", include_in_schema=False)
async def custom_openapi():
    """Serve raw OpenAPI schema for tools or /redoc."""
    return JSONResponse(get_openapi(title=app.title, version=app.version, routes=app.routes))

@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """Serve ReDoc interface manually."""
    return get_redoc_html(openapi_url="/openapi.json", title=f"{app.title} ReDoc")

# ── CORS
from fastapi.responses import Response

ENV = (os.getenv("ENV") or "development").lower()
ALLOW_ALL = _truthy("ALLOW_ALL_CORS", False)

# Feature flags to prevent “startup storms” in dev while keeping prod fully-on
ENABLE_SCHEDULER        = _truthy("AION_ENABLE_SCHEDULER", ENV == "production")
ENABLE_SEED_PATTERNS    = _truthy("AION_SEED_PATTERNS", True)
ENABLE_DEPRECATION_HOOK = _truthy("AION_ENABLE_DEPRECATION_HOOK", True)

ENABLE_HQCE             = _truthy("AION_ENABLE_HQCE", True)
ENABLE_GHX_TELEMETRY    = _truthy("AION_ENABLE_GHX_TELEMETRY", True)
ENABLE_DUAL_HEARTBEAT   = _truthy("AION_ENABLE_DUAL_HEARTBEAT", True)
ENABLE_BOOT_LOADER      = _truthy("AION_ENABLE_BOOT_LOADER", True)

if ALLOW_ALL:
    # Debug: open to any origin; cannot use credentials with "*"/fully-open regex.
    allow_origins = []
    allow_origin_regex = r"^https?://.*$"
    allow_credentials = False
else:
    # Allow common local dev hosts + your production domains
    # Allow common local dev hosts + prod site + vercel
    # Allow common local dev hosts + your deployed frontends
    allow_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://localhost:5173",
        "https://127.0.0.1:5173",

        # Vercel
        "https://comdex-fawn.vercel.app",
        "https://comdex-kevins-projects-e296122e.vercel.app",

        # Firebase / web.app (your screenshot)
        "https://swift-area-459514-d1.web.app",

        # Your custom domain
        "https://tessaris.ai",
        "https://www.tessaris.ai",
    ]

    # Codespaces + Vercel previews + web.app previews
    allow_origin_regex = (
        r"^https://[-a-z0-9]+-(5173|3000|8080)\.app\.github\.dev$"
        r"|^https://.*\.vercel\.app$"
        r"|^https://.*\.web\.app$"
    )

    allow_credentials = True

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=allow_origin_regex,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=86400,
    )

# Optional: explicit preflight for /api/glyphnet/tx (router is prefixed with /api/glyphnet)
from backend.modules.glyphnet.glyphnet_router import router as glyphnet_router
@glyphnet_router.options("/tx")
def _tx_preflight():
    return Response(status_code=204)


# ── Unified startup event
@app.on_event("startup")
async def startup_event():
    # Idempotency guard: prevents duplicate startup runs if event gets registered twice
    if getattr(app.state, "_startup_event_ran", False):
        logger.warning("[startup] startup_event already ran in this process; skipping duplicate call.")
        return
    app.state._startup_event_ran = True

    # Ensure HQ first so others can wormhole-link to it
    if ensure_tesseract_hub:
        try:
            ensure_tesseract_hub(...)
        except Exception as e:
            logger.warning(...)

    # ALWAYS seed patterns if enabled (independent)
    if ENABLE_SEED_PATTERNS and not getattr(app.state, "_seeded_patterns", False):
        try:
            from backend.modules.patterns.seed_patterns import seed_builtin_patterns
            seed_builtin_patterns()
            app.state._seeded_patterns = True
            logger.info("✅ Seeded built-in symbolic patterns.")
        except Exception as e:
            logger.warning(f"Failed to seed built-in patterns: {e}")

    # Preload UCS container templates (.dc.json) into runtime
    try:
        loaded = container_loader_mod.auto_load_all_templates()
        logger.info(f"[startup] Preloaded {len(loaded)} UCS containers.")
    except Exception as e:
        logger.warning(f"[startup] Failed to auto-load UCS containers: {e}")

    # Existing boot steps (guarded so dev can turn it down if needed)
    if ENABLE_BOOT_LOADER:
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
    else:
        logger.warning("[startup] Boot loader disabled (AION_ENABLE_BOOT_LOADER=0).")

    # ── Initialize Tessaris Quantum Quad Core + HQCE
    if ENABLE_HQCE:
        try:
            from backend.QQC.qqc_central_kernel import QuantumQuadCore
            from backend.modules.holograms.morphic_ledger import morphic_ledger
            global qqc_kernel
            qqc_kernel = QuantumQuadCore(container_id="hqce_main_runtime")
            logger.info("[HQCE] QuantumQuadCore initialized for main runtime.")
            morphic_ledger.append(
                {"psi": 0.0, "kappa": 0.0, "T": 0.0, "coherence": 0.0},
                observer="startup"
            )
            logger.info("[HQCE] Morphic Ledger initialized and ready.")
        except Exception as e:
            logger.warning(f"[HQCE] Initialization failed: {e}")
            qqc_kernel = None

        # ── Initialize Tessaris runtime
        try:
            from backend.modules.tessaris.tessaris_runtime import TessarisRuntime
            global tessaris_runtime
            tessaris_runtime = TessarisRuntime()
            logger.info("[HQCE] TessarisRuntime initialized.")
        except Exception as e:
            logger.warning(f"[HQCE] Tessaris runtime failed to initialize: {e}")
            tessaris_runtime = None

        # ── Start Symbolic-Holographic Convergence Engine (ψ-κ-T Learning Loop)
        try:
            from backend.modules.holograms.convergence_engine import ConvergenceEngine
            if qqc_kernel and tessaris_runtime:
                convergence_engine = ConvergenceEngine(qqc_kernel, tessaris_runtime)
                asyncio.create_task(convergence_engine.run())
                logger.info("[HQCE] ConvergenceEngine started (ψ-κ-T loop).")
            else:
                logger.warning("[HQCE] ConvergenceEngine skipped: dependencies missing.")
        except Exception as e:
            logger.warning(f"[HQCE] Failed to start ConvergenceEngine: {e}")

        # ── Initialize QuantumMorphicRuntime (ψ-κ-T Field Regulation)
        try:
            from backend.modules.holograms.quantum_morphic_runtime import QuantumMorphicRuntime

            # Example GHX packet + avatar placeholder - will be replaced by live feed later
            ghx_packet = {"container_id": "hqce_main_runtime", "phase": "init"}
            avatar_state = {"id": "AION_CORE", "state": "boot"}

            qmr = QuantumMorphicRuntime(ghx_packet, avatar_state)
            qmr_state = qmr.run()

            logger.info("[HQCE] QuantumMorphicRuntime executed successfully.")
            logger.debug(f"[HQCE] ψ-κ-T snapshot -> {qmr_state.get('psi_kappa_T')}")
        except Exception as e:
            logger.warning(f"[HQCE] QuantumMorphicRuntime failed to initialize: {e}")
    else:
        logger.warning("[startup] HQCE disabled (AION_ENABLE_HQCE=0).")

    # ── Start GHX Telemetry Adapter (CodexMetrics -> MorphicLedger -> GHXVisualizer)
    if ENABLE_GHX_TELEMETRY:
        try:
            from backend.modules.cognitive_fabric.ghx_telemetry_adapter import GHX_TELEMETRY
            GHX_TELEMETRY.start()
            logger.info("[GHXTelemetry] Adapter started - streaming Φ-ψ-κ-T metrics to GHXVisualizer.")
        except Exception as e:
            logger.warning(f"[GHXTelemetry] Adapter not started: {e}")
    else:
        logger.warning("[startup] GHX Telemetry disabled (AION_ENABLE_GHX_TELEMETRY=0).")

    # ── Start AION Dual Heartbeat Supervisor (Primary or Mirror)
    if ENABLE_DUAL_HEARTBEAT:
        import psutil

        def is_heartbeat_running(role="primary"):
            """Check if a specific AION Dual Heartbeat instance is already active."""
            for proc in psutil.process_iter(['cmdline']):
                cmd = proc.info['cmdline']
                if cmd and f"aion_dual_heartbeat.py" in " ".join(cmd) and f"--role {role}" in " ".join(cmd):
                    return True
            return False

        try:
            role = os.environ.get("AION_ROLE", "primary").lower()
            logger.info(f"💠 Detected AION node role: {role.upper()}")

            if not is_heartbeat_running(role):
                logger.info(f"💓 Launching AION Dual Heartbeat Supervisor ({role.upper()})...")
                subprocess.Popen(
                    ["python", "backend/AION/system/aion_dual_heartbeat.py", "--role", role],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                logger.info(f"✅ AION {role.capitalize()} Heartbeat running in background.")
            else:
                logger.info(f"💤 AION {role.capitalize()} Heartbeat already running - skipping launch.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to start AION Dual Heartbeat: {e}")
    else:
        logger.warning("[startup] Dual Heartbeat disabled (AION_ENABLE_DUAL_HEARTBEAT=0).")
        
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
from backend.RQC.src.photon_runtime.telemetry.ledger_feed import router as ledger_router
from backend.routes import aion_phi_stream
from backend.routes import aion_brain
from backend.api import ghx
from backend.routes import aion_lexicon
import backend.routes.aion_lexicon as aion_lexicon
from backend.routes import aion_lexicon
from backend.routes import aion_graph
from backend.routes import aion_memory
from backend.routes import aion_reinforce
from backend.modules.aion_resonance import aion_llm_bridge
from backend.modules.aion_resonance import symatic_bridge
from backend.modules.aion_resonance import thought_stream
from backend.modules.aion_resonance.thought_stream import thought_stream_router
from backend.routes.aion_synthesize_glyphs import router as synth_router
from backend.api.api_sci_memory import router as sci_memory_router
from backend.api.api_sci_ide import router as sci_ide_router
from backend.api.api_sci_commit import router as sci_commit_router
from backend.api import api_sci_commit_atom
from backend.api import api_sci_commit_atom as sci_commit_atom
from backend.api.sci_export_lean_atoms import router as sci_export_lean_atoms_router
from backend.api.api_sci_sync_proof_links import router as sci_sync_router  
from backend.api import photon_reverse_router
from backend.api.trace import router as trace_router
from backend.routes.atom_save import router as atom_save_router
from backend.api import replay
from backend.routes.replay_apply import router as replay_apply_router
from backend.routes.replay_ws import router as replay_ws_router
from backend.routes.replay_log import router as replay_log_router
from backend.routes.wormholes import router as wormholes_router
from backend.api.aion.container_api import router as aion_container_router
from backend.api import ghx
from backend.api.aion import prompt_api
from backend.api.aion import time_api
from backend.routers.gip_api import router as gip_api_router
from backend.api.photon_api import router as photon_api_router
from backend.api.photon_reverse import router as photon_reverse_router
from backend.modules.glyphnet.glyphnet_router import router as glyphnet_router
from backend.api.media_api import router as media_router
from backend.routes.name_service import name_router
from backend.api import rtc_api
from backend.routes.voice import router as voice_router
from backend.routes.voice import register_events as register_voice_events
from backend.api import ast_api, ast_hologram_api
from backend.modules.holo.holo_routes import router as holo_router
from backend.routes.holo_aion_routes import router as holo_aion_router
from backend.routes.holo_index_routes import router as holo_index_router
from backend.routes.crystal_routes import router as crystal_router
from backend.api.motif_compile_api import router as motif_compile_router
from backend.modules.mesh.mesh_reconcile_routes import router as mesh_router
from backend.modules.wallet.wallet_routes import router as wallet_router
from backend.modules.gma.gma_state_routes import router as gma_state_router
from backend.modules.photon_pay.photon_pay_routes import router as photon_pay_router
from backend.modules.identity.wave_identity_routes import router as wave_identity_router
# Floor control (PTT) lock manager
from backend.modules.glyphnet.lock_manager import LOCKS
from backend.modules.wallet.wallet_receipts_routes import router as wallet_receipts_router
from backend.modules.bonds import bond_state_routes
from backend.modules.glyph_bonds.glyph_bond_routes import router as glyph_bonds_router
from backend.modules.photon_savings.photon_savings_routes import router as photon_savings_router
from backend.modules.escrow.escrow_routes import router as escrow_router
from backend.modules.transactable_docs.transactable_doc_routes import router as transactable_docs_router
from backend.modules.p2p.router import router as p2p_router
from backend.routes.lean_snapshot_api import router as lean_snapshot_router
from backend.genome_engine.web_gx1_upload import build_fastapi_router
from backend.routes.sqi_demo import router as sqi_demo_router
from backend.api.photon_bridge import router as photon_router
from backend.modules.staking.staking_routes import router as staking_router
from backend.routes.glyphchain_perf_routes import router as glyphchain_perf_router
from backend.routes.aion_heartbeat_api import router as aion_heartbeat_router
# from backend.api.aion_dashboard import router as aion_dashboard_router
# from backend.api.aion_dashboard_ws import router as aion_dashboard_router
from backend.routes.aion_akg_demo_api import router as aion_akg_demo_router
from backend.api.aion_proof_of_life import router as aion_proof_of_life_router
from backend.routes.aion_mirror_api import router as aion_mirror_router
from backend.routes.aion_homeostasis_alias import router as aion_homeostasis_alias_router
from backend.routes.aion_cognitive_api import router as aion_cognitive_router
from backend.api.aion import router as aion_router
from backend.api.wirepack_api import router as wirepack_router
from backend.api.ws import router as ws_router
# from backend.modules.aion_demo.demo_bridge import router as aion_demo_router
from backend.modules.chain_sim.chain_sim_routes import (
    router as chain_sim_router,
    chain_sim_async_startup,
    chain_sim_async_shutdown,
    chain_sim_replay_startup,
)

# ===== Atomsheet / LightCone / QFC wiring =====
from backend.routes.dev import glyphwave_test_router        # dev-only routes (mounted elsewhere in your file)  # noqa: F401
from backend.api.workspace import workspace_router          # workspace API (mounted elsewhere in your file)    # noqa: F401
from backend.modules.patterns.seed_patterns import seed_builtin_patterns
from backend.api import api_sheets                          # exposes /api/sheets/list

# ── Optional routers (guarded so boot never breaks)
try:
    # ✅ Canonical AtomSheets router -> /api/atomsheet, /api/atomsheet/execute, /api/atomsheet/export
    from backend.routers.atomsheets import router as atomsheets_router
except Exception as e:
    atomsheets_router = None
    logger.warning("[atomsheets] not mounted: %s", e)

try:
    # 🔭 LightCone router -> /api/lightcone*
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
    # 🌐 QFC extras (stub HUD endpoints) -> /api/qfc_entanglement, /api/qfc_entangled
    from backend.api.api_qfc_extras import router as qfc_extras_router
except Exception as e:
    qfc_extras_router = None
    logger.warning("[qfc_extras] not mounted: %s", e)

# ── Mount routers (order: canonical -> optional -> legacy)
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

# ✅ HQCE WebSocket - live ψκT telemetry bridge
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


# ── 12) Import standalone routers from backend.api (if used)
from backend.api.aion.status           import router as status_router
from backend.api.aion.grid_progress    import router as grid_progress_router
from backend.routes.aion_grid_progress import router as aion_grid_progress_router

# ── 13) Mount all routers under /api prefix
api = APIRouter()

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
app.include_router(aion_reinforce.router, prefix="/api/aion")
app.include_router(aion_lexicon.router, prefix="/api/aion")

api.include_router(aion_game_router)
api.include_router(game_event_router)
api.include_router(game_router, prefix="/aion")
api.include_router(skill_router)
app.include_router(aion_memory.router, prefix="/api/aion")
api.include_router(wirepack_router, prefix="/wirepack", tags=["wirepack"])
app.include_router(api, prefix="/api")


# ── 15) Include standalone routers
app.include_router(aion_grid_progress_router)
app.include_router(status_router, prefix="/api")
app.include_router(grid_progress_router, prefix="/api")
app.include_router(aion_prompt.router, prefix="/api/aion")
app.include_router(aion_command.router, prefix="/api/aion")
app.include_router(aion_phi_stream.router, prefix="/api/aion")
app.include_router(aion_brain.router, prefix="/api/aion")
app.include_router(aion_lexicon.router, prefix="/api/aion")
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
app.include_router(lean_inject_api.router, prefix="/api")
app.include_router(ledger_router)
app.include_router(aion_lexicon.router, prefix="/api/aion")
app.include_router(aion_graph.router, prefix="/api/aion")
app.include_router(aion_llm_bridge.router, prefix="/api/aion")
app.include_router(symatic_bridge.router, prefix="/api/aion")
app.include_router(thought_stream_router)
app.include_router(synth_router)
app.include_router(sci_memory_router)
app.include_router(sci_ide_router)
app.include_router(sci_commit_router)
app.include_router(api_sci_commit_atom.router)
app.include_router(sci_commit_atom.router)
app.include_router(sci_export_lean_atoms_router)
app.include_router(sci_sync_router)
app.include_router(photon_reverse_router)
app.include_router(trace_router)
app.include_router(atom_save_router)
app.include_router(replay.router, prefix="/api")
app.include_router(replay_apply_router)
app.include_router(replay_ws_router)
app.include_router(replay_log_router)
app.include_router(wormholes_router)
app.include_router(aion_container_router, prefix="/api/aion")
app.include_router(ghx.router, prefix="/api", tags=["ghx"])  # => /api/ghx/stream
app.include_router(ghx.ws_router)                            # => /ws/ghx/{container_id}
app.include_router(prompt_api.router, prefix="/api/aion", tags=["AION Prompt"])
app.include_router(time_api.router, prefix="/api/aion", tags=["AION Time"])
app.include_router(gip_api_router)
app.include_router(photon_api_router)
app.include_router(photon_reverse_router)
app.include_router(glyphnet_router)
app.include_router(media_router)
app.include_router(name_router)
app.include_router(rtc_api.router)
app.include_router(voice_router, prefix="/api/voice")
app.include_router(photon_api_router)
app.include_router(ast_api.router, prefix="/api")
app.include_router(ast_hologram_api.router, prefix="/api")
# Generic Holo API – expose as /api/holo/*
app.include_router(holo_router, prefix="/api", tags=["holo"])
app.include_router(crystal_router)
app.include_router(motif_compile_router, prefix="/api")
app.include_router(mesh_router, prefix="/api", tags=["mesh"])
app.include_router(wallet_router, prefix="/api", tags=["wallet"])
# Holo index – expose as /api/holo/index/*
app.include_router(holo_index_router)
app.include_router(gma_state_router, prefix="/api")
app.include_router(photon_pay_router, prefix="/api")
app.include_router(wave_identity_router, prefix="/api")
app.include_router(wallet_receipts_router, prefix="/api")
app.include_router(bond_state_routes.router)
app.include_router(glyph_bonds_router, prefix="/api")
app.include_router(photon_savings_router, prefix="/api")
app.include_router(escrow_router, prefix="/api")
app.include_router(transactable_docs_router, prefix="/api")
app.include_router(chain_sim_router, prefix="/api")
app.include_router(staking_router, prefix="/api")
app.include_router(glyphchain_perf_router, prefix="/api")
app.include_router(lean_snapshot_router)
app.include_router(p2p_router, prefix="/api/p2p", tags=["p2p"])
app.include_router(build_fastapi_router(), prefix="/api")
app.include_router(sqi_demo_router)
app.include_router(photon_router)
app.include_router(aion_heartbeat_router, prefix="/api")
# AION Memory / Holo seeds API – expose as /api/holo/aion/*
app.include_router(holo_aion_router)
app.include_router(aion_proof_of_life_router)
app.include_router(aion_akg_demo_router)
app.include_router(aion_mirror_router)
app.include_router(aion_homeostasis_alias_router)
# app.include_router(aion_dashboard_router)
app.include_router(aion_cognitive_router)
app.include_router(aion_router, prefix="/api/aion", tags=["AION"])
app.include_router(ws_router) 
# app.include_router(aion_demo_router, prefix="/aion-demo")
register_voice_events(app)

# --- Floor-control lock sweeper (PTT) ---
# (Make sure you also have at the top of the file:)
# from backend.modules.glyphnet.lock_manager import LOCKS
@app.on_event("startup")
async def start_lock_sweeper():
    async def sweeper():
        import asyncio, time
        while True:
            freed = LOCKS.sweep()
            # Announce freed resources so UIs drop the "busy" badge
            for res, owner in freed:
                try:
                    # res looks like "voice:<topic>"
                    if res.startswith("voice:"):
                        topic = res.split("voice:", 1)[1]
                        LOCKS._emit(topic, {
                            "type": "entanglement_lock",
                            "resource": res,
                            "state": "free",
                            "owner": owner,
                            "ts": int(time.time() * 1000),
                        })
                except Exception:
                    # never let the sweeper die on a bad emit
                    pass
            await asyncio.sleep(1.0)
    asyncio.create_task(sweeper())

# =========================
# One-time guards (avoid duplicate startup work under reload / multi-import)
# =========================
_SEEDED_PATTERNS = False
_DEPRECATION_HOOK_INSTALLED = False
_SQI_REHYDRATED = False
_PHI_BALANCE_STARTED = False
_COG_THREADS_STARTED = False
_SCHEDULER_STARTED = False


# Seed patterns + deprecation hook (guarded)
if ENABLE_SEED_PATTERNS:
    try:
        if not _SEEDED_PATTERNS:
            seed_builtin_patterns()
            _SEEDED_PATTERNS = True
            logger.info("✅ seed_builtin_patterns() ran once.")
    except Exception as e:
        logger.warning(f"Failed to seed_builtin_patterns(): {e}")

if ENABLE_DEPRECATION_HOOK:
    try:
        if not _DEPRECATION_HOOK_INSTALLED:
            install_deprecation_hook()
            _DEPRECATION_HOOK_INSTALLED = True
            logger.info("✅ install_deprecation_hook() ran once.")
    except Exception as e:
        logger.warning(f"Failed to install_deprecation_hook(): {e}")


# Optional routers
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

# If not already mounted, also include your existing WS router:
try:
    from backend.modules.gip.gip_websocket_interface import router as gip_ws_router
    app.include_router(gip_ws_router)  # exposes /ws/gip/{cid} (assumed)
except Exception:
    pass

from backend.modules.sqi.sqi_container_registry import sqi_registry

@app.on_event("startup")
def _rehydrate_sqi_registry():
    global _SQI_REHYDRATED
    if _SQI_REHYDRATED:
        return
    _SQI_REHYDRATED = True
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

import asyncio
from backend.modules.aion_resonance.phi_learning import auto_balance_loop

# Gate this loop if you want to reduce background churn in dev:
ENABLE_PHI_BALANCE = _truthy("AION_ENABLE_PHI_BALANCE", ENV == "production")

@app.on_event("startup")
async def launch_phi_balance():
    global _PHI_BALANCE_STARTED
    if not ENABLE_PHI_BALANCE:
        logger.info("[startup] auto_balance_loop disabled (AION_ENABLE_PHI_BALANCE=0).")
        return
    if _PHI_BALANCE_STARTED:
        return
    _PHI_BALANCE_STARTED = True
    asyncio.create_task(auto_balance_loop())
    logger.info("[startup] auto_balance_loop started once.")

# ============================================================
# 🧠 AION Cognitive & Continuum Background Processes
# ============================================================
from threading import Thread
import time
from backend.modules.aion_resonance.cognitive_loop import run_cognitive_cycle
from backend.modules.aion_resonance.cognitive_continuum import run_continuum_cycle

ENABLE_COG_THREADS = _truthy("AION_ENABLE_COG_THREADS", ENV == "production")

def background_loop():
    """Continuously run AION's internal self-reflection loop."""
    while True:
        try:
            run_cognitive_cycle()
        except Exception as e:
            print(f"[AION Cognitive Loop Error] {e}")
        time.sleep(60)  # Reflect once per minute

def continuum_thread():
    """Run AION's full cognitive continuum cycle periodically."""
    while True:
        try:
            print("🧠 Running Cognitive Continuum Cycle...")
            result = run_continuum_cycle()
            print(f"Continuum result: {result.get('status')}")
        except Exception as e:
            print(f"[AION Continuum Error] {e}")
        time.sleep(180)  # every 3 minutes (adjust as desired)

@app.on_event("startup")
async def on_startup():
    """Launch all autonomous AION background processes."""
    global _COG_THREADS_STARTED
    if not ENABLE_COG_THREADS:
        print("🧠 Cognitive/Continuum threads disabled (AION_ENABLE_COG_THREADS=0).")
        return
    if _COG_THREADS_STARTED:
        return
    _COG_THREADS_STARTED = True
    print("🧠 Starting AION Reflection + Continuum threads...")
    Thread(target=background_loop, daemon=True).start()
    Thread(target=continuum_thread, daemon=True).start()

# ── Root route for quick health check / base URL
@app.get("/", include_in_schema=False)
async def root():
    return {"status": "ok", "message": "AION backend running"}

# --- WS proxy helpers ---
import json
import websockets
from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState


async def _ws_proxy(ws: WebSocket, target_url: str, name: str):
    await ws.accept()
    backend = None

    try:
        backend = await websockets.connect(target_url, ping_interval=None)

        async def client_to_backend():
            try:
                async for msg in ws.iter_text():
                    await backend.send(msg)
            except WebSocketDisconnect:
                pass
            except Exception:
                pass

        async def backend_to_client():
            try:
                async for msg in backend:
                    if ws.application_state == WebSocketState.CONNECTED:
                        await ws.send_text(msg)
                    else:
                        break
            except Exception:
                pass

        t1 = asyncio.create_task(client_to_backend())
        t2 = asyncio.create_task(backend_to_client())

        done, pending = await asyncio.wait({t1, t2}, return_when=asyncio.FIRST_COMPLETED)

        for t in pending:
            t.cancel()
        await asyncio.gather(*pending, return_exceptions=True)

    except Exception as e:
        if ws.application_state == WebSocketState.CONNECTED:
            try:
                await ws.send_text(json.dumps({"type": "proxy_error", "proxy": name, "error": str(e)}))
            except Exception:
                pass
        print(f"❌ {name} proxy error: {e}")

    finally:
        try:
            if backend is not None:
                await backend.close()
        except Exception:
            pass

        if ws.application_state == WebSocketState.CONNECTED:
            try:
                await ws.close()
            except Exception:
                pass


# --- WS proxy endpoints (single-port frontends hit these) ---

@app.websocket("/api/ws/symatics")
async def proxy_symatics(ws: WebSocket):
    await _ws_proxy(ws, "ws://127.0.0.1:8001/ws/symatics", "Symatics")


@app.websocket("/api/ws/analytics")
async def proxy_analytics(ws: WebSocket):
    await _ws_proxy(ws, "ws://127.0.0.1:8002/ws/analytics", "Analytics")


@app.websocket("/api/ws/fusion")
async def proxy_fusion(ws: WebSocket):
    await _ws_proxy(ws, "ws://127.0.0.1:8005/ws/fusion", "Fusion")


@app.websocket("/api/ws/rqfs_feedback")
async def proxy_rqfs_feedback(ws: WebSocket):
    await _ws_proxy(ws, "ws://127.0.0.1:8006/ws/rqfs_feedback", "RQFS")


@app.websocket("/api/ws/control")
async def proxy_control(ws: WebSocket):
    await _ws_proxy(ws, "ws://127.0.0.1:8004/ws/control", "Control")

# ── 21) Run via Uvicorn when executed directly
if __name__ == "__main__":
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        reload=(ENV != "production"),
        forwarded_allow_ips="*",
    )

# ── 22) 💤 Start AION scheduler (best effort) — move to startup + guard (prevents double-starts)
@app.on_event("startup")
def _start_aion_scheduler():
    global _SCHEDULER_STARTED
    if not ENABLE_SCHEDULER:
        logger.info("[startup] Scheduler disabled (AION_ENABLE_SCHEDULER=0).")
        return
    if _SCHEDULER_STARTED:
        return
    _SCHEDULER_STARTED = True
    try:
        from backend.tasks.scheduler import start_scheduler
        start_scheduler()
        logger.info("✅ AION scheduler started once.")
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

def verify_snapshot(steps: int = 1024, dt_ms: int = 16, spec_version: str = "v1") -> dict:
    snap = {"steps": int(steps), "dt_ms": int(dt_ms)}
    git_rev = get_git_rev()
    versions = get_tool_versions()

    proof_hash_hex = compute_proof_hash(snap, spec_version, git_rev)
    lf = write_snapshot_lean(snap, spec_version, proof_hash_hex)

    ok, out, err, rc, elapsed_ms = run_lean(lf)

    cert = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "kind": "lean_snapshot_verify",
        "ok": ok,
        "returncode": rc,
        "elapsed_ms": elapsed_ms,
        "spec_version": spec_version,
        "git_rev": git_rev,
        "proof_hash": proof_hash_hex,
        "proof_hash_short": short_hash_hex(proof_hash_hex, 16),
        "lean_file": str(lf),
        "imports": IMPORTS,
        "params": snap,
        "versions": versions,
        "stdout_tail": tail_lines(out, 40),
        "stderr_tail": tail_lines(err, 40),
        "axioms_used": ["Tessaris.Symatics.Axioms"],
        "deps": {"workspace": str(WS)},
    }

    append_ledger(cert)
    return cert