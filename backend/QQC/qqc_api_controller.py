# ==========================================================
#  Tessaris • Quantum Quad Core (QQC) API Controller
#  FastAPI orchestration layer for remote control & telemetry.
# ==========================================================

import asyncio
import time
import logging
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import JSONResponse

from backend.modules.config import (
    QQC_CONFIG_PATH,
    QQC_MODE,
    QQC_AUTO_START,
    load_qqc_config,
)
from backend.QQC.qqc_kernel_v2 import QuantumQuadCore

# ----------------------------------------------------------
# Logging setup
# ----------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------
# FastAPI app
# ----------------------------------------------------------
app = FastAPI(title="Tessaris Quantum Quad Core API", version="2.0")

# ----------------------------------------------------------
# Kernel instance (singleton)
# ----------------------------------------------------------
qqc_kernel: QuantumQuadCore | None = None


async def boot_kernel():
    """Initialize and start the QQC runtime."""
    global qqc_kernel
    if qqc_kernel:
        return {"status": "already_running"}

    logger.info(f"[QQC API] Loading configuration from {QQC_CONFIG_PATH}")
    cfg = load_qqc_config()
    qqc_kernel = QuantumQuadCore()

    mode = QQC_MODE or cfg.get("boot", {}).get("mode", "resonant")
    await qqc_kernel.boot(mode=mode)

    logger.info(f"[QQC API] Kernel booted in mode='{mode}'")
    return {"status": "booted", "mode": mode, "session": qqc_kernel.session_id}


async def shutdown_kernel():
    """Gracefully shut down the kernel."""
    global qqc_kernel
    if not qqc_kernel:
        return {"status": "not_running"}
    await qqc_kernel.shutdown()
    sid = qqc_kernel.session_id
    qqc_kernel = None
    logger.info(f"[QQC API] Kernel '{sid}' shutdown complete.")
    return {"status": "stopped", "session": sid}


# ----------------------------------------------------------
# Routes
# ----------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    if QQC_AUTO_START:
        await boot_kernel()


@app.get("/qqc/status")
async def get_status():
    if not qqc_kernel:
        return JSONResponse({"status": "offline", "detail": "Kernel not active"})
    return JSONResponse({
        "status": "online",
        "session_id": qqc_kernel.session_id,
        "summary": qqc_kernel.last_summary or {},
    })


@app.post("/qqc/start")
async def start_kernel(background_tasks: BackgroundTasks):
    if qqc_kernel:
        return {"status": "already_running"}
    background_tasks.add_task(boot_kernel)
    return {"status": "starting"}


@app.post("/qqc/stop")
async def stop_kernel(background_tasks: BackgroundTasks):
    if not qqc_kernel:
        return {"status": "not_running"}
    background_tasks.add_task(shutdown_kernel)
    return {"status": "stopping"}


@app.post("/qqc/run_cycle")
async def run_cycle(beam: dict):
    """Manually trigger a single cycle with optional beam data."""
    if not qqc_kernel:
        return JSONResponse({"status": "error", "message": "Kernel not active"}, status_code=400)

    result = await qqc_kernel.run_cycle(beam)
    return JSONResponse({"status": "ok", "result": result})


@app.get("/qqc/telemetry")
async def get_telemetry():
    """Return live coherence / entropy metrics."""
    if not qqc_kernel:
        return JSONResponse({"status": "offline"})
    return JSONResponse({
        "timestamp": time.time(),
        "summary": qqc_kernel.last_summary or {},
    })


@app.post("/qqc/teleport")
async def teleport_state(source: str, target: str):
    """Simulate portal/teleportation operation."""
    if not qqc_kernel:
        return JSONResponse({"status": "error", "message": "Kernel not active"}, status_code=400)
    result = await qqc_kernel.teleport_state(source, target)
    return JSONResponse({"status": "ok", "result": result})


# ----------------------------------------------------------
# Local dev harness
# ----------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    logger.info("🌐 Starting Tessaris Quantum Quad Core API server...")
    uvicorn.run(app, host="0.0.0.0", port=9050)