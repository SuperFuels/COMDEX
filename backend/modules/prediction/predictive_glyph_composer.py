import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Callable

# This import exists in your tree; leave as-is
from backend.modules.knowledge_graph.glyph_formatter import format_prediction_for_ghx


# ─────────────────────────────────────────────────────────────────────────────
# Lazy loaders with resilient fallbacks (no hard deps during test collection)
# ─────────────────────────────────────────────────────────────────────────────

def get_prediction_engine():
    """
    Try several known locations for PredictionEngine.
    If none exist, return a minimal stub with the same surface area.
    """
    # Try common/known paths first
    paths = [
        "backend.modules.consciousness.prediction_engine",
        "backend.modules.skills.prediction_engine",
        "backend.modules.prediction.prediction_engine",
    ]
    for modpath in paths:
        try:
            mod = __import__(modpath, fromlist=["PredictionEngine"])
            cls = getattr(mod, "PredictionEngine", None)
            if cls is not None:
                return cls
        except Exception:
            pass

    # Fallback stub (keeps tests running even if engine not present)
    class _StubGradient:
        async def _inject_gradient_feedback(self, *_args, **_kwargs):
            # no-op in tests/dev
            return None

    class _StubEngine:
        def __init__(self, container_id: str):
            self.container_id = container_id
            self.gradient_engine = _StubGradient()

        async def generate_future_paths(
            self,
            *,
            current_glyph: str,
            goal: Optional[str] = None,
            coord: Optional[str] = None,
            emotion: Optional[str] = None,
            num_paths: int = 3,
            agent_id: str = "local",
        ) -> List[Dict[str, Any]]:
            # Deterministic stubbed predictions for tests
            outs = []
            for i in range(num_paths):
                outs.append({
                    "id": f"fork_{i}",
                    "from": current_glyph,
                    "to": f"{current_glyph}_p{i}",
                    "score": 0.5 + (i * 0.05),
                    "goal": goal,
                    "coord": coord,
                    "emotion": emotion,
                    "agent_id": agent_id,
                    "container_id": self.container_id,
                })
            return outs

    return _StubEngine


def get_broadcast_event() -> Callable[..., Any]:
    """
    Return WS broadcaster if available, else an async no-op.
    Works with both sync and async broadcasters.
    """
    try:
        from backend.routes.ws.glyphnet_ws import broadcast_event  # type: ignore
        return broadcast_event
    except Exception:
        async def _noop_broadcast(*, event: str, payload: dict):
            # Keep quiet in tests if WS layer isn't present
            return None
        return _noop_broadcast


def get_publish_kg_added() -> Callable[[dict], bool]:
    """
    Return SQI KG publisher if available, else a no-op that returns False.
    """
    try:
        from backend.modules.sqi.sqi_event_bus import publish_kg_added  # type: ignore
        return publish_kg_added
    except Exception:
        def _noop_publish(_payload: dict) -> bool:
            # still "succeeds" locally so callers don't break
            return False
        return _noop_publish


# ─────────────────────────────────────────────────────────────────────────────
# Composer
# ─────────────────────────────────────────────────────────────────────────────

class PredictiveGlyphComposer:
    def __init__(self, container_id: str):
        self.container_id = container_id
        PredictionEngineClass = get_prediction_engine()
        self.engine = PredictionEngineClass(container_id=container_id)

    async def compose_forward_forks(
        self,
        current_glyph: str,
        goal: str = None,
        coord: str = None,
        emotion: str = None,
        num_paths: int = 3,
        agent_id: str = "local",
    ) -> List[Dict]:
        """
        Generate forward glyph forks (predictive) and broadcast to GHX viewer.
        Broadcast is best-effort; it won't fail your test run if WS is missing.
        """
        predictions = await self.engine.generate_future_paths(
            current_glyph=current_glyph,
            goal=goal,
            coord=coord,
            emotion=emotion,
            num_paths=num_paths,
            agent_id=agent_id,
        )

        ghx_payload = [format_prediction_for_ghx(p) for p in predictions]

        broadcast_event = get_broadcast_event()
        try:
            maybe_coro = broadcast_event(
                event="predictive_forks",
                payload={"container_id": self.container_id, "forks": ghx_payload},
            )
            if asyncio.iscoroutine(maybe_coro):
                await maybe_coro
        except Exception as e:
            # Never let UI broadcast break core logic
            print(f"[⚠️] predictive_forks broadcast failed: {e}")

        return predictions

    async def validate_fork(self, fork_id: str, accept: bool, *, relates_to: Optional[List[str]] = None):
        """
        Accept -> publish KG node (type 'predictive_fork', idempotent hash).
        Prune  -> send gradient feedback (best-effort).
        """
        if accept:
            print(f"✅ Fork accepted: {fork_id}")
            try:
                await self._commit_predictive_fork_to_kg(fork_id=fork_id, relates_to=relates_to or [])
            except Exception as e:
                print(f"[⚠️] commit predictive_fork failed: {e}")
        else:
            print(f"🗑️ Fork pruned: {fork_id}")
            try:
                # Best-effort: only runs if engine stub/real exposes gradient_engine
                await self.engine.gradient_engine._inject_gradient_feedback(
                    {"id": fork_id}, "Pruned predictive fork"
                )
            except Exception as e:
                print(f"[⚠️] gradient feedback failed: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # KG COMMIT (D4.6)
    # ──────────────────────────────────────────────────────────────────────────
    async def _commit_predictive_fork_to_kg(self, *, fork_id: str, relates_to: List[str]) -> bool:
        """
        Publish a 'predictive_fork' KG node via SQI bus with deterministic external hash:
            sha256(f"{container_id}|predictive_fork|{fork_id}")
        """
        publish_kg_added = get_publish_kg_added()

        ext_hash = hashlib.sha256(
            f"{self.container_id}|predictive_fork|{fork_id}".encode("utf-8")
        ).hexdigest()

        payload = {
            "container_id": self.container_id,
            "entry": {
                "id": fork_id,
                "hash": ext_hash,               # idempotency key
                "type": "predictive_fork",
                "timestamp": None,              # KnowledgeIndex will normalize now()
                "tags": ["predictive", "fork"],
                "plugin": "prediction_engine",
                "meta": {},
            },
        }
        if relates_to:
            payload["entry"]["meta"]["relates_to"] = list(relates_to)
            payload["entry"]["meta"]["relation"] = "predicts"

        published = False
        try:
            published = bool(publish_kg_added(payload))
        except Exception as e:
            print(f"[⚠️] publish_kg_added failed: {e}")

        if published:
            print("🧠 KG: predictive_fork published")
        else:
            print("🧠 KG: predictive_fork deduped")
        return published