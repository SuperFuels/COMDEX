# backend/glyphchain_test_asgi.py
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

logger = logging.getLogger("glyphchain-test")

def _truthy(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # chain_sim replay + async ingest (tests rely on this)
    from backend.modules.chain_sim.chain_sim_routes import (
        chain_sim_async_startup,
        chain_sim_async_shutdown,
        chain_sim_replay_startup,
    )

    try:
        await chain_sim_replay_startup()
    except Exception as e:
        logger.warning("[chain_sim] replay startup failed (continuing): %s", e)

    try:
        asyncio.create_task(chain_sim_async_startup())
        await asyncio.sleep(0)
    except Exception as e:
        logger.warning("[chain_sim] async startup failed (continuing): %s", e)

    # consensus on (tests rely on this)
    if _truthy("GLYPHCHAIN_CONSENSUS_ENABLE", True):
        try:
            from backend.modules.consensus.engine import get_engine
            eng = get_engine()
            eng.start()
            app.state.consensus_engine = eng
        except Exception as e:
            logger.warning("[consensus] start failed (continuing): %s", e)

    yield

    try:
        eng = getattr(app.state, "consensus_engine", None)
        if eng is not None:
            await eng.stop()
    except Exception:
        pass

    try:
        await chain_sim_async_shutdown()
    except Exception:
        pass


app = FastAPI(lifespan=lifespan)

# ONLY mount what consensus tests need
from backend.modules.p2p.router import router as p2p_router
from backend.modules.chain_sim.chain_sim_routes import router as chain_sim_router

app.include_router(p2p_router, prefix="/api/p2p", tags=["p2p"])
app.include_router(chain_sim_router, prefix="/api", tags=["chain_sim"])